from django.contrib import admin
from .models import Order, OrderProduct, Payment
# Register your models here.

class OrderProductInline(admin.TabularInline):
    model = OrderProduct
    readonly_fields = ('payment', 'user', 'product', 'variation','quantity', 'product_price', 'ordered')
    extra = 0

class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'full_name', 'phone', 'email', 'city', 'order_total', 'tax', 'status', 'is_ordered', 'created_at')
    list_filter = ('status', 'is_ordered')
    search_fields = ('order_number', 'first_name', 'last_name', 'phone', 'email')
    inlines = [OrderProductInline]
class OrderProductAdmin(admin.ModelAdmin):
    list_display = ('order', 'payment', 'user', 'product', 'quantity', 'product_price', 'ordered', 'created_at', 'updated_at')
    list_filter = ('ordered', 'payment', 'user')
    search_fields = ('order', 'payment', 'user', 'product')

class PaymentAdmin(admin.ModelAdmin):
    list_display = ('user', 'payment_id', 'payment_method', 'amount_paid', 'status', 'created_at')
    list_filter = ('payment_method', 'status')
    search_fields = ('user', 'payment_id')

admin.site.register(Order, OrderAdmin)
admin.site.register(OrderProduct, OrderProductAdmin)
admin.site.register(Payment, PaymentAdmin)