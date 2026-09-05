import json
from pathlib import Path

import apilot.audit
from apilot.models import AuditRecord

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _invoices():
    return json.loads((DATA_DIR / "invoices.json").read_text(encoding="utf-8"))


def _labels():
    return json.loads((DATA_DIR / "labels.json").read_text(encoding="utf-8"))


def test_one_record_per_invoice():
    records = apilot.audit.run_pipeline()
    invoices = _invoices()
    ids = [r.invoice_id for r in records]
    assert len(records) == len(invoices)
    assert len(set(ids)) == len(invoices)  # ids unique
    assert set(ids) == {inv["id"] for inv in invoices}


def test_records_sorted_by_invoice_id():
    records = apilot.audit.run_pipeline()
    ids = [r.invoice_id for r in records]
    assert ids == sorted(ids)


def test_deterministic_across_runs():
    r1 = apilot.audit.run_pipeline()
    b1 = (DATA_DIR / "audit.json").read_bytes()
    r2 = apilot.audit.run_pipeline()
    b2 = (DATA_DIR / "audit.json").read_bytes()
    assert b1 == b2
    assert [r.model_dump() for r in r1] == [r.model_dump() for r in r2]


EXCEPTION_LABELS = {
    "PRICE_MISMATCH",
    "QTY_MISMATCH",
    "MISSING_PO",
    "DUPLICATE_INVOICE",
    "MISSING_RECEIPT",
    "TAX_MISMATCH",
}


def test_action_matches_label():
    records = apilot.audit.run_pipeline()
    by_id = {r.invoice_id: r for r in records}
    for inv_id, label in _labels().items():
        action = by_id[inv_id].action
        if label == "CLEAN":
            assert action == "AUTO_POST"
        else:
            assert label in EXCEPTION_LABELS
            assert action == "HUMAN_REVIEW"


def test_records_are_audit_records():
    records = apilot.audit.run_pipeline()
    for r in records:
        assert isinstance(r, AuditRecord)
        assert isinstance(r.invoice_id, str)
        assert r.action in {"AUTO_POST", "HUMAN_REVIEW"}
        assert isinstance(r.confidence, float)
        assert isinstance(r.findings, list)
        assert isinstance(r.suggested_resolution, str)


def test_audit_json_roundtrip():
    records = apilot.audit.run_pipeline()
    with open(DATA_DIR / "audit.json", encoding="utf-8") as fh:
        dumped = json.load(fh)
    assert len(dumped) == len(records)
    assert [AuditRecord.model_validate(d).model_dump() for d in dumped] == [
        r.model_dump() for r in records
    ]
