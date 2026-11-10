"""Canonical phone identity shared by imports, signup and duplicate cleanup."""
from django.apps import apps as live_apps
from django.db import transaction
from django.utils import timezone


def _move_message_log(log, anchor, Log):
    existing = Log.objects.filter(auto_message_id=log.auto_message_id, anchor=anchor).exclude(pk=log.pk).first()
    if existing:
        if log.success and not existing.success:
            Log.objects.filter(pk=existing.pk).update(success=True, error_detail='')
        log.delete()
    else:
        Log.objects.filter(pk=log.pk).update(anchor=anchor)


@transaction.atomic
def merge_customers(source_id, target_id, *, registry=None):
    registry = registry or live_apps
    Customer = registry.get_model('users', 'TelegramUser')
    if source_id == target_id:
        return Customer.objects.get(pk=target_id)
    locked = {user.pk:user for user in Customer.objects.select_for_update().filter(pk__in=[source_id,target_id]).order_by('pk')}
    source, target = locked[source_id], locked[target_id]
    if source.telegram_id and target.telegram_id and source.telegram_id != target.telegram_id:
        raise ValueError('different_telegram_accounts')
    if source.phone_number and target.phone_number and source.phone_number != target.phone_number:
        raise ValueError('different_phone_numbers')

    Grant = registry.get_model('users', 'UserProduct')
    Log = registry.get_model('campaigns', 'AutoMessageLog')
    replacements = {f'user:{source.pk}':f'user:{target.pk}'}
    for old in Grant.objects.filter(user_id=source.pk):
        kept = Grant.objects.filter(user_id=target.pk, product_id=old.product_id).first()
        if kept:
            replacements[f'up:{old.pk}'] = f'up:{kept.pk}'
            Grant.objects.filter(pk=kept.pk).update(
                purchased_at=min(old.purchased_at, kept.purchased_at),
                auto_messages_enabled=old.auto_messages_enabled or kept.auto_messages_enabled,
                week1_sent=old.week1_sent or kept.week1_sent,
                week2_sent=old.week2_sent or kept.week2_sent,
            )
            old.delete()
        else:
            Grant.objects.filter(pk=old.pk).update(user_id=target.pk)
    for log in Log.objects.filter(user_id=source.pk):
        anchor = replacements.get(log.anchor, log.anchor)
        parts = anchor.split(':')
        if len(parts)==3 and parts[0] in ('billz','br') and parts[2]==str(source.pk):
            anchor = f'{parts[0]}:{parts[1]}:{target.pk}'
        _move_message_log(log, anchor, Log)

    Points = registry.get_model('loyalty', 'PointsTransaction')
    Account = registry.get_model('loyalty', 'LoyaltyAccount')
    duplicate_balance = duplicate_lifetime = 0
    for entry in Points.objects.filter(user_id=source.pk):
        reference = f'registration:{target.pk}' if entry.reason=='registration' else entry.reference
        collision = Points.objects.filter(user_id=target.pk, reason=entry.reason)
        collision = collision if entry.reason=='registration' else collision.filter(reference=reference) if reference else collision.none()
        if collision.exists():
            duplicate_balance += entry.points
            duplicate_lifetime += max(0, entry.points)
            entry.delete()
        else:
            Points.objects.filter(pk=entry.pk).update(user_id=target.pk, reference=reference)
    old_account = Account.objects.filter(user_id=source.pk).first()
    kept_account = Account.objects.filter(user_id=target.pk).first()
    if old_account and kept_account:
        lifetime = max(0, old_account.lifetime_points + kept_account.lifetime_points - duplicate_lifetime)
        conf = registry.get_model('loyalty', 'LoyaltySettings').objects.filter(pk=1).first()
        tier = 'bronze'
        Conf = registry.get_model('loyalty','LoyaltySettings')
        for name in ['silver','gold','platinum']:
            threshold=getattr(conf,name+'_from') if conf else Conf._meta.get_field(name+'_from').get_default()
            if lifetime >= threshold:tier=name
        Account.objects.filter(pk=kept_account.pk).update(balance=old_account.balance+kept_account.balance-duplicate_balance, lifetime_points=lifetime, tier=tier)
        old_account.delete()
    elif old_account:
        Account.objects.filter(pk=old_account.pk).update(user_id=target.pk, balance=old_account.balance-duplicate_balance, lifetime_points=max(0,old_account.lifetime_points-duplicate_lifetime))

    Unlock = registry.get_model('lessons', 'LessonUnlock')
    old_unlock = Unlock.objects.filter(user_id=source.pk).first()
    kept_unlock = Unlock.objects.filter(user_id=target.pk).first()
    if old_unlock and kept_unlock:
        if old_unlock.unlocked_at < kept_unlock.unlocked_at:
            Unlock.objects.filter(pk=kept_unlock.pk).update(unlocked_at=old_unlock.unlocked_at, code_id=old_unlock.code_id)
        old_unlock.delete()

    # The remaining relations are ordinary foreign keys: orders, support,
    # analytics, referrals, codes and historical logs retain their rows/IDs.
    for relation in Customer._meta.get_fields(include_hidden=True):
        if not relation.auto_created or relation.concrete or not relation.is_relation or relation.many_to_many:
            continue
        relation.related_model.objects.filter(**{relation.field.attname:source.pk}).update(**{relation.field.attname:target.pk})

    changes = {}
    for field in ['full_name','username','birth_date','face_condition','photo','referred_by_seller_id','registered_by_id']:
        if not getattr(target,field) and getattr(source,field):
            changes[field] = getattr(source,field)
    if source.registration_status=='completed':changes['registration_status']='completed'
    dates = [value for value in [source.registered_at,target.registered_at] if value]
    if dates:changes['registered_at']=min(dates)
    if not target.phone_number and source.phone_number:
        changes['phone_number']=source.phone_number
        changes['phone_tail']=source.phone_tail
    changes['phone_verified']=target.phone_verified or source.phone_verified
    if not target.telegram_id and source.telegram_id:
        changes['telegram_id']=source.telegram_id
        Customer.objects.filter(pk=source.pk).update(telegram_id=None)
    # Free the unique phone before assigning it to a previously blank card.
    Customer.objects.filter(pk=source.pk).update(phone_number='',phone_tail='')
    source.delete()
    Customer.objects.filter(pk=target.pk).update(**changes)
    Customer.objects.filter(pk=target.pk,registered_by_id=target.pk).update(registered_by_id=None)
    return Customer.objects.get(pk=target.pk)


def normalize_and_deduplicate(registry, schema_editor=None):
    from apps.users.models import TelegramUser as LiveCustomer
    Customer = registry.get_model('users','TelegramUser')
    groups = {}
    for user in Customer.objects.all().order_by('pk'):
        phone = LiveCustomer.normalize_phone(user.phone_number)
        if phone:
            groups.setdefault(phone,[]).append(user)
    # Refuse unsafe merges before changing any group.
    if any(len({u.telegram_id for u in group if u.telegram_id})>1 for group in groups.values()):
        raise ValueError('Duplicate phone belongs to distinct Telegram accounts; manual review required.')
    for phone, group in groups.items():
        for user in group:
            Customer.objects.filter(pk=user.pk).update(phone_number=phone,phone_tail=LiveCustomer.phone_tail_of(phone))
            user.phone_number=phone
        group.sort(key=lambda u:(bool(u.telegram_id),u.phone_verified,u.registration_status=='completed',-u.pk),reverse=True)
        kept = group[0]
        for duplicate in group[1:]:
            kept=merge_customers(duplicate.pk,kept.pk,registry=registry)


@transaction.atomic
def bind_verified_contact(*, telegram_id, phone, username, full_name, language, source='self', referred_by_seller_id=None, registered_by_id=None):
    from .models import TelegramUser
    from apps.billz.models import BillzPurchase
    from apps.billz.services import reconcile_entitlements
    phone = TelegramUser.normalize_phone(phone)
    if not phone:
        raise ValueError('invalid_phone')
    # Serializing a same-phone claim through its unique customer row prevents
    # two Telegram accounts from claiming the same pending card concurrently.
    card, _ = TelegramUser.objects.get_or_create(phone_number=phone,defaults={'full_name':full_name,'source':source})
    card = TelegramUser.objects.select_for_update().get(pk=card.pk)
    if card.telegram_id and card.telegram_id != telegram_id:
        raise ValueError('phone_already_linked')
    current = TelegramUser.objects.select_for_update().filter(telegram_id=telegram_id).first()
    if current and current.pk != card.pk:
        previous_phone = current.phone_number
        if previous_phone and previous_phone != phone:
            TelegramUser.objects.filter(pk=current.pk).update(phone_number='',phone_tail='',phone_verified=False)
            old_purchases=BillzPurchase.objects.filter(user_id=current.pk).exclude(phone_number=phone)
            if old_purchases.exists():
                old_card,_ = TelegramUser.objects.get_or_create(phone_number=previous_phone,defaults={'source':'billz','full_name':current.full_name})
                old_purchases.update(user=old_card,intro_sent_at=None)
        current.refresh_from_db()
        # This path has an owned Telegram contact, so it can safely retain the
        # sender's existing account while adding the pending phone card.
        current.phone_verified=True
        current.save(update_fields=['phone_verified'])
        card=merge_customers(card.pk,current.pk)
    card.telegram_id=telegram_id
    card.username=username
    card.phone_verified=True
    card.language=language
    card.registration_status='completed'
    if not card.full_name:card.full_name=full_name
    if card.registered_at is None:card.registered_at=timezone.now()
    if card.referred_by_seller_id is None:card.referred_by_seller_id=referred_by_seller_id
    if card.registered_by_id is None and registered_by_id != card.pk:card.registered_by_id=registered_by_id
    card.save(update_fields=['telegram_id','username','phone_verified','language','registration_status','full_name','registered_at','referred_by_seller','registered_by'])
    # A CRM phone edit can make current == card before contact verification.
    # Always detach mismatched receipts, irrespective of the merge path.
    for purchase in BillzPurchase.objects.select_for_update().filter(user_id=card.pk).exclude(phone_number=phone):
        owner=None
        if purchase.phone_number:
            owner,_=TelegramUser.objects.get_or_create(phone_number=purchase.phone_number,defaults={'source':'billz','full_name':purchase.customer_name[:256]})
        purchase.user=owner
        purchase.intro_sent_at=None
        purchase.save(update_fields=['user','intro_sent_at'])
    reconcile_entitlements()
    from apps.billz.models import BillzReceipt
    from apps.billz.receipts import finalize_receipts
    finalize_receipts(BillzReceipt.objects.filter(user=card).values_list('pk',flat=True))
    return card
