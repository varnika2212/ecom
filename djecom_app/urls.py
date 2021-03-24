from django.urls import path
from .views import (
                    ItemDetailView,
                    HomeView,
                    CheckoutView,
                    add_to_cart,
                    remove_from_cart,
                    OrderSummaryView,
                    remove_single_item_from_cart,
                    PaymentView,
                    RequestRefundView,
                    tshirts)

app_name='djecom_app'
urlpatterns=[
    path('',HomeView.as_view(),name='home'),
    path('tshirts/',tshirts,name='tshirts'),
    path('checkout/',CheckoutView.as_view(),name='checkout'),
    path('product/<slug>',ItemDetailView.as_view(),name='products'),
    path('add_to_cart/<slug>',add_to_cart,name='add_to_cart'),
    path('remove_from_cart/<slug>',remove_from_cart,name='remove_from_cart'),
    path('order_summary/',OrderSummaryView.as_view(),name='order_summary'),
    path('remove_single_item_from_cart/<slug>',remove_single_item_from_cart,name='remove_single_item_from_cart'),
    path('payment/<payment_option>/',PaymentView.as_view(),name='payment'),
    path('request_refund/',RequestRefundView.as_view(),name='request_refund'),

]
