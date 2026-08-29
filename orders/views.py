import stripe
from django.conf import settings
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from orders.models import Order, Payment
from carts.forms import CheckoutForm
from datetime import date
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from carts.stock import stock_errors
from carts.totals import cart_totals
from carts.views import _active_cart_items
from django.urls import reverse
from urllib.parse import urlencode
from orders.coupons import coupon_from_session
from orders.services import (
    cancel_order as cancel_placed_order,
    fulfill_order,
    locked_skus_for_cart,
)


COUNTRY_CODES = {
    'india': 'IN',
    'united states': 'US',
    'usa': 'US',
    'united kingdom': 'GB',
    'uk': 'GB',
    'canada': 'CA',
    'australia': 'AU',
    'germany': 'DE',
    'france': 'FR',
    'japan': 'JP',
    'singapore': 'SG',
    'united arab emirates': 'AE',
}


def get_country_code(country):
    country_value = (country or '').strip()
    if country_value.lower() in COUNTRY_CODES:
        return COUNTRY_CODES[country_value.lower()]
    country_code = country_value.upper()
    if len(country_code) == 2 and country_code.isalpha():
        return country_code
    return None


def order_complete_url(order, payment):
    query = urlencode({
        'order_number': order.order_number,
        'payment_id': payment.payment_id,
    })
    return f'{reverse("order_complete")}?{query}'


def _checkout_page(request, form, cart_items):
    totals = cart_totals(cart_items, coupon_from_session(request))
    return render(request, 'store/checkout.html', {
        'form': form,
        'cart_items': cart_items,
        **totals,
    })


@login_required
def place_order(request):
    current_user = request.user
    cart_items = _active_cart_items(request)
    if not cart_items.exists():
        return redirect('store')

    coupon = coupon_from_session(request)
    totals = cart_totals(cart_items, coupon)

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        current_stock_errors = stock_errors(cart_items)
        if current_stock_errors:
            form.is_valid()
            for message in current_stock_errors:
                form.add_error(None, message)
            return _checkout_page(request, form, cart_items)
        if form.is_valid():
            request.session['checkout_data'] = form.cleaned_data
            pending_order_id = request.session.get('pending_order_id')
            data = Order.objects.filter(
                id=pending_order_id, user=current_user, is_ordered=False
            ).first() or Order()
            data.first_name = form.cleaned_data['first_name']
            data.last_name = form.cleaned_data['last_name']
            data.phone = form.cleaned_data['phone_number']
            data.email = form.cleaned_data['email']
            data.address_line_1 = form.cleaned_data['address_line_1']
            data.address_line_2 = form.cleaned_data['address_line_2']
            data.country = form.cleaned_data['country']
            data.state = form.cleaned_data['state']
            data.city = form.cleaned_data['city']
            data.zip_code = form.cleaned_data['zip_code']
            data.order_note = form.cleaned_data['order_note']
            data.order_total = totals['grand_total']
            data.tax = totals['tax']
            data.discount = totals['discount']
            data.coupon = coupon
            data.ip = request.META.get('REMOTE_ADDR')
            data.user = current_user
            data.save()

            if not data.order_number:
                today = date.today()
                current_date = today.strftime("%Y%d%m")
                data.order_number = current_date + str(data.id)
                data.save(update_fields=['order_number', 'updated_at'])

            request.session['pending_order_id'] = data.id
            return redirect('payments')

        return _checkout_page(request, form, cart_items)

    return redirect('checkout')


@login_required
def payments(request):
    order_id = request.session.get('pending_order_id')
    if not order_id and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'error': 'Your checkout session has expired. Please return to checkout.'}, status=400)
    order = Order.objects.filter(
        id=order_id, user=request.user, is_ordered=False
    ).select_related('payment', 'coupon').first()
    if order is None:
        if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'This checkout session is no longer active. Please start checkout again.'}, status=400)
        return redirect('checkout')
    cart_items = _active_cart_items(request)

    if not cart_items.exists():
        if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Your cart is empty. Please add an item and try again.'}, status=400)
        return redirect('store')

    country_code = get_country_code(order.country)

    if request.method == 'POST':
        action = request.POST.get('action')
        payment_method = request.POST.get('payment_method', 'card')

        if action == 'complete_cod':
            current_stock_errors = stock_errors(cart_items)
            if current_stock_errors:
                return JsonResponse({'error': ' '.join(current_stock_errors)}, status=409)
            with transaction.atomic():
                locked = locked_skus_for_cart(cart_items)
                current_stock_errors = stock_errors(cart_items, locked)
                if current_stock_errors:
                    return JsonResponse({'error': ' '.join(current_stock_errors)}, status=409)
                payment = Payment.objects.create(
                    user=request.user,
                    payment_id=f'COD-{order.order_number}',
                    payment_method='cod',
                    amount_paid=str(order.order_total),
                    status='Pending',
                )
                order.payment = payment
                order.is_ordered = True
                order.save(update_fields=['payment', 'is_ordered', 'updated_at'])
                fulfill_order(request, order, payment, cart_items)
            return JsonResponse({'redirect_url': order_complete_url(order, payment)})

        if payment_method == 'paypal':
            return JsonResponse({'error': 'PayPal is not configured yet.'}, status=501)

        stripe.api_key = settings.STRIPE_SECRET_KEY
        if not stripe.api_key:
            return JsonResponse({'error': 'Stripe is not configured on the server.'}, status=503)

        try:
            if action == 'create_payment_intent':
                if not country_code:
                    return JsonResponse({
                        'error': 'Enter a valid country name or two-letter country code in the billing address.'
                    }, status=400)
                current_stock_errors = stock_errors(cart_items)
                if current_stock_errors:
                    return JsonResponse({'error': ' '.join(current_stock_errors)}, status=409)
                product_description = ', '.join(
                    f'{item.product.product_name} x {item.quantity}' for item in cart_items
                )
                intent = stripe.PaymentIntent.create(
                    amount=int(round(order.order_total * 100)),
					currency='inr',
                    payment_method_types=['card'],
                    description=f'Export order {order.order_number}: {product_description}'[:500],
                    shipping={
                        'name': order.full_name(),
                        'address': {
                            'line1': order.address_line_1,
                            'line2': order.address_line_2 or None,
                            'city': order.city,
                            'state': order.state,
                            'postal_code': order.zip_code,
                            'country': country_code,
                        },
                    },
                    metadata={
                        'order_id': str(order.id),
                        'order_number': order.order_number,
                        'customer_name': order.full_name(),
                        'customer_country': order.country,
                    },
                )
                return JsonResponse({'client_secret': intent.client_secret})

            if action == 'confirm_payment':
                intent_id = request.POST.get('payment_intent_id')
                if not intent_id:
                    return JsonResponse({'error': 'Payment confirmation is missing.'}, status=400)

                intent = stripe.PaymentIntent.retrieve(intent_id)
                expected_amount = int(round(order.order_total * 100))
                intent_metadata = intent.metadata.to_dict()
                if (intent.status != 'succeeded' or intent.amount != expected_amount
                        or intent.currency != 'inr'
                    or intent_metadata.get('order_id') != str(order.id)):
                    return JsonResponse({'error': 'Stripe could not verify this payment.'}, status=400)

                with transaction.atomic():
                    locked = locked_skus_for_cart(cart_items)
                    current_stock_errors = stock_errors(cart_items, locked)
                    if current_stock_errors:
                        return JsonResponse({'error': ' '.join(current_stock_errors)}, status=409)
                    payment, created = Payment.objects.get_or_create(
                        payment_id=intent.id,
                        defaults={
                            'user': request.user,
                            'payment_method': 'stripe_card',
                            'amount_paid': str(order.order_total),
                            'status': intent.status,
                        },
                    )
                    if created:
                        order.payment = payment
                        order.is_ordered = True
                        order.save(update_fields=['payment', 'is_ordered', 'updated_at'])
                        fulfill_order(request, order, payment, cart_items)

                return JsonResponse({'redirect_url': order_complete_url(order, payment)})

            return JsonResponse({'error': 'Unsupported payment action.'}, status=400)
        except stripe.StripeError as error:
            return JsonResponse({'error': str(error)}, status=400)

    context = {
        'order': order,
        'cart_items': cart_items,
        'total': order.order_total - order.tax + order.discount,
        'discount': order.discount,
        'tax': order.tax,
        'grand_total': order.order_total,
        'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
        'country_code': country_code,
    }
    return render(request, 'orders/payments.html', context)


@login_required
def order_complete(request):
    order_number = request.GET.get('order_number')
    payment_id = request.GET.get('payment_id')
    if not order_number or not payment_id:
        return redirect('store')

    order = get_object_or_404(
        Order.objects.select_related('payment'),
        order_number=order_number,
        payment__payment_id=payment_id,
        user=request.user,
        is_ordered=True,
    )
    order_products = order.orderproduct_set.select_related('product', 'sku').prefetch_related('variation')
    return render(request, 'orders/order_complete.html', {
        'order': order,
        'payment': order.payment,
        'order_products': order_products,
        'subtotal': order.order_total - order.tax + order.discount,
    })


@login_required
def orders(request):
    orders = Order.objects.filter(user=request.user, is_ordered=True).order_by('-created_at')
    return render(request, 'orders/orders.html', {'orders': orders})


@login_required
def order_details(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user, is_ordered=True)
    order_detail = order.orderproduct_set.select_related('product', 'sku').prefetch_related('variation')
    sub_total = sum(item.subtotal() for item in order_detail)
    return render(request, 'orders/order_details.html', {
        'order_detail': order_detail,
        'order': order,
        'sub_total': sub_total,
        'can_cancel': order.status in ('New', 'Accepted'),
    })


@login_required
def cancel_order(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user, is_ordered=True)
    if request.method != 'POST':
        return redirect('order_details', order_number=order.order_number)
    if order.status not in ('New', 'Accepted'):
        messages.error(request, 'This order can no longer be cancelled.')
        return redirect('order_details', order_number=order.order_number)
    try:
        cancel_placed_order(order)
        messages.success(request, 'Your order has been cancelled. If you paid by card, a refund has been requested.')
    except stripe.StripeError as error:
        messages.error(request, f'Order was not cancelled: {error}')
    return redirect('order_details', order_number=order.order_number)
