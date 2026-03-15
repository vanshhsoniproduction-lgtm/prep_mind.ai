from django.urls import path
from . import views

app_name = 'interviews'

urlpatterns = [
    path('start/', views.start_interview, name='start'),
    path('room/<int:session_id>/', views.room, name='room'),
    path('api/response/<int:session_id>/', views.handle_response, name='handle_response'),
    path('api/evaluate/<int:session_id>/', views.evaluate_coding_round, name='evaluate_coding'),
    path('schedule-next-interview/', views.schedule_next_interview, name='schedule_next_interview'),
    path('api/schedule-interview/', views.api_schedule_interview, name='api_schedule_interview'),
    path('api/create-doc-report/', views.api_create_doc_report, name='api_create_doc_report'),
]