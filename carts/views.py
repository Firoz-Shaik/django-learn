from django.shortcuts import render, redirect, get_object_or_404
from store.models import Product, Variation
from .models import Cart, CartItem
from .forms import CheckoutForm
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .stock import cart_quantity_for_product, stock_errors
# Create your views here.


def _cart_id(request):
    cart = request.session.session_key
    if not cart:
        cart = request.session.create()
    return cart

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
    else:
        cart = Cart.objects.get(cart_id=_cart_id(request))
        cart_item = CartItem.objects.get(product=product, cart=cart, id=cart_item_id)
        cart_item.delete()
    return redirect('cart')

def add_to_cart(request, product_id):
    product = Product.objects.get(id=product_id)
    product_variation = []

    if request.method == 'POST':
        for item in request.POST:
            key = item
            value = request.POST[key]
            try:
                variation = Variation.objects.get(product=product, variation_category__iexact=key, variation_value__iexact=value)
                product_variation.append(variation)
            except:
                pass
    current_user = request.user
    if current_user.is_authenticated:
        current_quantity = cart_quantity_for_product(product=product, user=current_user)
        if not product.is_available:
            messages.error(request, f'{product.product_name} is currently unavailable.')
            return redirect('cart' if request.POST.get('return_to_cart') else 'product_detail',
                            *([] if request.POST.get('return_to_cart') else [product.category.slug, product.slug]))
        if current_quantity + 1 > product.stock:
            messages.error(request, f'Only {product.stock} {product.product_name} item(s) are in stock.')
            return redirect('cart' if request.POST.get('return_to_cart') else 'product_detail',
                            *([] if request.POST.get('return_to_cart') else [product.category.slug, product.slug]))
        is_cart_item_exists = CartItem.objects.filter(
            product=product, user=current_user, is_active=True
        ).exists()
        if is_cart_item_exists:
            cart_items = CartItem.objects.filter(
                product=product, user=current_user, is_active=True
            )
            existing_variations = []
            item_id = []
            for item in cart_items:
                existing_variation = item.variations.all()
                # store variation ids sorted so order doesn't matter
                existing_variations.append(sorted([v.id for v in existing_variation]))
                item_id.append(item.id)
    
            product_variation_ids = sorted([v.id for v in product_variation])
    
            if product_variation_ids in existing_variations:
                index = existing_variations.index(product_variation_ids)
                id = item_id[index]
                item = CartItem.objects.get(product=product, id=id)
                item.quantity += 1
                item.save()
            else:
                item = CartItem.objects.create(product=product, quantity=1, user=current_user)
                if len(product_variation) > 0:
                    item.variations.clear()
                    item.variations.add(*product_variation)
                item.save()
        else:
            cart_item = CartItem.objects.create(
                product=product,
                quantity=1,
                user=current_user
            )
            if len(product_variation) > 0:
                cart_item.variations.clear()
                cart_item.variations.add(*product_variation)
            cart_item.save()
        return redirect('cart')
    else:
        try:
            cart = Cart.objects.get(cart_id=_cart_id(request))
        except Cart.DoesNotExist:
            cart = Cart.objects.create(cart_id=_cart_id(request))
            cart.save()
        current_quantity = cart_quantity_for_product(product=product, cart=cart)
        if not product.is_available:
            messages.error(request, f'{product.product_name} is currently unavailable.')
            return redirect('cart' if request.POST.get('return_to_cart') else 'product_detail',
                            *([] if request.POST.get('return_to_cart') else [product.category.slug, product.slug]))
        if current_quantity + 1 > product.stock:
            if product.stock == 0:
                messages.error(request, f'{product.product_name} is currently unavailable.')
            else:
                messages.error(request, f'Only {product.stock} {product.product_name} item(s) are in stock.')
            return redirect('cart' if request.POST.get('return_to_cart') else 'product_detail',
                            *([] if request.POST.get('return_to_cart') else [product.category.slug, product.slug]))
        is_cart_item_exists = CartItem.objects.filter(
            product=product, cart=cart, is_active=True
        ).exists()

        if is_cart_item_exists:
            cart_items = CartItem.objects.filter(
                product=product, cart=cart, is_active=True
            )
            existing_variations = []
            item_id = []
            for item in cart_items:
                existing_variation = item.variations.all()
                # store variation ids sorted so order doesn't matter
                existing_variations.append(sorted([v.id for v in existing_variation]))
                item_id.append(item.id)

            product_variation_ids = sorted([v.id for v in product_variation])

            if product_variation_ids in existing_variations:
                index = existing_variations.index(product_variation_ids)
                id = item_id[index]
                item = CartItem.objects.get(product=product, id=id)
                item.quantity += 1
                item.save()
            else:
                item = CartItem.objects.create(product=product, quantity=1, cart=cart)
                if len(product_variation) > 0:
                    item.variations.clear()
                    item.variations.add(*product_variation)
                item.save()
        else:
            cart_item = CartItem.objects.create(
                product=product,
                quantity=1,
                cart=cart
            )
            if len(product_variation) > 0:
                cart_item.variations.clear()
                cart_item.variations.add(*product_variation)
            cart_item.save()
        return redirect('cart')
def cart(request, total=0, quantity=0, cart_items=None):
    tax = 0
    grand_total = 0
    try:
        if request.user.is_authenticated:
            cart_items = CartItem.objects.filter(user=request.user, is_active=True)
        else:
            cart = Cart.objects.get(cart_id=_cart_id(request))
            cart_items = CartItem.objects.filter(cart=cart, is_active=True)
        for cart_item in cart_items:
            total += (cart_item.product.price * cart_item.quantity)
            quantity += cart_item.quantity
        tax = (12 * total) / 100
        grand_total = round((total + tax), 2)
    except ObjectDoesNotExist:
        pass
    context = {
        'total': total,
        'quantity': quantity,
        'cart_items': cart_items,
        'tax': tax,
        'grand_total': grand_total,
    }
    return render(request, "store/cart.html", context)

@login_required
def checkout(request):
    saved_checkout_data = request.session.get('checkout_data', {})
    form = CheckoutForm(request.POST or None, initial=saved_checkout_data)
    total = 0
    quantity = 0
    tax = 0
    grand_total = 0
    try:
        if request.user.is_authenticated:
            cart_items = CartItem.objects.filter(user=request.user, is_active=True)
        else:
            cart = Cart.objects.get(cart_id=_cart_id(request))
            cart_items = CartItem.objects.filter(cart=cart, is_active=True)
        for cart_item in cart_items:
            total += (cart_item.product.price * cart_item.quantity)
            quantity += cart_item.quantity
        tax = (12 * total) / 100
        grand_total = round((total + tax), 2)
    except ObjectDoesNotExist:
        pass
    if request.method == 'POST' and form.is_valid():
        stock_messages = stock_errors(cart_items)
        if stock_messages:
            for message in stock_messages:
                form.add_error(None, message)
        else:
            request.session['checkout_data'] = form.cleaned_data
            messages.success(request, 'Billing details received. Your order is ready to place.')
    context = {
        'form': form,
        'total': total,
        'quantity': quantity,
        'cart_items': cart_items,
        'tax': tax,
        'grand_total': grand_total,
    }
    return render(request, "store/checkout.html", context)