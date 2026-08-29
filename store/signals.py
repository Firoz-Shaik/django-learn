from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import ProductSKU, Variation
from .sku import ensure_skus, sync_product_stock


@receiver(post_save, sender=Variation)
def create_skus_for_variation(sender, instance, **kwargs):
    ensure_skus(instance.product)


@receiver(post_save, sender=ProductSKU)
def refresh_product_stock(sender, instance, **kwargs):
    sync_product_stock(instance.product)
