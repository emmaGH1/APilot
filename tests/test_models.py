from apilot.models import Decision, Finding, Invoice, LineItem


def test_invoice_total():
    invoice = Invoice(
        id="INV-0001",
        vendor="Acme",
        invoice_number="INV-0001",
        po_number="PO-0001",
        line_items=[
            LineItem(sku="A", qty=2, unit_price=10.0),
            LineItem(sku="B", qty=3, unit_price=2.5),
        ],
    )
    assert invoice.total == 27.5


def test_finding_and_decision_fields():
    finding = Finding(
        type="PRICE_MISMATCH",
        detail="unit price 10.00 vs PO 9.00",
        severity="high",
    )
    decision = Decision(
        invoice_id="INV-0001",
        action="HUMAN_REVIEW",
        findings=[finding],
        confidence=0.8,
        suggested_resolution="Review price discrepancy",
    )
    assert decision.invoice_id == "INV-0001"
    assert decision.action == "HUMAN_REVIEW"
    assert decision.findings == [finding]
    assert decision.confidence == 0.8
    assert decision.suggested_resolution == "Review price discrepancy"


def test_invoice_without_po():
    invoice = Invoice(
        id="INV-0002",
        vendor="Acme",
        invoice_number="INV-0002",
        po_number=None,
        line_items=[],
    )
    assert invoice.po_number is None
