from django.db import models
from django.urls import reverse
from accounts.models import Account

class VariationsManager(models.Manager):
    def colors(self):
        return super(VariationsManager, self).filter(variation_category='color', is_active=True)

    def sizes(self):
        return super(VariationsManager, self).filter(variation_category='size', is_active=True)

# Create your models here.
class Product(models.Model):
    product_name = models.CharField(max_length=200,unique=True)
    slug = models.SlugField(max_length=200,unique=True)
    description = models.TextField(max_length=500,blank=True)
    price = models.IntegerField()
    images = models.ImageField(upload_to='store/products', blank=True)
    stock = models.IntegerField()
    is_available = models.BooleanField(default=True)
    category = models.ForeignKey('category.Category',on_delete=models.CASCADE)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.product_name

    def get_url(self):
        return reverse('product_detail',args=[self.category.slug,self.slug])

    def get_primary_image(self):
        gallery_image = self.productgallery_set.first()
        return gallery_image.image if gallery_image else self.images

    def get_average_rating(self):
        average = self.reviewrating_set.filter(status=True).aggregate(
            average=models.Avg('rating')
        )['average']
        return average or 0

    def get_review_count(self):
        return self.reviewrating_set.filter(status=True).count()

    def total_sku_stock(self):
        from django.db.models import Sum
        total = self.skus.filter(is_active=True).aggregate(total=Sum('stock'))['total']
        return total if total is not None else self.stock

    def has_colors(self):
        return self.variation_set.colors().exists()

    def has_sizes(self):
        return self.variation_set.sizes().exists()
    
class Variation(models.Model):
    product = models.ForeignKey(Product,on_delete=models.CASCADE)
    variation_category = models.CharField(max_length=100,choices=(('color','color'),('size','size')))
    variation_value = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_date = models.DateTimeField(auto_now=True)
    objects = VariationsManager()

    def __str__(self):
        return self.variation_value

class ProductSKU(models.Model):
    product = models.ForeignKey(Product, related_name='skus', on_delete=models.CASCADE)
    color = models.ForeignKey(
        Variation, related_name='color_skus', on_delete=models.CASCADE,
        null=True, blank=True, limit_choices_to={'variation_category': 'color'},
    )
    size = models.ForeignKey(
        Variation, related_name='size_skus', on_delete=models.CASCADE,
        null=True, blank=True, limit_choices_to={'variation_category': 'size'},
    )
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'product SKU'
        verbose_name_plural = 'product SKUs'
        constraints = [
            models.UniqueConstraint(fields=['product', 'color', 'size'], name='unique_product_color_size_sku'),
        ]

    def __str__(self):
        parts = [self.product.product_name]
        if self.color:
            parts.append(str(self.color))
        if self.size:
            parts.append(str(self.size))
        return ' / '.join(parts)

    def label(self):
        parts = []
        if self.color:
            parts.append(self.color.variation_value)
        if self.size:
            parts.append(self.size.variation_value)
        return ' / '.join(parts) or 'Default'

class Wishlist(models.Model):
    user = models.ForeignKey(Account, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')

    def __str__(self):
        return f'{self.user.email} - {self.product.product_name}'

class ReviewRating(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    user = models.ForeignKey(Account, on_delete=models.CASCADE)
    subject = models.CharField(max_length=100, blank=True)
    review = models.TextField(max_length=500, blank=True)
    rating = models.FloatField()
    ip = models.CharField(max_length=20, blank=True)
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.subject

class ProductGallery(models.Model):
    product = models.ForeignKey(Product, default=None, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='store/products', max_length=255)

    class Meta:
        verbose_name = 'productgallery'
        verbose_name_plural = 'product gallery'

    def __str__(self):
        return self.product.product_name