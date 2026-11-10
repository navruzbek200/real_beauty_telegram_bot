from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase, SimpleTestCase, override_settings
from django.utils import timezone

from apps.billz.client import BillzClient, BillzError
from apps.billz.models import BillzProduct, BillzPurchase, BillzSyncState
from apps.billz.services import import_purchase, deliver_pending, sync_billz
from apps.campaigns.models import AutoMessage
from apps.products.models import Product, ProductTutorialStep
from apps.users.models import TelegramUser, UserProduct
from tasks.scheduled import dispatch_auto_messages


def row(**changes):
    value = {
        'created_at': timezone.localtime().strftime('%Y-%m-%d %H:%M:%S'),
        'shop_id': 'shop-1', 'order_id': 'sale-1', 'order_number': '101',
        'order_type': 'Продажа', 'customer_id': 'client-1',
        'customer_name': 'Test Customer', 'phone_numbers': ['998901234567'],
        'product_id': 'item-1', 'product_name': 'Serum',
        'product_barcode': '12345', 'product_sku': 'SERUM',
        'sold_measurement_value': 1, 'returned_measurement_value': 0,
    }
    value.update(changes)
    return value


class ImportTests(TestCase):
    def setUp(self):
        self.started = timezone.now() - timedelta(hours=1)
        self.product = Product.objects.create(name='Serum')

    def test_replayed_report_creates_one_customer_purchase_and_entitlement(self):
        purchase = import_purchase(row(), started_at=self.started)
        import_purchase(row(), started_at=self.started)
        self.assertEqual(BillzPurchase.objects.count(), 1)
        self.assertEqual(TelegramUser.objects.count(), 1)
        self.assertEqual(UserProduct.objects.count(), 1)
        self.assertEqual(purchase.user.phone_number, '+998901234567')
        self.assertEqual(purchase.item.product, self.product)
        self.assertFalse(UserProduct.objects.get().auto_messages_enabled)

    def test_repeat_real_sales_remain_separate(self):
        import_purchase(row(), started_at=self.started)
        import_purchase(row(order_id='sale-2'), started_at=self.started)
        self.assertEqual(BillzPurchase.objects.count(), 2)
        self.assertEqual(UserProduct.objects.count(), 1)

    def test_history_uses_actual_company_local_date_and_stays_silent_on_replay(self):
        purchase = import_purchase(row(created_at='2026-01-10 12:30:00'), started_at=self.started)
        self.assertTrue(purchase.historical)
        self.assertEqual(timezone.localtime(purchase.purchased_at).hour, 12)
        import_purchase(row(created_at='2026-01-10 12:30:00'), started_at=timezone.now()-timedelta(days=900))
        purchase.refresh_from_db()
        self.assertTrue(purchase.historical)

    def test_only_verified_exact_full_phone_can_receive_imported_history(self):
        unverified = TelegramUser.objects.create(telegram_id=10, phone_number='+998901234567')
        other_country = TelegramUser.objects.create(telegram_id=11, phone_number='+996901234567', phone_verified=True)
        purchase = import_purchase(row(), started_at=self.started)
        self.assertEqual(purchase.user_id, unverified.pk)
        self.assertNotEqual(purchase.user_id,other_country.pk)
        self.assertFalse(UserProduct.objects.filter(user=unverified).exists())
        verified = TelegramUser.objects.create(telegram_id=12, phone_number='+998901234568', phone_verified=True)
        second = import_purchase(row(order_id='sale-2', phone_numbers=['+998 90 123 45 68']), started_at=self.started)
        self.assertEqual(second.user, verified)

    def test_unknown_product_and_missing_phone_are_preserved_without_guesses(self):
        purchase = import_purchase(row(product_name='Unknown', phone_numbers=[]), started_at=self.started)
        self.assertIsNone(purchase.user)
        self.assertIsNone(purchase.item.product)
        self.assertEqual(purchase.product_name, 'Unknown')
        self.assertEqual(UserProduct.objects.count(), 0)

    def test_returned_or_unknown_transaction_cannot_trigger_messages(self):
        purchase = import_purchase(row(), started_at=self.started)
        import_purchase(row(returned_measurement_value=1), started_at=self.started)
        purchase.refresh_from_db()
        self.assertFalse(purchase.active)
        unknown = import_purchase(row(order_id='sale-2', order_type='Unknown'), started_at=self.started)
        self.assertFalse(unknown.active)

    def test_invalid_row_cannot_silently_advance_sync(self):
        with self.assertRaises(BillzError):
            import_purchase(row(created_at='broken'), started_at=self.started)

    def test_late_mapping_grants_history_and_fully_returned_sale_revokes_imported_access(self):
        from apps.billz.services import reconcile_entitlements
        purchase = import_purchase(row(product_name='Different name'), started_at=self.started)
        self.assertEqual(UserProduct.objects.count(), 0)
        purchase.item.product = self.product
        purchase.item.save()
        reconcile_entitlements()
        self.assertEqual(UserProduct.objects.count(), 1)
        import_purchase(row(product_name='Different name', returned_measurement_value=1), started_at=self.started)
        reconcile_entitlements()
        self.assertEqual(UserProduct.objects.count(), 0)


@override_settings(BOT_TOKEN='mocked-telegram-only')
class DeliveryTests(TestCase):
    def setUp(self):
        AutoMessage.objects.all().delete()
        self.product = Product.objects.create(name='Serum')
        self.user = TelegramUser.objects.create(telegram_id=20, full_name='Test', phone_number='+998901234567', phone_verified=True, registration_status='completed')
        self.started = timezone.now()-timedelta(hours=1)

    def guide(self):
        return ProductTutorialStep.objects.create(product=self.product, order=1, button_label='Use', video_file_id='test-file')

    @override_settings(BILLZ_SECRET_TOKEN='test-only',BOT_TOKEN='test-only')
    @patch('tasks.billz.sync_billz',side_effect=BillzError('deletion check unavailable'))
    @patch('core.telegram.call',return_value={'message_id':1})
    def test_failed_sync_does_not_mark_a_pending_intro_as_delivered(self, call, sync):
        from tasks.billz import poll_billz
        self.guide()
        purchase=import_purchase(row(),started_at=self.started)
        poll_billz()
        purchase.refresh_from_db()
        self.assertIsNone(purchase.intro_sent_at)

    @patch('apps.users.admin.TelegramUserAdmin._send_purchase_message', return_value=True)
    def test_waits_for_guide_then_delivers_once(self, send):
        import_purchase(row(), started_at=self.started)
        self.assertEqual(deliver_pending(), 0)
        self.guide()
        self.assertEqual(deliver_pending(), 1)
        self.assertEqual(deliver_pending(), 0)
        send.assert_called_once()

    @patch('apps.users.admin.TelegramUserAdmin._send_purchase_message', return_value=True)
    def test_historical_and_unlinked_purchases_are_silent(self, send):
        self.guide()
        import_purchase(row(created_at='2026-01-01 12:00:00'), started_at=self.started)
        import_purchase(row(order_id='sale-2', phone_numbers=['+998901234569']), started_at=self.started)
        self.assertEqual(deliver_pending(), 0)
        send.assert_not_called()

    @patch('apps.users.admin.TelegramUserAdmin._send_purchase_message', return_value=True)
    def test_retry_and_later_contact_link_deliver_existing_pending_purchase(self, send):
        self.guide()
        purchase = import_purchase(row(phone_numbers=['+998901234569']), started_at=self.started)
        user = purchase.user
        user.telegram_id = 21
        user.phone_verified = True
        user.registration_status = 'completed'
        user.save()
        send.return_value = False
        self.assertEqual(deliver_pending(), 0)
        send.return_value = True
        self.assertEqual(deliver_pending(), 1)

    def test_new_repeat_sales_get_independent_reminder_anchors_and_history_never_does(self):
        self.guide()
        AutoMessage.objects.create(name='Check', trigger='after_purchase', delay_value=1, delay_unit='minute', body='Hello {{ product.name }}')
        created = timezone.localtime(timezone.now()-timedelta(minutes=2)).strftime('%Y-%m-%d %H:%M:%S')
        first = import_purchase(row(created_at=created), started_at=self.started)
        BillzPurchase.objects.filter(pk=first.pk).update(intro_sent_at=timezone.now())
        from apps.billz.receipts import finalize_receipts
        finalize_receipts([first.receipt_id],timezone.now())
        with patch('tasks.scheduled.send_message'):
            self.assertEqual(dispatch_auto_messages(), 1)
        second = import_purchase(row(order_id='sale-2', created_at=created), started_at=self.started)
        BillzPurchase.objects.filter(pk=second.pk).update(intro_sent_at=timezone.now())
        import_purchase(row(order_id='old', created_at=created), started_at=timezone.now())
        finalize_receipts([second.receipt_id],timezone.now())
        with patch('tasks.scheduled.send_message'):
            self.assertEqual(dispatch_auto_messages(), 1)
            self.assertEqual(dispatch_auto_messages(), 0)

    def test_overlapping_delivery_sends_one_intro(self):
        self.guide()
        import_purchase(row(), started_at=self.started)
        recipients = []
        def send(user, product, **kwargs):
            recipients.append(user.pk)
            if len(recipients) == 1:
                deliver_pending()
            return True
        with patch('apps.users.admin.TelegramUserAdmin._send_purchase_message', side_effect=send):
            deliver_pending()
        self.assertEqual(recipients, [self.user.pk])

    def test_corrected_receipt_keeps_one_row_and_delivers_to_new_recipient(self):
        from apps.billz.services import reconcile_entitlements
        self.guide()
        first = import_purchase(row(), started_at=self.started)
        BillzPurchase.objects.filter(pk=first.pk).update(intro_sent_at=timezone.now())
        target = TelegramUser.objects.create(telegram_id=29, phone_number='+998901234569', phone_verified=True, registration_status='completed')
        corrected = import_purchase(row(customer_id='corrected-client', phone_numbers=['+998901234569']), started_at=self.started)
        reconcile_entitlements()
        self.assertEqual(BillzPurchase.objects.count(), 1)
        self.assertEqual(corrected.user, target)
        self.assertIsNone(corrected.intro_sent_at)
        self.assertFalse(UserProduct.objects.filter(user=self.user, auto_messages_enabled=False).exists())
        with patch('apps.users.admin.TelegramUserAdmin._send_purchase_message', return_value=True) as send:
            self.assertEqual(deliver_pending(), 1)
        self.assertEqual(send.call_args.args[0], target)

    def test_verifying_a_different_number_detaches_old_phone_purchases(self):
        from apps.billz.services import verify_phone
        self.guide()
        purchase = import_purchase(row(), started_at=self.started)
        verify_phone(self.user.pk, '+998901234569')
        purchase.refresh_from_db()
        self.assertNotEqual(purchase.user_id, self.user.pk)
        with patch('apps.users.admin.TelegramUserAdmin._send_purchase_message', return_value=True) as send:
            self.assertEqual(deliver_pending(), 0)
        send.assert_not_called()


class PhoneVerificationTests(TestCase):
    def test_own_contact_moves_imported_history_to_existing_account(self):
        from apps.billz.services import verify_phone
        purchase = import_purchase(row(), started_at=timezone.now())
        old_card = purchase.user_id
        account = TelegramUser.objects.create(telegram_id=22)
        verify_phone(account.pk, '+998901234567')
        purchase.refresh_from_db()
        account.refresh_from_db()
        self.assertEqual(purchase.user, account)
        self.assertTrue(account.phone_verified)
        self.assertFalse(TelegramUser.objects.filter(pk=old_card).exists())

    def test_unverified_text_or_username_cannot_claim_card_with_billz_history(self):
        from bot.services.user_service import _find_preregistered
        purchase = import_purchase(row(), started_at=timezone.now())
        purchase.user.username = 'someone'
        purchase.user.save()
        self.assertIsNone(_find_preregistered(username='someone', phone_number='+998901234567'))

    def test_staff_phone_edit_revokes_previous_verification(self):
        account = TelegramUser.objects.create(telegram_id=23, phone_number='+998901234567', phone_verified=True)
        account.phone_number = '+998901234568'
        account.save()
        account.refresh_from_db()
        self.assertFalse(account.phone_verified)

    def test_verified_contact_cannot_claim_imported_card_using_another_username_or_country_tail(self):
        from bot.services.user_service import _find_preregistered
        purchase = import_purchase(row(), started_at=timezone.now())
        purchase.user.username = 'someone'
        purchase.user.save()
        self.assertIsNone(_find_preregistered(username='someone', phone_number='+996901234567', verified_phone=True))


class PanelTests(TestCase):
    def test_customer_detail_exposes_immutable_history_even_without_product_mapping(self):
        from django.contrib.auth.models import User
        from rest_framework.test import APIClient
        purchase = import_purchase(row(product_name='Unknown'), started_at=timezone.now())
        client = APIClient()
        client.force_authenticate(User.objects.create_superuser('owner', password='test'))
        response = client.get(f'/api/v1/customers/{purchase.user_id}/')
        self.assertEqual(response.status_code, 200)
        history = response.json()['billz_purchases']
        self.assertEqual(history[0]['product_name'], 'Unknown')
        self.assertFalse(history[0]['has_tutorial'])


@override_settings(BILLZ_SECRET_TOKEN='test-only', BILLZ_HISTORY_START='2026-01-01')
class SyncTests(TestCase):
    def setUp(self):
        cache.clear()

    @patch('apps.billz.services.BillzClient')
    def test_all_shops_are_polled_and_failure_does_not_advance_cursor(self, client):
        client.return_value.shops.return_value = [{'id':'s1'}, {'id':'s2'}]
        client.return_value.purchases.return_value = iter([])
        sync_billz()
        self.assertEqual({call.args[0] for call in client.return_value.purchases.call_args_list}, {'s1','s2'})
        state = BillzSyncState.objects.get(pk=1)
        old = state.last_synced_at
        client.return_value.purchases.side_effect = BillzError('unavailable')
        with self.assertRaises(BillzError): sync_billz()
        state.refresh_from_db()
        self.assertEqual(state.last_synced_at, old)

    @patch('apps.billz.services.BillzClient')
    def test_initial_sync_uses_small_daily_windows_for_slow_reports(self, client):
        client.return_value.shops.return_value = [{'id':'s1'}]
        def daily_only(shop, start, end):
            if start != end:
                raise BillzError('slow large report')
            return iter([])
        client.return_value.purchases.side_effect = daily_only
        result = sync_billz()
        self.assertIn('rows', result)
        self.assertIsNotNone(BillzSyncState.objects.get(pk=1).last_synced_at)


@override_settings(BILLZ_SECRET_TOKEN='test-only')
class CancelledSaleTests(TestCase):
    def setUp(self):
        cache.clear()
        self.now=timezone.now()
        self.product=Product.objects.create(name='Serum')
        self.purchase=import_purchase(row(),started_at=self.now-timedelta(hours=1))
        self.other_line=import_purchase(row(product_id='item-2',product_name='Second product'),started_at=self.now)
        self.state=BillzSyncState.objects.create(pk=1,last_synced_at=self.now,history_complete=True,history_checked_on=timezone.localdate())

    def fake_client(self, mock, *, deleted):
        client=mock.return_value
        client.shops.return_value=[{'id':'shop-1'}]
        client.purchases.side_effect=lambda *args:iter([])
        client.is_cancelled.return_value=deleted
        return client

    @patch('apps.billz.services.BillzClient')
    def test_deleted_receipt_stays_in_history_but_loses_imported_access(self, mock):
        self.fake_client(mock,deleted=True)
        manual=Product.objects.create(name='Separate manual purchase')
        UserProduct.objects.create(user=self.purchase.user,product=manual)
        sync_billz()
        self.purchase.refresh_from_db();self.other_line.refresh_from_db()
        self.assertFalse(self.purchase.active)
        self.assertTrue(self.purchase.cancelled)
        self.assertTrue(self.other_line.cancelled)
        self.assertEqual(BillzPurchase.objects.count(),2)
        self.assertFalse(UserProduct.objects.filter(user=self.purchase.user,product=self.product).exists())
        self.assertTrue(UserProduct.objects.filter(user=self.purchase.user,product=manual).exists())

    @patch('apps.billz.services.BillzClient')
    def test_missing_report_row_does_not_cancel_an_undeleted_receipt(self, mock):
        self.fake_client(mock,deleted=False)
        sync_billz()
        self.purchase.refresh_from_db()
        self.assertTrue(self.purchase.active)
        self.assertFalse(self.purchase.cancelled)

    @patch('apps.billz.services.BillzClient')
    def test_failed_deletion_check_keeps_cursor_and_existing_history(self, mock):
        client=self.fake_client(mock,deleted=False)
        client.is_cancelled.side_effect=BillzError('sale lookup unavailable')
        with self.assertRaises(BillzError):sync_billz()
        self.state.refresh_from_db();self.purchase.refresh_from_db()
        self.assertEqual(self.state.last_synced_at,self.now)
        self.assertTrue(self.purchase.active)

    @patch('apps.billz.services.BillzClient')
    def test_partial_report_cannot_cancel_missing_rows(self, mock):
        client=self.fake_client(mock,deleted=True)
        def partial(*args):
            yield row(order_id='another-order')
            raise BillzError('incomplete report')
        client.purchases.side_effect=partial
        with self.assertRaises(BillzError):sync_billz()
        self.purchase.refresh_from_db()
        self.assertTrue(self.purchase.active)

    @patch('apps.billz.services.BillzClient')
    def test_confirmed_cancellation_revokes_access_even_if_later_report_fails(self, mock):
        client=self.fake_client(mock,deleted=True)
        client.shops.return_value=[{'id':'shop-1'},{'id':'shop-2'}]
        def reports(shop,start,end):
            if shop=='shop-2' and start==timezone.localdate():
                raise BillzError('later report unavailable')
            return iter([])
        client.purchases.side_effect=reports
        with self.assertRaises(BillzError):sync_billz()
        self.purchase.refresh_from_db()
        self.assertTrue(self.purchase.cancelled)
        self.assertFalse(UserProduct.objects.filter(user=self.purchase.user,product=self.product).exists())

    @patch('apps.billz.services.BillzClient')
    def test_reappearing_receipt_restores_access_without_duplicate_history(self, mock):
        BillzPurchase.objects.filter(pk=self.purchase.pk).update(active=False,cancelled=True)
        UserProduct.objects.filter(user=self.purchase.user,product=self.product).delete()
        client=self.fake_client(mock,deleted=False)
        client.purchases.side_effect=lambda shop,start,end:iter([row()]) if start==timezone.localdate() else iter([])
        sync_billz()
        self.purchase.refresh_from_db()
        self.assertTrue(self.purchase.active)
        self.assertFalse(self.purchase.cancelled)
        self.assertEqual(BillzPurchase.objects.count(),2)
        self.assertTrue(UserProduct.objects.filter(user=self.purchase.user,product=self.product).exists())


@override_settings(BILLZ_SECRET_TOKEN='do-not-expose')
class ClientTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    @patch.object(BillzClient, '_get')
    def test_deleted_flag_uses_sale_details_and_validates_identity(self, get):
        get.side_effect=lambda path,params:{'id':'sale-1','deleted':True} if path=='/v2/order/sale-1' else {'id':'wrong-sale','deleted':True}
        self.assertTrue(BillzClient().is_cancelled('sale-1'))
        with self.assertRaises(BillzError):BillzClient().is_cancelled('sale-2')

    @patch.object(BillzClient, '_get', return_value={'id':'sale-1','deleted':'false'})
    def test_non_boolean_deleted_flag_cannot_cancel_purchase(self, get):
        with self.assertRaises(BillzError):BillzClient().is_cancelled('sale-1')

    @patch.object(BillzClient, '_get')
    def test_explicit_empty_page_finishes_report_with_overstated_total(self, get):
        rows=[{'id':str(index)} for index in range(45)]
        get.side_effect=[{'purchases':rows[:20],'count':46},{'purchases':rows[20:40],'count':46},{'purchases':rows[40:],'count':46},{'purchases':None,'count':46}]
        self.assertEqual(list(BillzClient()._pages('/v1/customer-purchases-table','purchases')),rows)
        self.assertEqual(get.call_count,4)

    @patch.object(BillzClient, '_get', return_value={'count':46})
    def test_missing_report_field_cannot_advance_history(self, get):
        with self.assertRaises(BillzError):
            list(BillzClient()._pages('/v1/customer-purchases-table','purchases'))

    @patch('apps.billz.client.requests.request')
    def test_login_envelope_token_reuse_pagination_and_null_rows(self, request):
        def response(data):
            from requests import Response
            import json
            result = Response(); result.status_code = 200
            result._content = json.dumps(data).encode()
            return result
        request.side_effect = [response({'data':{'access_token':'access','expires_in':3600}}), response({'shops':[{'id':'s1'}],'count':1}), response({'purchases':None,'count':0})]
        client = BillzClient()
        self.assertEqual(client.shops(), [{'id':'s1'}])
        self.assertEqual(list(client.purchases('s1', timezone.localdate(), timezone.localdate())), [])
        self.assertEqual(request.call_count, 3)
        self.assertEqual(request.call_args.kwargs['headers']['Authorization'], 'Bearer access')

    @patch('apps.billz.client.requests.request')
    def test_transport_error_does_not_expose_key_or_remote_response(self, request):
        from requests import ConnectionError
        request.side_effect = ConnectionError('do-not-expose')
        with self.assertRaises(BillzError) as error: BillzClient().shops()
        self.assertNotIn('do-not-expose', str(error.exception))
