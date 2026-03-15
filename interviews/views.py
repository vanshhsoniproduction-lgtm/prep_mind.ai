
import json
import logging

from django.conf import settings
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
            return JsonResponse({
                'success': True,
                'status': 'ended',
                'ai_text': fallback_text,
                'is_ended': True,
                'redirect_url': f'/dashboard/?schedule_session_id={session.id}',
            })

        questions = session.questions.order_by('order')
        history_text = ''
        for q in questions:
            history_text += f'Interviewer: {q.question_text}\n'
            ans = Answer.objects.filter(question=q).first()
            if ans and ans.transcript:
                history_text += f'Candidate: {ans.transcript}\n'
            if ans and ans.code_submitted:
                history_text += f'Candidate Code: {ans.code_submitted}\n'

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
            feedback_data = generate_final_feedback(history_text + f'Candidate: {user_transcript}\n', resume_context)
            session.stage = 'ended'
            session.technical_score = feedback_data.get('technical_score', 0)
            session.communication_score = feedback_data.get('communication_score', 0)
            session.confidence_score = feedback_data.get('confidence_score', 0)
            session.feedback_text = feedback_data.get('detailed_feedback', '')
            session.end_time = timezone.now()
            session.save()
            
            end_text = feedback_data.get('spoken_text', 'Thank you!')
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
            history_text,
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

        history_text = f'Problem: {problem}\nCode Submitted:\n{code}\nEvaluation: {"Passed" if passed else "Failed"}\n'
        
        if session.stage == 'feedback':
            feedback_data = generate_final_feedback(history_text, resume_context)
            session.stage = 'ended'
            session.technical_score = feedback_data.get('technical_score', 0)
            session.communication_score = feedback_data.get('communication_score', 0)
            session.confidence_score = feedback_data.get('confidence_score', 0)
            session.feedback_text = feedback_data.get('detailed_feedback', '')
            session.end_time = timezone.now()
            session.save()
            return JsonResponse({
                'success': True,
                'status': 'success',
                'ai_text': feedback_speech + ' ' + feedback_data.get('spoken_text', ''),
                'is_ended': True,
                'redirect_url': f'/dashboard/?schedule_session_id={session.id}',
            })

        interaction = generate_next_interaction(
            history_text,
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
        
        doc_link = create_interview_report(
            user=request.user,
            candidate_name=request.user.get_full_name() or request.user.username,
            role=session.role,
            date=str(session.created_at.date()),
            transcript=transcript,
            scores=session.communication_score or "Not scored",
            strengths="Strengths determined by AI.",
            weaknesses="Areas to improve determined by AI.",
            improvement_plan="Practice mock sessions."
        )
        return JsonResponse({'success': True, 'doc_link': doc_link})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
