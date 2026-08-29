from django.db import migrations


def assign_cart_skus(apps, schema_editor):
    CartItem = apps.get_model('carts', 'CartItem')
    ProductSKU = apps.get_model('store', 'ProductSKU')
    for item in CartItem.objects.all():
        variations = list(item.variations.all())
        color = next((variation for variation in variations if variation.variation_category == 'color'), None)
        size = next((variation for variation in variations if variation.variation_category == 'size'), None)
        sku = ProductSKU.objects.filter(
            product_id=item.product_id,
            color=color,
            size=size,
        ).first()
        if sku:
            CartItem.objects.filter(pk=item.pk).update(sku=sku)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('carts', '0006_product_sku_wishlist_coupons'),
        ('store', '0008_seed_product_skus'),
    ]

    operations = [
        migrations.RunPython(assign_cart_skus, noop),
    ]
