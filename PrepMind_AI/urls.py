"""
URL configuration for PrepMind_AI project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('user/', include('accounts.urls')),
    path('interviews/', include('interviews.urls')),
    path('analytics/', include('analytics.urls')),
    path('', include('core.urls')),
]
