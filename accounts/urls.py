from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('setup-profile/', views.setup_profile, name='setup_profile'),
    path('guest-login/', views.guest_login, name='guest_login'),
]
