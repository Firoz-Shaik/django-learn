from django.shortcuts import render, get_object_or_404
from .models import Product
from category.models import Category
# Create your views here.

def store(request, category_slug=None):
    categories = None
    products = None
    if category_slug != None:
        categories = get_object_or_404(Category, slug=category_slug)
        # include all products in the category; template will mark out-of-stock items
        products = Product.objects.filter(category=categories)
        product_count = products.count()
    else:
        # include all products so out-of-stock items appear with proper label
        products = Product.objects.all()
        product_count = products.count()
    context = {
        'products': products,
        'product_count': product_count,
        }
    return render(request, "store/store.html", context)

def product_detail(request, category_slug, product_slug):
    try:
        single_product = Product.objects.get(category__slug=category_slug, slug=product_slug)
    except Exception as e:
        raise e
    context = {
        'single_product': single_product,
    }
    return render(request, "store/product_detail.html", context)