from django.urls import path
from . import views

app_name = 'accounts'

from django.contrib.auth.views import LogoutView

urlpatterns = [
    path('setup-profile/', views.setup_profile, name='setup_profile'),
    path('guest-login/', views.guest_login, name='guest_login'),
    path('logout/', LogoutView.as_view(next_page='/'), name='logout'),
    path('hr/login/', views.hr_login, name='hr_login'),
    path('hr/register/', views.hr_register, name='hr_register'),
    # HR Credit & Unlock
    path('hr/api/unlock/<int:candidate_id>/', views.hr_unlock_candidate, name='hr_unlock'),
    path('hr/api/check-unlock/<int:candidate_id>/', views.hr_check_unlock, name='hr_check_unlock'),
    # HR Interview Requests
    path('hr/api/send-request/', views.hr_send_request, name='hr_send_request'),
    path('hr/api/sent-requests/', views.hr_sent_requests, name='hr_sent_requests'),
    # Candidate side
    path('api/hr-requests/', views.candidate_hr_requests, name='candidate_hr_requests'),
    path('api/hr-requests/<int:request_id>/read/', views.candidate_mark_read, name='candidate_mark_read'),
]
