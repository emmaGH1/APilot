import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import apilot.api
from apilot.policy import ALL_STATUSES

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
FILES = ("invoices.json", "pos.json", "receipts.json", "audit.json", "labels.json")


@pytest.fixture
def client(tmp_path, monkeypatch):
    for name in FILES:
        shutil.copy(DATA_DIR / name, tmp_path / name)
    monkeypatch.setattr(apilot.api, "DATA_DIR", tmp_path)
    return TestClient(apilot.api.app)


def _labels():
    return json.loads((DATA_DIR / "labels.json").read_text(encoding="utf-8"))


def test_summary(client):
    res = client.get("/api/summary")
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 120
    assert body["auto_post"] == 80
    assert body["human_review"] == 40
    # no reviews committed yet: everything human-review is still pending
    assert body["pending_review"] == 40
    assert body["reviewed"] == 0
    assert body["touchless_rate"] == round(80 / 120, 4)


def test_summary_reflects_reviews_and_statuses(client, tmp_path):
    labels = _labels()
    exception_id = next(iid for iid, lab in labels.items() if lab != "CLEAN")
    clean_id = next(iid for iid, lab in labels.items() if lab == "CLEAN")

    res = client.post(f"/api/review/{exception_id}", json={"verdict": "approve", "reason": "ok"})
    assert res.status_code == 200
    assert res.json()["posting_status"] == "OVERRIDE_APPROVED"
    res = client.post(f"/api/review/{clean_id}", json={"verdict": "hold", "reason": "still post?"})
    assert res.status_code == 200
    # an already auto-posted invoice stays AUTO_POSTED regardless of review
    assert res.json()["posting_status"] == "AUTO_POSTED"

    body = client.get("/api/summary").json()
    assert body["reviewed"] == 2
    assert body["pending_review"] == 39
    assert body["auto_post"] == 80
    assert body["touchless_rate"] == round(80 / 120, 4)


def test_invoice_details_include_findings_and_source_docs(client):
    labels = _labels()
    pm_id = next(iid for iid, lab in labels.items() if lab == "PRICE_MISMATCH")
    invoices = client.get("/api/invoices").json()

    ids = [inv["id"] for inv in invoices]
    assert ids == sorted(ids)  # sorted by invoice id

    inv = next(i for i in invoices if i["id"] == pm_id)
    assert inv["total"] > 0
    assert inv["source_docs"]["po"] is not None
    assert inv["source_docs"]["receipt"] is not None
    assert len(inv["source_docs"]["po"]["line_items"]) >= 1
    assert isinstance(inv["source_docs"]["receipt"]["received"], dict)
    assert inv["audit"]["action"] == "HUMAN_REVIEW"
    assert any(f["type"] == "PRICE_MISMATCH" for f in inv["audit"]["findings"])
    assert inv["reviews"] == []


def test_invoice_details_carry_policy_fields_and_posting_status(client):
    labels = _labels()
    invoices = client.get("/api/invoices").json()
    by_id = {inv["id"]: inv for inv in invoices}
    assert len(by_id) == len(invoices)

    for inv in invoices:
        audit = inv["audit"]
        # additive policy-aware fields mirror the audit record
        assert inv["policy_rule"] == audit["policy_rule"]
        assert inv["review_owner"] == audit["review_owner"]
        assert inv["recommended_action"] == audit["recommended_action"]
        assert inv["posting_status"] in set(ALL_STATUSES)
        assert audit["posting_status"] in set(ALL_STATUSES)
        if audit["action"] == "AUTO_POST":
            assert inv["posting_status"] == "AUTO_POSTED"
            assert inv["review_owner"] == ""
        else:
            assert inv["posting_status"] == "BLOCKED_FOR_REVIEW"  # no reviews yet
            assert inv["review_owner"]

    # an exception owner is routed to Receiving/Procurement/AP managers etc.
    qty_id = next(iid for iid, lab in labels.items() if lab == "QTY_MISMATCH")
    assert by_id[qty_id]["review_owner"] == "Receiving"
    dup_id = next(iid for iid, lab in labels.items() if lab == "DUPLICATE_INVOICE")
    assert by_id[dup_id]["review_owner"] == "AP manager"


def test_review_updates_posting_status_on_followup(client):
    labels = _labels()
    inv_id = next(iid for iid, lab in labels.items() if lab != "CLEAN")
    assert client.post(f"/api/review/{inv_id}",
                       json={"verdict": "hold", "reason": "first"}).json()["posting_status"] == "ON_HOLD"
    # the LATEST review wins
    assert client.post(f"/api/review/{inv_id}",
                       json={"verdict": "escalate", "reason": "latest"}).json()["posting_status"] == "ESCALATED"
    inv = next(i for i in client.get("/api/invoices").json() if i["id"] == inv_id)
    assert inv["posting_status"] == "ESCALATED"
    assert len(inv["reviews"]) == 2


def test_post_review_appends_record(client, tmp_path):
    labels = _labels()
    inv_id = next(iter(labels))
    res = client.post(f"/api/review/{inv_id}", json={"verdict": "hold", "reason": "check totals"})
    assert res.status_code == 200
    record = res.json()
    assert record["invoice_id"] == inv_id
    assert record["verdict"] == "hold"
    assert record["reason"] == "check totals"
    assert record["reviewer"] == "AP Analyst (demo)"
    ts = datetime.fromisoformat(record["timestamp"])
    assert ts.tzinfo is not None and ts.utcoffset() == timezone.utc.utcoffset(None)

    reviews_path = tmp_path / "reviews.json"
    assert reviews_path.exists()
    saved = json.loads(reviews_path.read_text(encoding="utf-8"))
    # posting_status is derived per-request; only the record itself is persisted
    stored = {k: v for k, v in record.items() if k != "posting_status"}
    assert saved == [stored]

    # second POST appends (append-only)
    res2 = client.post(f"/api/review/{inv_id}", json={"verdict": "approve", "reason": "ok"})
    assert res2.status_code == 200
    saved2 = json.loads(reviews_path.read_text(encoding="utf-8"))
    assert len(saved2) == 2
    assert saved2[0] == stored
    assert saved2[1] == {k: v for k, v in res2.json().items() if k != "posting_status"}


def test_invalid_verdict_422_and_blank_reason_422_and_unknown_invoice_404(client):
    inv_id = next(iter(_labels()))
    res = client.post(f"/api/review/{inv_id}", json={"verdict": "nuke", "reason": "x"})
    assert res.status_code == 422
    res_blank = client.post(f"/api/review/{inv_id}", json={"verdict": "hold", "reason": "   "})
    assert res_blank.status_code == 422
    res2 = client.post("/api/review/INV-9999", json={"verdict": "hold", "reason": "x"})
    assert res2.status_code == 404
    assert "INV-9999" in str(res2.json()["detail"])


def test_evaluation_endpoint(client):
    res = client.get("/api/evaluation")
    assert res.status_code == 200
    body = res.json()
    assert body["total_invoices"] == 120
    assert body["total_exceptions"] == 40
    assert body["overall_action_accuracy"] == 1.0


def test_capabilities_endpoint_reflects_llm_key(client, monkeypatch):
    monkeypatch.delenv("APILOT_LLM_KEY", raising=False)
    assert client.get("/api/capabilities").json() == {"extraction_enabled": False}
    monkeypatch.setenv("APILOT_LLM_KEY", "test-key")
    assert client.get("/api/capabilities").json() == {"extraction_enabled": True}


def test_committed_data_files_unchanged_after_posts(client, tmp_path):
    before = {name: (tmp_path / name).read_bytes() for name in FILES}
    inv_id = next(iter(_labels()))
    for _ in range(3):
        client.post(f"/api/review/{inv_id}", json={"verdict": "escalate", "reason": "x"})
    client.get("/api/invoices")
    client.get("/api/summary")
    after = {name: (tmp_path / name).read_bytes() for name in FILES}
    assert after == before


def test_index_serves_html(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert "<html" in res.text
