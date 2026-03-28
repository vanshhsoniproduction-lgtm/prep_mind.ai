import os
import json
import logging
import time
from typing import Any, Dict, Optional

from django.conf import settings
from google import genai
from google.genai import types

LOGGER = logging.getLogger(__name__)
MODELS = ["gemini-3-flash-preview", "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
RATE_LIMIT_DELAY = 5

ALL_KEYS = []
if hasattr(settings, 'GEMINI_API_KEY') and settings.GEMINI_API_KEY:
    ALL_KEYS.append(settings.GEMINI_API_KEY)

for k, v in os.environ.items():
    if k.startswith("GEMINI_API_KEY_") and v:
        ALL_KEYS.append(v)

ALL_KEYS = list(set(ALL_KEYS))
if not ALL_KEYS:
    LOGGER.warning("No GEMINI_API_KEY found. Engine may fail.")



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
        for api_key in ALL_KEYS:
            try:
                LOGGER.info("[GEMINI] trying model=%s with key ending in %s", model_name, api_key[-4:])
                client = genai.Client(api_key=api_key)
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
                    "[GEMINI] error model=%s key=%s rate_limited=%s error=%s",
                    model_name,
                    api_key[-4:],
                    is_rate_limit,
                    str(exc)[:200],
                )
                # Try the next API key in the pool
                continue

    fallback = fallback_text or (
        "I'm sorry, let's continue the interview. Could you elaborate more on your previous answer?"
    )
    LOGGER.warning("[GEMINI] ALL MODELS FAILED. fallback triggered")
    return {"text": fallback, "status": "fallback", "usage": None}


def parse_json_response(raw_text: str) -> Dict[str, Any]:
    cleaned = raw_text.replace("`json", "").replace("`", "").strip()
    return json.loads(cleaned)
