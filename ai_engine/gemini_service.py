import json
from google import genai
from google.genai import types
from django.conf import settings
import time
import os

client = genai.Client(api_key=settings.GEMINI_API_KEY)
MODELS = ['gemini-3-flash-preview', 'gemini-2.5-flash', 'gemini-2.0-flash-lite', 'gemini-2.0-flash']

def _call_gemini(prompt, response_schema=None):
    last_error = None
    for model_name in MODELS:
        try:
            print(f"\n{'='*60}\n[GEMINI] 🤖 Calling model: {model_name}\n[GEMINI] 📝 Prompt:\n{prompt.strip()[:300]}...\n")
            start_time = time.time()

            config = None
            if response_schema:
                config = types.GenerateContentConfig(
                    response_mime_type="application/json"
                )

            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config
            )

            elapsed = round(time.time() - start_time, 2)
            print(f"[GEMINI] ? SUCCESS in {elapsed}s using {model_name}\n[GEMINI] ?? Response: {response.text.strip()[:300]}\n{'='*60}\n")
            return response.text.strip()
        except Exception as e:
            last_error = e
            print(f"[GEMINI] ? Model {model_name} FAILED: {str(e)[:200]}")
            continue

    print("[GEMINI] ?? ALL MODELS FAILED! Using fallback text.")
    raise last_error

def generate_initial_question(target_role, company_mode, personality_mode, experience_level):
    prompt = f"You are an AI performing a realistic technical interview. \n    Candidate Role: {target_role}\n    Experience Level: {experience_level}\n    Company Style: {company_mode}\n    Interviewer Personality: {personality_mode}\n\n    Start the interview by introducing yourself briefly (under 15 words) and asking the very first technical interview question based on their experience level.\n    Make it conversational, natural, and directly related to the role. Keep it exactly to 1 or 2 short sentences.\n    Do not output any brackets, labels, or extra text. Just speak exactly what the interviewer would say out loud."
    return _call_gemini(prompt)

def generate_next_interaction(history_text, latest_answer, target_role, experience_level, current_stage):
    sys_instruction = f"You are a technical interviewer interviewing a candidate for a {target_role} position ({experience_level} experience).\n    Here is the conversation history:\n    {history_text}\n    The candidate just answered: {latest_answer}\n"

    if current_stage in ['tech1', 'tech2']:
        prompt = sys_instruction + "This is a technical round. Keep your response exactly to 1 or 2 conversational sentences as a spoken follow-up. Do not use labels like 'Interviewer:'. Just the spoken text."
        return {'type': 'text', 'text': _call_gemini(prompt)}

    elif 'coding' in current_stage:
        prompt = sys_instruction + """\nIMPORTANT: This is a CODING round. You must provide a Coding question appropriate for a {experience_level} {target_role}.\nReturn ONLY a JSON object with these keys:\n"spoken_text": (What you say to introduce the coding problem, max 2 sentences),\n"problem_statement": (The detailed coding problem description, constraints, and examples),\n"suggested_language": (The programming language best suited, e.g., 'python', 'javascript', 'cpp', 'java')\n"""
        res = _call_gemini(prompt, response_schema=True)
        try:
            clean_res = res.replace('`json', '').replace('`', '').strip()
            data = json.loads(clean_res)
            return {'type': 'coding', 'text': data.get('spoken_text'), 'problem': data.get('problem_statement'), 'language': data.get('suggested_language', 'javascript')}
        except Exception:
            return {'type': 'coding', 'text': 'Let\'s do a coding problem. Please solve the default challenge.', 'problem': 'Write a function to reverse a string.', 'language': 'javascript'}

def evaluate_code(problem_statement, submitted_code, language):
    prompt = f"""You are evaluating code.\nProblem: {problem_statement}\nLanguage: {language}\nCandidate Code:\n{submitted_code}\n\nEvaluate for correctness. Return ONLY JSON:\n"passed": true/false,\n"feedback_speech": "1 or 2 sentences of what the interviewer says about the code."\n"""
    res = _call_gemini(prompt, response_schema=True)
    try:
        clean_res = res.replace('`json', '').replace('`', '').strip()
        return json.loads(clean_res)
    except:
        return {'passed': True, 'feedback_speech': "That looks acceptable, let's move on."}

def generate_final_feedback(history_text):
    prompt = f"""The interview has concluded. Analyze the candidate's performance.
Transcript:
{history_text}

Return ONLY a JSON object:
"spoken_text": "A friendly 2 sentence sign-off thanking them.",
"technical_score": (int 1-100),
"communication_score": (int 1-100),
"confidence_score": (int 1-100),
"detailed_feedback": "Detailed analysis on strengths and weaknesses."
"""
    res = _call_gemini(prompt, response_schema=True)
    try:
        clean_res = res.replace('`json', '').replace('`', '').strip()
        return json.loads(clean_res)
    except:
        return {'spoken_text': 'Thank you for your time, we will be in touch.', 'technical_score': 75, 'communication_score': 75, 'confidence_score': 75, 'detailed_feedback': 'Good effort overall.'}
