from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from interviews.models import InterviewSession
import datetime
from django.db.models import Avg, Count
from django.contrib.auth import get_user_model

def landing_page(request):
    return render(request, 'core/landing.html')

@login_required
def dashboard(request):
    User = get_user_model()
    
    # Statistics
    today = datetime.date.today()
    start_of_week = today - datetime.timedelta(days=today.weekday())
    weekly_interviews = (
        InterviewSession.objects.filter(
            user=request.user, 
            start_time__date__gte=start_of_week
        ).count()
    )
    
    # Leaderboard (Broader inclusion: any session with a score)
    lb_queryset = User.objects.annotate(
        avg_score=Avg('interviewsession__technical_score'),
        total_sessions=Count('interviewsession')
    ).filter(avg_score__isnull=False).order_by('-avg_score')
    
    leaderboard = lb_queryset[:3]
    leaderboard_all = lb_queryset[:100]

    # Current User Rank
    user_rank = None
    user_avg_score = None
    for i, u in enumerate(lb_queryset):
        if u.id == request.user.id:
            user_rank = i + 1
            user_avg_score = u.avg_score
            break

    recent_interviews = InterviewSession.objects.filter(user=request.user).order_by('-start_time')[:10]
    
    # Check for scheduling popup trigger
    schedule_session_id = request.GET.get('schedule_session_id')
    trigger_schedule = bool(schedule_session_id)

    # Dates for scheduling (Today up to end of next month)
    date_min = today.strftime('%Y-%m-%d')
    if today.month == 12:
        next_month_end = datetime.date(today.year + 1, 1, 31)
    else:
        next_month_end = (datetime.date(today.year, today.month + 1, 1) + datetime.timedelta(days=32)).replace(day=1) - datetime.timedelta(days=1)
    date_max = next_month_end.strftime('%Y-%m-%d')

    context = {
        'recent_interviews': recent_interviews,
        'weekly_count': weekly_interviews,
        'leaderboard': leaderboard,
        'leaderboard_all': leaderboard_all,
        'user_rank': user_rank,
        'user_avg_score': user_avg_score,
        'trigger_schedule': trigger_schedule,
        'schedule_session_id': schedule_session_id,
        'date_min': date_min,
        'date_max': date_max,
    }
    return render(request, 'core/dashboard.html', context)

def about(request):
    return render(request, 'core/about.html')

def privacy(request):
    return render(request, 'core/privacy.html')

def terms(request):
    return render(request, 'core/terms.html')

@login_required
def dashboard_redirect(request):
    return redirect('core:dashboard')
