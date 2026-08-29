from django.contrib import admin

from .models import Coupon, Order, OrderProduct, Payment
from .services import notify_status_change


class OrderProductInline(admin.TabularInline):
    model = OrderProduct
    readonly_fields = ('payment', 'user', 'product', 'sku', 'variation', 'quantity', 'product_price', 'ordered')
    extra = 0


class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'full_name', 'phone', 'email', 'city', 'order_total', 'discount', 'tax', 'status', 'is_ordered', 'created_at')
    list_filter = ('status', 'is_ordered')
    search_fields = ('order_number', 'first_name', 'last_name', 'phone', 'email')
    inlines = [OrderProductInline]

    def save_model(self, request, obj, form, change):
        previous_status = None
        if change:
            previous_status = Order.objects.filter(pk=obj.pk).values_list('status', flat=True).first()
        super().save_model(request, obj, form, change)
        if change and previous_status and previous_status != obj.status:
            notify_status_change(obj, previous_status)


class OrderProductAdmin(admin.ModelAdmin):
    list_display = ('order', 'payment', 'user', 'product', 'sku', 'quantity', 'product_price', 'ordered', 'created_at', 'updated_at')
    list_filter = ('ordered', 'payment', 'user')
    search_fields = ('order', 'payment', 'user', 'product')


class PaymentAdmin(admin.ModelAdmin):
    list_display = ('user', 'payment_id', 'payment_method', 'amount_paid', 'status', 'created_at')
    list_filter = ('payment_method', 'status')
    search_fields = ('user', 'payment_id')


class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_type', 'amount', 'min_amount', 'is_active', 'usage_limit', 'used_count', 'valid_from', 'valid_to')
    list_editable = ('is_active',)
    search_fields = ('code',)


admin.site.register(Order, OrderAdmin)
admin.site.register(OrderProduct, OrderProductAdmin)
admin.site.register(Payment, PaymentAdmin)
admin.site.register(Coupon, CouponAdmin)
