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
from ai_engine.gemini_service import generate_initial_question, generate_follow_up
from voice.elevenlabs_service import generate_audio, transcribe_audio

@login_required
def start_interview(request):
    if request.method == "POST":
        role = request.user.target_role or "Software Engineer"
        company = "Google"
        personality = "Friendly"
        
        print(f"\n{'#'*60}")
        print(f"[INTERVIEW] 🚀 NEW SESSION STARTED")
        print(f"[INTERVIEW] 👤 User: {request.user.username} ({request.user.email})")
        print(f"[INTERVIEW] 🎯 Role: {role} | Company: {company} | Mode: {personality}")
        print(f"{'#'*60}")
        
        session = InterviewSession.objects.create(
            user=request.user,
            role=role,
            company_mode=company,
            personality_mode=personality
        )
        print(f"[INTERVIEW] 📦 Session #{session.id} created in DB")
        
        try:
            ai_text = generate_initial_question(role, company, personality)
        except Exception as e:
            print(f"[INTERVIEW] ⚠️ Gemini FAILED, using fallback question")
            ai_text = f"Hi there! I'm your interviewer today. Tell me about your experience as a {role} and what excites you most about this field?"
        
        q = Question.objects.create(session=session, question_text=ai_text, order=1)
        print(f"[INTERVIEW] 💾 Q1 saved: {ai_text[:100]}...")
        
        return redirect('interviews:room', session_id=session.id)
    
    return redirect('core:dashboard')

@login_required
def room(request, session_id):
    session = InterviewSession.objects.get(id=session_id, user=request.user)
    first_q = session.questions.order_by('order').first()
    
    print(f"\n[ROOM] 🎙️ Room loaded for Session #{session_id}")
    print(f"[ROOM] 💬 First question: {first_q.question_text[:100] if first_q else 'N/A'}...")
    
    context = {
        'session': session,
        'first_question_text': first_q.question_text if first_q else "Hello, are you ready to begin?"
    }
    return render(request, 'interviews/room.html', context)

@csrf_exempt
@login_required
def transcribe(request):
    """Receive audio blob from frontend, save to temp file, transcribe via ElevenLabs STT."""
    if request.method == "POST":
        audio_file = request.FILES.get('audio')
        if not audio_file:
            print(f"[STT] ❌ No audio file received!")
            return JsonResponse({'status': 'error', 'message': 'No audio file'}, status=400)
        
        print(f"\n{'='*60}")
        print(f"[STT] 🎤 Audio received: {audio_file.name} ({audio_file.size} bytes)")
        
        # Save to temp file
        temp_dir = os.path.join(settings.BASE_DIR, 'static', 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, f"rec_{uuid.uuid4().hex[:8]}.webm")
        
        with open(temp_path, 'wb') as f:
            for chunk in audio_file.chunks():
                f.write(chunk)
        
        print(f"[STT] 💾 Saved temp file: {temp_path}")
        
        try:
            transcript = transcribe_audio(temp_path)
            print(f"[STT] ✅ Transcript: \"{transcript[:200]}\"")
        except Exception as e:
            print(f"[STT] ❌ ElevenLabs STT FAILED: {str(e)[:200]}")
            transcript = ""
        
        # Clean up temp file
        try:
            os.remove(temp_path)
        except:
            pass
        
        return JsonResponse({'status': 'success', 'transcript': transcript})
    
    return JsonResponse({'status': 'error'}, status=400)

@csrf_exempt
@login_required
def handle_response(request, session_id):
    """Process transcribed text: save answer, get Gemini follow-up, generate TTS."""
    if request.method == "POST":
        data = json.loads(request.body)
        user_transcript = data.get('transcript', '')
        
        print(f"\n{'='*60}")
        print(f"[RESPONSE] 🎤 User transcript for Session #{session_id}")
        print(f"[RESPONSE] 📝 Text: \"{user_transcript}\"")
        
        session = InterviewSession.objects.get(id=session_id)
        
        questions = session.questions.order_by('order')
        history_text = ""
        for q in questions:
            history_text += f"Interviewer: {q.question_text}\n"
            ans = Answer.objects.filter(question=q).first()
            if ans and ans.transcript:
                history_text += f"Candidate: {ans.transcript}\n"
        
        last_q = questions.last()
        q_num = last_q.order if last_q else 0
        
        Answer.objects.create(
            session=session,
            question=last_q,
            transcript=user_transcript
        )
        print(f"[RESPONSE] 💾 Answer saved for Q{q_num}")
        
        start = time.time()
        try:
            ai_response_text = generate_follow_up(history_text, user_transcript, session.role)
        except Exception as e:
            print(f"[RESPONSE] ⚠️ Gemini follow-up FAILED: {str(e)[:100]}")
            ai_response_text = "That's interesting. Can you elaborate a bit more on that?"
        
        gemini_time = round(time.time() - start, 2)
        print(f"[RESPONSE] ⏱️ Gemini took {gemini_time}s")
        
        new_q = Question.objects.create(
            session=session,
            question_text=ai_response_text,
            order=q_num + 1
        )
        print(f"[RESPONSE] 💾 Q{q_num + 1} saved: {ai_response_text[:100]}...")
        
        audio_url = None
        try:
            audio_url = generate_audio(ai_response_text, request.user.id)
        except Exception as e:
            print(f"[RESPONSE] ⚠️ ElevenLabs TTS FAILED: {str(e)[:150]}")
            print(f"[RESPONSE] 🔄 Frontend will use browser TTS fallback")
        
        print(f"[RESPONSE] ✅ Done! Sending response to frontend")
        print(f"{'='*60}\n")
        
        return JsonResponse({
            'status': 'success',
            'ai_text': ai_response_text,
            'audio_url': audio_url
        })
        
    return JsonResponse({'status': 'error'}, status=400)

@csrf_exempt
@login_required
def get_tts(request):
    """Generate TTS audio for any given text."""
    if request.method == "POST":
        data = json.loads(request.body)
        text = data.get('text', '')
        if text:
            print(f"\n[TTS] 🔊 TTS request: \"{text[:100]}...\"")
            try:
                audio_url = generate_audio(text, request.user.id)
                print(f"[TTS] ✅ Audio ready: {audio_url}")
                return JsonResponse({'status': 'success', 'audio_url': audio_url})
            except Exception as e:
                print(f"[TTS] ⚠️ ElevenLabs FAILED: {str(e)[:150]}")
                return JsonResponse({'status': 'fallback', 'message': str(e)[:200]})
    return JsonResponse({'status': 'error'}, status=400)
