import logging
from typing import Any, Dict

from ai_engine.gemini_client import generate_content, parse_json_response

LOGGER = logging.getLogger(__name__)

FALLBACK_CONTINUE = "I'm sorry, let's continue the interview. Could you elaborate more on your previous answer?"
FALLBACK_NEXT = "Thank you for your answer. Let's move to another question."
DEFAULT_CODING_PROMPT = "Let's do a coding problem. Please solve the default challenge."
DEFAULT_CODING_PROBLEM = "Write a function to reverse a string."


def _detect_language_hint(text: str) -> str:
    if not text:
        return ""
    t = text.lower()
    hindi_markers = ["hai", "kar", "kya", "nahi", "haan", "acha", "sahi"]
    tamil_markers = ["illai", "amma", "appa", "enna", "seri", "podu"]
    score_hindi = sum(1 for w in hindi_markers if w in t)
    score_tamil = sum(1 for w in tamil_markers if w in t)
    if score_tamil > score_hindi and score_tamil >= 1:
        return "tamil"
    if score_hindi >= 1:
        return "hindi"
    return "english"


def generate_initial_question(
    target_role: str,
    company_mode: str,
    personality_mode: str,
    experience_level: str,
    resume_context: str = "",
    language_hint: str = "",
) -> str:
    lang_hint = language_hint or ""
    prompt = (
        "You are an AI interviewer. Be warm, human, and concise. Mirror the candidate's language (Hindi -> Hinglish, Tamil -> Tamil, English -> English).\n"
        f"Candidate Role: {target_role}\n"
        f"Experience Level: {experience_level}\n"
        f"Company Style: {company_mode}\n"
        f"Interviewer Personality: {personality_mode}\n"
        f"Resume (if any): {resume_context[:800]}\n"
        f"Language preference hint from candidate: {lang_hint}\n\n"
        "Start the interview by introducing yourself briefly (under 15 words) and asking the first technical question based on their experience level and resume highlights."
        " Keep it to 1-2 sentences, natural and spoken."
    )
    result = generate_content(prompt, fallback_text=FALLBACK_CONTINUE)
    return result.get("text", FALLBACK_CONTINUE)


def generate_next_interaction(
    history_text: str,
    latest_answer: str,
    target_role: str,
    experience_level: str,
    current_stage: str,
    resume_context: str = "",
    language_hint: str = "",
) -> Dict[str, Any]:
    lang_hint = language_hint or _detect_language_hint(latest_answer)
    sys_instruction = (
        "You are a technical interviewer. Be empathetic, concise, and human. Mirror the candidate's languages: respond in the same language(s) they use (Hindi -> Hinglish, Tamil -> Tamil, mixed -> bilingual)."
        f" Candidate role: {target_role} ({experience_level} experience).\n"
        f"Conversation history:\n{history_text}\n"
        f"The candidate just answered: {latest_answer}\n"
        f"Resume context (if available): {resume_context[:800]}\n"
        "If the candidate corrects pronouns, acknowledge once with a brief apology, then continue naturally."
        f"Language preference hint: {lang_hint}\n"
    )

    if current_stage in ["tech1", "tech2"]:
        prompt = (
            sys_instruction
            + "This is a technical round. Keep your response to 1-2 spoken sentences. Reference their resume when relevant (skills, projects, experience)."
            + " Do not use labels. Speak naturally and match the candidate's language style."
        )
        result = generate_content(prompt, fallback_text=FALLBACK_NEXT)
        return {"type": "text", "text": result.get("text", FALLBACK_NEXT), "status": result.get("status")}

    if "coding" in current_stage:
        prompt = (
            sys_instruction
            + "IMPORTANT: This is a CODING round. You must provide a coding question appropriate for the candidate.\n"
            + "Return ONLY a JSON object with these keys:\n"
            + '"spoken_text": (What you say to introduce the coding problem, max 2 sentences),\n'
            + '"problem_statement": (The detailed coding problem description, constraints, and examples — align with their resume skills if possible),\n'
            + '"suggested_language": (The programming language best suited, e.g., "python", "javascript", "cpp", "java")\n'
        )
        result = generate_content(prompt, response_schema="application/json", fallback_text=DEFAULT_CODING_PROMPT)
        raw_text = result.get("text", "")
        if result.get("status") == "success":
            try:
                data = parse_json_response(raw_text)
                return {
                    "type": "coding",
                    "text": data.get("spoken_text", FALLBACK_NEXT),
                    "problem": data.get("problem_statement", DEFAULT_CODING_PROBLEM),
                    "language": data.get("suggested_language", "python"),
                    "status": "success",
                }
            except Exception as exc:  # noqa: BLE001
                LOGGER.error("[GEMINI] coding json parse failed error=%s", str(exc)[:300])
        return {
            "type": "coding",
            "text": FALLBACK_NEXT,
            "problem": DEFAULT_CODING_PROBLEM,
            "language": "python",
            "status": "fallback",
        }

    result = generate_content(sys_instruction, fallback_text=FALLBACK_NEXT)
    return {"type": "text", "text": result.get("text", FALLBACK_NEXT), "status": result.get("status")}


def evaluate_code(problem_statement: str, submitted_code: str, language: str) -> Dict[str, Any]:
    prompt = (
        "You are evaluating code.\n"
        f"Problem: {problem_statement}\n"
        f"Language: {language}\n"
        f"Candidate Code:\n{submitted_code}\n\n"
        'Evaluate for correctness. Return ONLY JSON:\n"passed": true/false,\n'
        '"feedback_speech": "1 or 2 sentences of what the interviewer says about the code."\n'
    )
    result = generate_content(prompt, response_schema="application/json", fallback_text=FALLBACK_NEXT)
    if result.get("status") == "success":
        try:
            return parse_json_response(result.get("text", ""))
        except Exception as exc:  # noqa: BLE001
            LOGGER.error("[GEMINI] evaluation json parse failed error=%s", str(exc)[:300])
    return {"passed": True, "feedback_speech": FALLBACK_NEXT}


def _clamp_score(value: Any, default: int = 75) -> int:
    try:
        val_int = int(value)
        return max(0, min(100, val_int))
    except Exception:  # noqa: BLE001
        return default


def generate_final_feedback(history_text: str, resume_context: str = "") -> Dict[str, Any]:
    prompt = (
        "The interview has concluded. Analyze the candidate's performance in a human, encouraging tone."
        " Mirror their languages (Hindi -> Hinglish, Tamil -> Tamil, mix -> bilingual).\n"
        f"Transcript:\n{history_text}\n"
        f"Resume context (if available): {resume_context[:800]}\n\n"
        'Return ONLY a JSON object:\n"spoken_text": "A friendly 2 sentence sign-off thanking them.",\n'
        '"technical_score": (int 1-100),\n"communication_score": (int 1-100),\n"confidence_score": (int 1-100),\n'
        '"detailed_feedback": "Detailed analysis on strengths and weaknesses."\n'
    )
    result = generate_content(prompt, response_schema="application/json", fallback_text=FALLBACK_NEXT)
    if result.get("status") == "success":
        try:
            parsed = parse_json_response(result.get("text", ""))
            parsed["technical_score"] = _clamp_score(parsed.get("technical_score"), 75)
            parsed["communication_score"] = _clamp_score(parsed.get("communication_score"), 75)
            parsed["confidence_score"] = _clamp_score(parsed.get("confidence_score"), 75)
            return parsed
        except Exception as exc:  # noqa: BLE001
            LOGGER.error("[GEMINI] final feedback json parse failed error=%s", str(exc)[:300])
    return {
        "spoken_text": "Thank you for your time, we will be in touch.",
        "technical_score": 75,
        "communication_score": 75,
        "confidence_score": 75,
        "detailed_feedback": "Good effort overall.",
    }


def fallback_response() -> str:
    return FALLBACK_CONTINUE
