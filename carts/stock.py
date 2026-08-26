from .models import CartItem


def stock_errors(cart_items, products=None):
    """Return product stock errors for the supplied active cart items."""
    quantities = {}
    products = products or {}
    for item in cart_items:
        quantities[item.product_id] = quantities.get(item.product_id, 0) + item.quantity
        if item.product_id not in products:
            products[item.product_id] = item.product

    errors = []
    for product_id, quantity in quantities.items():
        product = products[product_id]
        if not product.is_available:
            errors.append(f'{product.product_name} is not available.')
        elif quantity > product.stock:
            if product.stock == 0:
                errors.append(f'{product.product_name} is currently out of stock.')
            else:
                errors.append(
                f'{product.product_name} has only {product.stock} item(s) in stock; '
                f'your cart requests {quantity}.'
                )
    return errors


def cart_quantity_for_product(*, product, user=None, cart=None):
    filters = {'product': product, 'is_active': True}
    filters['user' if user is not None else 'cart'] = user if user is not None else cart
    return sum(item.quantity for item in CartItem.objects.filter(**filters))
