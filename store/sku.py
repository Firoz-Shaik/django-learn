from django.db.models import Sum

from .models import Product, ProductSKU, Variation


def sku_combos(product):
    colors = list(product.variation_set.filter(variation_category='color', is_active=True))
    sizes = list(product.variation_set.filter(variation_category='size', is_active=True))
    if colors and sizes:
        return [(color, size) for color in colors for size in sizes]
    if colors:
        return [(color, None) for color in colors]
    if sizes:
        return [(None, size) for size in sizes]
    return [(None, None)]


def sync_product_stock(product):
    total = product.skus.filter(is_active=True).aggregate(total=Sum('stock'))['total']
    Product.objects.filter(pk=product.pk).update(stock=total or 0)


def ensure_skus(product, distribute_stock=False):
    combos = sku_combos(product)
    existing = {(sku.color_id, sku.size_id): sku for sku in product.skus.all()}
    valid_keys = set()
    for color, size in combos:
        key = (color.id if color else None, size.id if size else None)
        valid_keys.add(key)
        if key not in existing:
            existing[key] = ProductSKU.objects.create(
                product=product, color=color, size=size, stock=0,
            )
        elif not existing[key].is_active:
            existing[key].is_active = True
            existing[key].save(update_fields=['is_active'])
    for key, sku in existing.items():
        if key not in valid_keys and sku.is_active:
            sku.is_active = False
            sku.save(update_fields=['is_active'])
    if distribute_stock:
        skus = list(existing.values())
        if skus and product.stock and not any(sku.stock for sku in skus):
            base, remainder = divmod(max(product.stock, 0), len(skus))
            for index, sku in enumerate(skus):
                sku.stock = base + (1 if index < remainder else 0)
                sku.save(update_fields=['stock'])
    sync_product_stock(product)
    return existing


def find_sku(product, variations):
    color = next((item for item in variations if item.variation_category == 'color'), None)
    size = next((item for item in variations if item.variation_category == 'size'), None)
    return ProductSKU.objects.filter(
        product=product, color=color, size=size, is_active=True,
    ).first()


def resolve_variations(product, post_data):
    selected = []
    if product.has_colors():
        value = (post_data.get('color') or '').strip()
        if not value:
            return None, 'Please select a color.'
        color = Variation.objects.filter(
            product=product, variation_category='color',
            variation_value__iexact=value, is_active=True,
        ).first()
        if color is None:
            return None, 'Selected color is not available.'
        selected.append(color)
    if product.has_sizes():
        value = (post_data.get('size') or '').strip()
        if not value:
            return None, 'Please select a size.'
        size = Variation.objects.filter(
            product=product, variation_category='size',
            variation_value__iexact=value, is_active=True,
        ).first()
        if size is None:
            return None, 'Selected size is not available.'
        selected.append(size)
    return selected, None


def sku_payload(product):
    colors = list(product.variation_set.colors())
    sizes = list(product.variation_set.sizes())
    skus = {}
    for sku in product.skus.filter(is_active=True):
        key = f'{sku.color_id or 0}-{sku.size_id or 0}'
        skus[key] = sku.stock
    return {
        'colors': [{'id': item.id, 'value': item.variation_value.lower(), 'label': item.variation_value} for item in colors],
        'sizes': [{'id': item.id, 'value': item.variation_value.lower(), 'label': item.variation_value} for item in sizes],
        'skus': skus,
    }
