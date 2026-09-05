from apilot.matcher import match_invoice
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
LI_B = LineItem(sku="SKU-B", qty=5, unit_price=20.0)


def test_clean_match_no_findings():
    po = make_po(LI_A, LI_B)
    receipt = make_receipt(po, **{li.sku: li.qty for li in po.line_items})
    invoice = make_invoice(po, LI_A, LI_B)
    assert match_invoice(invoice, [po], [receipt]) == []


def test_price_mismatch():
    po = make_po(LI_A)
    receipt = make_receipt(po, **{li.sku: li.qty for li in po.line_items})
    invoice = make_invoice(po, LineItem(sku="SKU-A", qty=10, unit_price=10.50))
    findings = match_invoice(invoice, [po], [receipt])
    assert len(findings) == 1
    assert findings[0].type == "PRICE_MISMATCH"
    assert findings[0].severity == "medium"
    assert "SKU-A" in findings[0].detail


def test_qty_mismatch():
    po = make_po(LI_A)
    receipt = make_receipt(po, **{li.sku: li.qty for li in po.line_items})
    invoice = make_invoice(po, LineItem(sku="SKU-A", qty=12, unit_price=10.0))
    findings = match_invoice(invoice, [po], [receipt])
    assert len(findings) == 1
    assert findings[0].type == "QTY_MISMATCH"
    assert findings[0].severity == "medium"
    assert "SKU-A" in findings[0].detail
    assert "12" in findings[0].detail
    assert "10" in findings[0].detail


def test_missing_po():
    # po_number=None
    no_ref = Invoice(
        id="INV-NOREF", vendor="Acme Supplies", invoice_number="T1",
        po_number=None, line_items=[LI_A],
    )
    findings = match_invoice(no_ref, [], [])
    assert len(findings) == 1
    assert findings[0].type == "MISSING_PO"
    assert findings[0].severity == "high"

    # dangling po_number not present in pos
    dangling = make_invoice(make_po(LI_A, po_number="PO-X"), LI_A, po_number="PO-9999")
    findings = match_invoice(dangling, [make_po(LI_A, po_number="PO-X")], [])
    assert len(findings) == 1
    assert findings[0].type == "MISSING_PO"
    assert findings[0].severity == "high"
    assert "PO-9999" in findings[0].detail


def test_missing_receipt():
    po = make_po(LI_A)
    invoice = make_invoice(po, LI_A)
    findings = match_invoice(invoice, [po], [])
    assert len(findings) == 1
    assert findings[0].type == "MISSING_RECEIPT"
    assert findings[0].severity == "high"
    assert "PO-1" in findings[0].detail
