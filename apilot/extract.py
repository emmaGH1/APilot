"""Minimal LLM invoice-extraction layer.

One chat-completions POST (stdlib only); the LLM is never a dependency of the
core pipeline. APILOT_LLM_KEY / APILOT_LLM_BASE_URL / APILOT_LLM_MODEL are read
from the environment on every call so tests can set/unset them.
"""
import json
import os
import urllib.error
import urllib.request
from urllib.request import urlopen  # patched as apilot.extract.urlopen in tests

from apilot.models import Invoice
from pydantic import ValidationError

DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"
FALLBACK_ID = "INV-EXTRACT"
SYSTEM_PROMPT = (
    "Extract vendor, invoice number, PO number (null if absent), currency, "
    "line items (sku, qty, unit_price); respond with JSON only."
)


class ExtractionError(Exception):
    """Base class for extraction failures."""


class MissingAPIKeyError(ExtractionError):
    """APILOT_LLM_KEY is not set; raised before any request is made."""


class HTTPExtractionError(ExtractionError):
    """The LLM endpoint answered with an HTTP error status."""

    def __init__(self, status: int, body: str):
        super().__init__(f"LLM HTTP {status}: {body}")
        self.status = status
        self.body = body


class InvalidResponseError(ExtractionError):
    """The response envelope is missing or has unusable content."""


class InvalidContentError(ExtractionError):
    """The model's content was not a valid invoice after the retry."""


def _post(request) -> str:
    """Send one request; return the message content or raise an ExtractionError."""
    try:
        with urlopen(request, timeout=60) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise HTTPExtractionError(exc.code, exc.read().decode("utf-8", errors="replace")) from exc
    except urllib.error.URLError as exc:
        raise HTTPExtractionError(0, f"network error: {exc}") from exc
    try:
        envelope = json.loads(body)
        content = envelope["choices"][0]["message"]["content"]
    except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
        raise InvalidResponseError("response envelope is not valid JSON "
                                   "or lacks choices[0].message.content") from exc
    return content


def extract_invoice(text: str) -> Invoice:
    """Extract an Invoice from raw invoice text via one chat-completions call."""
    key = os.environ.get("APILOT_LLM_KEY")
    if not key:
        raise MissingAPIKeyError("APILOT_LLM_KEY is not set")

    base_url = (os.environ.get("APILOT_LLM_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
    model = os.environ.get("APILOT_LLM_MODEL") or DEFAULT_MODEL

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        "temperature": 0,
    }
    request = urllib.request.Request(
        base_url + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )

    last_error: Exception | None = None
    for _ in range(2):  # retry once when the model returns invalid invoice JSON
        content = _post(request)  # envelope/HTTP errors raise immediately
        try:
            data = json.loads(content)
            if not isinstance(data, dict):
                raise ValueError("content is not a JSON object")
            data.setdefault("id", FALLBACK_ID)
            return Invoice.model_validate(data)
        except (json.JSONDecodeError, ValueError, ValidationError) as exc:
            last_error = exc
            continue
    raise InvalidContentError(f"model returned invalid invoice JSON twice: {last_error}")
