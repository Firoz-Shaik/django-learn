from django.db import models
from accounts.models import Account
from store.models import Product, Variation, ProductSKU

class Coupon(models.Model):
    DISCOUNT_PERCENT = 'percent'
    DISCOUNT_FIXED = 'fixed'
    DISCOUNT_TYPES = (
        (DISCOUNT_PERCENT, 'Percent'),
        (DISCOUNT_FIXED, 'Fixed amount'),
    )

    code = models.CharField(max_length=30, unique=True)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPES, default=DISCOUNT_PERCENT)
    amount = models.FloatField(help_text='Percent (0-100) or fixed amount in INR')
    min_amount = models.FloatField(default=0)
    is_active = models.BooleanField(default=True)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_to = models.DateTimeField(null=True, blank=True)
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    used_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.code

    def is_valid(self, subtotal=None):
        from django.utils import timezone
        if not self.is_active:
            return False
        now = timezone.now()
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_to and now > self.valid_to:
            return False
        if self.usage_limit is not None and self.used_count >= self.usage_limit:
            return False
        if subtotal is not None and subtotal < self.min_amount:
            return False
        return True

    def discount_for(self, subtotal):
        if not self.is_valid(subtotal):
            return 0
        if self.discount_type == self.DISCOUNT_PERCENT:
            return round(min(subtotal, subtotal * self.amount / 100), 2)
        return round(min(subtotal, self.amount), 2)


class Payment(models.Model):
    user = models.ForeignKey(Account, on_delete=models.CASCADE)
    payment_id = models.CharField(max_length=100)
    payment_method = models.CharField(max_length=100)
    amount_paid = models.CharField(max_length=100)
    status = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.payment_id

class Order(models.Model):
    STATUS = (
        ('New', 'New'),
        ('Accepted', 'Accepted'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    )

    user = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True)
    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, blank=True, null=True)
    order_number = models.CharField(max_length=20)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    phone = models.CharField(max_length=15)
    email = models.EmailField(max_length=50)
    address_line_1 = models.CharField(max_length=50)
    address_line_2 = models.CharField(max_length=50, blank=True)
    country = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    city = models.CharField(max_length=50)
    zip_code = models.CharField(max_length=10)
    order_note = models.CharField(max_length=100, blank=True)
    order_total = models.FloatField()
    tax = models.FloatField()
    discount = models.FloatField(default=0)
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)
    stock_restored = models.BooleanField(default=False)
    status = models.CharField(max_length=10, choices=STATUS, default='New')
    ip = models.CharField(blank=True, max_length=20)
    is_ordered = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.first_name

    def full_name(self):
        return f'{self.first_name} {self.last_name}'


    def billing_address(self):
        return f'{self.address_line_1}, {self.address_line_2}, {self.city}, {self.state}, {self.country}, {self.zip_code}'


class OrderProduct(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, blank=True, null=True)
    user = models.ForeignKey(Account, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    sku = models.ForeignKey(ProductSKU, on_delete=models.SET_NULL, null=True, blank=True)
    variation = models.ManyToManyField(Variation, blank=True)
    quantity = models.IntegerField()
    product_price = models.FloatField()
    ordered = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.product.product_name

    def subtotal(self):
        return self.product_price * self.quantity