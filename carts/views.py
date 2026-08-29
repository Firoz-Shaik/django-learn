from django.shortcuts import render, redirect, get_object_or_404
from store.models import Product
from store.sku import find_sku, resolve_variations
from .models import Cart, CartItem
from .forms import CheckoutForm
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.models import UserProfile
from orders.coupons import coupon_from_session
from orders.models import Coupon
from .stock import cart_quantity_for_sku, stock_errors
from .totals import cart_totals


def _cart_id(request):
    cart = request.session.session_key
    if not cart:
        cart = request.session.create()
    return cart


def _active_cart_items(request):
    if request.user.is_authenticated:
        return CartItem.objects.filter(user=request.user, is_active=True).select_related(
            'product', 'sku'
        ).prefetch_related('variations')
    cart = Cart.objects.filter(cart_id=_cart_id(request)).first()
    if cart is None:
        return CartItem.objects.none()
    return CartItem.objects.filter(cart=cart, is_active=True).select_related(
        'product', 'sku'
    ).prefetch_related('variations')


def _cart_owner(request):
    if request.user.is_authenticated:
        return {'user': request.user}
    cart, _created = Cart.objects.get_or_create(cart_id=_cart_id(request))
    return {'cart': cart}


def merge_guest_cart(request, user):
    try:
        cart = Cart.objects.get(cart_id=_cart_id(request))
    except Cart.DoesNotExist:
        return
    guest_items = list(
        CartItem.objects.filter(cart=cart, is_active=True).prefetch_related('variations')
    )
    if not guest_items:
        return

    def item_key(item):
        if item.sku_id:
            return ('sku', item.sku_id)
        variation_ids = tuple(sorted(item.variations.values_list('id', flat=True)))
        return ('vars', item.product_id, variation_ids)

    user_items = list(
        CartItem.objects.filter(user=user, is_active=True).prefetch_related('variations')
    )
    user_map = {item_key(item): item for item in user_items}
    for guest in guest_items:
        match = user_map.get(item_key(guest))
        if match:
            match.quantity += guest.quantity
            match.save(update_fields=['quantity'])
            guest.delete()
        else:
            guest.user = user
            guest.cart = None
            guest.save(update_fields=['user', 'cart'])
            user_map[item_key(guest)] = guest


def _add_to_cart_redirect(request, product):
    if request.POST.get('return_to_cart'):
        return redirect('cart')
    return redirect('product_detail', product.category.slug, product.slug)


def checkout_initial(request):
    data = {
        'first_name': request.user.first_name or '',
        'last_name': request.user.last_name or '',
        'email': request.user.email or '',
        'phone_number': request.user.phone_number or '',
    }
    profile = UserProfile.objects.filter(user=request.user).first()
    if profile:
        data.update({
            'address_line_1': profile.address_line_1 or '',
            'address_line_2': profile.address_line_2 or '',
            'city': profile.city or '',
            'state': profile.state or '',
            'country': profile.country or '',
            'zip_code': profile.pin_code or '',
        })
    saved = request.session.get('checkout_data') or {}
    for key, value in saved.items():
        if value not in (None, ''):
            data[key] = value
    return {key: value for key, value in data.items() if value not in (None, '')}


def remove_from_cart(request, product_id, cart_item_id):
    product = get_object_or_404(Product, id=product_id)
    if request.user.is_authenticated:
        cart_item = CartItem.objects.get(product=product, user=request.user, id=cart_item_id)
    else:
        cart = Cart.objects.get(cart_id=_cart_id(request))
        cart_item = CartItem.objects.get(product=product, cart=cart, id=cart_item_id)
    if cart_item.quantity > 1:
        cart_item.quantity -= 1
        cart_item.save()
    else:
        cart_item.delete()
    return redirect('cart')


def remove_cart_item(request, product_id, cart_item_id):
    product = get_object_or_404(Product, id=product_id)
    if request.user.is_authenticated:
        cart_item = CartItem.objects.get(product=product, user=request.user, id=cart_item_id)
        cart_item.delete()
        return redirect('cart')
    cart = Cart.objects.get(cart_id=_cart_id(request))
    cart_item = CartItem.objects.get(product=product, cart=cart, id=cart_item_id)
    cart_item.delete()
    return redirect('cart')


def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method != 'POST':
        return redirect(product.get_url())
    variations, error = resolve_variations(product, request.POST)
    if error:
        messages.error(request, error)
        return _add_to_cart_redirect(request, product)
    sku = find_sku(product, variations)
    if sku is None or not sku.is_active:
        messages.error(request, f'{product.product_name} is not available in that combination.')
        return _add_to_cart_redirect(request, product)
    if not product.is_available:
        messages.error(request, f'{product.product_name} is currently unavailable.')
        return _add_to_cart_redirect(request, product)
    owner = _cart_owner(request)
    current_quantity = cart_quantity_for_sku(sku=sku, **owner)
    if current_quantity + 1 > sku.stock:
        if sku.stock == 0:
            messages.error(request, f'{product.product_name} ({sku.label()}) is currently out of stock.')
        else:
            messages.error(request, f'Only {sku.stock} {product.product_name} ({sku.label()}) item(s) are in stock.')
        return _add_to_cart_redirect(request, product)
    item = CartItem.objects.filter(product=product, sku=sku, is_active=True, **owner).first()
    if item:
        item.quantity += 1
        item.save(update_fields=['quantity'])
    else:
        item = CartItem.objects.create(product=product, sku=sku, quantity=1, **owner)
        if variations:
            item.variations.set(variations)
    return redirect('cart')


def cart(request):
    cart_items = []
    totals = {'total': 0, 'discount': 0, 'tax': 0, 'grand_total': 0, 'coupon': None}
    try:
        cart_items = _active_cart_items(request)
        totals = cart_totals(cart_items, coupon_from_session(request))
    except ObjectDoesNotExist:
        pass
    context = {'cart_items': cart_items, **totals}
    return render(request, 'store/cart.html', context)


@login_required
def checkout(request):
    cart_items = _active_cart_items(request)
    coupon = coupon_from_session(request)
    totals = cart_totals(cart_items, coupon)
    form = CheckoutForm(request.POST or None, initial=checkout_initial(request))
    if request.method == 'POST' and form.is_valid():
        stock_messages = stock_errors(cart_items)
        if stock_messages:
            for message in stock_messages:
                form.add_error(None, message)
        else:
            request.session['checkout_data'] = form.cleaned_data
            messages.success(request, 'Billing details received. Your order is ready to place.')
    context = {'form': form, 'cart_items': cart_items, **totals}
    return render(request, 'store/checkout.html', context)


@login_required
def apply_coupon(request):
    if request.method == 'POST':
        code = (request.POST.get('code') or '').strip()
        cart_items = _active_cart_items(request)
        subtotal = cart_totals(cart_items)['total']
        coupon = Coupon.objects.filter(code__iexact=code).first()
        if coupon is None or not coupon.is_valid(subtotal):
            request.session.pop('coupon_id', None)
            messages.error(request, 'This coupon is invalid or does not apply to your cart.')
        else:
            request.session['coupon_id'] = coupon.id
            messages.success(request, f'Coupon {coupon.code} applied.')
    return redirect(request.POST.get('next') or 'checkout')


@login_required
def remove_coupon(request):
    request.session.pop('coupon_id', None)
    messages.success(request, 'Coupon removed.')
    return redirect(request.POST.get('next') or request.GET.get('next') or 'checkout')
