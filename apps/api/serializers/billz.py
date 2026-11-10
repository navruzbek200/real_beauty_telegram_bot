from rest_framework import serializers
import html
from django.utils.html import strip_tags

from apps.billz.models import BillzReceipt
from apps.billz.receipts import receipt_state
from .users import BillzPurchaseSerializer

STATE_LABELS={'pending':'Navbatda','sending':'Yuborilmoqda','sent':'Yuborildi','failed':'Yuborilmadi','unknown':'Yetkazilishi noaniq','historical':'Eski xarid — xabar yuborilmaydi','cancelled':'Bekor qilingan yoki qaytarilgan','disabled':'Avtomatik xabar o‘chirilgan','syncing':'Chek to‘liq olinishi kutilmoqda','unlinked':'Telegramga ulanmagan','unverified':'Telefon tasdig‘i kutilmoqda','inactive':'Mijoz faol emas'}


class BillzReceiptSerializer(serializers.ModelSerializer):
    products=BillzPurchaseSerializer(source='purchases',many=True,read_only=True)
    notification_state=serializers.SerializerMethodField()
    notification_label=serializers.SerializerMethodField()
    message_text=serializers.SerializerMethodField()

    def get_message_text(self,obj)->str:
        return '\n'.join(html.unescape(strip_tags(part['text'])) if part.get('parse_mode')=='HTML' else part['text'] for part in obj.message_parts)

    def get_notification_state(self,obj)->str:
        return receipt_state(obj,self.context.get('thanks_enabled',True))

    def get_notification_label(self,obj)->str:
        return STATE_LABELS.get(self.get_notification_state(obj),'Navbatda')

    class Meta:
        model=BillzReceipt
        fields=['id','shop_id','shop_name','order_id','order_number','user','customer_name','phone_number','purchased_at','historical','products','notification_state','notification_label','sent_at','last_attempt_at','next_attempt_at','attempt_count','last_error','message_text']
        read_only_fields=fields


class ReceiptPreviewRequestSerializer(serializers.Serializer):
    body=serializers.CharField(required=False,max_length=4096)


class ReceiptPreviewSerializer(serializers.Serializer):
    text=serializers.CharField()
    parts=serializers.IntegerField()
