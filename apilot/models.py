from pydantic import BaseModel

class LineItem(BaseModel):
    sku: str
    qty: int
    unit_price: float   # 2-decimal amounts; matcher will compare with tolerance

class Invoice(BaseModel):
    id: str                     # e.g. "INV-0001"
    vendor: str
    invoice_number: str
    po_number: str | None       # None = no PO referenced
    currency: str = "USD"
    line_items: list[LineItem]

    @property
    def total(self) -> float:
        return round(sum(i.qty * i.unit_price for i in self.line_items), 2)

class PurchaseOrder(BaseModel):
    po_number: str
    vendor: str
    currency: str = "USD"
    line_items: list[LineItem]

    @property
    def total(self) -> float:
        return round(sum(i.qty * i.unit_price for i in self.line_items), 2)

class GoodsReceipt(BaseModel):
    po_number: str
    received: dict[str, int]    # sku -> qty received

class Finding(BaseModel):
    type: str      # one of: PRICE_MISMATCH, QTY_MISMATCH, MISSING_PO, DUPLICATE_INVOICE, MISSING_RECEIPT, TAX_MISMATCH, UNKNOWN_VENDOR
    detail: str
    severity: str  # "high" | "medium" | "low"

class Decision(BaseModel):
    invoice_id: str
    action: str        # "AUTO_POST" | "HUMAN_REVIEW"
    findings: list[Finding]
    confidence: float  # 0.0 to 1.0
    suggested_resolution: str
    # Policy-aware control fields (see apilot.policy for the routing table).
    policy_rule: str        # control rule that fired
    review_owner: str       # finance owner for the exception ("" when clean)
    recommended_action: str # what the owner should do next
    posting_status: str     # one of apilot.policy.ALL_STATUSES

class AuditRecord(BaseModel):
    invoice_id: str
    action: str
    confidence: float
    findings: list[Finding]
    suggested_resolution: str
    policy_rule: str
    review_owner: str
    recommended_action: str
    posting_status: str
