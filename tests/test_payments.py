"""
Card payments through Telegram's invoice flow.

The whole feature hangs off one switch: with no PAYMENT_PROVIDER_TOKEN nothing
may promise a card payment we cannot take, so the first tests here pin that
"off" behaviour as hard as the "on" one.
"""

from __future__ import annotations

from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase, override_settings

from apps.orders.models import Order
from apps.orders.payments import (
    CURRENCY_MULTIPLIER,
    MAX_INVOICE_SOM,
    MIN_INVOICE_SOM,
    can_invoice,
    mark_paid,
    order_id_from_payload,
    payments_enabled,
    send_invoice,
)
from apps.products.models import Product
from apps.users.models import TelegramUser
from tests.test_webapp_lessons import TOKEN, make_init_data

PROVIDER = "398062629:TEST:secret"


class PayloadTests(TestCase):
    def test_round_trips_an_order_id(self):
        self.assertEqual(order_id_from_payload("order:42"), 42)

    def test_rejects_a_payload_that_is_not_ours(self):
        self.assertIsNone(order_id_from_payload("subscription:42"))
        self.assertIsNone(order_id_from_payload("order:abc"))
        self.assertIsNone(order_id_from_payload(""))


class SwitchTests(TestCase):
    @override_settings(PAYMENT_PROVIDER_TOKEN="")
    def test_off_without_a_token(self):
        self.assertFalse(payments_enabled())

    @override_settings(PAYMENT_PROVIDER_TOKEN="   ")
    def test_whitespace_is_not_a_token(self):
        self.assertFalse(payments_enabled())

    @override_settings(PAYMENT_PROVIDER_TOKEN=PROVIDER)
    def test_on_with_a_token(self):
        self.assertTrue(payments_enabled())


@override_settings(PAYMENT_PROVIDER_TOKEN=PROVIDER)
class InvoiceableAmountTests(TestCase):
    """Telegram refuses UZS invoices outside the band it publishes."""

    def test_an_ordinary_basket_is_invoiceable(self):
        self.assertTrue(can_invoice(250_000))

    def test_an_unpriced_basket_is_not(self):
        # Every product added without a price yet totals zero.
        self.assertFalse(can_invoice(0))

    def test_the_band_edges_hold(self):
        self.assertTrue(can_invoice(MIN_INVOICE_SOM))
        self.assertTrue(can_invoice(MAX_INVOICE_SOM))
        self.assertFalse(can_invoice(MIN_INVOICE_SOM - 1))
        self.assertFalse(can_invoice(MAX_INVOICE_SOM + 1))

    @override_settings(PAYMENT_PROVIDER_TOKEN="")
    def test_a_fine_amount_is_still_refused_without_a_provider(self):
        self.assertFalse(can_invoice(250_000))


class OrderPaymentTestCase(TestCase):
    def setUp(self):
        patcher = patch("core.telegram.call", return_value={})
        self.telegram_call = patcher.start()
        self.addCleanup(patcher.stop)
        cache.clear()
        self.user = TelegramUser.objects.create(
            telegram_id=8001,
            full_name="Mijoz",
            phone_number="+998901234567",
            language="uz",
            registration_status=TelegramUser.RegistrationStatus.COMPLETED,
        )
        self.product = Product.objects.create(name="Serum", current_price=250_000)

    def _order(self, **kwargs) -> Order:
        order = Order.objects.create(
            user=self.user,
            customer_name="Mijoz",
            phone_number="+998901234567",
            delivery_method=Order.Delivery.YANDEX,
            address="Toshkent, Chilonzor 5",
            total=250_000,
            **kwargs,
        )
        order.items.create(
            product=self.product, product_name="Serum", price=250_000, quantity=1
        )
        return order

    def _invoice_calls(self) -> list[dict]:
        return [
            c.args[1] for c in self.telegram_call.call_args_list
            if c.args[0] == "sendInvoice"
        ]


@override_settings(BOT_TOKEN=TOKEN, PAYMENT_PROVIDER_TOKEN=PROVIDER)
class SendInvoiceTests(OrderPaymentTestCase):
    def test_amounts_are_scaled_to_the_smallest_currency_unit(self):
        order = self._order()
        self.assertTrue(send_invoice(order))

        payload = self._invoice_calls()[0]
        self.assertEqual(payload["chat_id"], 8001)
        self.assertEqual(payload["currency"], "UZS")
        self.assertEqual(payload["payload"], f"order:{order.pk}")
        self.assertEqual(
            payload["prices"][0]["amount"], 250_000 * CURRENCY_MULTIPLIER
        )

    def test_the_order_moves_to_awaiting_payment(self):
        order = self._order()
        send_invoice(order)
        order.refresh_from_db()
        self.assertEqual(order.payment_status, Order.PaymentStatus.PENDING)

    def test_a_telegram_failure_leaves_the_order_unpaid_and_reports_it(self):
        from core.telegram import TelegramError

        self.telegram_call.side_effect = TelegramError("PAYMENT_PROVIDER_INVALID")
        order = self._order()
        self.assertFalse(send_invoice(order))
        order.refresh_from_db()
        self.assertEqual(order.payment_status, Order.PaymentStatus.UNPAID)

    @override_settings(PAYMENT_PROVIDER_TOKEN="")
    def test_no_invoice_is_sent_without_a_token(self):
        order = self._order()
        self.assertFalse(send_invoice(order))
        self.assertEqual(self._invoice_calls(), [])


class MarkPaidTests(OrderPaymentTestCase):
    def test_records_the_charge_id_and_time(self):
        order = self._order(payment_status=Order.PaymentStatus.PENDING)
        settled = mark_paid(order.pk, "charge-123")
        self.assertIsNotNone(settled)
        self.assertEqual(settled.payment_status, Order.PaymentStatus.PAID)
        self.assertEqual(settled.provider_charge_id, "charge-123")
        self.assertIsNotNone(settled.paid_at)

    def test_a_redelivered_payment_settles_only_once(self):
        order = self._order(payment_status=Order.PaymentStatus.PENDING)
        self.assertIsNotNone(mark_paid(order.pk, "charge-123"))
        # Telegram can send the same successful_payment again — the second
        # call must report "already done" rather than re-announcing it.
        self.assertIsNone(mark_paid(order.pk, "charge-123"))

    def test_an_unknown_order_is_not_invented(self):
        self.assertIsNone(mark_paid(999999, "charge-123"))


@override_settings(BOT_TOKEN=TOKEN)
class CheckoutPaymentChoiceTests(OrderPaymentTestCase):
    def _checkout(self, payment: str):
        return self.client.post(
            "/api/v1/webapp/orders/",
            {
                "init_data": make_init_data(8001),
                "delivery": "yandex",
                "address": "Toshkent, Chilonzor 5, 12-uy",
                "payment": payment,
                "items": [{"id": self.product.pk, "qty": 1}],
            },
            content_type="application/json",
        )

    def _set_cash(self, enabled: bool) -> None:
        from apps.bot_settings.models import GlobalSettings

        conf = GlobalSettings.get()
        conf.cash_on_delivery_enabled = enabled
        conf.save()

    @override_settings(PAYMENT_PROVIDER_TOKEN=PROVIDER)
    def test_every_order_is_invoiced_by_card(self):
        response = self._checkout("online")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["payment"], "online")
        self.assertTrue(response.json()["invoice_sent"])
        self.assertEqual(len(self._invoice_calls()), 1)

    @override_settings(PAYMENT_PROVIDER_TOKEN=PROVIDER)
    def test_the_client_cannot_opt_out_of_paying(self):
        # The app no longer offers a choice; a hand-rolled request asking for
        # cash must not get goods shipped against a promise to pay later.
        response = self._checkout("cod")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["payment"], "online")
        self.assertEqual(len(self._invoice_calls()), 1)

    @override_settings(PAYMENT_PROVIDER_TOKEN="")
    def test_a_broken_provider_leaves_the_order_on_cash(self):
        # Losing the token must not shut the shop; with cash on (the default)
        # the order is taken as «yetkazishda naqd».
        response = self._checkout("online")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["payment"], "cod")
        self.assertFalse(response.json()["invoice_sent"])
        self.assertEqual(self._invoice_calls(), [])
        order = Order.objects.get(pk=response.json()["order_id"])
        self.assertEqual(order.payment_method, Order.PaymentMethod.COD)

    @override_settings(PAYMENT_PROVIDER_TOKEN=PROVIDER)
    def test_an_uninvoiceable_basket_is_rejected_when_cash_is_off(self):
        # A provider is configured but the amount is outside the band Telegram
        # will invoice, and the shop has switched cash off — nothing can take
        # the order, so it is refused rather than booked against no method.
        self._set_cash(False)
        self.product.current_price = MAX_INVOICE_SOM + 1
        self.product.save()

        response = self._checkout("online")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "amount")
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(self._invoice_calls(), [])

    @override_settings(PAYMENT_PROVIDER_TOKEN=PROVIDER)
    def test_an_uninvoiceable_basket_falls_back_to_cash_when_cash_is_on(self):
        # Cash on delivery has no amount limit, so an order Telegram would not
        # invoice is still taken — as cash — while the shop leaves cash on.
        self.product.current_price = MAX_INVOICE_SOM + 1
        self.product.save()

        response = self._checkout("online")

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["payment"], "cod")
        self.assertFalse(response.json()["invoice_sent"])
        order = Order.objects.get(pk=response.json()["order_id"])
        self.assertEqual(order.payment_method, Order.PaymentMethod.COD)

    @override_settings(PAYMENT_PROVIDER_TOKEN="")
    def test_nothing_takes_the_order_when_cash_is_off_and_no_provider(self):
        # Both methods unavailable: the Mini App must not be able to place an
        # order at all.
        self._set_cash(False)

        response = self._checkout("online")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "no_payment_method")
        self.assertEqual(Order.objects.count(), 0)


class CatalogFlagTests(TestCase):
    @override_settings(PAYMENT_PROVIDER_TOKEN="")
    def test_catalog_reports_payments_off(self):
        response = self.client.get("/api/v1/webapp/catalog/")
        self.assertFalse(response.json()["payments_enabled"])

    @override_settings(PAYMENT_PROVIDER_TOKEN=PROVIDER)
    def test_catalog_reports_payments_on(self):
        response = self.client.get("/api/v1/webapp/catalog/")
        self.assertTrue(response.json()["payments_enabled"])

    def test_catalog_reports_cash_enabled_by_default(self):
        response = self.client.get("/api/v1/webapp/catalog/")
        self.assertTrue(response.json()["cash_enabled"])

    def test_catalog_reports_cash_disabled_when_switched_off(self):
        from apps.bot_settings.models import GlobalSettings

        conf = GlobalSettings.get()
        conf.cash_on_delivery_enabled = False
        conf.save()

        response = self.client.get("/api/v1/webapp/catalog/")
        self.assertFalse(response.json()["cash_enabled"])
