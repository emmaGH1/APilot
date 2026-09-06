"""Hand-authored policy-aware control tests.

Each scenario builds its own PO/receipt/invoice (no shared data fixtures) and
asserts the routed review owner, recommended action, findings and posting
status produced by the policy-aware decision engine.
"""
import pytest

from apilot.decide import decide
from apilot.models import GoodsReceipt, Invoice, LineItem, PurchaseOrder
from apilot.policy import (
    AUTO_POST_ROUTE,
    ROUTES,
    STATUS_AUTO_POSTED,
    STATUS_BLOCKED,
    STATUS_ESCALATED,
    STATUS_ON_HOLD,
    STATUS_OVERRIDE_APPROVED,
    posting_status,
    route,
)

LI_A = LineItem(sku="SKU-A", qty=10, unit_price=10.00)
LI_B = LineItem(sku="SKU-B", qty=5, unit_price=20.00)


def po(*lines, po_number="PO-1", vendor="Acme Supplies", currency="USD"):
    return PurchaseOrder(
        po_number=po_number, vendor=vendor, currency=currency, line_items=list(lines)
    )


def receipt(p, **received):
    return GoodsReceipt(po_number=p.po_number, received=received)


def invoice(p, *lines, invoice_number="INV-1", id="INV-T", vendor=None,
            currency="USD", po_number="keep"):
    if not lines:
        lines = p.line_items
    return Invoice(
        id=id,
        vendor=p.vendor if vendor is None else vendor,
        invoice_number=invoice_number,
        po_number=p.po_number if po_number == "keep" else po_number,
        currency=currency,
        line_items=list(lines),
    )


def full_receipt(p):
    return receipt(p, **{li.sku: li.qty for li in p.line_items})


def test_clean_invoice_auto_posts():
    p = po(LI_A, LI_B)
    decision = decide(invoice(p), [p], [full_receipt(p)])
    assert decision.action == "AUTO_POST"
    assert decision.findings == []
    assert decision.policy_rule == AUTO_POST_ROUTE.policy_rule
    assert decision.review_owner == ""  # no exception, nobody to route to
    assert decision.recommended_action == AUTO_POST_ROUTE.recommended_action
    assert decision.posting_status == STATUS_AUTO_POSTED


def test_price_under_tolerance_is_still_clean():
    p = po(LI_A)
    # 10.01 vs 10.00 is +0.1%, inside the 0.5% tolerance
    under = invoice(p, LineItem(sku="SKU-A", qty=10, unit_price=10.01))
    decision = decide(under, [p], [full_receipt(p)])
    assert decision.action == "AUTO_POST"
    assert decision.findings == []
    assert decision.posting_status == STATUS_AUTO_POSTED


def test_price_over_tolerance_routes_to_ap_procurement():
    p = po(LI_A)
    over = invoice(p, LineItem(sku="SKU-A", qty=10, unit_price=10.10))  # +1.0%
    decision = decide(over, [p], [full_receipt(p)])
    assert decision.action == "HUMAN_REVIEW"
    assert [f.type for f in decision.findings] == ["PRICE_MISMATCH"]
    assert decision.review_owner == "AP/procurement"
    assert decision.policy_rule == ROUTES["PRICE_MISMATCH"].policy_rule
    assert decision.recommended_action == ROUTES["PRICE_MISMATCH"].recommended_action
    assert decision.posting_status == STATUS_BLOCKED


def test_excess_qty_routes_to_receiving():
    p = po(LI_A)
    excess = invoice(p, LineItem(sku="SKU-A", qty=12, unit_price=10.00))  # +2 over PO
    decision = decide(excess, [p], [full_receipt(p)])
    assert decision.action == "HUMAN_REVIEW"
    assert [f.type for f in decision.findings] == ["QTY_MISMATCH"]
    assert decision.review_owner == "Receiving"
    assert decision.recommended_action == ROUTES["QTY_MISMATCH"].recommended_action
    assert decision.posting_status == STATUS_BLOCKED


def test_missing_receipt_routes_to_receiving():
    p = po(LI_A)
    decision = decide(invoice(p), [p], [])
    assert [f.type for f in decision.findings] == ["MISSING_RECEIPT"]
    assert decision.review_owner == "Receiving"
    assert decision.policy_rule == ROUTES["MISSING_RECEIPT"].policy_rule
    assert decision.posting_status == STATUS_BLOCKED


def test_missing_po_routes_to_procurement_ap():
    no_ref = Invoice(
        id="INV-NOREF", vendor="Acme Supplies", invoice_number="T1",
        po_number=None, line_items=[LI_A],
    )
    dangling = Invoice(
        id="INV-DANGLE", vendor="Acme Supplies", invoice_number="T2",
        po_number="PO-9999", line_items=[LI_A],
    )
    for bad in (no_ref, dangling):
        decision = decide(bad, [po(LI_A)], [])
        assert [f.type for f in decision.findings] == ["MISSING_PO"]
        assert decision.review_owner == "Procurement/AP"
        assert decision.recommended_action == ROUTES["MISSING_PO"].recommended_action
        assert decision.posting_status == STATUS_BLOCKED


def test_duplicate_routes_to_ap_manager():
    p = po(LI_A)
    first = invoice(p, id="INV-0001", invoice_number="DUP-1")
    second = invoice(p, id="INV-0002", invoice_number="DUP-1")
    invoices = [first, second]

    # first occurrence is clean
    d1 = decide(first, [p], [full_receipt(p)], invoices)
    assert d1.action == "AUTO_POST"
    assert d1.posting_status == STATUS_AUTO_POSTED

    # second occurrence is the duplicate
    d2 = decide(second, [p], [full_receipt(p)], invoices)
    assert [f.type for f in d2.findings] == ["DUPLICATE_INVOICE"]
    assert d2.review_owner == "AP manager"
    assert d2.policy_rule == ROUTES["DUPLICATE_INVOICE"].policy_rule
    assert d2.posting_status == STATUS_BLOCKED


def test_tax_uplift_routes_to_tax_controller():
    p = po(LI_A, LI_B)
    tax_lines = [
        LineItem(sku=li.sku, qty=li.qty, unit_price=round(li.unit_price * 1.1, 2))
        for li in p.line_items
    ]
    decision = decide(invoice(p, *tax_lines), [p], [full_receipt(p)])
    assert [f.type for f in decision.findings] == ["TAX_MISMATCH"]
    assert decision.review_owner == "Tax/controller"
    assert decision.policy_rule == ROUTES["TAX_MISMATCH"].policy_rule
    assert decision.posting_status == STATUS_BLOCKED


def test_vendor_mismatch_routes_to_vendor_master():
    p = po(LI_A, vendor="Acme Supplies")
    wrong_vendor = invoice(p, vendor="Bolt Hardware")
    decision = decide(wrong_vendor, [p], [full_receipt(p)])
    assert [f.type for f in decision.findings] == ["UNKNOWN_VENDOR"]
    assert decision.review_owner == "Vendor master/AP manager"
    assert decision.recommended_action == ROUTES["UNKNOWN_VENDOR"].recommended_action
    assert decision.posting_status == STATUS_BLOCKED


def test_currency_mismatch_routes_to_vendor_master():
    p = po(LI_A, currency="USD")
    foreign = invoice(p, currency="EUR")
    decision = decide(foreign, [p], [full_receipt(p)])
    assert [f.type for f in decision.findings] == ["UNKNOWN_VENDOR"]
    assert decision.review_owner == "Vendor master/AP manager"
    assert decision.posting_status == STATUS_BLOCKED


def test_multi_finding_routes_to_highest_severity_owner():
    p = po(LI_A)
    # missing receipt (high) AND price mismatch (medium) on the same invoice
    over = invoice(p, LineItem(sku="SKU-A", qty=10, unit_price=10.50))
    decision = decide(over, [p], [])
    assert {f.type for f in decision.findings} == {"MISSING_RECEIPT", "PRICE_MISMATCH"}
    # routing follows the highest-severity finding: Receiving owns it
    assert decision.review_owner == "Receiving"
    assert decision.policy_rule == ROUTES["MISSING_RECEIPT"].policy_rule
    assert decision.posting_status == STATUS_BLOCKED


def test_route_tiebreak_keeps_matcher_order():
    # two medium findings: price mismatch is reported before qty mismatch
    p = po(LI_A)
    bad = invoice(p, LineItem(sku="SKU-A", qty=12, unit_price=10.50))
    decision = decide(bad, [p], [full_receipt(p)])
    types = [f.type for f in decision.findings]
    assert types == ["PRICE_MISMATCH", "QTY_MISMATCH"]
    assert route(decision.findings) == ROUTES["PRICE_MISMATCH"]
    assert decision.review_owner == "AP/procurement"


def test_posting_status_derives_from_latest_review():
    assert posting_status("AUTO_POST") == STATUS_AUTO_POSTED
    # a review cannot un-post a clean auto-posted invoice
    assert posting_status("AUTO_POST", {"verdict": "hold"}) == STATUS_AUTO_POSTED

    assert posting_status("HUMAN_REVIEW") == STATUS_BLOCKED
    assert posting_status("HUMAN_REVIEW", {"verdict": "approve"}) == STATUS_OVERRIDE_APPROVED
    assert posting_status("HUMAN_REVIEW", {"verdict": "hold"}) == STATUS_ON_HOLD
    assert posting_status("HUMAN_REVIEW", {"verdict": "escalate"}) == STATUS_ESCALATED


def test_every_finding_type_has_a_route_and_owner():
    # each matcher finding type must route somewhere (safety net for new types)
    from apilot.matcher import SEVERITY

    assert set(ROUTES) >= set(SEVERITY)
    for owner in (r.review_owner for r in ROUTES.values()):
        assert owner
