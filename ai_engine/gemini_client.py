import os
import json
import logging
import time
from typing import Any, Dict, Optional

from django.conf import settings
from google import genai
from google.genai import types

LOGGER = logging.getLogger(__name__)
MODELS = ['gemini-3-flash-preview']
RATE_LIMIT_DELAY = 2

client = genai.Client(api_key=settings.GEMINI_API_KEY)


def _is_rate_limit_error(exc: Exception) -> bool:
    message = str(exc)
    if "RESOURCE_EXHAUSTED" in message or "429" in message:
        return True
    status = getattr(getattr(exc, "response", None), "status_code", None)
    if status == 429:
        return True
    code = getattr(exc, "code", None)
    if code in (429, "429", "StatusCode.RESOURCE_EXHAUSTED"):
        return True
    return False


def _extract_usage(response: Any) -> Optional[Dict[str, Any]]:
    usage_obj = getattr(response, "usage_metadata", None) or getattr(response, "usage", None)
    if not usage_obj:
        return None
    return {
        "prompt_token_count": getattr(usage_obj, "prompt_token_count", None),
        "candidates_token_count": getattr(usage_obj, "candidates_token_count", None),
        "total_token_count": getattr(usage_obj, "total_token_count", None),
    }


def generate_content(prompt: str, response_schema: Optional[str] = None, fallback_text: Optional[str] = None) -> Dict[str, Any]:
    config = None
    if response_schema:
        config = types.GenerateContentConfig(
            response_mime_type="application/json"
        )

    for model_name in MODELS:
        try:
            LOGGER.info("[GEMINI] trying model=%s", model_name)
            start_time = time.time()
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config,
            )
            elapsed = round(time.time() - start_time, 2)
            usage = _extract_usage(response)
            text = (getattr(response, "text", "") or "").strip()
            LOGGER.info("[GEMINI] success model=%s elapsed=%.2fs", model_name, elapsed)
            return {"text": text, "status": "success", "usage": usage}
        except Exception as exc:  # noqa: BLE001
            is_rate_limit = _is_rate_limit_error(exc)
            LOGGER.error(
                "[GEMINI] error model=%s rate_limited=%s error=%s",
                model_name,
                is_rate_limit,
                str(exc)[:200],
            )
            # If it's a rate limit or another error, we just continue to the next model in the list
            continue

    fallback = fallback_text or (
        "I'm sorry, let's continue the interview. Could you elaborate more on your previous answer?"
    )
    LOGGER.warning("[GEMINI] ALL MODELS FAILED. fallback triggered")
    return {"text": fallback, "status": "fallback", "usage": None}


def parse_json_response(raw_text: str) -> Dict[str, Any]:
    cleaned = raw_text.replace("`json", "").replace("`", "").strip()
    return json.loads(cleaned)
