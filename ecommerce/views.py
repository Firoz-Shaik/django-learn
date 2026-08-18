from django.shortcuts import render

from store.models import Product

def index(request):
    # include all products on the homepage so out-of-stock items can be shown
    products = Product.objects.all()
    context = {
        'products': products,
    }
    return render(request, "index.html", context)