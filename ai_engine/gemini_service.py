from google import genai
from django.conf import settings
import time

# Initialize the new google-genai client
client = genai.Client(api_key=settings.GEMINI_API_KEY)

# Try multiple models as fallback
MODELS = ["gemini-2.0-flash-lite", "gemini-2.0-flash"]

def _call_gemini(prompt):
    """Try multiple models as fallback in case one hits quota."""
    last_error = None
    for model_name in MODELS:
        try:
            print(f"\n{'='*60}")
            print(f"[GEMINI] ⏳ Calling model: {model_name}")
            print(f"[GEMINI] 📝 Prompt (first 200 chars): {prompt.strip()[:200]}...")
            
            start_time = time.time()
            
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            
            elapsed = round(time.time() - start_time, 2)
            
            print(f"[GEMINI] ✅ SUCCESS in {elapsed}s using {model_name}")
            print(f"[GEMINI] 💬 Response: {response.text.strip()[:300]}")
            print(f"{'='*60}\n")
            
            return response.text.strip()
        except Exception as e:
            last_error = e
            print(f"[GEMINI] ❌ Model {model_name} FAILED: {str(e)[:200]}")
            continue
    
    print(f"[GEMINI] 🚨 ALL MODELS FAILED! Using fallback text.")
    raise last_error

def generate_initial_question(target_role, company_mode, personality_mode):
    print(f"\n[GEMINI] 🎬 generate_initial_question(role={target_role}, company={company_mode}, personality={personality_mode})")
    
    prompt = f"""
    You are an AI performing a realistic technical interview.
    Role: {target_role}
    Company Style: {company_mode}
    Interviewer Personality: {personality_mode}
    
    Start the interview by introducing yourself briefly (under 15 words) and asking the very first interview question.
    Make it conversational, natural, and directly related to the role. Keep it exactly to 1 or 2 short sentences.
    Do not output any brackets, labels, or extra text. Just speak exactly what the interviewer would say out loud.
    """
    
    return _call_gemini(prompt)

def generate_follow_up(transcript_history, latest_answer, target_role):
    print(f"\n[GEMINI] 🔄 generate_follow_up(role={target_role})")
    print(f"[GEMINI] 👤 User said: {latest_answer[:200]}")
    
    prompt = f"""
    You are a technical interviewer interviewing a candidate for a {target_role} position.
    
    Here is the conversation history so far:
    {transcript_history}
    
    The candidate just answered with: "{latest_answer}"
    
    Ask a relevant, natural follow-up question based ONLY on their latest answer. 
    If their answer was weak, ask a simpler question to drill down.
    If their answer was strong, ask a more advanced question related to what they just said.
    
    Keep your response exactly to 1 or 2 conversational sentences. Do not use labels like "Interviewer:". Just the spoken text.
    """
    
    return _call_gemini(prompt)
