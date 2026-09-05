import json
from pathlib import Path

import apilot.data

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
FILES = ("invoices.json", "pos.json", "receipts.json", "labels.json")
EXCEPTION_TYPES = {
    "PRICE_MISMATCH",
    "QTY_MISMATCH",
    "MISSING_PO",
    "DUPLICATE_INVOICE",
    "MISSING_RECEIPT",
    "TAX_MISMATCH",
}


def _load(name: str):
    with open(DATA_DIR / name, encoding="utf-8") as fh:
        return json.load(fh)


def test_files_exist():
    apilot.data.generate()
    for name in FILES:
        assert (DATA_DIR / name).exists()


def test_invoice_count():
    apilot.data.generate()
    invoices = _load("invoices.json")
    assert 115 <= len(invoices) <= 125


def test_labels_cover_all_exception_types():
    apilot.data.generate()
    labels = _load("labels.json")
    exceptions = [label for label in labels.values() if label != "CLEAN"]
    assert EXCEPTION_TYPES <= set(exceptions)
    assert len(exceptions) >= 30


def test_deterministic():
    apilot.data.generate()
    first = {name: _load(name) for name in FILES}
    apilot.data.generate()
    second = {name: _load(name) for name in FILES}
    assert first == second
