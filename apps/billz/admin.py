from django.contrib import admin
from core.admin import RBModelAdmin
from .models import BillzProduct, BillzPurchase, BillzSyncState


@admin.register(BillzProduct)
class BillzProductAdmin(RBModelAdmin):
    list_display = ['name', 'sku', 'barcode', 'product']
    list_filter = ['product']
    search_fields = ['name', 'sku', 'barcode', 'product__name']
    autocomplete_fields = ['product']
    readonly_fields = ['external_id', 'name', 'sku', 'barcode']

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(BillzPurchase)
class BillzPurchaseAdmin(RBModelAdmin):
    list_display = ['customer_name', 'phone_number', 'product_name', 'purchased_at', 'quantity', 'historical', 'active', 'cancelled']
    list_filter = ['historical', 'active', 'cancelled', 'shop_id']
    search_fields = ['customer_name', 'phone_number', 'product_name', 'order_number']
    readonly_fields = [field.name for field in BillzPurchase._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(BillzSyncState)
class BillzSyncStateAdmin(RBModelAdmin):
    list_display = ['started_at', 'last_synced_at', 'history_complete', 'history_until']
    readonly_fields = [field.name for field in BillzSyncState._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
