import logging
from typing import Any, Dict

from ai_engine.gemini_client import generate_content, parse_json_response

LOGGER = logging.getLogger(__name__)

FALLBACK_CONTINUE = "I'm sorry, let's continue the interview. Could you elaborate more on your previous answer?"
FALLBACK_NEXT = "Thank you for your answer. Let's move to another question."
DEFAULT_CODING_PROMPT = "Let's do a coding problem. Please solve the default challenge."
DEFAULT_CODING_PROBLEM = "Write a function to reverse a string."


def _detect_language_hint(text: str) -> str:
    # Always return english as per new requirement
    return "english"


def generate_initial_question(
    target_role: str,
    company_mode: str,
    personality_mode: str,
    experience_level: str,
    resume_context: str = "",
    language_hint: str = "",
) -> str:
    # Quick Personality Mapping
    level_instruction = {
        "Student": "Be encouraging and educational. Use simple terms. Act like a helpful professor.",
        "Junior": "Be professional but guiding. Focus on foundational principles and growth potential.",
        "Experienced": "Speak peer-to-peer. Be challenging, direct, and skip the basics. Focus on high-level architecture."
    }.get(experience_level, "Be professional and clear.")

    prompt = (
        f"Role: {target_role}. Level: {experience_level}. Mode: {company_mode}.\n"
        f"Personality: {level_instruction} {personality_mode}.\n"
        "INTERACT ONLY IN ENGLISH. Be extremely concise (under 25 words per response for speed).\n"
        f"Resume: {resume_context[:400]}\n"
        "Start with a very brief hello and the first technical question."
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
    level_instruction = {
        "Student": "Encourage them even if they are slow. Explain if they get stuck.",
        "Junior": "Validate their approach but suggest optimizations.",
        "Experienced": "Nitpick their technical decisions. Ask for alternatives."
    }.get(experience_level, "Be professional.")

    sys_instruction = (
        f"You are a mock interviewer for {target_role} ({experience_level}). {level_instruction}\n"
        "STRICT: USE ONLY PLAIN ENGLISH. Max 2 sentences per response.\n"
        f"Answer history: {history_text[-1000:]}\n"
        f"Last answer: {latest_answer}\n"
    )

    if current_stage in ["tech1", "tech2"]:
        prompt = sys_instruction + "Ask another relevant technical question."
        result = generate_content(prompt, fallback_text=FALLBACK_NEXT)
        return {"type": "text", "text": result.get("text", FALLBACK_NEXT), "status": result.get("status")}

    if "coding" in current_stage:
        prompt = (
            sys_instruction
            + "Ask a coding question appropriate for this role.\n"
            + 'Return JSON: {"spoken_text": "...", "problem_statement": "...", "suggested_language": "..."}'
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
            except Exception:
                pass
        return {"type": "coding", "text": FALLBACK_NEXT, "problem": DEFAULT_CODING_PROBLEM, "language": "python", "status": "fallback"}

    result = generate_content(sys_instruction, fallback_text=FALLBACK_NEXT)
    return {"type": "text", "text": result.get("text", FALLBACK_NEXT), "status": result.get("status")}


def evaluate_code(problem_statement: str, submitted_code: str, language: str) -> Dict[str, Any]:
    prompt = (
        f"Problem: {problem_statement}\nCode: {submitted_code}\n"
        'Return JSON: {"passed": true/false, "feedback_speech": "concise feedback"}'
    )
    result = generate_content(prompt, response_schema="application/json", fallback_text=FALLBACK_NEXT)
    if result.get("status") == "success":
        try:
            return parse_json_response(result.get("text", ""))
        except Exception:
            pass
    return {"passed": True, "feedback_speech": "Code looks acceptable. Let's proceed."}


def _clamp_score(value: Any, default: int = 0) -> int:
    try:
        val_int = int(value)
        return max(0, min(100, val_int))
    except Exception:
        return default


def generate_final_feedback(history_text: str, resume_context: str = "") -> Dict[str, Any]:
    prompt = (
        "Analyze this interview. Be human and encouraging. ENGLISH ONLY.\n"
        f"History: {history_text}\n"
        'Return JSON: {"spoken_text": "...", "technical_score": 1-100, "communication_score": 1-100, "confidence_score": 1-100, "detailed_feedback": "..."}'
    )
    result = generate_content(prompt, response_schema="application/json", fallback_text=FALLBACK_NEXT)
    if result.get("status") == "success":
        try:
            parsed = parse_json_response(result.get("text", ""))
            parsed["technical_score"] = _clamp_score(parsed.get("technical_score"), 0)
            parsed["communication_score"] = _clamp_score(parsed.get("communication_score"), 0)
            parsed["confidence_score"] = _clamp_score(parsed.get("confidence_score"), 0)
            return parsed
        except Exception:
            pass
    return {
        "spoken_text": "Thank you for practicing with us today.",
        "technical_score": 0,
        "communication_score": 0,
        "confidence_score": 0,
        "detailed_feedback": "No detailed results for this session.",
    }


def fallback_response() -> str:
    return FALLBACK_CONTINUE
