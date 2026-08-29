from store.sku import find_sku


def item_sku(item, locked_skus=None):
    if item.sku_id and locked_skus is not None and item.sku_id in locked_skus:
        return locked_skus[item.sku_id]
    if item.sku_id:
        return item.sku
    return find_sku(item.product, list(item.variations.all()))


def stock_errors(cart_items, locked_skus=None):
    quantities = {}
    sku_map = {}
    errors = []
    for item in cart_items:
        sku = item_sku(item, locked_skus)
        product = item.product
        if not product.is_available:
            errors.append(f'{product.product_name} is not available.')
            continue
        if sku is None or not sku.is_active:
            errors.append(f'{product.product_name} ({_variation_label(item)}) is no longer available.')
            continue
        quantities[sku.id] = quantities.get(sku.id, 0) + item.quantity
        sku_map[sku.id] = sku

    for sku_id, quantity in quantities.items():
        sku = sku_map[sku_id]
        label = f'{sku.product.product_name} ({sku.label()})'
        if quantity > sku.stock:
            if sku.stock == 0:
                errors.append(f'{label} is currently out of stock.')
            else:
                errors.append(
                    f'{label} has only {sku.stock} item(s) in stock; your cart requests {quantity}.'
                )
    return errors


def _variation_label(item):
    values = [str(variation) for variation in item.variations.all()]
    return ' / '.join(values) if values else 'selected option'


def cart_quantity_for_sku(*, sku, user=None, cart=None):
    from .models import CartItem
    filters = {'sku': sku, 'is_active': True}
    filters['user' if user is not None else 'cart'] = user if user is not None else cart
    return sum(item.quantity for item in CartItem.objects.filter(**filters))
