"""
The Mini App checkout endpoint and the order records it writes.

What matters here: only a verified, finished customer can order; prices come
from the database, never from the client; and the order survives even when
Telegram notifications fail (test settings blank the token on purpose).
"""

from __future__ import annotations

from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase, override_settings

from apps.orders.models import Order
from apps.products.models import Product
from apps.users.models import TelegramUser
from tests.test_webapp_lessons import TOKEN, make_init_data


@override_settings(BOT_TOKEN=TOKEN)
class WebAppOrderTests(TestCase):
    def setUp(self):
        # A real token is needed for the initData HMAC, which would otherwise
        # let the notification step reach out to api.telegram.org for real.
        patcher = patch("core.telegram.call", return_value={})
        self.telegram_call = patcher.start()
        self.addCleanup(patcher.stop)
        # The per-customer order rate limit lives in the (process-wide) cache,
        # so without this the later tests in this class trip it.
        cache.clear()
        self.user = TelegramUser.objects.create(
            telegram_id=7001,
            full_name="Mijoz",
            phone_number="+998901234567",
            language="uz",
            registration_status=TelegramUser.RegistrationStatus.COMPLETED,
        )
        self.serum = Product.objects.create(name="Serum", current_price=250_000)
        self.cream = Product.objects.create(name="Krem", current_price=100_000)

    def _post(self, **overrides):
        payload = {
            "init_data": make_init_data(7001),
            "delivery": "yandex",
            "address": "Toshkent, Chilonzor 5, 12-uy",
            "items": [
                {"id": self.serum.pk, "qty": 2},
                {"id": self.cream.pk, "qty": 1},
            ],
        }
        payload.update(overrides)
        return self.client.post(
            "/api/v1/webapp/orders/", payload, content_type="application/json"
        )

    def test_creates_the_order_with_database_prices(self):
        response = self._post()
        self.assertEqual(response.status_code, 200, response.content)
        order = Order.objects.get(pk=response.json()["order_id"])
        self.assertEqual(order.user, self.user)
        # 2×250 000 + 1×100 000 goods, plus the Yandex delivery fee.
        self.assertEqual(order.delivery_fee, 25_000)
        self.assertEqual(order.total, 625_000)
        self.assertEqual(order.status, Order.Status.NEW)
        self.assertEqual(order.phone_number, "+998901234567")
        names = sorted(i.product_name for i in order.items.all())
        self.assertEqual(names, ["Krem", "Serum"])

    def test_client_supplied_prices_are_ignored(self):
        response = self._post(
            items=[{"id": self.serum.pk, "qty": 1, "price": 1}],
        )
        self.assertEqual(response.status_code, 200)
        order = Order.objects.get(pk=response.json()["order_id"])
        self.assertEqual(order.total, 250_000 + 25_000)

    def test_the_bts_fee_applies_to_a_regional_order(self):
        response = self._post(delivery="bts", items=[{"id": self.serum.pk, "qty": 1}])
        order = Order.objects.get(pk=response.json()["order_id"])
        self.assertEqual(order.delivery_fee, 35_000)
        self.assertEqual(order.total, 285_000)

    def test_an_unpriced_product_cannot_be_ordered(self):
        # Otherwise the customer would be billed for delivery alone.
        self.serum.current_price = 0
        self.serum.save()
        response = self._post(items=[{"id": self.serum.pk, "qty": 1}])
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "unpriced")
        self.assertEqual(Order.objects.count(), 0)

    def test_forged_init_data_is_rejected(self):
        response = self._post(init_data=make_init_data(7001, token="999:OTHER"))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Order.objects.count(), 0)

    def test_unregistered_customer_cannot_order(self):
        response = self._post(init_data=make_init_data(7999))
        self.assertEqual(response.status_code, 403)

    def test_short_address_is_rejected(self):
        response = self._post(address="ok")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "address")

    def test_unknown_delivery_is_rejected(self):
        response = self._post(delivery="teleport")
        self.assertEqual(response.status_code, 400)

    def test_a_yandex_order_asks_for_a_location_pin(self):
        # No provider token in this class, so the ask is not deferred behind
        # an invoice — it goes out with the confirmation.
        self._post(delivery="yandex")
        texts = [
            c.args[1].get("text", "")
            for c in self.telegram_call.call_args_list
            if c.args[0] == "sendMessage"
        ]
        self.assertTrue(any("Joylashuv" in t or "joylashuv" in t for t in texts))

    def test_a_bts_order_does_not_ask_for_one(self):
        # BTS carries to a branch, so a pin buys nothing.
        self._post(delivery="bts")
        texts = [
            c.args[1].get("text", "")
            for c in self.telegram_call.call_args_list
            if c.args[0] == "sendMessage"
        ]
        self.assertFalse(any("joylashuv" in t.lower() for t in texts))

    def test_inactive_products_do_not_make_an_order(self):
        self.serum.is_active = False
        self.serum.save()
        self.cream.is_active = False
        self.cream.save()
        response = self._post()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "items")

    def test_explicit_phone_overrides_the_profile_one(self):
        response = self._post(phone="+998 93 765 43 21")
        self.assertEqual(response.status_code, 200)
        order = Order.objects.get(pk=response.json()["order_id"])
        self.assertEqual(order.phone_number, "+998937654321")

    def test_the_staff_group_and_the_customer_are_both_notified(self):
        from apps.support.models import SupportSettings

        settings_obj = SupportSettings.get()
        settings_obj.group_chat_id = -100123
        settings_obj.save()

        # BTS, so there is no location ask on top of the two notifications.
        self._post(delivery="bts")

        chat_ids = [
            c.args[1]["chat_id"]
            for c in self.telegram_call.call_args_list
            if c.args[0] == "sendMessage"
        ]
        self.assertEqual(chat_ids, [-100123, 7001])

    def test_a_telegram_outage_still_leaves_the_order_saved(self):
        from core.telegram import TelegramError

        self.telegram_call.side_effect = TelegramError("bot was blocked")
        response = self._post()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Order.objects.count(), 1)

    def test_a_burst_of_orders_is_rate_limited(self):
        for _ in range(5):
            self.assertEqual(self._post().status_code, 200)
        self.assertEqual(self._post().status_code, 429)


class OrdersAdminApiTests(TestCase):
    def test_anonymous_is_rejected(self):
        response = self.client.get("/api/v1/orders/")
        self.assertIn(response.status_code, (401, 403))
