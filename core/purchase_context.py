from decimal import Decimal
from types import SimpleNamespace

from django.utils import timezone


def quantity_text(value):
    text=format(Decimal(str(value)),'f')
    return text.rstrip('0').rstrip('.') if '.' in text else text


def purchase_context(user, products=(), receipt=None):
    """One safe, consistent context for receipts and timed purchase messages."""
    if receipt is not None and not products:
        lines=list(receipt.purchases.all())
        active=[line for line in lines if line.active]
        products=[{'name':line.product_name,'quantity':line.quantity-line.returned_quantity if active else line.quantity} for line in active or lines]
    items=[]
    for product in products:
        if isinstance(product,dict):items.append((product['name'],product.get('quantity',1)))
        else:items.append((getattr(product,'name',str(product)),1))
    full_name=(receipt.customer_name if receipt else '') or getattr(user,'full_name','') or 'Aziz mijoz'
    first_name=full_name.split()[0] if full_name.strip() else 'Aziz mijoz'
    safe_user=SimpleNamespace(full_name=full_name,first_name=first_name,phone_number=getattr(user,'phone_number',''),username=getattr(user,'username',''),language=getattr(user,'language','uz'),pk=getattr(user,'pk',None),id=getattr(user,'pk',None))
    names=', '.join(name for name,_ in items)
    return {'user':safe_user,'first_name':first_name,'full_name':full_name,'product':SimpleNamespace(name=names,pk=None),'product_name':names,'product_names':[name for name,_ in items],'products_text':'\n'.join(f'• {name} × {quantity_text(qty)}' for name,qty in items),'purchase_date':timezone.localtime(receipt.purchased_at).strftime('%d.%m.%Y') if receipt else '', 'order_number':receipt.order_number if receipt else ''}
