from django.urls import path
from . import views

urlpatterns = [
    path('', views.orders, name='orders'),
    path('place_order/', views.place_order, name='place_order'),
    path('payments/', views.payments, name='payments'),
    path('order_complete/', views.order_complete, name='order_complete'),
    path('order_details/<str:order_number>/', views.order_details, name='order_details'),
    path('cancel_order/<str:order_number>/', views.cancel_order, name='cancel_order'),
]