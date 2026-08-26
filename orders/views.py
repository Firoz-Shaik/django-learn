import stripe
from django.conf import settings
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from carts.models import CartItem
from orders.models import Order,Payment,OrderProduct
from store.models import Product
from carts.forms import CheckoutForm
from datetime import date
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from carts.stock import stock_errors
from django.core.mail import EmailMessage
from django.urls import reverse
from urllib.parse import urlencode


# Create your views here.
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

@login_required
def place_order(request):
    current_user = request.user

    cart_items = CartItem.objects.filter(user=current_user, is_active=True)
    cart_count = cart_items.count()
    if cart_count <= 0:
        return redirect('store')

    total = 0
    quantity = 0
    grand_total = 0
    tax = 0
    for item in cart_items:
        total += (item.product.price * item.quantity)
        quantity += item.quantity
    tax = (12 * total) / 100
    grand_total = total + tax

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        current_stock_errors = stock_errors(cart_items)
        if current_stock_errors:
            form.is_valid()
            for message in current_stock_errors:
                form.add_error(None, message)
            return render(request, "store/checkout.html", {
                'form': form,
                'total': total,
                'quantity': quantity,
                'cart_items': cart_items,
                'tax': tax,
                'grand_total': grand_total,
            })
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
            data.order_total = grand_total
            data.tax = tax
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

        return render(request, "store/checkout.html", {
            'form': form,
            'total': total,
            'quantity': quantity,
            'cart_items': cart_items,
            'tax': tax,
            'grand_total': grand_total,
        })

    return redirect('checkout')


    
@login_required
def payments(request):
    order_id = request.session.get('pending_order_id')
    order = get_object_or_404(Order, id=order_id, user=request.user, is_ordered=False)
    cart_items = CartItem.objects.filter(user=request.user, is_active=True).select_related('product')

    if not cart_items.exists():
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
                locked_products = {
                    product.id: product
                    for product in Product.objects.select_for_update().filter(
                        id__in=cart_items.values_list('product_id', flat=True)
                    )
                }
                current_stock_errors = stock_errors(cart_items, locked_products)
                if current_stock_errors:
                    return JsonResponse({'error': ' '.join(current_stock_errors)}, status=409)
                payment = Payment.objects.create(
                    user=request.user,
                    payment_id=f'COD-{order.order_number}',
                    payment_method='cod',
                    amount_paid=str(order.order_total),
                    status='Pending',
                )
                quantities = {}
                order.payment = payment
                order.is_ordered = True
                order.save(update_fields=['payment', 'is_ordered', 'updated_at'])
                for item in cart_items:
                    quantities[item.product_id] = quantities.get(item.product_id, 0) + item.quantity
                    order_product = OrderProduct.objects.create(
                        order=order, payment=payment, user=request.user,
                        product=item.product, quantity=item.quantity,
                        product_price=item.product.price, ordered=True,
                    )
                    order_product.variation.set(item.variations.all())
                for product_id, quantity in quantities.items():
                    locked_products[product_id].stock -= quantity
                    locked_products[product_id].save(update_fields=['stock'])
                cart_items.update(is_active=False)
            request.session.pop('pending_order_id', None)
            request.session.pop('checkout_data', None)
            return JsonResponse({'redirect_url': order_complete_url(order, payment)})

        if payment_method == 'paypal':
            return JsonResponse({'error': 'PayPal is not configured yet.'}, status=501)

        if stripe is None:
            return JsonResponse({'error': 'The Stripe SDK is not installed on the server.'}, status=503)
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
                    currency='usd',
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
                        or intent.currency != 'usd'
                    or intent_metadata.get('order_id') != str(order.id)):
                    return JsonResponse({'error': 'Stripe could not verify this payment.'}, status=400)

                with transaction.atomic():
                    locked_products = {
                        product.id: product
                        for product in Product.objects.select_for_update().filter(
                            id__in=cart_items.values_list('product_id', flat=True)
                        )
                    }
                    current_stock_errors = stock_errors(cart_items, locked_products)
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
                    #Add products to ordered product table and mark order complete as true in order table
                    if created:
                        order.payment = payment
                        order.is_ordered = True
                        order.save(update_fields=['payment', 'is_ordered', 'updated_at'])

                        for item in cart_items:
                            order_product = OrderProduct.objects.create(
                                order=order,
                                payment=payment,
                                user=request.user,
                                product=item.product,
                                quantity=item.quantity,
                                product_price=item.product.price,
                                ordered=True,
                            )
                            order_product.variation.set(item.variations.all())
                            order_product.save()

                            #Update the product stock
                            product = item.product
                            locked_product = locked_products[product.id]
                            locked_product.stock -= item.quantity
                            locked_product.save(update_fields=['stock'])

                        #Clear the cart
                        cart_items.update(is_active=False)
                        request.session.pop('pending_order_id', None)
                        request.session.pop('checkout_data', None)

                    #Send order received email to the customer
                    mail_subject = 'Order Places Successfully'
                    message = render_to_string('orders/order_received_email.html', {
                        'user': request.user,
                        'order': order,
                    })
                    to_email = request.user.email
                    send_email = EmailMessage(mail_subject, message, to=[to_email])
                    send_email.send()

                return JsonResponse({'redirect_url': order_complete_url(order, payment)})

            return JsonResponse({'error': 'Unsupported payment action.'}, status=400)
        except stripe.StripeError as error:
            return JsonResponse({'error': str(error)}, status=400)

    context = {
        'order': order,
        'cart_items': cart_items,
        'total': order.order_total - order.tax,
        'tax': order.tax,
        'grand_total': order.order_total,
        'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
        'country_code': country_code,
    }
    return render(request, "orders/payments.html", context)

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
    order_products = OrderProduct.objects.filter(order=order).select_related(
        'product'
    ).prefetch_related('variation')
    return render(request, "orders/order_complete.html", {
        'order': order,
        'payment': order.payment,
        'order_products': order_products,
        'subtotal': order.order_total - order.tax,
    })


def orders(request):
    return render(request, "orders/orders.html")