"""Deterministic three-way match: invoice vs PO vs goods receipt."""
import json
from pathlib import Path

from apilot.models import Finding, GoodsReceipt, Invoice, PurchaseOrder

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[1] / "data"

PRICE_TOLERANCE = 0.005  # |invoice - po| / po > this -> PRICE_MISMATCH (mirrors data.py)

SEVERITY = {
    "MISSING_PO": "high",
    "MISSING_RECEIPT": "high",
    "UNKNOWN_VENDOR": "high",
    "PRICE_MISMATCH": "medium",
    "QTY_MISMATCH": "medium",
}


def load_data(data_dir=None) -> tuple[list[PurchaseOrder], list[GoodsReceipt]]:
    """Read pos.json and receipts.json into models. Defaults to repo data/."""
    if data_dir is None:
        data_dir = DEFAULT_DATA_DIR
    data_dir = Path(data_dir)
    pos = [
        PurchaseOrder.model_validate(d)
        for d in json.loads((data_dir / "pos.json").read_text(encoding="utf-8"))
    ]
    receipts = [
        GoodsReceipt.model_validate(d)
        for d in json.loads((data_dir / "receipts.json").read_text(encoding="utf-8"))
    ]
    return pos, receipts


def _finding(type_: str, detail: str) -> Finding:
    return Finding(type=type_, severity=SEVERITY[type_], detail=detail)


def match_invoice(invoice: Invoice, pos: list[PurchaseOrder], receipts: list[GoodsReceipt]) -> list[Finding]:
    """Return all 3-way-match findings for one invoice, in deterministic order."""
    findings: list[Finding] = []

    # --- 1. MISSING_PO -------------------------------------------------------
    po = None
    if invoice.po_number is None:
        return [_finding("MISSING_PO", f"invoice {invoice.id} has no PO referenced")]
    for candidate in pos:
        if candidate.po_number == invoice.po_number:
            po = candidate
            break
    if po is None:
        return [_finding("MISSING_PO", f"no PO found for po_number '{invoice.po_number}'")]

    # --- 2. Vendor / currency consistency -------------------------------------
    # A PO from a different vendor or currency makes line comparison meaningless.
    if invoice.vendor != po.vendor:
        return [_finding("UNKNOWN_VENDOR",
                         f"vendor mismatch: invoice vendor '{invoice.vendor}' != PO vendor '{po.vendor}'")]
    if invoice.currency != po.currency:
        return [_finding("UNKNOWN_VENDOR",
                         f"currency mismatch: invoice currency '{invoice.currency}' != PO currency '{po.currency}'")]

    # --- 3. MISSING_RECEIPT -----------------------------------------------------
    if not any(r.po_number == po.po_number for r in receipts):
        findings.append(_finding("MISSING_RECEIPT",
                                 f"no GoodsReceipt found for po_number '{po.po_number}'"))

    # --- 4/5. Line-level price and quantity checks -------------------------------
    po_lines = {li.sku: li for li in po.line_items}
    for line in invoice.line_items:
        po_line = po_lines.get(line.sku)
        if po_line is None:
            findings.append(_finding("QTY_MISMATCH", f"no PO line for sku {line.sku}"))
            continue

        po_price = po_line.unit_price
        if po_price == 0:
            price_mismatch = line.unit_price != 0
        else:
            price_mismatch = abs(line.unit_price - po_price) / po_price > PRICE_TOLERANCE
        if price_mismatch:
            findings.append(_finding(
                "PRICE_MISMATCH",
                f"sku {line.sku}: invoice price {line.unit_price:.2f} != PO price {po_price:.2f} "
                f"(> {PRICE_TOLERANCE * 100:.1f}% tolerance)",
            ))

        if line.qty != po_line.qty:
            findings.append(_finding(
                "QTY_MISMATCH",
                f"sku {line.sku}: invoiced qty {line.qty} != ordered qty {po_line.qty}",
            ))

    return findings
