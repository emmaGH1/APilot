import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import apilot.api
import apilot.extract
from apilot.extract import MissingAPIKeyError, extract_invoice
from apilot.models import Invoice

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
FILES = ("invoices.json", "pos.json", "receipts.json", "audit.json", "labels.json")

VALID_INVOICE = {
    "vendor": "Acme Supplies",
    "invoice_number": "INV-9001",
    "po_number": None,
    "currency": "USD",
    "line_items": [{"sku": "SKU-1001", "qty": 2, "unit_price": 12.5}],
}


def _envelope(content: str) -> bytes:
    payload = {"choices": [{"message": {"content": content}}]}
    return json.dumps(payload).encode("utf-8")


class FakeResp:
    def __init__(self, body: bytes):
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


@pytest.fixture
def llm_key(monkeypatch):
    monkeypatch.setenv("APILOT_LLM_KEY", "test-key")


def test_valid_extraction_uses_fallback_id(monkeypatch, llm_key):
    monkeypatch.setattr(apilot.extract, "urlopen", lambda req, timeout=60: FakeResp(_envelope(json.dumps(VALID_INVOICE))))
    invoice = extract_invoice("some invoice text")
    assert isinstance(invoice, Invoice)
    assert invoice.id == "INV-EXTRACT"
    assert invoice.vendor == "Acme Supplies"
    assert invoice.invoice_number == "INV-9001"
    assert invoice.po_number is None
    assert invoice.currency == "USD"
    assert len(invoice.line_items) == 1
    assert invoice.line_items[0].sku == "SKU-1001"


def test_retry_once_on_invalid_content_json(monkeypatch, llm_key):
    calls = []

    def fake_urlopen(req, timeout=60):
        calls.append(req)
        if len(calls) == 1:
            return FakeResp(_envelope("this is not json"))
        return FakeResp(_envelope(json.dumps(VALID_INVOICE)))

    monkeypatch.setattr(apilot.extract, "urlopen", fake_urlopen)
    invoice = extract_invoice("some invoice text")
    assert invoice.id == "INV-EXTRACT"
    assert len(calls) == 2


def test_fenced_json_content_is_parsed(monkeypatch, llm_key):
    fenced = (
        "Here is the extracted invoice:\n"
        f"```json\n{json.dumps(VALID_INVOICE)}\n```\n"
        "Let me know if you need anything else."
    )
    monkeypatch.setattr(
        apilot.extract, "urlopen",
        lambda req, timeout=60: FakeResp(_envelope(fenced)),
    )
    invoice = extract_invoice("some invoice text")
    assert invoice.vendor == "Acme Supplies"
    assert invoice.invoice_number == "INV-9001"
    assert invoice.line_items[0].sku == "SKU-1001"


def test_fence_without_language_tag_is_parsed(monkeypatch, llm_key):
    fenced = f"```\n{json.dumps(VALID_INVOICE)}\n```"
    monkeypatch.setattr(
        apilot.extract, "urlopen",
        lambda req, timeout=60: FakeResp(_envelope(fenced)),
    )
    invoice = extract_invoice("some invoice text")
    assert invoice.invoice_number == "INV-9001"


def test_plain_json_content_still_parses(monkeypatch, llm_key):
    monkeypatch.setattr(
        apilot.extract, "urlopen",
        lambda req, timeout=60: FakeResp(_envelope(json.dumps(VALID_INVOICE))),
    )
    invoice = extract_invoice("some invoice text")
    assert invoice.invoice_number == "INV-9001"


def test_missing_key_raises_before_any_request(monkeypatch):
    monkeypatch.delenv("APILOT_LLM_KEY", raising=False)
    calls = []

    def fake_urlopen(req, timeout=60):
        calls.append(req)
        raise AssertionError("must not be called")

    monkeypatch.setattr(apilot.extract, "urlopen", fake_urlopen)
    with pytest.raises(MissingAPIKeyError):
        extract_invoice("some invoice text")
    assert calls == []


@pytest.fixture
def client(tmp_path, monkeypatch):
    for name in FILES:
        shutil.copy(DATA_DIR / name, tmp_path / name)
    monkeypatch.setattr(apilot.api, "DATA_DIR", tmp_path)
    return TestClient(apilot.api.app)


def test_api_extract_happy_path(client, monkeypatch, llm_key):
    monkeypatch.setattr(apilot.extract, "urlopen",
                        lambda req, timeout=60: FakeResp(_envelope(json.dumps(VALID_INVOICE))))
    res = client.post("/api/extract", json={"text": "ACME SUPPLIES  INV-9001  2x SKU-1001 @12.5"})
    assert res.status_code == 200
    body = res.json()
    assert body["invoice"]["id"] == "INV-EXTRACT"
    assert body["invoice"]["vendor"] == "Acme Supplies"
    assert [f["type"] for f in body["findings"]] == ["MISSING_PO"]
    assert body["action"] == "HUMAN_REVIEW"
    assert body["posting_status"] == "BLOCKED_FOR_REVIEW"
    assert body["review_owner"] == "Procurement/AP"
    assert body["policy_rule"] and body["recommended_action"]
    assert "purchase order" in body["suggested_resolution"]
    assert body["po"] is None
    assert body["receipt"] is None


def test_api_extract_empty_text_422(client):
    for bad in ("", "   "):
        res = client.post("/api/extract", json={"text": bad})
        assert res.status_code == 422
