from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('pricing/', views.pricing_page, name='pricing'),
    path('create-order/', views.create_order, name='create_order'),
    path('verify-payment/', views.verify_payment, name='verify_payment'),
    # HR Credit Payments
    path('hr/create-order/', views.hr_create_order, name='hr_create_order'),
    path('hr/verify-payment/', views.hr_verify_payment, name='hr_verify_payment'),
]
