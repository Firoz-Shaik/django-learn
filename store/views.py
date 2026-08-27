from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from carts.views import _cart_id
from .forms import ReviewForm
from .models import Product, ProductGallery, ReviewRating
from orders.models import OrderProduct
from carts.models import CartItem
from category.models import Category
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.decorators import login_required
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
    product_reviews = ReviewRating.objects.filter(product=single_product, status=True)
    product_gallery = ProductGallery.objects.filter(product=single_product)
    average_rating = single_product.get_average_rating()
    ordered_products = OrderProduct.objects.filter(
        user=request.user,
        product=single_product,
        order__user=request.user,
        order__is_ordered=True,
        ordered=True,
    ).exists() if request.user.is_authenticated else False
    user_review = ReviewRating.objects.filter(
        product=single_product, user=request.user
    ).first() if request.user.is_authenticated else None
    context = {
        'single_product': single_product,
        'in_cart': in_cart,
        'product_reviews' : product_reviews,
        'average_rating': average_rating,
        'review_count': single_product.get_review_count(),
        'ordered_products': ordered_products,
        'user_review': user_review,
        'product_gallery': product_gallery,
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

@login_required
def submit_review(request, product_id):
    url = request.META.get('HTTP_REFERER')
    product = get_object_or_404(Product, id=product_id)
    has_purchased = OrderProduct.objects.filter(
        user=request.user,
        product=product,
        order__user=request.user,
        order__is_ordered=True,
        ordered=True,
    ).exists()
    if not has_purchased:
        messages.error(request, 'You can review this product only after purchasing it.')
        return redirect(url or product.get_url())

    if request.method == 'POST':
        try:
            reviews = ReviewRating.objects.get(user=request.user, product=product)
            form = ReviewForm(request.POST, instance=reviews)
            if form.is_valid():
                form.save()
                messages.success(request, 'Thank you! Your review has been updated.')
        except ReviewRating.DoesNotExist:
            form = ReviewForm(request.POST)
            if form.is_valid():
                data = form.save(commit=False)
                data.ip = request.META.get('REMOTE_ADDR')
                data.product = product
                data.user = request.user
                data.save()
                messages.success(request, 'Thank you! Your review has been submitted.')
        return redirect(url or product.get_url())

    return redirect(url or product.get_url())

