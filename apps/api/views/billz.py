import html
from types import SimpleNamespace

from django.db import transaction
from django.db.models import Exists, OuterRef, Q, F
from django.utils.html import strip_tags
from drf_spectacular.utils import extend_schema,OpenApiParameter
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from apps.api.permissions import IsSuperUser
from apps.api.serializers.billz import BillzReceiptSerializer, ReceiptPreviewRequestSerializer, ReceiptPreviewSerializer
from apps.api.serializers.common import DetailMessageSerializer
from apps.billz.models import BillzPurchase, BillzReceipt
from apps.billz.receipts import render_receipt
from apps.campaigns.models import MessageTemplate


class CanViewBillzReceipts(BasePermission):
    def has_permission(self,request,view):
        return bool(request.user and request.user.is_staff and request.user.has_perm('billz.view_billzreceipt'))


@extend_schema(parameters=[OpenApiParameter('notification_state',str),OpenApiParameter('date_from',str),OpenApiParameter('date_to',str)])
class BillzReceiptViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class=BillzReceiptSerializer
    permission_classes=[CanViewBillzReceipts]
    queryset=BillzReceipt.objects.select_related('user').prefetch_related('purchases__item__product__tutorial_steps')
    search_fields=['customer_name','phone_number','order_number','purchases__product_name']
    ordering_fields=['purchased_at','sent_at']

    def get_permissions(self):
        return [IsSuperUser()] if self.action=='retry' else super().get_permissions()

    def get_queryset(self):
        qs=super().get_queryset()
        state=self.request.query_params.get('notification_state')
        if state in ('sent','sending','failed','unknown'):qs=qs.filter(delivery_status=state)
        elif state=='historical':qs=qs.filter(historical=True).exclude(delivery_status__in=['sent','sending','unknown'])
        elif state in ('pending','unlinked','unverified','cancelled'):
            qs=qs.filter(historical=False).exclude(delivery_status__in=['sent','sending','unknown'])
            active=BillzPurchase.objects.filter(receipt_id=OuterRef('pk'),active=True)
            qs=qs.annotate(has_active=Exists(active))
            if state=='cancelled':qs=qs.filter(has_active=False)
            elif state=='unlinked':qs=qs.filter(has_active=True).filter(Q(user__isnull=True)|Q(user__telegram_id__isnull=True))
            elif state=='unverified':qs=qs.filter(has_active=True,user__telegram_id__isnull=False).filter(Q(user__phone_verified=False)|~Q(phone_number=F('user__phone_number')))
            else:qs=qs.filter(has_active=True,delivery_status='pending',user__telegram_id__isnull=False,user__phone_verified=True,user__registration_status='completed',user__is_active=True,phone_number=F('user__phone_number'),ready_at__isnull=False)
        for name,lookup in [('date_from','purchased_at__date__gte'),('date_to','purchased_at__date__lte')]:
            value=self.request.query_params.get(name)
            if value:
                from datetime import date
                from rest_framework.exceptions import ValidationError
                try:date.fromisoformat(value)
                except ValueError:raise ValidationError({name:'Sana YYYY-MM-DD shaklida bo‘lsin.'}) from None
                qs=qs.filter(**{lookup:value})
        return qs.distinct()

    def get_serializer_context(self):
        context=super().get_serializer_context()
        context['thanks_enabled']=MessageTemplate.objects.filter(template_type='purchase_thanks',is_active=True).exists()
        return context

    @extend_schema(request=ReceiptPreviewRequestSerializer,responses=ReceiptPreviewSerializer)
    @action(detail=True,methods=['post'])
    def preview(self,request,pk=None):
        receipt=self.get_object()
        payload=ReceiptPreviewRequestSerializer(data=request.data);payload.is_valid(raise_exception=True)
        template=MessageTemplate.objects.get(template_type='purchase_thanks')
        if 'body' in payload.validated_data:
            template=SimpleNamespace(body=payload.validated_data['body'],body_ru='',body_en='',parse_mode='HTML')
        try:parts=render_receipt(receipt,template)
        except Exception:return Response({'detail':'Xabar matni yoki o‘zgaruvchi noto‘g‘ri.'},status=400)
        text='\n'.join(html.unescape(strip_tags(part['text'])) if part.get('parse_mode')=='HTML' else part['text'] for part in parts)
        return Response({'text':text,'parts':len(parts)})

    @extend_schema(request=None,responses=DetailMessageSerializer)
    @action(detail=True,methods=['post'])
    def retry(self,request,pk=None):
        with transaction.atomic():
            receipt=BillzReceipt.objects.select_for_update().get(pk=self.get_object().pk)
            if receipt.delivery_status!='failed':
                return Response({'detail':'Faqat Telegram rad etgan xabarni qayta navbatga qo‘yish mumkin. Yuborilgan yoki noaniq xabar takrorlanmaydi.'},status=status.HTTP_409_CONFLICT)
            receipt.delivery_status='pending';receipt.next_attempt_at=None;receipt.last_error=''
            if not receipt.message_ids:receipt.message_parts=[]
            receipt.save(update_fields=['delivery_status','next_attempt_at','last_error','message_parts'])
        return Response({'detail':'Xabar qayta navbatga qo‘yildi. Bot keyingi tekshiruvda yuboradi.'})
