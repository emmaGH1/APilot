from apilot.decide import decide
from apilot.models import GoodsReceipt, Invoice, LineItem, PurchaseOrder


def make_po(*lines, po_number="PO-1", vendor="Acme Supplies"):
    return PurchaseOrder(po_number=po_number, vendor=vendor, line_items=list(lines))


def make_receipt(po, **received):
    return GoodsReceipt(po_number=po.po_number, received=received)


def make_invoice(po, *lines, po_number="sentinel"):
    return Invoice(
        id="INV-TEST",
        vendor=po.vendor,
        invoice_number="TEST-0001",
        po_number=po.po_number if po_number == "sentinel" else po_number,
        line_items=list(lines),
    )


LI_A = LineItem(sku="SKU-A", qty=10, unit_price=10.0)


def test_clean_invoice_auto_posts():
    po = make_po(LI_A)
    receipt = make_receipt(po, **{li.sku: li.qty for li in po.line_items})
    decision = decide(make_invoice(po, LI_A), [po], [receipt])
    assert decision.action == "AUTO_POST"
    assert decision.confidence == 1.0
    assert decision.findings == []
    assert decision.suggested_resolution == "Automatically post invoice"
    assert decision.invoice_id == "INV-TEST"


def test_missing_po_goes_to_human_review():
    no_ref = Invoice(
        id="INV-NOREF", vendor="Acme Supplies", invoice_number="T1",
        po_number=None, line_items=[LI_A],
    )
    decision = decide(no_ref, [], [])
    assert decision.action == "HUMAN_REVIEW"
    assert decision.confidence == 0.0
    assert [f.type for f in decision.findings] == ["MISSING_PO"]
    assert "purchase order" in decision.suggested_resolution


def test_price_mismatch_goes_to_human_review():
    po = make_po(LI_A)
    receipt = make_receipt(po, **{li.sku: li.qty for li in po.line_items})
    invoice = make_invoice(po, LineItem(sku="SKU-A", qty=10, unit_price=10.50))
    decision = decide(invoice, [po], [receipt])
    assert decision.action == "HUMAN_REVIEW"
    assert decision.confidence == 0.0
    assert [f.type for f in decision.findings] == ["PRICE_MISMATCH"]
    assert "price" in decision.suggested_resolution


def test_qty_mismatch_goes_to_human_review():
    po = make_po(LI_A)
    receipt = make_receipt(po, **{li.sku: li.qty for li in po.line_items})
    invoice = make_invoice(po, LineItem(sku="SKU-A", qty=12, unit_price=10.0))
    decision = decide(invoice, [po], [receipt])
    assert decision.action == "HUMAN_REVIEW"
    assert decision.confidence == 0.0
    assert [f.type for f in decision.findings] == ["QTY_MISMATCH"]
    assert "quantity" in decision.suggested_resolution


def test_missing_receipt_goes_to_human_review():
    po = make_po(LI_A)
    decision = decide(make_invoice(po, LI_A), [po], [])
    assert decision.action == "HUMAN_REVIEW"
    assert decision.confidence == 0.0
    assert [f.type for f in decision.findings] == ["MISSING_RECEIPT"]
    assert "receipt" in decision.suggested_resolution
