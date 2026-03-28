
import json
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from responses.models import Answer

from .models import InterviewSession, Question
from .services.interview_agent import (
    evaluate_code,
    fallback_response,
    generate_final_feedback,
    generate_initial_question,
    generate_next_interaction,
)
from .services.resume_utils import extract_resume_text

LOGGER = logging.getLogger(__name__)


def _resume_context_for_user(user) -> str:
    resume_file = getattr(user, 'resume', None)
    if resume_file and getattr(resume_file, 'path', None):
        return extract_resume_text(resume_file.path)
    return ""

@login_required
def start_interview(request):
    if request.method == 'POST':
        # Check for credits
        if request.user.interview_credits <= 0:
            messages.warning(request, "You have run out of interview credits. Please top up to continue.")
            return redirect('payments:pricing')
            
        role = request.user.target_role or 'Software Engineer'
        experience_level = request.user.experience_level or 'Mid-Level'
        company = 'Google'
        personality = 'Friendly'

        resume_context = _resume_context_for_user(request.user)

        session = InterviewSession.objects.create(
            user=request.user,
            role=role,
            company_mode=company,
            personality_mode=personality,
            stage='tech1',
            question_count=1
        )
        
        # Deduct credit
        request.user.interview_credits -= 1
        request.user.save()

        try:
            ai_text = generate_initial_question(role, company, personality, experience_level, resume_context)
        except Exception as e:
            LOGGER.warning("[INTERVIEW] initial question fallback error=%s", str(e)[:300])
            ai_text = f'Hi there! I am your interviewer today. Tell me about your experience as a {role}.'
        
        Question.objects.create(session=session, question_text=ai_text, order=1)
        return redirect('interviews:room', session_id=session.id)
    return redirect('core:dashboard')

@login_required
def room(request, session_id):
    session = InterviewSession.objects.get(id=session_id, user=request.user)
    first_q = session.questions.order_by('order').first()

    first_text = first_q.question_text if first_q else 'Hello, are you ready to begin?'
    first_audio_url = ""

    context = {
        'session': session,
        'first_question_text': first_text,
        'first_audio_url': first_audio_url,
    }
    return render(request, 'interviews/room.html', context)

@csrf_exempt
@login_required
def handle_response(request, session_id):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'status': 'error'}, status=400)

    fallback_text = fallback_response()
    try:
        data = json.loads(request.body)
        user_transcript = data.get('transcript', '')
        resume_context = _resume_context_for_user(request.user)

        session = InterviewSession.objects.get(id=session_id)
        if session.stage == 'ended':
            if session.status != 'COMPLETED' and session.status != 'CANCELLED_BY_USER' and session.status != 'FAILED_BY_AI':
                 session.status = 'COMPLETED'
                 session.save()
            return JsonResponse({
                'success': True,
                'status': 'ended',
                'ai_text': fallback_text,
                'is_ended': True,
                'redirect_url': f'/dashboard/?schedule_session_id={session.id}',
            })

        questions = session.questions.order_by('order')
        
        history_list = []
        full_history_str = ''
        for q in questions:
            ans = Answer.objects.filter(question=q).first()
            
            exchange = {"Q": q.question_text[:250]}
            full_history_str += f'Interviewer: {q.question_text}\n'
            
            if ans and ans.transcript:
                exchange["A"] = ans.transcript[:300]
                full_history_str += f'Candidate: {ans.transcript}\n'
            if ans and ans.code_submitted:
                exchange["Code"] = "Code omitted for brevity"
                full_history_str += f'Candidate Code: {ans.code_submitted}\n'
                
            history_list.append(exchange)
            
        recent_history_json = json.dumps(history_list[-3:])

        last_q = questions.last()

        Answer.objects.create(
            session=session,
            question=last_q,
            transcript=user_transcript
        )
        
        if session.stage == 'tech1' and session.question_count >= 5:
            session.stage = 'coding1'
        elif session.stage == 'tech2' and session.question_count >= 10:
            session.stage = 'coding2'

        session.question_count += 1
        session.save()

        if session.stage == 'feedback' or session.question_count > 15:
            feedback_data = generate_final_feedback(full_history_str + f'Candidate: {user_transcript}\n', resume_context)
            session.technical_score = feedback_data.get('technical_score', 0)
            session.communication_score = feedback_data.get('communication_score', 0)
            session.confidence_score = feedback_data.get('confidence_score', 0)
            session.feedback_text = feedback_data.get('detailed_feedback', '')
            session.end_time = timezone.now()
            session.status = 'COMPLETED'
            session.stage = 'ended'
            session.save()
            
            response_data = {
                'success': True,
                'status': 'success',
                'ai_text': end_text,
                'is_ended': True,
                'redirect_url': f'/dashboard/?schedule_session_id={session.id}',
            }
            return JsonResponse(response_data)

        exp_level = request.user.experience_level or 'Mid-Level'
        interaction = generate_next_interaction(
            recent_history_json,
            user_transcript,
            session.role,
            exp_level,
            session.stage,
            resume_context,
        )
        
        Question.objects.create(
            session=session,
            question_text=interaction.get('text', ''),
            is_coding=(interaction.get('type') == 'coding'),
            order=session.question_count
        )
        
        response_data = {
            'success': True,
            'status': interaction.get('status', 'success'),
            'ai_text': interaction.get('text'),
            'type': interaction.get('type'),
            'is_ended': False,
        }
        
        if interaction.get('type') == 'coding':
            response_data['problem'] = interaction.get('problem')
            response_data['language'] = interaction.get('language')
            
        return JsonResponse(response_data)
    except Exception as e:  # noqa: BLE001
        LOGGER.error("[INTERVIEW] handle_response fallback error=%s", str(e)[:500])
        return JsonResponse({
            'success': True,
            'status': 'fallback',
            'ai_response': fallback_text,
            'ai_text': fallback_text,
            'is_ended': False,
        })

@csrf_exempt
@login_required
def evaluate_coding_round(request, session_id):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'status': 'error'}, status=400)

    fallback_text = fallback_response()
    try:
        data = json.loads(request.body)
        code = data.get('code', '')
        language = data.get('language', 'javascript')
        problem = data.get('problem', '')
        resume_context = _resume_context_for_user(request.user)

        session = InterviewSession.objects.get(id=session_id)
        last_q = session.questions.last()
        
        eval_result = evaluate_code(problem, code, language)
        passed = eval_result.get('passed', False)
        feedback_speech = eval_result.get('feedback_speech', 'Let us move on.')

        Answer.objects.create(
            session=session,
            question=last_q,
            transcript='[Code Submitted]',
            code_submitted=code,
            language_used=language,
            evaluation_passed=passed
        )

        session.question_count += 1
        
        if passed and session.stage == 'coding1':
            session.stage = 'tech2'
        else:
            session.stage = 'feedback'

        session.save()

        full_history_text = f'Problem: {problem}\nCode Submitted:\n{code}\nEvaluation: {"Passed" if passed else "Failed"}\n'
        recent_history_json = json.dumps([{
            "Task": "Coding Problem", 
            "Problem": problem[:150],
            "Status": "Passed" if passed else "Failed"
        }])
        
        if session.stage == 'feedback':
            feedback_data = generate_final_feedback(full_history_text, resume_context)
            session.stage = 'ended'
            session.technical_score = feedback_data.get('technical_score', 0)
            session.communication_score = feedback_data.get('communication_score', 0)
            session.confidence_score = feedback_data.get('confidence_score', 0)
            session.feedback_text = feedback_data.get('detailed_feedback', '')
            session.end_time = timezone.now()
            session.status = 'COMPLETED'
            session.save()
            return JsonResponse({
                'success': True,
                'status': 'success',
                'ai_text': feedback_speech + ' ' + feedback_data.get('spoken_text', ''),
                'is_ended': True,
                'redirect_url': f'/dashboard/?schedule_session_id={session.id}',
            })

        interaction = generate_next_interaction(
            recent_history_json,
            'Code generated.',
            session.role,
            request.user.experience_level or 'Mid',
            session.stage,
            resume_context,
        )
        Question.objects.create(
            session=session,
            question_text=interaction.get('text', ''),
            is_coding=False,
            order=session.question_count
        )
        
        ai_response_text = feedback_speech + ' ' + interaction.get('text', '')
        response_data = {
            'success': True,
            'status': interaction.get('status', 'success'),
            'ai_text': ai_response_text,
            'type': 'text',
            'is_ended': False
        }
        
        return JsonResponse(response_data)
    except Exception as e:  # noqa: BLE001
        LOGGER.error("[INTERVIEW] evaluate_coding_round fallback error=%s", str(e)[:500])
        return JsonResponse({
            'success': True,
            'status': 'fallback',
            'ai_response': fallback_text,
            'ai_text': fallback_text,
            'is_ended': False,
        })



# --- NEW FEATURES ---

import json
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .models import InterviewSession
from django.http import JsonResponse
from .services.google_docs_service import create_interview_report

@login_required
def schedule_next_interview(request):
    session_id = request.GET.get('session_id')
    return render(request, 'interviews/schedule.html', {'session_id': session_id})

@login_required
@require_POST
def api_schedule_interview(request):
    try:
        # Handle both JSON and standard POST data
        if request.content_type == 'application/json':
            data = json.loads(request.body)
            session_id = data.get('session_id')
            date_str = data.get('date')
            time_str = data.get('time', '10:00') # default or from field
        else:
            session_id = request.POST.get('session_id')
            date_str = request.POST.get('scheduled_date')
            time_str = request.POST.get('scheduled_time', '10:00')

        if not date_str:
            return JsonResponse({'success': False, 'error': 'Date is required'})

        # Update the session with the scheduled date
        session = InterviewSession.objects.get(id=session_id, user=request.user)
        session.scheduled_date = date_str
        session.status = 'SCHEDULED'
        session.save()

        # Attempt to create Google Calendar event if logic exists
        try:
            from .services.google_calendar_service import create_calendar_event
            # If time_str is empty we still provide a default
            create_calendar_event(
                user=request.user,
                title=f"PrepMind: {session.role} Interview",
                date=date_str,
                time=time_str,
                role=session.role
            )
        except Exception:
            # Calendar might not be linked, but we still mark it in our database
            pass

        return redirect('core:dashboard') # Redirect after successful schedule if from form
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@require_POST
def api_create_doc_report(request):
    try:
        data = json.loads(request.body)
        session_id = data.get('session_id')
        session = get_object_or_404(InterviewSession, id=session_id, user=request.user)

        # Basic report content from the session
        transcript = session.feedback_text if session.feedback_text else "No feedback available."
        
        doc_link = create_interview_report(
            user=request.user,
            candidate_name=request.user.get_full_name() or request.user.username,
            role=session.role,
            date=str(session.start_time.date()),
            transcript=transcript,
            scores=session.communication_score or "Not scored",
            strengths="Strengths determined by AI.",
            weaknesses="Areas to improve determined by AI.",
            improvement_plan="Practice mock sessions."
        )
        return JsonResponse({'success': True, 'doc_link': doc_link})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
@login_required
def get_candidate_details(request, user_id):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    try:
        user = User.objects.get(id=user_id)
        sessions = InterviewSession.objects.filter(user=user, technical_score__isnull=False).order_by('start_time')
        
        history = [{
            'date': s.start_time.strftime('%b %d'),
            'tech': s.technical_score,
            'comm': s.communication_score,
            'conf': s.confidence_score or 70,
            'role': s.role
        } for s in sessions]
        
        latest = sessions.last()
        feedback = {
            'strengths': "Problem solving, System design" if not latest else "Analytical thinking",
            'improvements': "Time complexity, Communication" if not latest else "Edge cases"
        }

        badges = []
        if sessions.count() >= 5: badges.append('Consistent')
        if any(s.technical_score >= 90 for s in sessions): badges.append('Expert')
        
        resume_url = user.resume.url if user.resume and hasattr(user.resume, 'url') else None
        
        return JsonResponse({
            'success': True,
            'username': user.username,
            'role': user.target_role or "Full Stack Developer",
            'level': user.experience_level or "Junior",
            'resume_url': resume_url,
            'history': history,
            'total_interviews': sessions.count(),
            'feedback': feedback,
            'badges': badges
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@csrf_exempt
def cancel_session(request, session_id):
    if request.method == 'POST':
        try:
            from django.utils import timezone
            session = InterviewSession.objects.get(id=session_id, user=request.user)
            session.status = 'CANCELLED_BY_USER'
            session.end_time = timezone.now()
            session.technical_score = None
            session.communication_score = None
            session.confidence_score = None
            session.stage = 'ended'
            session.save()
            return JsonResponse({'success': True, 'redirect_url': f'/dashboard/?schedule_session_id={session.id}'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    return JsonResponse({'success': False}, status=400)
