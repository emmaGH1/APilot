import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import apilot.api

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
    assert res.json() == {"total": 120, "auto_post": 80, "human_review": 40}


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


def test_post_review_appends_record(client, tmp_path):
    labels = _labels()
    inv_id = next(iter(labels))
    res = client.post(f"/api/review/{inv_id}", json={"verdict": "hold", "reason": "check totals"})
    assert res.status_code == 200
    record = res.json()
    assert record["invoice_id"] == inv_id
    assert record["verdict"] == "hold"
    assert record["reason"] == "check totals"
    assert record["reviewer"] == "demo"
    ts = datetime.fromisoformat(record["timestamp"])
    assert ts.tzinfo is not None and ts.utcoffset() == timezone.utc.utcoffset(None)

    reviews_path = tmp_path / "reviews.json"
    assert reviews_path.exists()
    saved = json.loads(reviews_path.read_text(encoding="utf-8"))
    assert saved == [record]

    # second POST appends (append-only)
    res2 = client.post(f"/api/review/{inv_id}", json={"verdict": "approve", "reason": ""})
    assert res2.status_code == 200
    saved2 = json.loads(reviews_path.read_text(encoding="utf-8"))
    assert len(saved2) == 2
    assert saved2[0] == record
    assert saved2[1] == res2.json()


def test_invalid_verdict_422_and_unknown_invoice_404(client):
    inv_id = next(iter(_labels()))
    res = client.post(f"/api/review/{inv_id}", json={"verdict": "nuke", "reason": ""})
    assert res.status_code == 422
    res2 = client.post("/api/review/INV-9999", json={"verdict": "hold", "reason": ""})
    assert res2.status_code == 404
    assert "INV-9999" in str(res2.json()["detail"])


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
