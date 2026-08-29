from django.db import migrations


def seed_skus(apps, schema_editor):
    Product = apps.get_model('store', 'Product')
    Variation = apps.get_model('store', 'Variation')
    ProductSKU = apps.get_model('store', 'ProductSKU')

    for product in Product.objects.all():
        colors = list(Variation.objects.filter(product=product, variation_category='color', is_active=True))
        sizes = list(Variation.objects.filter(product=product, variation_category='size', is_active=True))
        if colors and sizes:
            combos = [(color, size) for color in colors for size in sizes]
        elif colors:
            combos = [(color, None) for color in colors]
        elif sizes:
            combos = [(None, size) for size in sizes]
        else:
            combos = [(None, None)]

        existing = list(ProductSKU.objects.filter(product=product))
        if not existing:
            skus = [
                ProductSKU(product=product, color=color, size=size, stock=0, is_active=True)
                for color, size in combos
            ]
            ProductSKU.objects.bulk_create(skus)
            existing = list(ProductSKU.objects.filter(product=product))

        if existing and product.stock and not any(sku.stock for sku in existing):
            base, remainder = divmod(max(product.stock, 0), len(existing))
            for index, sku in enumerate(existing):
                sku.stock = base + (1 if index < remainder else 0)
                sku.save(update_fields=['stock'])
        total = sum(sku.stock for sku in ProductSKU.objects.filter(product=product, is_active=True))
        Product.objects.filter(pk=product.pk).update(stock=total)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0007_product_sku_wishlist_coupons'),
    ]

    operations = [
        migrations.RunPython(seed_skus, noop),
    ]
