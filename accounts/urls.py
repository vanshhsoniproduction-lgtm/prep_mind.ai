from django.urls import path
from . import views

app_name = 'accounts'

from django.contrib.auth.views import LogoutView

urlpatterns = [
    path('setup-profile/', views.setup_profile, name='setup_profile'),
    path('guest-login/', views.guest_login, name='guest_login'),
    path('logout/', LogoutView.as_view(next_page='/'), name='logout'),
]
