from apilot.matcher import match_invoice
from apilot.models import GoodsReceipt, Invoice, LineItem, PurchaseOrder


def make_po(*lines, po_number="PO-1", vendor="Acme Supplies"):
    return PurchaseOrder(po_number=po_number, vendor=vendor, line_items=list(lines))


def make_receipt(po, **received):
    return GoodsReceipt(po_number=po.po_number, received=received)


def make_invoice(po, *lines, po_number="sentinel", id="INV-TEST",
                 invoice_number="TEST-0001", vendor=None):
    return Invoice(
        id=id,
        vendor=po.vendor if vendor is None else vendor,
        invoice_number=invoice_number,
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


def test_duplicate_pair_flags_only_second():
    po = make_po(LI_A)
    receipt = make_receipt(po, **{li.sku: li.qty for li in po.line_items})
    inv1 = make_invoice(po, LI_A, id="INV-0001", invoice_number="DUP-1")
    inv2 = make_invoice(po, LI_A, id="INV-0002", invoice_number="DUP-1")
    invoices = [inv1, inv2]
    # first occurrence: no duplicate finding (clean match otherwise)
    assert match_invoice(inv1, [po], [receipt], invoices) == []
    # second occurrence: exactly one DUPLICATE_INVOICE
    findings = match_invoice(inv2, [po], [receipt], invoices)
    assert len(findings) == 1
    assert findings[0].type == "DUPLICATE_INVOICE"
    assert findings[0].severity == "high"
    assert "INV-0001" in findings[0].detail
    assert "DUP-1" in findings[0].detail


def test_no_duplicate_without_invoices_list():
    po = make_po(LI_A)
    receipt = make_receipt(po, **{li.sku: li.qty for li in po.line_items})
    inv2 = make_invoice(po, LI_A, id="INV-0002", invoice_number="DUP-1")
    # invoices omitted -> duplicate detection is off
    assert match_invoice(inv2, [po], [receipt]) == []


def test_same_invoice_number_different_vendor_is_not_duplicate():
    po1 = make_po(LI_A, vendor="Acme Supplies")
    po2 = make_po(LI_A, vendor="Bolt Hardware")
    receipt1 = make_receipt(po1, **{li.sku: li.qty for li in po1.line_items})
    receipt2 = make_receipt(po2, **{li.sku: li.qty for li in po2.line_items})
    inv1 = make_invoice(po1, LI_A, id="INV-0001", invoice_number="X-1")
    inv2 = make_invoice(po2, LI_A, id="INV-0002", invoice_number="X-1")
    assert match_invoice(inv2, [po2], [receipt2], [inv1, inv2]) == []


def test_uniform_tax_scale_is_tax_mismatch():
    po = make_po(LI_A, LI_B)
    receipt = make_receipt(po, **{li.sku: li.qty for li in po.line_items})
    tax_lines = [
        LineItem(sku=li.sku, qty=li.qty, unit_price=round(li.unit_price * 1.1, 2))
        for li in po.line_items
    ]
    invoice = make_invoice(po, *tax_lines)
    findings = match_invoice(invoice, [po], [receipt])
    assert [f.type for f in findings] == ["TAX_MISMATCH"]
    assert findings[0].severity == "medium"


def test_single_line_price_change_is_price_not_tax():
    po = make_po(LI_A, LI_B)
    receipt = make_receipt(po, **{li.sku: li.qty for li in po.line_items})
    # one line 5% up, the other unchanged -> not a uniform 10% uplift
    invoice = make_invoice(po, LI_A, LineItem(sku="SKU-B", qty=5, unit_price=21.00))
    findings = match_invoice(invoice, [po], [receipt])
    assert [f.type for f in findings] == ["PRICE_MISMATCH"]
    assert "SKU-B" in findings[0].detail
