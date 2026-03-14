
import json
import time
import os
import uuid
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.conf import settings

from .models import InterviewSession, Question
from responses.models import Answer
from ai_engine.gemini_service import generate_initial_question, generate_next_interaction, evaluate_code, generate_final_feedback

@login_required
def start_interview(request):
    if request.method == 'POST':
        role = request.user.target_role or 'Software Engineer'
        experience_level = request.user.experience_level or 'Mid-Level'
        company = 'Google'
        personality = 'Friendly'

        session = InterviewSession.objects.create(
            user=request.user,
            role=role,
            company_mode=company,
            personality_mode=personality,
            stage='tech1',
            question_count=1
        )

        try:
            ai_text = generate_initial_question(role, company, personality, experience_level)
        except Exception as e:
            ai_text = f'Hi there! I am your interviewer today. Tell me about your experience as a {role}.'
        
        Question.objects.create(session=session, question_text=ai_text, order=1)
        return redirect('interviews:room', session_id=session.id)
    return redirect('core:dashboard')

@login_required
def room(request, session_id):
    session = InterviewSession.objects.get(id=session_id, user=request.user)
    first_q = session.questions.order_by('order').first()

    context = {
        'session': session,
        'first_question_text': first_q.question_text if first_q else 'Hello, are you ready to begin?'
    }
    return render(request, 'interviews/room.html', context)

@csrf_exempt
@login_required
def handle_response(request, session_id):
    if request.method == 'POST':
        data = json.loads(request.body)
        user_transcript = data.get('transcript', '')

        session = InterviewSession.objects.get(id=session_id)
        if session.stage == 'ended':
            return JsonResponse({'status': 'ended'})

        questions = session.questions.order_by('order')
        history_text = ''
        for q in questions:
            history_text += f'Interviewer: {q.question_text}\n'
            # If there's an answer, append it
            ans = Answer.objects.filter(question=q).first()
            if ans and ans.transcript:
                history_text += f'Candidate: {ans.transcript}\n'
            if ans and ans.code_submitted:
                history_text += f'Candidate Code: {ans.code_submitted}\n'

        last_q = questions.last()
        q_num = last_q.order if last_q else 0

        # Save user response
        Answer.objects.create(
            session=session,
            question=last_q,
            transcript=user_transcript
        )
        
        # Determine next stage logic before generating question
        if session.stage == 'tech1' and session.question_count >= 5:
            session.stage = 'coding1'
        elif session.stage == 'tech2' and session.question_count >= 10:
            session.stage = 'coding2' # Or feedback if no coding2

        session.question_count += 1
        session.save()

        # If feedback stage
        if session.stage == 'feedback' or session.question_count > 15:
            feedback_data = generate_final_feedback(history_text + f'Candidate: {user_transcript}\n')
            session.stage = 'ended'
            session.technical_score = feedback_data.get('technical_score', 0)
            session.communication_score = feedback_data.get('communication_score', 0)
            session.confidence_score = feedback_data.get('confidence_score', 0)
            session.feedback_text = feedback_data.get('detailed_feedback', '')
            session.save()
            return JsonResponse({
                'status': 'success',
                'ai_text': feedback_data.get('spoken_text', 'Thank you!'),
                'is_ended': True
            })

        # Get next interaction
        try:
            exp_level = request.user.experience_level or 'Mid-Level'
            interaction = generate_next_interaction(history_text, user_transcript, session.role, exp_level, session.stage)
            
            # Save the new question
            new_q = Question.objects.create(
                session=session,
                question_text=interaction.get('text', ''),
                is_coding=(interaction.get('type') == 'coding'),
                order=session.question_count
            )
            
            response_data = {
                'status': 'success',
                'ai_text': interaction.get('text'),
                'type': interaction.get('type'),
                'is_ended': False
            }
            if interaction.get('type') == 'coding':
                response_data['problem'] = interaction.get('problem')
                response_data['language'] = interaction.get('language')
                
            return JsonResponse(response_data)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error'}, status=400)

@csrf_exempt
@login_required
def evaluate_coding_round(request, session_id):
    if request.method == 'POST':
        data = json.loads(request.body)
        code = data.get('code', '')
        language = data.get('language', 'javascript')
        problem = data.get('problem', '')

        session = InterviewSession.objects.get(id=session_id)
        last_q = session.questions.last()
        
        # Evaluate
        eval_result = evaluate_code(problem, code, language)
        passed = eval_result.get('passed', False)
        feedback_speech = eval_result.get('feedback_speech', 'Let us move on.')

        # Save Answer
        Answer.objects.create(
            session=session,
            question=last_q,
            transcript='[Code Submitted]',
            code_submitted=code,
            language_used=language,
            evaluation_passed=passed
        )

        session.question_count += 1
        
        # Logic branch:
        if passed and session.stage == 'coding1':
            session.stage = 'tech2'
        else:
            session.stage = 'feedback' # Skip to end if failed, or if it was coding2

        session.save()

        # Follow up question based on the transition
        history_text = f'Problem: {problem}\nCode Submitted:\n{code}\nEvaluation: \'Passed\' if passed else \'Failed\'\n'
        
        if session.stage == 'feedback':
            feedback_data = generate_final_feedback(history_text)
            session.stage = 'ended'
            session.technical_score = feedback_data.get('technical_score', 0)
            session.communication_score = feedback_data.get('communication_score', 0)
            session.confidence_score = feedback_data.get('confidence_score', 0)
            session.feedback_text = feedback_data.get('detailed_feedback', '')
            session.save()
            return JsonResponse({
                'status': 'success',
                'ai_text': feedback_speech + ' ' + feedback_data.get('spoken_text', ''),
                'is_ended': True
            })
        else:
            interaction = generate_next_interaction(history_text, 'Code generated.', session.role, request.user.experience_level or 'Mid', session.stage)
            Question.objects.create(
                session=session,
                question_text=interaction.get('text', ''),
                is_coding=False,
                order=session.question_count
            )
            return JsonResponse({
                'status': 'success',
                'ai_text': feedback_speech + ' ' + interaction.get('text', ''),
                'type': 'text',
                'is_ended': False
            })

