"""Dependency-free Gemini adapter for PayArc."""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sqlalchemy.orm import Session

from .assistant import finance_snapshot

_last_error: str | None = None


def _load_local_env() -> None:
    """Load .env values locally without overriding deployed environment values."""
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if not env_file.is_file():
        return
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_local_env()


def _model() -> str:
    # Gemini 2.0 Flash has been retired; this is the current API default.
    return os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()


def _provider_error(error: HTTPError) -> str:
    try:
        message = json.loads(error.read().decode("utf-8", errors="replace")).get("error", {}).get("message")
        if message:
            return str(message)[:300]
    except Exception:
        pass
    return f"Gemini returned HTTP {error.code}."


def _generate(parts: list[dict], generation_config: dict | None = None) -> str | None:
    """Call GenerateContent and retain a safe diagnostic for the UI."""
    global _last_error
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        _last_error = "GEMINI_API_KEY is not configured on the server."
        return None
    payload = {"contents": [{"parts": parts}]}
    if generation_config:
        payload["generationConfig"] = generation_config
    request = Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{_model()}:generateContent",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
        method="POST",
    )
    try:
        timeout = max(10, int(os.getenv("GEMINI_TIMEOUT_SECONDS", "60")))
        with urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
        text = "".join(part.get("text", "") for part in body.get("candidates", [{}])[0].get("content", {}).get("parts", [])).strip()
        if text:
            _last_error = None
            return text
        _last_error = "Gemini returned no usable text."
    except HTTPError as error:
        _last_error = _provider_error(error)
    except URLError:
        _last_error = "Could not reach Gemini. Check the internet connection or firewall."
    except (KeyError, IndexError, TypeError, json.JSONDecodeError):
        _last_error = "Gemini returned an unexpected response."
    except TimeoutError:
        _last_error = "Gemini timed out. Please try again."
    return None


def gemini_status() -> dict:
    configured = bool(os.getenv("GEMINI_API_KEY", "").strip())
    return {"provider": "gemini", "configured": configured, "model": _model(), "last_error": _last_error, "receipt_ocr": "gemini" if configured else "unavailable"}


def verify_gemini() -> dict:
    answer = _generate([{"text": "Reply with exactly: ready"}], {"temperature": 0, "maxOutputTokens": 8})
    status = gemini_status()
    return {**status, "reachable": bool(answer), "message": "Gemini is connected." if answer else (_last_error or "Gemini connection failed.")}


def ask_gemini(db: Session, message: str) -> str | None:
    snapshot = finance_snapshot(db)
    context = {"currency": snapshot["currency"], "monthly_income": snapshot["income"], "monthly_spending": snapshot["spending"], "transaction_count": snapshot["transaction_count"], "spending_by_category": snapshot["by_category"]}
    prompt = ("You are PayArc Copilot, a supportive personal-finance organiser. Use only the supplied aggregate data. "
              "Do not provide investment, tax, legal, or debt advice. Give practical tracking or budgeting steps in under 170 words.\n"
              f"Financial snapshot: {json.dumps(context)}\nUser question: {message}")
    return _generate([{"text": prompt}], {"temperature": 0.35, "maxOutputTokens": 320})


def extract_receipt_text(raw: bytes, mime_type: str) -> str | None:
    """Gemini vision OCR fallback for explicitly uploaded image receipts."""
    if not mime_type.startswith("image/"):
        return None
    return _generate([
        {"text": "Transcribe this receipt faithfully. Return plain text only. Preserve merchant, date, line items, tax, and total when legible. Do not invent unreadable values."},
        {"inline_data": {"mime_type": mime_type, "data": base64.b64encode(raw).decode("ascii")}},
    ], {"temperature": 0, "maxOutputTokens": 1024})
