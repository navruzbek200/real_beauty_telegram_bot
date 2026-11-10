from datetime import timedelta
import html

from django.db import transaction
from django.db.models import Q, Exists, OuterRef, F
from django.utils import timezone
from django.utils.html import strip_tags
from jinja2 import StrictUndefined, meta
from jinja2.sandbox import SandboxedEnvironment

from apps.campaigns.models import MessageTemplate
from apps.users.models import TelegramUser
from core import telegram
from core.i18n import pick
from core.purchase_context import purchase_context
from .models import BillzReceipt, BillzPurchase

DEFAULT_THANKS="{{ first_name }}, Real Beauty’dan xarid qilganingiz uchun katta rahmat! 🌸\n\nSiz tanlagan mahsulotlar:\n{{ products_text }}\n\nSizni yana kutamiz! 💛\nSavollaringiz bo‘lsa, botdagi «Yordam» bo‘limi orqali bizga yozing.\n\n📅 {{ purchase_date }} · Chek №{{ order_number }}"
ALLOWED_CONTEXT={'user','first_name','full_name','product','product_name','product_names','products_text','purchase_date','order_number'}


def validate_thanks_body(body):
    env=SandboxedEnvironment(undefined=StrictUndefined,autoescape=True)
    tree=env.parse(body)
    unknown=meta.find_undeclared_variables(tree)-ALLOWED_CONTEXT
    if unknown:raise ValueError('Noma’lum o‘zgaruvchi: '+', '.join(sorted(unknown)))
    return env,meta.find_undeclared_variables(tree)


def render_receipt(receipt, template):
    context=purchase_context(receipt.user,receipt=receipt)
    body=pick(template,'body',receipt.user.language if receipt.user else 'uz')
    env,used=validate_thanks_body(body)
    if not used&{'first_name','full_name','user'}:body='{{ first_name }}, '+body
    if not used&{'product','product_name','product_names','products_text'}:body+='\n\nSiz olgan mahsulotlar:\n{{ products_text }}'
    text=env.from_string(body).render(**context)
    if len(text.encode('utf-16-le'))//2<=4000:
        return [{'text':text,'parse_mode':'HTML'}]
    # Telegram has a hard message limit. Keep every line; long receipts use
    # tracked plain-text parts so a retry resumes after accepted parts.
    text=html.unescape(strip_tags(text))
    parts=[]
    while text:
        end=min(2000,len(text))
        if end<len(text):end=text.rfind('\n',0,end)+1 or end
        parts.append({'text':text[:end]});text=text[end:]
    return parts


def finalize_receipts(ids, completed_at=None):
    for receipt_id in list(BillzReceipt.objects.filter(pk__in=ids).values_list('pk',flat=True)):
        _finalize_receipt(receipt_id,completed_at)


@transaction.atomic
def _finalize_receipt(receipt_id,completed_at):
    # Serializes metadata refresh with send claims; never restore a stale
    # pending state over a message that another worker has already accepted.
    receipt=BillzReceipt.objects.select_for_update().get(pk=receipt_id)
    lines=list(receipt.purchases.all())
    if not lines:return
    active=[line for line in lines if line.active] or lines
    owners={(line.user_id,line.phone_number) for line in active}
    first=active[0]
    old_recipient=(receipt.user_id,receipt.phone_number)
    receipt.user_id=first.user_id if len(owners)==1 else None
    receipt.phone_number=first.phone_number if len(owners)==1 else ''
    receipt.customer_name=first.customer_name
    receipt.order_number=first.order_number
    receipt.purchased_at=min(line.purchased_at for line in lines)
    if completed_at is not None:receipt.ready_at=completed_at
    if old_recipient!=(receipt.user_id,receipt.phone_number):
        if receipt.message_ids or receipt.delivery_status in ('sending','sent','unknown'):
            receipt.delivery_status='unknown';receipt.last_error='Chekning qabul qiluvchisi o‘zgargan. Avvalgi yuborilishni tekshiring.'
        else:
            receipt.delivery_status='pending';receipt.message_parts=[];receipt.last_error='';receipt.next_attempt_at=None
    # Customer cards may be merged or corrected while the Telegram recipient
    # stays the same. Recorded acceptance of every part proves delivery to that
    # exact chat and phone; restore the fact without sending anything again.
    if receipt.delivery_status=='unknown' and receipt.message_parts and len(receipt.message_ids)==len(receipt.message_parts) and receipt.user_id and receipt.recipient_telegram_id and receipt.user.telegram_id==receipt.recipient_telegram_id and receipt.phone_number==receipt.recipient_phone and receipt.user.phone_number==receipt.phone_number:
        receipt.delivery_status='sent';receipt.sent_at=receipt.sent_at or receipt.last_attempt_at
        receipt.last_error='';receipt.next_attempt_at=None
    receipt.save(update_fields=['user','phone_number','customer_name','order_number','purchased_at','ready_at','delivery_status','message_parts','sent_at','last_error','next_attempt_at'])

def receipt_state(receipt, enabled=True):
    if receipt.delivery_status in ('sent','sending','unknown'):return receipt.delivery_status
    if receipt.historical:return 'historical'
    if not any(line.active for line in receipt.purchases.all()):return 'cancelled'
    if not enabled:return 'disabled'
    if not receipt.ready_at:return 'syncing'
    if any(line.active and (line.user_id!=receipt.user_id or line.phone_number!=receipt.phone_number) for line in receipt.purchases.all()):return 'unverified'
    user=receipt.user
    if not user or not user.telegram_id:return 'unlinked'
    if not user.phone_verified or user.phone_number!=receipt.phone_number:return 'unverified'
    if not user.is_active or user.registration_status!='completed':return 'inactive'
    return receipt.delivery_status


def receipt_can_notify(receipt):
    user=receipt.user
    lines=[line for line in receipt.purchases.all() if line.active]
    return bool(receipt.ready_at and user and user.telegram_id and user.phone_verified and user.is_active and user.registration_status=='completed' and user.phone_number==receipt.phone_number and lines and all(line.user_id==user.pk and line.phone_number==receipt.phone_number for line in lines))


def _claim(receipt_id,template):
    with transaction.atomic():
        receipt=BillzReceipt.objects.select_for_update().get(pk=receipt_id)
        if receipt.user_id:
            receipt.user=TelegramUser.objects.get(pk=receipt.user_id)
        if receipt_state(receipt) not in ('pending','failed'):return None
        if receipt.delivery_status=='failed' and (receipt.next_attempt_at is None or receipt.next_attempt_at>timezone.now()):return None
        if receipt.message_ids and (receipt.recipient_telegram_id!=receipt.user.telegram_id or receipt.recipient_phone!=receipt.phone_number):
            receipt.delivery_status='unknown';receipt.last_error='Qabul qiluvchi o‘zgargan.';receipt.save(update_fields=['delivery_status','last_error']);return None
        try:
            if not receipt.message_ids:receipt.message_parts=render_receipt(receipt,template)
        except Exception:
            receipt.delivery_status='failed';receipt.last_error='Xabar matnini tekshiring: o‘zgaruvchi yoki format noto‘g‘ri.';receipt.next_attempt_at=None
            receipt.save(update_fields=['delivery_status','last_error','next_attempt_at']);return None
        receipt.delivery_status='sending';receipt.last_attempt_at=timezone.now();receipt.attempt_count+=1
        receipt.recipient_telegram_id=receipt.user.telegram_id;receipt.recipient_phone=receipt.phone_number
        receipt.save(update_fields=['delivery_status','last_attempt_at','attempt_count','message_parts','recipient_telegram_id','recipient_phone'])
        return receipt.pk


def _deliver(receipt_id):
    while True:
        with transaction.atomic():
            receipt=BillzReceipt.objects.select_for_update().get(pk=receipt_id)
            if receipt.delivery_status!='sending':return 0
            user=TelegramUser.objects.filter(pk=receipt.user_id).first()
            if not user or not user.phone_verified or not user.is_active or user.registration_status!='completed' or user.telegram_id!=receipt.recipient_telegram_id or user.phone_number!=receipt.phone_number or receipt.phone_number!=receipt.recipient_phone or not receipt.purchases.filter(active=True).exists() or receipt.purchases.filter(active=True).exclude(user_id=user.pk,phone_number=receipt.phone_number).exists():
                receipt.delivery_status='unknown';receipt.last_error='Mijoz yoki chek holati o‘zgargan. Yuborish to‘xtatildi.';receipt.save(update_fields=['delivery_status','last_error']);return 0
            index=len(receipt.message_ids)
            if index>=len(receipt.message_parts):
                receipt.delivery_status='sent';receipt.sent_at=timezone.now();receipt.last_error='';receipt.next_attempt_at=None
                receipt.save(update_fields=['delivery_status','sent_at','last_error','next_attempt_at']);return 1
            part=receipt.message_parts[index]
            try:
                result=telegram.call('sendMessage',{'chat_id':user.telegram_id,**part})
                if not isinstance(result,dict) or not result.get('message_id'):
                    raise telegram.TelegramError('Telegram javobi noaniq.',delivery_uncertain=True)
            except telegram.TelegramError as exc:
                receipt.delivery_status='unknown' if exc.delivery_uncertain else 'failed'
                receipt.last_error='Telegram javobi noaniq. Takror yuborishdan oldin tekshirish kerak.' if exc.delivery_uncertain else 'Telegram xabarni qabul qilmadi. Bot bloklangan yoki vaqtincha aloqa xatosi bo‘lishi mumkin.'
                receipt.next_attempt_at=None if exc.delivery_uncertain or exc.is_permanent or receipt.attempt_count>=10 else timezone.now()+timedelta(seconds=max(exc.retry_after or 0,min(3600,60*2**min(receipt.attempt_count,6))))
                receipt.save(update_fields=['delivery_status','last_error','next_attempt_at']);return 0
            receipt.message_ids=[*receipt.message_ids,result['message_id']]
            receipt.save(update_fields=['message_ids'])


def deliver_receipts():
    from django.conf import settings
    if not settings.BOT_TOKEN:return 0
    template=MessageTemplate.objects.filter(template_type='purchase_thanks',is_active=True).first()
    if template is None:return 0
    for stale in BillzReceipt.objects.filter(delivery_status='sending',last_attempt_at__lt=timezone.now()-timedelta(minutes=10)):
        with transaction.atomic():
            stale=BillzReceipt.objects.select_for_update().get(pk=stale.pk)
            if stale.delivery_status!='sending':continue
            accepted=bool(stale.message_parts) and len(stale.message_ids)==len(stale.message_parts)
            stale.delivery_status='sent' if accepted else 'unknown'
            stale.sent_at=(stale.sent_at or stale.last_attempt_at) if accepted else stale.sent_at
            stale.last_error='' if accepted else 'Yuborish uzilgan. Telegramdagi holatni tekshiring.'
            stale.save(update_fields=['delivery_status','sent_at','last_error'])
    active=BillzPurchase.objects.filter(receipt_id=OuterRef('pk'),active=True)
    wrong=active.filter(Q(user_id__isnull=True)|~Q(user_id=OuterRef('user_id'),phone_number=OuterRef('phone_number')))
    due=BillzReceipt.objects.filter(historical=False,ready_at__isnull=False,purchased_at__lte=timezone.now(),user__telegram_id__isnull=False,user__phone_verified=True,user__is_active=True,user__registration_status='completed',phone_number=F('user__phone_number')).annotate(has_active=Exists(active),has_wrong_owner=Exists(wrong)).filter(has_active=True,has_wrong_owner=False).filter(Q(delivery_status='pending')|Q(delivery_status='failed',next_attempt_at__lte=timezone.now())).order_by('purchased_at','pk')
    sent=0
    for receipt_id in list(due.values_list('pk',flat=True)[:200]):
        if _claim(receipt_id,template):sent+=_deliver(receipt_id)
    return sent
