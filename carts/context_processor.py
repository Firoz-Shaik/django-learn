from .models import Cart, CartItem
from .views import _cart_id

def counter(request):
    # don't run for admin URLs
    if 'admin' in request.path:
        return {}

    total_quantity = 0
    try:
        if request.user.is_authenticated:
            cart_items = CartItem.objects.filter(user=request.user)
            total_quantity = sum(item.quantity for item in cart_items)
        else:
            cart_id = _cart_id(request)
            cart = Cart.objects.filter(cart_id=cart_id).first()
            if cart:
                cart_items = CartItem.objects.filter(cart=cart, is_active=True)
                total_quantity = sum(item.quantity for item in cart_items)
    except Exception:
        total_quantity = 0

    return {'total_quantity': total_quantity}