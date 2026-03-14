from django.urls import path
from . import views

app_name = 'interviews'

urlpatterns = [
    path('start/', views.start_interview, name='start'),
    path('room/<int:session_id>/', views.room, name='room'),
    path('api/response/<int:session_id>/', views.handle_response, name='handle_response'),
    path('api/evaluate/<int:session_id>/', views.evaluate_coding_round, name='evaluate_coding'),
]