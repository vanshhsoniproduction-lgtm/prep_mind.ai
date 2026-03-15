from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    path('', views.overview, name='overview'),
    path('interview/<int:session_id>/', views.session_detail, name='session_detail'),
]
