import hashlib
import uuid
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models import Q, Min, F
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.products.models import Product
from apps.users.models import TelegramUser, UserProduct
from .client import BillzClient, BillzError
from .models import BillzProduct, BillzPurchase, BillzReceipt, BillzSyncState


def _product(name):
    # Exact names only: a guessed cosmetic match can deliver the wrong instructions.
    normalized = ' '.join(name.casefold().split())
    matches = [p for p in Product.objects.all() if normalized in {' '.join(getattr(p, f).casefold().split()) for f in ('name', 'name_ru', 'name_en')}]
    return matches[0] if len(matches) == 1 else None


def _customer(name, phone):
    if not phone:
        return None
    customer, _ = TelegramUser.objects.get_or_create(phone_number=phone,defaults={'full_name':name[:256],'source':'billz'})
    return customer


def _grant(purchase):
    if purchase.user_id and purchase.item.product_id and purchase.active and purchase.phone_number == purchase.user.phone_number and (purchase.user.telegram_id is None or purchase.user.phone_verified):
        entitlement, created = UserProduct.objects.get_or_create(user=purchase.user, product=purchase.item.product, defaults={'auto_messages_enabled': False})
        if created:
            UserProduct.objects.filter(pk=entitlement.pk).update(purchased_at=purchase.purchased_at)


def reconcile_entitlements():
    """Reconcile tutorial access in two reads; only missing pairs need writes."""
    owned = BillzPurchase.objects.filter(active=True, user__isnull=False, item__product__isnull=False,phone_number=F('user__phone_number')).filter(Q(user__telegram_id__isnull=True)|Q(user__phone_verified=True)).order_by().values('user_id', 'item__product_id').annotate(first=Min('purchased_at'))
    expected = {(r['user_id'], r['item__product_id']): r['first'] for r in owned}
    existing = {(user, product): (pk, enabled) for pk, user, product, enabled in UserProduct.objects.values_list('pk', 'user_id', 'product_id', 'auto_messages_enabled')}
    for (user, product), purchased_at in expected.items():
        if (user, product) not in existing:
            entitlement, created = UserProduct.objects.get_or_create(user_id=user, product_id=product, defaults={'auto_messages_enabled': False})
            if created:
                UserProduct.objects.filter(pk=entitlement.pk).update(purchased_at=purchased_at)
    remove = [pk for pair, (pk, enabled) in existing.items() if not enabled and pair not in expected]
    if remove:
        UserProduct.objects.filter(pk__in=remove).delete()


def import_purchase(row, *, started_at):
    # Commit invalidation before touching any line. A report may stop midway;
    # its previous complete snapshot must not remain eligible for delivery.
    if isinstance(row,dict):
        BillzReceipt.objects.filter(shop_id=str(row.get('shop_id','')).strip(),order_id=str(row.get('order_id','')).strip()).update(ready_at=None)
    return _import_purchase(row,started_at=started_at)


@transaction.atomic
def _import_purchase(row, *, started_at):
    try:
        identity = [str(row[key]).strip() for key in ('shop_id', 'order_id', 'product_id', 'customer_id')]
        if not all(identity) or any(x in ('None', 'null') for x in identity):
            raise ValueError
        purchased_at = parse_datetime(row['created_at'])
        if purchased_at is None:
            raise ValueError
        if timezone.is_naive(purchased_at):
            purchased_at = timezone.make_aware(purchased_at, timezone.get_default_timezone())
        quantity = Decimal(str(row['sold_measurement_value']))
        returned = Decimal(str(row.get('returned_measurement_value') or 0))
        if not quantity.is_finite() or not returned.is_finite() or quantity < 0 or returned < 0:
            raise ValueError
        name = str(row['product_name']).strip()
        if not name:
            raise ValueError
    except (KeyError, ValueError, TypeError, InvalidOperation):
        raise BillzError('BILLZ xarid yozuvi noto‘g‘ri; sinxronlash belgisi surilmadi.') from None
    # A receipt line survives corrections to its customer assignment.
    source_key = hashlib.sha256('\0'.join(identity[:3]).encode()).hexdigest()
    phone = next((p for raw in (row.get('phone_numbers') or []) if (p := TelegramUser.normalize_phone(raw))), '')
    customer_name = str(row.get('customer_name') or '')
    item = BillzProduct.objects.filter(external_id=identity[2]).first()
    if item is None:
        item = BillzProduct.objects.create(external_id=identity[2], name=name[:512], barcode=str(row.get('product_barcode') or '')[:256], sku=str(row.get('product_sku') or '')[:256], product=_product(name))
    elif item.name != name:
        item.name = name[:512]
        item.save(update_fields=['name'])
    kind = str(row.get('order_type') or '')
    active = quantity > returned and kind.casefold() in {'sale', 'продажа', 'sotuv', 'exchange', 'обмен', 'almashuv'}
    defaults = dict(shop_id=identity[0], order_id=identity[1], customer_id=identity[3], order_number=str(row.get('order_number') or '')[:128], customer_name=customer_name[:512], phone_number=phone, item=item, product_name=name[:512], purchased_at=purchased_at, quantity=quantity, returned_quantity=returned, transaction_type=kind[:64], active=active, cancelled=False)
    customer=_customer(customer_name,phone)
    cutoff=BillzSyncState.objects.filter(pk=1).values_list('receipt_notifications_started_at',flat=True).first() or started_at
    receipt,_=BillzReceipt.objects.get_or_create(shop_id=identity[0],order_id=identity[1],defaults={'user':customer,'customer_name':customer_name[:512],'phone_number':phone,'order_number':defaults['order_number'],'shop_name':str(row.get('shop_name') or '')[:256],'purchased_at':purchased_at,'historical':purchased_at<cutoff})
    defaults['receipt']=receipt
    purchase = BillzPurchase.objects.select_for_update().filter(source_key=source_key).first()
    grant_needed = purchase is None
    if purchase is None:
        purchase = BillzPurchase.objects.create(source_key=source_key, user=customer, historical=purchased_at < started_at, **defaults)
    else:
        original_user_id = purchase.user_id
        original_phone = purchase.phone_number
        for key, value in defaults.items():
            setattr(purchase, key, value)
        # Customer changes on a receipt must not keep the previous customer's access.
        if purchase.user is None or purchase.user.phone_number != phone:
            purchase.user = customer
            grant_needed = True
        changed_recipient = original_user_id != purchase.user_id or original_phone != phone
        fields = list(defaults) + ['user']
        if changed_recipient:
            purchase.intro_sent_at = None
            fields.append('intro_sent_at')
        # An overlapping import must never overwrite a delivery marker it did
        # not change. The row lock also serializes recipient corrections.
        purchase.save(update_fields=fields)
    if grant_needed:
        _grant(purchase)
    return purchase


@transaction.atomic
def verify_phone(user_id, phone):
    """Called only after Telegram supplied the sender's own contact."""
    from apps.users.identity import bind_verified_contact
    user = TelegramUser.objects.get(pk=user_id)
    if not user.telegram_id:raise ValueError('telegram_account_required')
    return bind_verified_contact(telegram_id=user.telegram_id,phone=phone,username=user.username,full_name=user.full_name,language=user.language)


def deliver_pending():
    if not settings.BOT_TOKEN:
        return 0
    from apps.users.admin import TelegramUserAdmin
    sent = 0
    purchases = BillzPurchase.objects.filter(historical=False, active=True, intro_sent_at__isnull=True, user__telegram_id__isnull=False, user__phone_verified=True, user__is_active=True, user__registration_status='completed', item__product__isnull=False).select_related('user', 'item__product').order_by('purchased_at', 'pk')
    for candidate in purchases:
        lock = f'billz:intro:{candidate.pk}'
        owner = uuid.uuid4().hex
        if not cache.add(lock, owner, 180):
            continue
        try:
            with transaction.atomic():
                purchase = BillzPurchase.objects.select_for_update(of=('self',)).select_related('user', 'item__product').get(pk=candidate.pk)
                user = purchase.user
                product = purchase.item.product
                if purchase.intro_sent_at or purchase.historical or not purchase.active or not product or not user or not user.telegram_id or not user.is_active or not user.phone_verified or user.phone_number != purchase.phone_number or user.registration_status != 'completed':
                    continue
                _grant(purchase)
                if not product.tutorial_steps.filter(Q(video_file_id__gt='') | Q(video_file__gt='')).exists():
                    continue
                if TelegramUserAdmin._send_purchase_message(user, product, greet=False):
                    purchase.intro_sent_at = timezone.now()
                    purchase.save(update_fields=['intro_sent_at'])
                    sent += 1
        finally:
            if cache.get(lock) == owner:
                cache.delete(lock)
    return sent


def sync_billz():
    lock = 'billz:sync-lock'
    owner = uuid.uuid4().hex
    if not cache.add(lock, owner, 900):
        return {'busy': True}
    try:
        client = BillzClient()
        state, _ = BillzSyncState.objects.get_or_create(pk=1)
        now = timezone.now()
        today = timezone.localdate(now)
        shops = client.shops()
        live_start = timezone.localdate(state.last_synced_at or now) - timedelta(days=1)
        count = 0

        def consume(start, end):
            nonlocal count
            for shop in shops:
                seen_orders = set()
                receipt_ids=set()
                for row in client.purchases(shop['id'], start, end):
                    if cache.get(lock) != owner:
                        raise BillzError('BILLZ sinxronlash qulfi tugadi; keyingi ish davom ettiradi.')
                    cache.touch(lock, 900)
                    purchase=import_purchase(row, started_at=state.started_at)
                    receipt_ids.add(purchase.receipt_id)
                    seen_orders.add(str(row['order_id']).strip())
                    count += 1
                # A cancelled sale disappears from the report. Missing rows
                # alone are not proof: confirm deletion on the receipt itself.
                period_start = timezone.make_aware(datetime.combine(start, time.min))
                period_end = timezone.make_aware(datetime.combine(end + timedelta(days=1), time.min))
                missing_orders = BillzPurchase.objects.filter(shop_id=shop['id'], active=True, purchased_at__gte=period_start, purchased_at__lt=period_end).exclude(order_id__in=seen_orders).order_by().values_list('order_id', flat=True).distinct()
                for order_id in missing_orders:
                    if cache.get(lock) != owner:
                        raise BillzError('BILLZ sinxronlash qulfi tugadi; keyingi ish davom ettiradi.')
                    cache.touch(lock, 900)
                    if client.is_cancelled(order_id) is True:
                        with transaction.atomic():
                            BillzPurchase.objects.filter(shop_id=shop['id'], order_id=order_id).update(active=False, cancelled=True)
                            reconcile_entitlements()
                from .receipts import finalize_receipts
                finalize_receipts(receipt_ids,timezone.now())

        # Bound a long outage to API-sized windows, then catch up without losing rows.
        cursor = live_start
        while cursor <= today:
            end = cursor
            consume(cursor, end)
            cursor = end + timedelta(days=1)
        history_start = date.fromisoformat(settings.BILLZ_HISTORY_START)
        if state.history_complete and state.history_checked_on != today:
            state.history_complete = False
            state.history_until = None
        if not state.history_complete:
            end = state.history_until or (today - timedelta(days=2))
            if end >= history_start:
                start = max(history_start, end - timedelta(days=state.history_window_days-1))
                before = count
                try:
                    consume(start, end)
                except BillzError as exc:
                    # Keep live polling progressing when a large historical
                    # report times out. Retry the same cursor in a smaller slice.
                    state.history_window_days = max(1, state.history_window_days // 2)
                    state.last_synced_at = now
                    state.save()
                    from .client import BillzHistoryError
                    raise BillzHistoryError(str(exc)) from None
                state.history_until = start - timedelta(days=1)
                state.history_window_days = 1 if count > before else min(365, state.history_window_days * 2)
            if state.history_until is None or state.history_until < history_start:
                state.history_complete = True
                state.history_checked_on = today
        state.last_synced_at = now
        state.save()
        reconcile_entitlements()
        return {'rows': count, 'shops': len(shops), 'history_complete': state.history_complete}
    finally:
        if cache.get(lock) == owner:
            cache.delete(lock)
