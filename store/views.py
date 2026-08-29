from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from carts.views import _cart_id
from .forms import ReviewForm
from .models import Product, ProductGallery, ReviewRating, Wishlist, Variation
from .sku import sku_payload
from orders.models import OrderProduct
from carts.models import CartItem
from category.models import Category
from django.contrib import messages
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required

PRICE_CHOICES = [0, 500, 1000, 1500, 2000, 3000]


def _int_or_none(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def apply_store_filters(request, products):
    selected_sizes = [value.strip() for value in request.GET.getlist('size') if value.strip()]
    min_price = _int_or_none(request.GET.get('min_price')) or 0
    max_price = _int_or_none(request.GET.get('max_price'))
    sort = request.GET.get('sort') or 'newest'

    size_options = list(
        Variation.objects.filter(
            product__in=products,
            variation_category='size',
            is_active=True,
        ).values_list('variation_value', flat=True).distinct()
    )
    size_options.sort(key=lambda value: (not value.isdigit(), int(value) if value.isdigit() else value.lower()))

    if selected_sizes:
        size_query = Q()
        for size in selected_sizes:
            size_query |= Q(
                variation__variation_category='size',
                variation__variation_value__iexact=size,
            )
        products = products.filter(size_query).distinct()
    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)

    if sort == 'price_asc':
        products = products.order_by('price', 'id')
    elif sort == 'price_desc':
        products = products.order_by('-price', 'id')
    else:
        sort = 'newest'
        products = products.order_by('-created_date', 'id')

    query = request.GET.copy()
    query.pop('page', None)
    return products, {
        'size_options': size_options,
        'selected_sizes': selected_sizes,
        'min_price': min_price,
        'max_price': '' if max_price is None else max_price,
        'sort': sort,
        'price_choices': PRICE_CHOICES,
        'filter_query': query.urlencode(),
        'keyword': request.GET.get('keyword', '').strip(),
    }


def _store_page(request, products):
    products, filters = apply_store_filters(request, products)
    product_count = products.count()
    paged_products = Paginator(products, 6).get_page(request.GET.get('page'))
    return render(request, 'store/store.html', {
        'products': paged_products,
        'product_count': product_count,
        **filters,
    })


def store(request, category_slug=None):
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = Product.objects.filter(category=category)
    else:
        products = Product.objects.all()
    return _store_page(request, products)


def search(request):
    keyword = request.GET.get('keyword', '').strip()
    if not keyword and not request.GET.getlist('size') and not request.GET.get('min_price') and not request.GET.get('max_price'):
        return redirect('store')
    products = Product.objects.all()
    if keyword:
        products = products.filter(
            Q(description__icontains=keyword) | Q(product_name__icontains=keyword)
        )
    return _store_page(request, products)

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
    in_wishlist = Wishlist.objects.filter(
        user=request.user, product=single_product
    ).exists() if request.user.is_authenticated else False
    context = {
        'single_product': single_product,
        'in_cart': in_cart,
        'in_wishlist': in_wishlist,
        'product_reviews' : product_reviews,
        'average_rating': average_rating,
        'review_count': single_product.get_review_count(),
        'ordered_products': ordered_products,
        'user_review': user_review,
        'product_gallery': product_gallery,
        'sku_data': sku_payload(single_product),
        'colors': single_product.variation_set.colors(),
        'sizes': single_product.variation_set.sizes(),
    }
    return render(request, "store/product_detail.html", context)

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


@login_required
def wishlist(request):
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related(
        'product', 'product__category'
    )
    return render(request, 'store/wishlist.html', {'wishlist_items': wishlist_items})


@login_required
def add_to_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    Wishlist.objects.get_or_create(user=request.user, product=product)
    messages.success(request, f'{product.product_name} was added to your wishlist.')
    return redirect(request.POST.get('next') or request.GET.get('next') or product.get_url())


@login_required
def remove_from_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    Wishlist.objects.filter(user=request.user, product=product).delete()
    messages.success(request, f'{product.product_name} was removed from your wishlist.')
    return redirect(request.POST.get('next') or request.GET.get('next') or 'wishlist')

