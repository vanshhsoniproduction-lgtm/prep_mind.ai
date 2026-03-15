import os

with open("interviews/views.py", "a") as f:
    f.write("""

# --- NEW FEATURES ---

import json
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .models import InterviewSession
from django.http import JsonResponse
from .services.google_docs_service import generate_interview_report

@login_required
def schedule_next_interview(request):
    session_id = request.GET.get('session_id')
    return render(request, 'interviews/schedule.html', {'session_id': session_id})

@login_required
@require_POST
def api_schedule_interview(request):
    try:
        data = json.loads(request.body)
        summary = data.get('summary', 'PrepMind Mock Interview')
        description = data.get('description', 'Your mock interview session is scheduled.')
        start_datetime = data.get('start_datetime')
        end_datetime = data.get('end_datetime')

        from .services.google_calendar_service import GoogleCalendarService
        service = GoogleCalendarService()
        event_link, meet_link = service.create_interview_event(
            summary=summary,
            description=description,
            start_datetime=start_datetime,
            end_datetime=end_datetime
        )
        return JsonResponse({'success': True, 'event_link': event_link, 'meet_link': meet_link})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@require_POST
def api_create_doc_report(request):
    try:
        data = json.loads(request.body)
        session_id = data.get('session_id')
        session = get_object_or_404(InterviewSession, id=session_id, user=request.user)

        # Basic report content from the session
        transcript = session.ai_feedback if session.ai_feedback else "No feedback available."
        
        doc_link = generate_interview_report(
            session_id=str(session.id),
            candidate_name=request.user.get_full_name() or request.user.username,
            transcript=transcript
        )
        return JsonResponse({'success': True, 'doc_link': doc_link})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
""")
