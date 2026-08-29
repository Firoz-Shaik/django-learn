from django.contrib import admin
from .models import Product, ProductSKU, Variation, ReviewRating, ProductGallery, Wishlist
from .sku import ensure_skus
import admin_thumbnails


@admin_thumbnails.thumbnail('image')
class ProductGalleryInline(admin.TabularInline):
    model = ProductGallery
    extra = 1


class VariationInline(admin.TabularInline):
    model = Variation
    extra = 1


class ProductSKUInline(admin.TabularInline):
    model = ProductSKU
    extra = 0

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        object_id = request.resolver_match.kwargs.get('object_id') if request.resolver_match else None
        if object_id and db_field.name == 'color':
            kwargs['queryset'] = Variation.objects.filter(product_id=object_id, variation_category='color')
        elif object_id and db_field.name == 'size':
            kwargs['queryset'] = Variation.objects.filter(product_id=object_id, variation_category='size')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class VariationAdmin(admin.ModelAdmin):
    list_display = ('product', 'variation_category', 'variation_value', 'is_active')
    list_editable = ('is_active',)
    list_filter = ('product', 'variation_category', 'variation_value')


class ProductSKUAdmin(admin.ModelAdmin):
    list_display = ('product', 'color', 'size', 'stock', 'is_active')
    list_editable = ('stock', 'is_active')
    list_filter = ('product', 'is_active')


class ProductAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'slug', 'price', 'stock', 'category', 'modified_date', 'is_available')
    prepopulated_fields = {'slug': ('product_name',)}
    list_filter = ('is_available', 'category')
    list_editable = ('price', 'is_available')
    exclude = ('images',)
    readonly_fields = ('stock',)
    inlines = [VariationInline, ProductSKUInline, ProductGalleryInline]

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        ensure_skus(form.instance)


admin.site.register(Product, ProductAdmin)
admin.site.register(Variation, VariationAdmin)
admin.site.register(ProductSKU, ProductSKUAdmin)
admin.site.register(ReviewRating)
admin.site.register(ProductGallery)
admin.site.register(Wishlist)
