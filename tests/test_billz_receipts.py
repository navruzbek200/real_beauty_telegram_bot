from datetime import timedelta
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase, TransactionTestCase, override_settings, skipUnlessDBFeature
from django.utils import timezone

from apps.billz.models import BillzPurchase, BillzReceipt, BillzSyncState
from apps.billz.receipts import deliver_receipts, finalize_receipts
from apps.billz.services import import_purchase
from apps.campaigns.models import AutoMessage, MessageTemplate
from apps.users.models import TelegramUser
from core.telegram import TelegramError
from tasks.scheduled import dispatch_auto_messages
from tests.test_billz import row


@override_settings(BOT_TOKEN='mocked-only',BILLZ_SECRET_TOKEN='test-only')
class ReceiptDeliveryTests(TestCase):
    def setUp(self):
        cache.clear()
        self.started=timezone.now()-timedelta(hours=1)
        BillzSyncState.objects.create(pk=1,receipt_notifications_started_at=self.started)
        self.user=TelegramUser.objects.create(telegram_id=600,full_name='Navruz Bektemirov',phone_number='+998901234567',phone_verified=True,registration_status='completed')
        MessageTemplate.objects.update_or_create(template_type='purchase_thanks',defaults={'name':'Purchase thanks','body':'{{ first_name }}, xaridingiz uchun rahmat!\n{{ products_text }}','is_active':True})

    def purchase(self, **changes):
        return import_purchase(row(**{'customer_name':'Navruz Bektemirov','product_name':'Non',**changes}),started_at=self.started)

    def ready(self, **changes):
        purchase=self.purchase(**changes)
        finalize_receipts([purchase.receipt_id],timezone.now())
        return purchase.receipt

    @patch('apps.billz.receipts.telegram.call',return_value={'message_id':91})
    def test_two_unmapped_products_send_one_personal_receipt_without_tutorial(self, send):
        first=self.purchase()
        self.purchase(product_id='milk',product_name='Sut',sold_measurement_value=2)
        finalize_receipts([first.receipt_id],timezone.now())
        self.assertEqual(deliver_receipts(),1)
        self.assertEqual(deliver_receipts(),0)
        self.assertEqual(send.call_count,1)
        text=send.call_args.args[1]['text']
        self.assertIn('Navruz',text);self.assertIn('Non',text);self.assertIn('Sut',text);self.assertIn('2',text)
        self.assertEqual(BillzReceipt.objects.count(),1)
        first.receipt.refresh_from_db()
        self.assertEqual(first.receipt.delivery_status,'sent')
        self.assertEqual(first.receipt.message_ids,[91])

    @patch('apps.billz.receipts.telegram.call',return_value={'message_id':92})
    def test_partial_report_is_not_ready_and_replay_does_not_duplicate(self, send):
        first=self.purchase()
        self.assertEqual(deliver_receipts(),0)
        self.purchase()
        finalize_receipts([first.receipt_id],timezone.now())
        self.assertEqual(deliver_receipts(),1)
        self.purchase()
        finalize_receipts([first.receipt_id],timezone.now())
        self.assertEqual(deliver_receipts(),0)
        self.assertEqual(BillzPurchase.objects.count(),1)
        self.assertEqual(send.call_count,1)

    @patch('apps.billz.receipts.telegram.call',return_value={'message_id':93})
    def test_different_receipts_each_send_once(self, send):
        self.ready();self.ready(order_id='second-sale')
        self.assertEqual(deliver_receipts(),2)
        self.assertEqual(deliver_receipts(),0)
        self.assertEqual(send.call_count,2)

    @patch('apps.billz.receipts.telegram.call')
    def test_old_cancelled_and_unverified_receipts_stay_silent(self, send):
        self.ready(created_at=timezone.localtime(self.started-timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S'))
        cancelled=self.ready(order_id='cancelled')
        BillzPurchase.objects.filter(receipt=cancelled).update(active=False,cancelled=True)
        self.ready(order_id='not-verified')
        TelegramUser.objects.filter(pk=self.user.pk).update(phone_verified=False)
        self.assertEqual(deliver_receipts(),0)
        self.assertFalse(send.called)

    @patch('apps.billz.receipts.telegram.call',return_value={'message_id':94})
    def test_later_owned_contact_can_receive_ready_receipt(self, send):
        TelegramUser.objects.filter(pk=self.user.pk).update(telegram_id=None,phone_verified=False)
        self.ready()
        self.assertEqual(deliver_receipts(),0)
        TelegramUser.objects.filter(pk=self.user.pk).update(telegram_id=600,phone_verified=True)
        self.assertEqual(deliver_receipts(),1)

    @patch('apps.billz.receipts.telegram.call')
    def test_overlapping_worker_cannot_send_same_receipt(self, send):
        self.ready()
        def accept(method,payload):
            self.assertEqual(deliver_receipts(),0)
            return {'message_id':95}
        send.side_effect=accept
        self.assertEqual(deliver_receipts(),1)
        self.assertEqual(send.call_count,1)

    @patch('apps.billz.receipts.telegram.call')
    def test_uncertain_delivery_is_visible_and_never_blindly_retried(self, send):
        receipt=self.ready()
        send.side_effect=TelegramError('network interrupted',delivery_uncertain=True)
        self.assertEqual(deliver_receipts(),0)
        receipt.refresh_from_db()
        self.assertEqual(receipt.delivery_status,'unknown')
        self.assertEqual(deliver_receipts(),0)
        self.assertEqual(send.call_count,1)

    @patch('apps.billz.receipts.telegram.call')
    def test_known_rejection_retries_and_does_not_claim_sent(self, send):
        receipt=self.ready()
        send.side_effect=TelegramError('Too Many Requests',retry_after=60)
        self.assertEqual(deliver_receipts(),0)
        receipt.refresh_from_db()
        self.assertEqual(receipt.delivery_status,'failed');self.assertIsNone(receipt.sent_at)
        send.side_effect=None;send.return_value={'message_id':96}
        BillzReceipt.objects.filter(pk=receipt.pk).update(next_attempt_at=timezone.now()-timedelta(seconds=1))
        self.assertEqual(deliver_receipts(),1)

    @patch('apps.billz.receipts.telegram.call',return_value={'message_id':97})
    def test_static_template_still_includes_real_name_and_every_product(self, send):
        MessageTemplate.objects.filter(template_type='purchase_thanks').update(body='Yana kelib turing!')
        self.ready()
        self.assertEqual(deliver_receipts(),1)
        text=send.call_args.args[1]['text']
        self.assertIn('Navruz',text);self.assertIn('Non',text);self.assertIn('Yana kelib',text)

    @patch('apps.billz.receipts.telegram.call',return_value={'message_id':105})
    def test_corrected_recipient_after_send_is_held_without_resending(self, send):
        receipt=self.ready()
        self.assertEqual(deliver_receipts(),1)
        target=TelegramUser.objects.create(telegram_id=601,phone_number='+998901234569',phone_verified=True,registration_status='completed')
        self.purchase(customer_id='other-client',phone_numbers=[target.phone_number])
        finalize_receipts([receipt.pk],timezone.now())
        receipt.refresh_from_db()
        self.assertEqual(receipt.delivery_status,'unknown')
        self.assertEqual(deliver_receipts(),0)
        self.assertEqual(send.call_count,1)

    @patch('apps.billz.receipts.telegram.call',return_value={'message_id':111})
    def test_customer_card_replacement_keeps_accepted_delivery_visible(self, send):
        receipt=self.ready()
        self.assertEqual(deliver_receipts(),1)
        phone=self.user.phone_number
        TelegramUser.objects.filter(pk=self.user.pk).update(telegram_id=None,phone_number='',phone_tail='',phone_verified=False)
        canonical=TelegramUser.objects.create(telegram_id=600,phone_number=phone,phone_verified=True,registration_status='completed')
        receipt.purchases.update(user=canonical)
        finalize_receipts([receipt.pk],timezone.now())
        receipt.refresh_from_db()
        self.assertEqual(receipt.delivery_status,'sent')
        self.assertIsNotNone(receipt.sent_at)
        self.assertEqual(deliver_receipts(),0)
        self.assertEqual(send.call_count,1)

    @patch('apps.billz.receipts.telegram.call',return_value={'message_id':112})
    def test_fully_accepted_delivery_recovers_only_for_its_original_recipient(self, send):
        receipt=self.ready()
        self.assertEqual(deliver_receipts(),1)
        target=TelegramUser.objects.create(telegram_id=601,phone_number='+998901234569',phone_verified=True,registration_status='completed')
        self.purchase(phone_numbers=[target.phone_number])
        finalize_receipts([receipt.pk],timezone.now())
        receipt.refresh_from_db()
        self.assertEqual(receipt.delivery_status,'unknown')
        self.purchase(phone_numbers=[self.user.phone_number])
        finalize_receipts([receipt.pk],timezone.now())
        receipt.refresh_from_db()
        self.assertEqual(receipt.delivery_status,'sent')
        self.assertEqual(deliver_receipts(),0)
        self.assertEqual(send.call_count,1)

    @patch('apps.billz.receipts.telegram.call')
    def test_partial_uncertainty_stays_held_after_metadata_refresh(self, send):
        receipt=self.ready()
        BillzReceipt.objects.filter(pk=receipt.pk).update(delivery_status='unknown',message_parts=[{'text':'part one'},{'text':'part two'}],message_ids=[113],recipient_telegram_id=600,recipient_phone=self.user.phone_number)
        finalize_receipts([receipt.pk],timezone.now())
        receipt.refresh_from_db()
        self.assertEqual(receipt.delivery_status,'unknown')
        self.assertIsNone(receipt.sent_at)
        self.assertEqual(deliver_receipts(),0)
        self.assertFalse(send.called)

    @patch('apps.billz.receipts.telegram.call')
    def test_inconsistent_receipt_owner_cannot_leak_new_lines(self, send):
        first=self.ready()
        self.purchase(product_id='other-phone-product',phone_numbers=['+998901234569'])
        self.assertEqual(deliver_receipts(),0)
        self.assertFalse(send.called)

    @patch('apps.billz.receipts.telegram.call',return_value={'message_id':106})
    def test_backfill_error_does_not_starve_validated_new_receipt(self, send):
        from apps.billz.client import BillzHistoryError
        from tasks.billz import poll_billz
        self.ready()
        with patch('tasks.billz.sync_billz',side_effect=BillzHistoryError('old report slow')),patch('tasks.billz.deliver_pending',return_value=0):
            self.assertEqual(poll_billz()['receipts_sent'],1)

    @patch('apps.billz.receipts.telegram.call',return_value={'message_id':107})
    def test_customer_html_is_escaped_in_receipt(self, send):
        self.ready(customer_name='<b>Customer</b>',product_name='<a>Product</a>')
        self.assertEqual(deliver_receipts(),1)
        text=send.call_args.args[1]['text']
        self.assertIn('&lt;a&gt;Product&lt;/a&gt;',text)

    @patch('apps.billz.services.BillzClient')
    @patch('apps.billz.receipts.telegram.call')
    def test_failed_pagination_never_makes_partial_receipt_ready(self, send, client):
        from apps.billz.client import BillzError
        from apps.billz.services import sync_billz
        client.return_value.shops.return_value=[{'id':'shop-1'}]
        def partial(*args):
            yield row()
            raise BillzError('page unavailable')
        client.return_value.purchases.side_effect=partial
        with self.assertRaises(BillzError):sync_billz()
        self.assertFalse(BillzReceipt.objects.filter(ready_at__isnull=False).exists())
        self.assertEqual(deliver_receipts(),0)
        self.assertFalse(send.called)

    @patch('apps.billz.receipts.telegram.call',return_value={'message_id':108})
    def test_partial_refresh_invalidates_a_previously_ready_receipt(self, send):
        from apps.billz.client import BillzHistoryError
        from tasks.billz import poll_billz
        created=timezone.localtime(timezone.now()-timedelta(days=3)).strftime('%Y-%m-%d %H:%M:%S')
        BillzSyncState.objects.update(receipt_notifications_started_at=timezone.now()-timedelta(days=7))
        receipt=self.ready(created_at=created)
        self.purchase(product_id='partial-new',product_name='New incomplete product',created_at=created)
        with patch('tasks.billz.sync_billz',side_effect=BillzHistoryError('report interrupted')),patch('tasks.billz.deliver_pending',return_value=0):
            self.assertEqual(poll_billz()['receipts_sent'],0)
        self.assertFalse(send.called)
        self.purchase(product_id='last-new',product_name='Last product',created_at=created)
        finalize_receipts([receipt.pk],timezone.now())
        self.assertEqual(deliver_receipts(),1)
        self.assertIn('Last product',send.call_args.args[1]['text'])

    @patch('apps.billz.receipts.telegram.call',return_value={'message_id':109})
    def test_delayed_campaign_cannot_use_partially_corrected_customer_lines(self, send):
        AutoMessage.objects.all().delete()
        created=timezone.localtime(timezone.now()-timedelta(minutes=3)).strftime('%Y-%m-%d %H:%M:%S')
        self.ready(created_at=created)
        self.assertEqual(deliver_receipts(),1)
        target=TelegramUser.objects.create(telegram_id=602,phone_number='+998901234569',phone_verified=True,registration_status='completed')
        self.purchase(product_name='Corrected private product',phone_numbers=[target.phone_number],created_at=created)
        AutoMessage.objects.create(name='due customer check',delay_value=1,delay_unit='minute',body='{{ first_name }}: {{ products_text }}')
        with patch('tasks.scheduled.send_message') as followup:
            self.assertEqual(dispatch_auto_messages(),0)
            self.assertFalse(followup.called)

    @patch('apps.billz.receipts.telegram.call',return_value={'message_id':110})
    def test_two_hundred_cancelled_receipts_cannot_starve_a_valid_new_sale(self, send):
        valid=self.ready(order_id='valid-last')
        when=self.started+timedelta(minutes=1)
        receipts=[BillzReceipt(shop_id='shop-1',order_id=f'cancel-{i}',user=self.user,phone_number=self.user.phone_number,purchased_at=when,ready_at=timezone.now(),historical=False) for i in range(200)]
        BillzReceipt.objects.bulk_create(receipts)
        item=valid.purchases.first().item
        BillzPurchase.objects.bulk_create([BillzPurchase(receipt=receipt,source_key=f'cancel-{i}',shop_id='shop-1',order_id=receipt.order_id,customer_id='client-1',user=self.user,phone_number=self.user.phone_number,item=item,product_name='Cancelled',purchased_at=when,quantity=1,transaction_type='SALE',active=False,cancelled=True,historical=False) for i,receipt in enumerate(receipts)])
        self.assertEqual(deliver_receipts(),1)
        self.assertEqual(send.call_count,1)

    @patch('apps.billz.receipts.telegram.call',return_value={'message_id':98})
    def test_long_receipt_keeps_all_product_lines(self, send):
        first=self.purchase()
        for index in range(25):self.purchase(product_id=f'long-{index}',product_name=f'Product-{index} '+('x'*190))
        finalize_receipts([first.receipt_id],timezone.now())
        self.assertEqual(deliver_receipts(),1)
        texts=[call.args[1]['text'] for call in send.call_args_list]
        self.assertGreater(len(texts),1)
        for index in range(25):self.assertIn(f'Product-{index} ',''.join(texts))
        self.assertTrue(all(len(text.encode('utf-16-le'))//2<=4096 for text in texts))

    @patch('apps.billz.receipts.telegram.call')
    def test_retry_of_long_receipt_resumes_after_accepted_part(self, send):
        first=self.purchase()
        for index in range(25):self.purchase(product_id=f'long-{index}',product_name=f'Product-{index} '+('x'*190))
        finalize_receipts([first.receipt_id],timezone.now())
        send.side_effect=[{'message_id':301},TelegramError('Too Many Requests',retry_after=1)]
        self.assertEqual(deliver_receipts(),0)
        first.receipt.refresh_from_db()
        self.assertEqual(first.receipt.message_ids,[301])
        accepted_text=send.call_args_list[0].args[1]['text']
        BillzReceipt.objects.filter(pk=first.receipt_id).update(next_attempt_at=timezone.now()-timedelta(seconds=1))
        send.side_effect=None;send.return_value={'message_id':302};send.reset_mock()
        self.assertEqual(deliver_receipts(),1)
        self.assertNotIn(accepted_text,[call.args[1]['text'] for call in send.call_args_list])

    @patch('apps.billz.receipts.telegram.call')
    def test_crash_after_recording_all_parts_is_recovered_without_resend(self, send):
        receipt=self.ready()
        BillzReceipt.objects.filter(pk=receipt.pk).update(delivery_status='sending',last_attempt_at=timezone.now()-timedelta(minutes=11),message_parts=[{'text':'accepted'}],message_ids=[303])
        deliver_receipts()
        receipt.refresh_from_db()
        self.assertEqual(receipt.delivery_status,'sent')
        self.assertFalse(send.called)

    @patch('apps.billz.receipts.telegram.call',return_value={'message_id':99})
    def test_delayed_campaign_uses_receipt_products_without_catalogue_mapping(self, send):
        AutoMessage.objects.all().delete()
        first=self.purchase(created_at=timezone.localtime(timezone.now()-timedelta(minutes=3)).strftime('%Y-%m-%d %H:%M:%S'))
        self.purchase(product_id='milk',product_name='Sut',created_at=timezone.localtime(first.purchased_at).strftime('%Y-%m-%d %H:%M:%S'))
        finalize_receipts([first.receipt_id],timezone.now())
        deliver_receipts()
        AutoMessage.objects.create(name='7/15-day context',delay_value=1,delay_unit='minute',body='{{ first_name }}: {{ product.name }} / {{ product_name }}')
        with patch('tasks.scheduled.send_message') as followup:
            self.assertEqual(dispatch_auto_messages(),1)
            self.assertEqual(dispatch_auto_messages(),0)
        text=followup.call_args.args[1]
        self.assertIn('Navruz',text);self.assertIn('Non',text);self.assertIn('Sut',text)


@override_settings(BOT_TOKEN='mocked-only',BILLZ_SECRET_TOKEN='test-only')
class ReceiptApiTests(TestCase):
    purchase=ReceiptDeliveryTests.purchase
    ready=ReceiptDeliveryTests.ready

    def setUp(self):
        ReceiptDeliveryTests.setUp(self)
        from django.contrib.auth.models import User
        from rest_framework.test import APIClient
        self.client=APIClient()
        self.admin=User.objects.create_superuser('receipt-admin',password='test')
        self.client.force_authenticate(self.admin)

    def test_list_groups_products_and_reports_actual_delivery_state(self):
        first=self.purchase();self.purchase(product_id='milk',product_name='Sut')
        finalize_receipts([first.receipt_id],timezone.now())
        response=self.client.get('/api/v1/billz-receipts/')
        self.assertEqual(response.status_code,200)
        data=response.json()['results']
        self.assertEqual(len(data),1)
        self.assertEqual(len(data[0]['products']),2)
        self.assertEqual(data[0]['notification_state'],'pending')
        BillzReceipt.objects.filter(pk=first.receipt_id).update(delivery_status='sent',sent_at=timezone.now(),message_ids=[100])
        self.assertEqual(self.client.get(f'/api/v1/billz-receipts/{first.receipt_id}/').json()['notification_state'],'sent')

    def test_anonymous_and_nonstaff_cannot_read_receipts(self):
        from django.contrib.auth.models import User
        self.client.force_authenticate(None)
        self.assertIn(self.client.get('/api/v1/billz-receipts/').status_code,[401,403])
        self.client.force_authenticate(User.objects.create_user('nonstaff',password='test'))
        self.assertEqual(self.client.get('/api/v1/billz-receipts/').status_code,403)

    def test_preview_uses_full_receipt_and_does_not_send(self):
        receipt=self.ready()
        response=self.client.post(f'/api/v1/billz-receipts/{receipt.pk}/preview/',{'body':'{{ first_name }}, yana kelib turing!'},format='json')
        self.assertEqual(response.status_code,200)
        self.assertIn('Navruz',response.json()['text']);self.assertIn('Non',response.json()['text'])
        receipt.refresh_from_db();self.assertIsNone(receipt.sent_at)

    def test_sent_or_unknown_receipt_cannot_be_resent(self):
        receipt=self.ready()
        for status in ['sent','unknown']:
            BillzReceipt.objects.filter(pk=receipt.pk).update(delivery_status=status)
            self.assertEqual(self.client.post(f'/api/v1/billz-receipts/{receipt.pk}/retry/').status_code,409)

    def test_invalid_thanks_variable_rejected_before_save(self):
        template=MessageTemplate.objects.get(template_type='purchase_thanks')
        response=self.client.patch(f'/api/v1/message-templates/{template.pk}/',{'body':'Hello {{ typo_variable }}'},format='json')
        self.assertEqual(response.status_code,400)

    def test_seller_can_read_but_cannot_change_template_or_retry(self):
        from django.contrib.auth.models import User
        from apps.users.roles import sync_seller_group
        seller=User.objects.create_user('receipt-seller',password='test',is_staff=True)
        seller.groups.add(sync_seller_group())
        receipt=self.ready()
        self.client.force_authenticate(seller)
        self.assertEqual(self.client.get('/api/v1/billz-receipts/').status_code,200)
        self.assertEqual(self.client.post(f'/api/v1/billz-receipts/{receipt.pk}/retry/').status_code,403)
        template=MessageTemplate.objects.get(template_type='purchase_thanks')
        self.assertEqual(self.client.patch(f'/api/v1/message-templates/{template.pk}/',{'body':'changed'},format='json').status_code,403)


@override_settings(BOT_TOKEN='mocked-only',BILLZ_SECRET_TOKEN='test-only')
class ReceiptPostgresConcurrencyTests(TransactionTestCase):
    purchase=ReceiptDeliveryTests.purchase
    ready=ReceiptDeliveryTests.ready

    def setUp(self):
        ReceiptDeliveryTests.setUp(self)

    @skipUnlessDBFeature('has_select_for_update')
    def test_metadata_refresh_cannot_reset_a_concurrent_successful_send(self):
        import threading
        from django.db import connections
        receipt=self.ready()
        prepared=threading.Event();release=threading.Event();accepted=threading.Event()
        errors=[]
        original_save=BillzReceipt.save
        def delayed_save(obj,*args,**kwargs):
            if threading.current_thread().name=='receipt-finalizer':
                prepared.set()
                if not release.wait(10):raise TimeoutError('finalizer not released')
            return original_save(obj,*args,**kwargs)
        def worker(function):
            try:function()
            except Exception as exc:errors.append(exc)
            finally:connections['default'].close()
        def send(method,payload):accepted.set();return {'message_id':401}
        with patch.object(BillzReceipt,'save',delayed_save),patch('apps.billz.receipts.telegram.call',side_effect=send):
            first=threading.Thread(name='receipt-finalizer',target=worker,args=(lambda:finalize_receipts([receipt.pk],timezone.now()),))
            second=threading.Thread(name='receipt-sender',target=worker,args=(deliver_receipts,))
            first.start()
            self.assertTrue(prepared.wait(10))
            second.start()
            accepted.wait(2)
            release.set();first.join(15);second.join(15)
        self.assertFalse(first.is_alive());self.assertFalse(second.is_alive());self.assertEqual(errors,[])
        receipt.refresh_from_db()
        self.assertEqual(receipt.delivery_status,'sent')
        self.assertEqual(receipt.message_ids,[401])
        self.assertEqual(deliver_receipts(),0)
