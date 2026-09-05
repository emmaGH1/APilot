"""Deterministic three-way match: invoice vs PO vs goods receipt.

Also detects duplicate invoices (needs the full invoice list) and
uniform ~10% tax-style price uplifts.
"""
import json
from pathlib import Path

from apilot.models import Finding, GoodsReceipt, Invoice, PurchaseOrder

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[1] / "data"

PRICE_TOLERANCE = 0.005  # |invoice - po| / po > this -> PRICE_MISMATCH (mirrors data.py)
TAX_RATIO = 1.1          # uniform uplift that marks a TAX_MISMATCH (mirrors data.py)

SEVERITY = {
    "MISSING_PO": "high",
    "MISSING_RECEIPT": "high",
    "UNKNOWN_VENDOR": "high",
    "DUPLICATE_INVOICE": "high",
    "PRICE_MISMATCH": "medium",
    "TAX_MISMATCH": "medium",
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


def _duplicate_finding(invoice: Invoice, invoices: list[Invoice] | None) -> Finding | None:
    """Flag the later occurrence of a (vendor, invoice_number) pair, if any.

    The occurrence later in `invoices` is the duplicate; when the invoice is not
    in the list at all, id ordering decides. Returns the first match, if any.
    """
    if invoices is None:
        return None

    self_idx = next((i for i, other in enumerate(invoices) if other.id == invoice.id), None)
    for other in invoices:
        if other.id == invoice.id:
            continue
        if other.vendor != invoice.vendor or other.invoice_number != invoice.invoice_number:
            continue
        if self_idx is None:
            later = invoice.id > other.id
        else:
            other_idx = next(i for i, cand in enumerate(invoices) if cand.id == other.id)
            later = self_idx > other_idx
        if later:
            return _finding(
                "DUPLICATE_INVOICE",
                f"invoice {invoice.id} duplicates invoice {other.id}: "
                f"vendor '{invoice.vendor}', invoice number '{invoice.invoice_number}'",
            )
    return None


def match_invoice(invoice: Invoice, pos: list[PurchaseOrder], receipts: list[GoodsReceipt],
                  invoices: list[Invoice] | None = None) -> list[Finding]:
    """Return all match findings for one invoice, in deterministic order.

    `invoices` enables DUPLICATE_INVOICE detection; when omitted that check is
    skipped entirely (single-invoice calls never report duplicates).
    """
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

    # --- 2b. DUPLICATE_INVOICE (dup first, then receipt, then lines) ----------
    dup = _duplicate_finding(invoice, invoices)
    if dup is not None:
        findings.append(dup)

    # --- 3. MISSING_RECEIPT -----------------------------------------------------
    if not any(r.po_number == po.po_number for r in receipts):
        findings.append(_finding("MISSING_RECEIPT",
                                 f"no GoodsReceipt found for po_number '{po.po_number}'"))

    # --- 4/5. Line-level TAX / price / quantity checks --------------------------
    po_lines = {li.sku: li for li in po.line_items}

    def _price_within(price: float, base: float) -> bool:
        if base == 0:
            return price == 0
        return abs(price - base) / base <= PRICE_TOLERANCE

    # TAX_MISMATCH: every line has a PO counterpart at the same qty, each priced
    # ~10% above its PO line (uniform uplift; tolerance absorbs 2dp rounding).
    is_tax = bool(invoice.line_items) and all(
        li.sku in po_lines
        and li.qty == po_lines[li.sku].qty
        and _price_within(li.unit_price, po_lines[li.sku].unit_price * TAX_RATIO)
        for li in invoice.line_items
    )
    if is_tax:
        findings.append(_finding(
            "TAX_MISMATCH",
            f"invoice {invoice.id}: all line prices are ~{int((TAX_RATIO - 1) * 100)}% above "
            f"PO '{po.po_number}' (uniform uplift consistent with a tax-inclusive total)",
        ))

    for line in invoice.line_items:
        po_line = po_lines.get(line.sku)
        if po_line is None:
            findings.append(_finding("QTY_MISMATCH", f"no PO line for sku {line.sku}"))
            continue

        if not is_tax:
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
