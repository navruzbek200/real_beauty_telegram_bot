from django.db import models
from django.utils import timezone


class BillzReceipt(models.Model):
    class DeliveryStatus(models.TextChoices):
        PENDING='pending','Navbatda'
        SENDING='sending','Yuborilmoqda'
        SENT='sent','Yuborildi'
        FAILED='failed','Yuborilmadi'
        UNKNOWN='unknown','Yetkazilishi noaniq'

    shop_id=models.CharField(max_length=64)
    shop_name=models.CharField(max_length=256,blank=True)
    order_id=models.CharField(max_length=64)
    order_number=models.CharField(max_length=128,blank=True)
    user=models.ForeignKey('users.TelegramUser',null=True,blank=True,on_delete=models.SET_NULL,related_name='billz_receipts')
    customer_name=models.CharField(max_length=512,blank=True)
    phone_number=models.CharField(max_length=64,blank=True)
    purchased_at=models.DateTimeField(db_index=True)
    historical=models.BooleanField(default=False)
    ready_at=models.DateTimeField(null=True,blank=True)
    delivery_status=models.CharField(max_length=12,choices=DeliveryStatus.choices,default=DeliveryStatus.PENDING,db_index=True)
    sent_at=models.DateTimeField(null=True,blank=True)
    last_attempt_at=models.DateTimeField(null=True,blank=True)
    next_attempt_at=models.DateTimeField(null=True,blank=True)
    attempt_count=models.PositiveIntegerField(default=0)
    message_parts=models.JSONField(default=list,blank=True)
    message_ids=models.JSONField(default=list,blank=True)
    recipient_telegram_id=models.BigIntegerField(null=True,blank=True)
    recipient_phone=models.CharField(max_length=64,blank=True)
    last_error=models.CharField(max_length=500,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering=['-purchased_at','-pk']
        verbose_name='BILLZ cheki'
        verbose_name_plural='BILLZ cheklari'
        constraints=[models.UniqueConstraint(fields=['shop_id','order_id'],name='unique_billz_receipt')]


class BillzProduct(models.Model):
    external_id = models.CharField(max_length=64, primary_key=True)
    name = models.CharField(max_length=512)
    barcode = models.CharField(max_length=256, blank=True)
    sku = models.CharField(max_length=256, blank=True)
    product = models.ForeignKey('products.Product', null=True, blank=True, on_delete=models.SET_NULL, verbose_name='Botdagi mahsulot')

    class Meta:
        verbose_name = 'BILLZ mahsuloti'
        verbose_name_plural = 'BILLZ mahsulotlari'

    def __str__(self):
        return self.name


class BillzPurchase(models.Model):
    receipt=models.ForeignKey(BillzReceipt,null=True,blank=True,on_delete=models.PROTECT,related_name='purchases')
    source_key = models.CharField(max_length=64, unique=True)
    shop_id = models.CharField(max_length=64)
    order_id = models.CharField(max_length=64)
    order_number = models.CharField(max_length=128, blank=True)
    customer_id = models.CharField(max_length=64)
    customer_name = models.CharField(max_length=512, blank=True)
    phone_number = models.CharField(max_length=64, blank=True)
    user = models.ForeignKey('users.TelegramUser', null=True, blank=True, on_delete=models.SET_NULL, related_name='billz_purchases')
    item = models.ForeignKey(BillzProduct, on_delete=models.PROTECT, related_name='purchases')
    product_name = models.CharField(max_length=512)
    purchased_at = models.DateTimeField(db_index=True)
    quantity = models.DecimalField(max_digits=16, decimal_places=3)
    returned_quantity = models.DecimalField(max_digits=16, decimal_places=3, default=0)
    transaction_type = models.CharField(max_length=64)
    active = models.BooleanField(default=False)
    cancelled = models.BooleanField(default=False)
    historical = models.BooleanField(default=True, db_index=True)
    intro_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-purchased_at', '-pk']
        verbose_name = 'BILLZ xaridi'
        verbose_name_plural = 'BILLZ xaridlari'


class BillzSyncState(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    started_at = models.DateTimeField(default=timezone.now)
    receipt_notifications_started_at=models.DateTimeField(default=timezone.now)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    history_until = models.DateField(null=True, blank=True)
    history_complete = models.BooleanField(default=False)
    history_checked_on = models.DateField(null=True, blank=True)
    history_window_days = models.PositiveSmallIntegerField(default=1)

    class Meta:
        verbose_name = 'BILLZ ulanish holati'
        verbose_name_plural = 'BILLZ ulanish holati'
