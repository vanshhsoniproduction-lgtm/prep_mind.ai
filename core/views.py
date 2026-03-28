from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from interviews.models import InterviewSession
import datetime
from django.db.models import Avg, Count
from django.contrib.auth import get_user_model

def landing_page(request):
    return render(request, 'core/landing.html')

def about(request):
    return render(request, 'core/about.html')

def privacy(request):
    return render(request, 'core/privacy.html')

def terms(request):
    return render(request, 'core/terms.html')

def refunds(request):
    return render(request, 'core/refunds.html')

def dashboard_redirect(request):
    return redirect('core:dashboard')

from django.utils import timezone

@login_required
def dashboard(request):
    User = get_user_model()
    now = timezone.localtime(timezone.now())
    today = now.date()
    
    # Statistics
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

    # Dates for scheduling
    date_min = today.strftime('%Y-%m-%d')
    next_month_raw = (today.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
    date_max = (next_month_raw.replace(day=28) + datetime.timedelta(days=4)).replace(day=1) - datetime.timedelta(days=1)
    date_max = date_max.strftime('%Y-%m-%d')

    # Pre-calculate status map for efficiency with PRIORITY
    full_history = InterviewSession.objects.filter(user=request.user).order_by('start_time')
    date_to_status = {}
    
    # Priority order: completed > scheduled > cancelled > aborted
    priority = {'has-green': 4, 'has-yellow': 3, 'has-red': 2, 'has-orange': 1, 'has-gray': 0, '': -1}

    for s in full_history:
        d_key = None
        s_status = ''
        
        if s.status == 'SCHEDULED' and s.scheduled_date:
            d_key = s.scheduled_date.strftime('%Y-%m-%d')
            s_status = 'has-yellow'
        elif s.start_time:
            local_dt = timezone.localtime(s.start_time)
            d_key = local_dt.strftime('%Y-%m-%d')
            s_map = {
                'COMPLETED': 'has-green',
                'CANCELLED_BY_USER': 'has-red',
                'FAILED_BY_AI': 'has-orange',
                'SCHEDULED': 'has-yellow'
            }
            s_status = s_map.get(s.status, 'has-gray')

        if d_key:
            current_p = priority.get(date_to_status.get(d_key, ''), -1)
            new_p = priority.get(s_status, -1)
            if new_p > current_p:
                date_to_status[d_key] = s_status

    # helper for 3-month calendar
    def get_month_calendar(date_obj):
        import calendar
        cal = calendar.monthcalendar(date_obj.year, date_obj.month)
        processed_weeks = []
        for week in cal:
            processed_week = []
            for day in week:
                if day == 0:
                    processed_week.append({'day': 0, 'status': '', 'is_today': False})
                else:
                    d_str = f"{date_obj.year}-{date_obj.month:02d}-{day:02d}"
                    processed_week.append({
                        'day': day,
                        'status': date_to_status.get(d_str, ''),
                        'is_today': (d_str == today.strftime('%Y-%m-%d'))
                    })
            processed_weeks.append(processed_week)
            
        return {
            'name': date_obj.strftime('%B %Y'),
            'weeks': processed_weeks
        }

    # Month objects
    prev_month = (today.replace(day=1) - datetime.timedelta(days=1)).replace(day=1)
    curr_month = today.replace(day=1)
    next_month = (today.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)

    calendars = [
        get_month_calendar(prev_month),
        get_month_calendar(curr_month),
        get_month_calendar(next_month)
    ]

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
        'calendars': calendars,
    }
    return render(request, 'core/dashboard.html', context)

def about(request):
    return render(request, 'core/about.html')

def privacy(request):
    return render(request, 'core/privacy.html')

def terms(request):
    return render(request, 'core/terms.html')
