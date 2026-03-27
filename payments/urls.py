from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('pricing/', views.pricing_page, name='pricing'),
    path('create-order/', views.create_order, name='create_order'),
    path('verify-payment/', views.verify_payment, name='verify_payment'),
]
