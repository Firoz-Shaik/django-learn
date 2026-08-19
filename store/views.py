from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from carts.views import _cart_id
from .models import Product
from carts.models import CartItem
from category.models import Category
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
# Create your views here.

def store(request, category_slug=None):
    categories = None
    products = None
    if category_slug != None:
        categories = get_object_or_404(Category, slug=category_slug)
        # include all products in the category; template will mark out-of-stock items
        products = Product.objects.filter(category=categories).order_by('id')
        paginator = Paginator(products, 3)
        page = request.GET.get('page')
        paged_products = paginator.get_page(page)
        
        product_count = products.count()
    else:
        # include all products so out-of-stock items appear with proper label
        products = Product.objects.all().order_by('id')
        product_count = products.count()
        paginator = Paginator(products, 3)
        page = request.GET.get('page')        
        paged_products = paginator.get_page(page)

    context = {
        'products': paged_products,
        'product_count': product_count,
        }
    return render(request, "store/store.html", context)

def product_detail(request, category_slug, product_slug):
    try:
        single_product = Product.objects.get(category__slug=category_slug, slug=product_slug)
        in_cart = CartItem.objects.filter(cart__cart_id=_cart_id(request), product=single_product).exists()
    except Exception as e:
        raise e
    context = {
        'single_product': single_product,
        'in_cart': in_cart
    }
    return render(request, "store/product_detail.html", context)

def search(request):
    # If no keyword supplied, redirect to the main store page (shows all products)
    keyword = request.GET.get('keyword', '').strip()
    if not keyword:
        return redirect('store')

    products = Product.objects.order_by('-created_date').filter(
        Q(description__icontains=keyword) | Q(product_name__icontains=keyword)
    )
    product_count = products.count()

    context = {
        'products': products,
        'product_count': product_count,
    }
    return render(request, "store/store.html", context)