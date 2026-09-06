"""Deterministic decision engine over 3-way-match findings."""
from apilot.matcher import match_invoice
from apilot.models import Decision
from apilot.policy import (
    AUTO_POST_ROUTE,
    STATUS_AUTO_POSTED,
    STATUS_BLOCKED,
    route,
)

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
            policy_rule=AUTO_POST_ROUTE.policy_rule,
            review_owner=AUTO_POST_ROUTE.review_owner,
            recommended_action=AUTO_POST_ROUTE.recommended_action,
            posting_status=STATUS_AUTO_POSTED,
        )

    # One phrase per distinct finding type, in matcher return order.
    phrases = [RESOLUTION_PHRASE[t] for t in dict.fromkeys(f.type for f in findings)]
    owner = route(findings)
    return Decision(
        invoice_id=invoice.id,
        action="HUMAN_REVIEW",
        findings=findings,
        confidence=0.0,
        suggested_resolution="Human review required: " + "; ".join(phrases),
        policy_rule=owner.policy_rule,
        review_owner=owner.review_owner,
        recommended_action=owner.recommended_action,
        posting_status=STATUS_BLOCKED,
    )
