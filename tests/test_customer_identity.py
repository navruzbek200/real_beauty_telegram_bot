from datetime import timedelta
from unittest.mock import patch, AsyncMock
from types import SimpleNamespace

from asgiref.sync import async_to_sync
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.billz.models import BillzPurchase
from apps.billz.services import import_purchase
from apps.products.models import Product
from apps.users.identity import bind_verified_contact, merge_customers
from apps.users.models import TelegramUser, UserProduct
from apps.users.services import register_app_user
from tests.test_billz import row


class IdentityTests(TestCase):
    def test_full_normalized_phone_is_unique_in_database(self):
        TelegramUser.objects.create(phone_number='+998 90 123 45 67')
        with self.assertRaises(IntegrityError), transaction.atomic():
            TelegramUser.objects.create(phone_number='998901234567')
        self.assertEqual(TelegramUser.objects.get().phone_number, '+998901234567')

    def test_blank_phone_is_not_an_identity(self):
        TelegramUser.objects.create(telegram_id=1)
        TelegramUser.objects.create(telegram_id=2)
        self.assertEqual(TelegramUser.objects.count(), 2)

    def test_app_signup_never_links_another_country_by_suffix(self):
        foreign = TelegramUser.objects.create(phone_number='+996901234567')
        local = register_app_user(full_name='Local', phone_number='+998901234567')
        self.assertNotEqual(local.pk, foreign.pk)
        again = register_app_user(full_name='Again', phone_number='90 123 45 67')
        self.assertEqual(again.pk, local.pk)

    @override_settings(BILLZ_SECRET_TOKEN='test-only')
    def test_import_reuses_unverified_card_but_does_not_unlock_its_history(self):
        from bot.services.user_service import get_user_products
        product = Product.objects.create(name='Serum')
        account = TelegramUser.objects.create(telegram_id=15, phone_number='+998901234567')
        purchase = import_purchase(row(), started_at=timezone.now())
        self.assertEqual(purchase.user, account)
        self.assertEqual(TelegramUser.objects.count(), 1)
        self.assertEqual(async_to_sync(get_user_products)(15), [])
        verified = bind_verified_contact(telegram_id=15, phone='+998901234567', username='owned', full_name='Telegram Name', language='uz')
        self.assertEqual(verified.pk, account.pk)
        self.assertTrue(verified.phone_verified)
        self.assertEqual(UserProduct.objects.get(user=verified).product, product)

    def test_contact_binds_existing_billz_card_without_a_second_signup(self):
        purchase = import_purchase(row(), started_at=timezone.now())
        user = bind_verified_contact(telegram_id=16, phone='+998901234567', username='owned', full_name='Telegram Name', language='ru')
        self.assertEqual(user.pk, purchase.user_id)
        self.assertEqual(user.full_name, 'Test Customer')
        self.assertIsNone(user.birth_date)
        self.assertEqual(user.registration_status, 'completed')
        self.assertEqual(user.language, 'ru')
        self.assertEqual(TelegramUser.objects.count(), 1)

    def test_own_contact_cannot_take_over_another_telegram_account(self):
        owner = TelegramUser.objects.create(telegram_id=17, phone_number='+998901234567')
        with self.assertRaises(ValueError):
            bind_verified_contact(telegram_id=18, phone='+998901234567', username='other', full_name='Other', language='uz')
        owner.refresh_from_db()
        self.assertEqual(owner.telegram_id, 17)

    def test_crm_phone_correction_cannot_unlock_the_previous_phone_history(self):
        Product.objects.create(name='Serum')
        user=TelegramUser.objects.create(telegram_id=119,phone_number='+998901234567')
        purchase=import_purchase(row(),started_at=timezone.now())
        user.phone_number='+998901234569'
        user.save()
        verified=bind_verified_contact(telegram_id=119,phone='+998901234569',username='owned',full_name='Current',language='uz')
        purchase.refresh_from_db()
        self.assertNotEqual(purchase.user_id,verified.pk)
        self.assertEqual(purchase.user.phone_number,'+998901234567')
        self.assertFalse(UserProduct.objects.filter(user=verified,auto_messages_enabled=False).exists())

    def test_merge_preserves_orders_points_lessons_and_existing_message_markers(self):
        from apps.campaigns.models import AutoMessage, AutoMessageLog
        from apps.lessons.models import LessonUnlock
        from apps.loyalty.models import LoyaltyAccount, PointsTransaction
        from apps.orders.models import Order
        product = Product.objects.create(name='Serum')
        target = TelegramUser.objects.create(telegram_id=19, phone_number='+998901234567')
        source = TelegramUser.objects.create()
        old = UserProduct.objects.create(user=source, product=product)
        kept = UserProduct.objects.create(user=target, product=product)
        order = Order.objects.create(user=source, customer_name='Customer', phone_number='+998901234567', delivery_method='yandex', address='Test', total=1)
        rule = AutoMessage.objects.first()
        AutoMessageLog.objects.create(user=source, auto_message=rule, anchor=f'up:{old.pk}')
        LessonUnlock.objects.create(user=source)
        LoyaltyAccount.objects.create(user=source, balance=50, lifetime_points=50)
        PointsTransaction.objects.create(user=source, points=50, reason='registration', reference=f'registration:{source.pk}')
        merge_customers(source.pk, target.pk)
        order.refresh_from_db()
        self.assertEqual(order.user, target)
        self.assertFalse(TelegramUser.objects.filter(pk=source.pk).exists())
        self.assertEqual(UserProduct.objects.filter(user=target).count(), 1)
        self.assertEqual(AutoMessageLog.objects.get().anchor, f'up:{kept.pk}')
        self.assertEqual(target.loyalty.balance, 50)
        self.assertTrue(LessonUnlock.objects.filter(user=target).exists())

    def test_merge_does_not_credit_registration_twice(self):
        from apps.loyalty.models import LoyaltyAccount,PointsTransaction
        target=TelegramUser.objects.create(telegram_id=121,phone_number='+998901234567')
        source=TelegramUser.objects.create()
        for user in [source,target]:
            LoyaltyAccount.objects.create(user=user,balance=50,lifetime_points=50)
            PointsTransaction.objects.create(user=user,points=50,reason='registration',reference=f'registration:{user.pk}')
        merge_customers(source.pk,target.pk)
        self.assertEqual(LoyaltyAccount.objects.get(user=target).balance,50)
        self.assertEqual(PointsTransaction.objects.filter(user=target).count(),1)


class ManualEntryTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(User.objects.create_superuser('owner', password='test'))
        self.user = TelegramUser.objects.create(full_name='Existing', phone_number='+998901234567')

    def test_manual_create_and_edit_cannot_duplicate_existing_phone(self):
        response = self.client.post('/api/v1/customers/', {'full_name':'Again','phone_number':'90 123 45 67'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('phone_number', response.json())
        other = TelegramUser.objects.create(phone_number='+998901234568')
        response = self.client.patch(f'/api/v1/customers/{other.pk}/', {'phone_number':'+998 90 123 45 67'}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_unauthenticated_user_cannot_read_customer_cards(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(f'/api/v1/customers/{self.user.pk}/')
        self.assertIn(response.status_code, [401,403])

    def test_imported_entitlement_is_labelled_so_ui_does_not_repeat_purchase(self):
        product = Product.objects.create(name='Serum')
        self.user.phone_verified = True
        self.user.save(update_fields=['phone_verified'])
        import_purchase(row(), started_at=timezone.now())
        response = self.client.get(f'/api/v1/customers/{self.user.pk}/')
        self.assertTrue(response.json()['purchases'][0]['is_billz'])
        self.assertEqual(len(response.json()['billz_purchases']), 1)

    def test_non_staff_account_cannot_read_customer_cards(self):
        self.client.force_authenticate(User.objects.create_user('customer',password='test'))
        self.assertEqual(self.client.get(f'/api/v1/customers/{self.user.pk}/').status_code,403)


@override_settings(BILLZ_SECRET_TOKEN='test-only')
class ContactFirstTests(TestCase):
    def test_billz_customer_only_selects_language_and_shares_own_contact(self):
        from aiogram.fsm.context import FSMContext
        from aiogram.fsm.storage.memory import MemoryStorage
        from aiogram.fsm.storage.base import StorageKey
        from bot.handlers import auth
        from bot.keyboards import inline
        from bot.states.registration import SelfReg
        purchase=import_purchase(row(),started_at=timezone.now())
        sent=[]
        async def send(chat_id=None,text='',**kwargs):
            sent.append((text,kwargs));return SimpleNamespace(message_id=len(sent))
        bot=SimpleNamespace(send_message=send,delete_message=AsyncMock())
        sender=SimpleNamespace(id=125,username='owned',full_name='Telegram Name')
        message=SimpleNamespace(chat=SimpleNamespace(id=125,username='owned'),from_user=sender,bot=bot,message_id=1,answer=lambda text,**kw:send(125,text,**kw),delete=AsyncMock(),edit_reply_markup=AsyncMock(),contact=SimpleNamespace(user_id=125,phone_number='998901234567',first_name='Telegram'))
        async def exercise():
            state=FSMContext(MemoryStorage(),StorageKey(bot_id=1,chat_id=125,user_id=125))
            await auth._begin_self(message,state,'uz')
            callback=SimpleNamespace(answer=AsyncMock(),data=f'{inline.CB_LANGUAGE_SETUP}{inline.SEP}uz',from_user=sender,message=message,bot=bot)
            await auth.step_language(callback,state)
            self.assertEqual(await state.get_state(),SelfReg.phone.state)
            self.assertTrue(any(button.request_contact for row in sent[-1][1]['reply_markup'].keyboard for button in row))
            self.assertTrue(all('Test Customer' not in text for text,_ in sent))
            await auth.step_phone_contact(message,state)
            self.assertIsNone(await state.get_state())
        async_to_sync(exercise)()
        user=TelegramUser.objects.get(telegram_id=125)
        self.assertEqual(user.pk,purchase.user_id)
        self.assertEqual(user.full_name,'Test Customer')
        self.assertIsNone(user.birth_date)
        self.assertTrue(user.phone_verified)
        self.assertEqual(TelegramUser.objects.count(),1)
        self.assertTrue(any('Test Customer' in text for text,_ in sent))


class DuplicateMigrationTests(TransactionTestCase):
    def test_existing_duplicate_is_merged_before_database_constraint(self):
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor
        executor=MigrationExecutor(connection)
        latest=executor.loader.graph.leaf_nodes()
        executor.migrate([('users','0016_telegramuser_phone_verified_and_more')])
        target=TelegramUser.objects.create(telegram_id=130,phone_number='+998901234567')
        source=TelegramUser.objects.create(phone_number='+998901234567')
        from apps.orders.models import Order
        order=Order.objects.create(user=source,customer_name='Customer',phone_number='+998901234567',delivery_method='yandex',address='Test',total=1)
        MigrationExecutor(connection).migrate([('users','0017_telegramuser_unique_customer_phone')])
        order.refresh_from_db()
        self.assertEqual(order.user_id,target.pk)
        self.assertEqual(TelegramUser.objects.filter(phone_number='+998901234567').count(),1)
        MigrationExecutor(connection).migrate(latest)
