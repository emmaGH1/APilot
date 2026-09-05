"""Deterministic audit pipeline: decide every invoice, write data/audit.json."""
import json
from pathlib import Path

import apilot.data
from apilot.decide import decide
from apilot.models import AuditRecord, GoodsReceipt, Invoice, PurchaseOrder

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
INPUT_FILES = ("invoices.json", "pos.json", "receipts.json", "labels.json")


def run_pipeline(data_dir=None) -> list[AuditRecord]:
    """Run the full audit: generate-if-missing, decide all invoices, persist audit.json."""
    if data_dir is None:
        data_dir = DEFAULT_DATA_DIR
    data_dir = Path(data_dir)

    if not all((data_dir / name).exists() for name in INPUT_FILES):
        apilot.data.generate()

    def load(name: str, model):
        with open(data_dir / name, encoding="utf-8") as fh:
            return [model.model_validate(d) for d in json.load(fh)]

    invoices = load("invoices.json", Invoice)
    pos = load("pos.json", PurchaseOrder)
    receipts = load("receipts.json", GoodsReceipt)

    records = [
        AuditRecord(
            invoice_id=decision.invoice_id,
            action=decision.action,
            confidence=decision.confidence,
            findings=decision.findings,
            suggested_resolution=decision.suggested_resolution,
        )
        for decision in (decide(inv, pos, receipts, invoices) for inv in invoices)
    ]
    records.sort(key=lambda r: r.invoice_id)

    with open(data_dir / "audit.json", "w", encoding="utf-8") as fh:
        json.dump([r.model_dump() for r in records], fh, indent=2)
        fh.write("\n")

    return records


if __name__ == "__main__":
    run_pipeline()
