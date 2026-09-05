import json
from pathlib import Path

from apilot.evaluate import TYPES, evaluate

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
FILES = ("invoices.json", "labels.json", "audit.json")


def _snapshot():
    return {name: (DATA_DIR / name).read_bytes() for name in FILES}


def test_counts():
    res = evaluate()
    assert res["total_invoices"] == 120
    assert res["total_exceptions"] == 40


def test_perfect_metrics():
    res = evaluate()
    assert res["overall_action_accuracy"] == 1.0
    for t, m in res["per_type"].items():
        assert (m["precision"], m["recall"], m["f1"]) == (1.0, 1.0, 1.0)


def test_deterministic():
    assert evaluate() == evaluate()


def test_all_types_have_support():
    res = evaluate()
    assert set(res["per_type"]) == set(TYPES)
    for t in TYPES:
        assert res["per_type"][t]["support"] > 0


def test_read_only():
    before = _snapshot()
    evaluate()
    evaluate()
    assert _snapshot() == before
