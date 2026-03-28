from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.landing_page, name='landing_page'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('about/', views.about, name='about'),
    path('privacy/', views.privacy, name='privacy'),
    path('terms/', views.terms, name='terms'),
    path('refunds/', views.refunds, name='refunds'),
    path('core/dashboard/', views.dashboard_redirect, name='dashboard_redirect'),
    path('hr-dashboard/', views.hr_dashboard, name='hr_dashboard'),
]
