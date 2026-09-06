"""FastAPI app: AP exception review dashboard (read-only over committed data + demo reviews)."""
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, field_validator

from apilot.decide import decide
from apilot.evaluate import evaluate as run_evaluation
from apilot.extract import (
    ExtractionError,
    extract_invoice,
)
from apilot.models import GoodsReceipt, Invoice, PurchaseOrder
from apilot.policy import STATUS_BLOCKED, posting_status

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
STATIC_INDEX = Path(__file__).resolve().parents[1] / "static" / "index.html"
REVIEWS_FILE = "reviews.json"

REVIEWER = "AP Analyst (demo)"

app = FastAPI(title="APilot exception review dashboard")


def _read(name: str):
    """Read a JSON file from the (monkeypatchable) data dir, per request."""
    with open(Path(DATA_DIR) / name, encoding="utf-8") as fh:
        return json.load(fh)


def _read_reviews():
    path = Path(DATA_DIR) / REVIEWS_FILE
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _total(line_items) -> float:
    return round(sum(li["qty"] * li["unit_price"] for li in line_items), 2)


def _latest_reviews(reviews: list[dict]) -> dict[str, dict]:
    """Map invoice_id -> most recently recorded review (append order)."""
    latest: dict[str, dict] = {}
    for review in reviews:
        latest[review["invoice_id"]] = review
    return latest


class ReviewRequest(BaseModel):
    verdict: Literal["approve", "hold", "escalate"]
    reason: str = ""

    @field_validator("reason")
    @classmethod
    def reason_must_be_nonblank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("review reason must not be blank")
        return v


class ExtractRequest(BaseModel):
    text: str


@app.get("/", response_class=FileResponse)
def index() -> FileResponse:
    return FileResponse(STATIC_INDEX, media_type="text/html")


@app.get("/api/summary")
def summary() -> dict:
    invoices = _read("invoices.json")
    audit = _read("audit.json")
    reviews = _read_reviews()
    latest = _latest_reviews(reviews)
    reviewed_ids = set(latest)

    auto_post = 0
    pending_review = 0
    for rec in audit:
        if rec["action"] == "AUTO_POST":
            auto_post += 1
        if posting_status(rec["action"], latest.get(rec["invoice_id"])) == STATUS_BLOCKED:
            pending_review += 1

    total = len(invoices)
    return {
        "total": total,
        "auto_post": auto_post,
        "human_review": len(audit) - auto_post,
        "pending_review": pending_review,
        "reviewed": sum(1 for inv in invoices if inv["id"] in reviewed_ids),
        "touchless_rate": round(auto_post / total, 4) if total else 0.0,
    }


@app.get("/api/invoices")
def invoices() -> list[dict]:
    invoices = sorted(_read("invoices.json"), key=lambda inv: inv["id"])
    pos_by_no = {po["po_number"]: po for po in _read("pos.json")}
    receipt_by_no = {r["po_number"]: r for r in _read("receipts.json")}
    audit_by_id = {rec["invoice_id"]: rec for rec in _read("audit.json")}

    reviews_by_id: dict[str, list[dict]] = defaultdict(list)
    for rev in _read_reviews():
        reviews_by_id[rev["invoice_id"]].append(rev)
    latest = _latest_reviews(_read_reviews())

    out = []
    for inv in invoices:
        po = pos_by_no.get(inv["po_number"]) if inv["po_number"] else None
        receipt = receipt_by_no.get(inv["po_number"]) if inv["po_number"] else None
        audit = audit_by_id.get(inv["id"])
        reviews = reviews_by_id.get(inv["id"], [])
        out.append({
            "id": inv["id"],
            "vendor": inv["vendor"],
            "invoice_number": inv["invoice_number"],
            "po_number": inv["po_number"],
            "currency": inv["currency"],
            "line_items": inv["line_items"],
            "total": _total(inv["line_items"]),
            "audit": audit,
            "policy_rule": audit["policy_rule"] if audit else "",
            "review_owner": audit["review_owner"] if audit else "",
            "recommended_action": audit["recommended_action"] if audit else "",
            "posting_status": posting_status(
                audit["action"], latest.get(inv["id"])
            ) if audit else STATUS_BLOCKED,
            "source_docs": {"po": po, "receipt": receipt},
            "reviews": reviews,
        })
    return out


@app.get("/api/evaluation")
def evaluation() -> dict:
    """Read-only evaluation of the audit trail vs ground-truth labels."""
    return run_evaluation(data_dir=DATA_DIR)


@app.get("/api/capabilities")
def capabilities() -> dict:
    """Feature flags the dashboard can consult."""
    return {"extraction_enabled": bool(os.environ.get("APILOT_LLM_KEY"))}


@app.post("/api/review/{invoice_id}")
def review(invoice_id: str, body: ReviewRequest) -> dict:
    audit_by_id = {rec["invoice_id"]: rec for rec in _read("audit.json")}
    if invoice_id not in audit_by_id:
        raise HTTPException(status_code=404, detail=f"unknown invoice_id '{invoice_id}'")

    record = {
        "invoice_id": invoice_id,
        "verdict": body.verdict,
        "reason": body.reason,
        "reviewer": REVIEWER,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    reviews = _read_reviews()
    reviews.append(record)
    with open(Path(DATA_DIR) / REVIEWS_FILE, "w", encoding="utf-8") as fh:
        json.dump(reviews, fh, indent=2)
        fh.write("\n")

    return {
        **record,
        "posting_status": posting_status(audit_by_id[invoice_id]["action"], record),
    }


@app.post("/api/extract")
def extract(body: ExtractRequest) -> dict:
    """Extract an invoice from raw text and run it through the decision engine."""
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="text must not be empty")

    try:
        invoice = extract_invoice(text)
    except ExtractionError as exc:
        raise HTTPException(status_code=502, detail=f"extraction failed: {exc}") from exc

    pos = [PurchaseOrder.model_validate(d) for d in _read("pos.json")]
    receipts = [GoodsReceipt.model_validate(d) for d in _read("receipts.json")]
    invoices = [Invoice.model_validate(d) for d in _read("invoices.json")]
    decision = decide(invoice, pos, receipts, invoices)

    po = next((p for p in pos if invoice.po_number and p.po_number == invoice.po_number), None)
    receipt = next(
        (r for r in receipts if invoice.po_number and r.po_number == invoice.po_number), None
    )
    return {
        "invoice": invoice.model_dump(),
        "findings": [f.model_dump() for f in decision.findings],
        "action": decision.action,
        "policy_rule": decision.policy_rule,
        "review_owner": decision.review_owner,
        "recommended_action": decision.recommended_action,
        "posting_status": decision.posting_status,
        "suggested_resolution": decision.suggested_resolution,
        "po": po.model_dump() if po else None,
        "receipt": receipt.model_dump() if receipt else None,
    }
