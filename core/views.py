from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from interviews.models import InterviewSession

def landing_page(request):
    return render(request, 'core/index.html')

@login_required
def dashboard(request):
    # Fetch recent interviews for the logged-in user
    recent_interviews = InterviewSession.objects.filter(user=request.user).order_by('-start_time')[:5]
    
    context = {
        'recent_interviews': recent_interviews,
    }
    return render(request, 'core/dashboard.html', context)
