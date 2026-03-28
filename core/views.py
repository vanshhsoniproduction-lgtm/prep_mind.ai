from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from interviews.models import InterviewSession
import datetime
from django.db.models import Avg, Count, F
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
    
    # Leaderboard (Top 3 only for normal dashboard)
    leaderboard = lb_queryset[:3]
    # Removed top 100 for normal users

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

    # HR Interview Requests for this user
    from accounts.models import HRInterviewRequest
    hr_requests = HRInterviewRequest.objects.filter(candidate=request.user).order_by('-created_at')[:10]
    unread_hr_count = HRInterviewRequest.objects.filter(candidate=request.user, is_read_by_candidate=False).count()

    context = {
        'recent_interviews': recent_interviews,
        'weekly_count': weekly_interviews,
        'leaderboard': leaderboard,
        'user_rank': user_rank,
        'user_avg_score': user_avg_score,
        'trigger_schedule': trigger_schedule,
        'schedule_session_id': schedule_session_id,
        'date_min': date_min,
        'date_max': date_max,
        'calendars': calendars,
        'hr_requests': hr_requests,
        'unread_hr_count': unread_hr_count,
    }
    return render(request, 'core/dashboard.html', context)

@login_required
def hr_dashboard(request):
    if not getattr(request.user, 'is_hr', False):
        return redirect('core:dashboard')
        
    User = get_user_model()
    from accounts.models import HRUnlockedCandidate, HRInterviewRequest
    
    # Leaderboard Logic Grouped by Target Role (Category)
    lb_queryset = User.objects.filter(is_hr=False).annotate(
        avg_score=Avg('interviewsession__technical_score'),
        total_sessions=Count('interviewsession')
    ).filter(avg_score__isnull=False).order_by('-avg_score')
    
    categories = {}
    
    # Efficiently add users to their respective category
    for u in lb_queryset:
        role_key = (u.target_role.strip().title() if u.target_role else 'Uncategorized')
        
        if role_key not in categories:
            categories[role_key] = []
            
        if len(categories[role_key]) < 100:
            categories[role_key].append(u)

    # Get unlocked candidate IDs for this HR
    unlocked_ids = list(HRUnlockedCandidate.objects.filter(
        hr_user=request.user
    ).values_list('candidate_id', flat=True))
    
    # Sent requests count
    sent_requests_count = HRInterviewRequest.objects.filter(hr_user=request.user).count()
    unread_by_candidate = HRInterviewRequest.objects.filter(hr_user=request.user, is_read_by_candidate=False).count()

    from django.conf import settings as django_settings
    
    context = {
        'categories': categories,
        'hr_credits': request.user.hr_credits,
        'unlocked_ids': unlocked_ids,
        'sent_requests_count': sent_requests_count,
        'unread_by_candidate': unread_by_candidate,
        'razorpay_key_id': django_settings.RAZORPAY_KEY_ID,
    }
    return render(request, 'core/hr_dashboard.html', context)

def about(request):
    return render(request, 'core/about.html')

def privacy(request):
    return render(request, 'core/privacy.html')

def terms(request):
    return render(request, 'core/terms.html')
