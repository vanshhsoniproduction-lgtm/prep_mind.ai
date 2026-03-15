import logging
from typing import Optional

from PyPDF2 import PdfReader

LOGGER = logging.getLogger(__name__)

MAX_CHARS = 4000


def extract_resume_text(file_path: Optional[str]) -> str:
    if not file_path:
        return ""
    try:
        reader = PdfReader(file_path)
        text_parts = []
        for page in reader.pages:
            try:
                page_text = page.extract_text() or ""
            except Exception:  # noqa: BLE001
                page_text = ""
            if page_text:
                text_parts.append(page_text)
            if sum(len(p) for p in text_parts) >= MAX_CHARS:
                break
        combined = "\n".join(text_parts)
        return combined[:MAX_CHARS]
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("[RESUME] failed to read pdf error=%s", str(exc)[:400])
        return ""
