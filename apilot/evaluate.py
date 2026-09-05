"""Deterministic, read-only evaluation of the audit trail vs ground-truth labels."""
import json
from pathlib import Path

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[1] / "data"

TYPES = [
    "CLEAN",
    "PRICE_MISMATCH",
    "QTY_MISMATCH",
    "MISSING_PO",
    "DUPLICATE_INVOICE",
    "MISSING_RECEIPT",
    "TAX_MISMATCH",
]


def _metrics(labeled: dict[str, bool], predicted: dict[str, bool]) -> dict:
    """Per-type precision/recall/F1 over boolean per-invoice arrays."""
    support = sum(labeled.values())
    tp = sum(1 for i in labeled if labeled[i] and predicted[i])
    fp = sum(1 for i in labeled if not labeled[i] and predicted[i])
    fn = sum(1 for i in labeled if labeled[i] and not predicted[i])
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"support": support, "precision": precision, "recall": recall, "f1": f1}


def evaluate(data_dir=None) -> dict:
    """Compare audit.json predictions against labels.json. Never writes files."""
    if data_dir is None:
        data_dir = DEFAULT_DATA_DIR
    data_dir = Path(data_dir)

    invoices = json.loads((data_dir / "invoices.json").read_text(encoding="utf-8"))
    labels = json.loads((data_dir / "labels.json").read_text(encoding="utf-8"))
    audit = json.loads((data_dir / "audit.json").read_text(encoding="utf-8"))
    audit_by_id = {rec["invoice_id"]: rec for rec in audit}

    ids = sorted(labels)
    total_invoices = len(invoices)
    total_exceptions = sum(1 for v in labels.values() if v != "CLEAN")

    per_type = {}
    for t in TYPES:
        if t == "CLEAN":
            predicted = {i: not audit_by_id[i]["findings"] for i in ids}
        else:
            predicted = {i: any(f["type"] == t for f in audit_by_id[i]["findings"]) for i in ids}
        labeled = {i: labels[i] == t for i in ids}
        per_type[t] = _metrics(labeled, predicted)

    correct = sum(
        1 for i in ids
        if (audit_by_id[i]["action"] == "AUTO_POST") == (labels[i] == "CLEAN")
    )
    overall_action_accuracy = correct / len(ids)

    manual_min, apilot_min = 5, 1
    count = len(ids)
    manual_baseline_assumption = {
        "manual_minutes_per_invoice": manual_min,
        "apilot_minutes_per_invoice": apilot_min,
        "total_manual_minutes": count * manual_min,
        "total_apilot_minutes": count * apilot_min,
        "time_saved_minutes": count * (manual_min - apilot_min),
        "note": "ASSUMPTION: manual AP review ~5 min/invoice vs ~1 min/invoice with APilot; not measured",
    }

    return {
        "overall_action_accuracy": overall_action_accuracy,
        "per_type": per_type,
        "manual_baseline_assumption": manual_baseline_assumption,
        "total_invoices": total_invoices,
        "total_exceptions": total_exceptions,
    }


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2))
