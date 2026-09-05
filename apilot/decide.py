"""Deterministic decision engine over 3-way-match findings."""
from apilot.matcher import match_invoice
from apilot.models import Decision

AUTO_RESOLUTION = "Automatically post invoice"

# Human-review phrasing per finding type (unions resolve in matcher order).
RESOLUTION_PHRASE = {
    "MISSING_PO": "locate or create the referenced purchase order",
    "MISSING_RECEIPT": "confirm goods receipt for the purchase order",
    "UNKNOWN_VENDOR": "verify vendor identity and currency",
    "DUPLICATE_INVOICE": "review the duplicate invoice pair",
    "PRICE_MISMATCH": "reconcile unit price discrepancies",
    "TAX_MISMATCH": "reconcile the tax-inclusive total discrepancy",
    "QTY_MISMATCH": "reconcile quantity discrepancies",
}


def decide(invoice, pos, receipts, invoices=None) -> Decision:
    """Decide AUTO_POST or HUMAN_REVIEW from matcher findings."""
    findings = match_invoice(invoice, pos, receipts, invoices)
    if not findings:
        return Decision(
            invoice_id=invoice.id,
            action="AUTO_POST",
            findings=[],
            confidence=1.0,
            suggested_resolution=AUTO_RESOLUTION,
        )

    # One phrase per distinct finding type, in matcher return order.
    phrases = [RESOLUTION_PHRASE[t] for t in dict.fromkeys(f.type for f in findings)]
    return Decision(
        invoice_id=invoice.id,
        action="HUMAN_REVIEW",
        findings=findings,
        confidence=0.0,
        suggested_resolution="Human review required: " + "; ".join(phrases),
    )
