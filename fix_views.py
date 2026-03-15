import sys

with open("interviews/views.py", "r") as f:
    text = f.read()

old_str = """@login_required
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
        return JsonResponse({'success': False, 'error': str(e)})"""

new_str = """@login_required
@require_POST
def api_schedule_interview(request):
    try:
        data = json.loads(request.body)
        title = data.get('title', 'PrepMind Mock Interview')
        date_str = data.get('date')
        time_str = data.get('time')

        if not date_str or not time_str:
            return JsonResponse({'success': False, 'error': 'Date and time are required'})

        from .services.google_calendar_service import create_calendar_event
        event_link, meet_link = create_calendar_event(
            user=request.user,
            title=title,
            date=date_str,
            time=time_str,
            role="Interactive Mock"
        )
        return JsonResponse({'success': True, 'event_link': event_link, 'meet_link': meet_link})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})"""

if old_str in text:
    with open("interviews/views.py", "w") as f:
        f.write(text.replace(old_str, new_str))
    print("Replaced successfully")
else:
    print("Could not find the block to replace")
