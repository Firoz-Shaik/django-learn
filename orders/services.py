import stripe
from django.conf import settings
from django.db import transaction
from django.db.models import F

from ecommerce.mail import send_templated_email
from store.models import ProductSKU
from store.sku import find_sku, sync_product_stock

from .models import Coupon, OrderProduct


def fulfill_order(request, order, payment, cart_items):
    for item in cart_items:
        sku = item.sku or find_sku(item.product, list(item.variations.all()))
        order_product = OrderProduct.objects.create(
            order=order,
            payment=payment,
            user=request.user,
            product=item.product,
            sku=sku,
            quantity=item.quantity,
            product_price=item.product.price,
            ordered=True,
        )
        order_product.variation.set(item.variations.all())
        if sku:
            sku.stock = max(sku.stock - item.quantity, 0)
            sku.save(update_fields=['stock'])
            sync_product_stock(sku.product)
        else:
            product = item.product
            product.stock = max(product.stock - item.quantity, 0)
            product.save(update_fields=['stock'])
    cart_items.update(is_active=False)
    if order.coupon_id:
        Coupon.objects.filter(pk=order.coupon_id).update(used_count=F('used_count') + 1)
    request.session.pop('pending_order_id', None)
    request.session.pop('checkout_data', None)
    request.session.pop('coupon_id', None)
    send_templated_email(
        'Order Placed Successfully',
        'orders/order_received_email.html',
        {'user': request.user, 'order': order},
        request.user.email,
    )


def restore_stock(order):
    if order.stock_restored:
        return
    for item in order.orderproduct_set.select_related('sku', 'product'):
        sku = item.sku or find_sku(item.product, list(item.variation.all()))
        if sku:
            sku.stock += item.quantity
            sku.save(update_fields=['stock'])
            sync_product_stock(sku.product)
        else:
            product = item.product
            product.stock += item.quantity
            product.save(update_fields=['stock'])
    if order.coupon_id:
        Coupon.objects.filter(pk=order.coupon_id, used_count__gt=0).update(
            used_count=F('used_count') - 1
        )
    order.stock_restored = True
    order.save(update_fields=['stock_restored', 'updated_at'])


def refund_payment(order):
    payment = order.payment
    if payment is None:
        return
    if payment.status in ('refunded', 'cancelled'):
        return
    if payment.payment_method == 'stripe_card' and str(payment.payment_id).startswith('pi_'):
        stripe.api_key = settings.STRIPE_SECRET_KEY
        if stripe.api_key:
            stripe.Refund.create(payment_intent=payment.payment_id)
        payment.status = 'refunded'
    else:
        payment.status = 'cancelled'
    payment.save(update_fields=['status'])


def cancel_order(order):
    if order.status == 'Cancelled' and order.stock_restored:
        return
    refund_payment(order)
    with transaction.atomic():
        restore_stock(order)
        order.status = 'Cancelled'
        order.save(update_fields=['status', 'updated_at'])
    if order.email:
        send_templated_email(
            f'Order {order.order_number} cancelled',
            'orders/order_status_email.html',
            {'order': order, 'status_label': 'Cancelled'},
            order.email,
        )


def notify_status_change(order, previous_status):
    if previous_status == order.status:
        return
    if order.status == 'Cancelled':
        cancel_order(order)
        return
    if order.email:
        send_templated_email(
            f'Order {order.order_number} update: {order.status}',
            'orders/order_status_email.html',
            {'order': order, 'status_label': order.status},
            order.email,
        )


def locked_skus_for_cart(cart_items):
    sku_ids = set()
    for item in cart_items:
        sku = item.sku or find_sku(item.product, list(item.variations.all()))
        if sku:
            sku_ids.add(sku.id)
            if item.sku_id is None:
                item.sku = sku
                item.save(update_fields=['sku'])
    return {
        sku.id: sku
        for sku in ProductSKU.objects.select_for_update().filter(id__in=sku_ids)
    }
