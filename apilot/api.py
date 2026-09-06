"""FastAPI app: AP exception review dashboard (read-only over committed data + demo reviews)."""
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
STATIC_INDEX = Path(__file__).resolve().parents[1] / "static" / "index.html"
REVIEWS_FILE = "reviews.json"

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


class ReviewRequest(BaseModel):
    verdict: Literal["approve", "hold", "escalate"]
    reason: str = ""


@app.get("/", response_class=FileResponse)
def index() -> FileResponse:
    return FileResponse(STATIC_INDEX, media_type="text/html")


@app.get("/api/summary")
def summary() -> dict:
    invoices = _read("invoices.json")
    audit = _read("audit.json")
    auto_post = sum(1 for rec in audit if rec["action"] == "AUTO_POST")
    return {
        "total": len(invoices),
        "auto_post": auto_post,
        "human_review": len(audit) - auto_post,
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

    out = []
    for inv in invoices:
        po = pos_by_no.get(inv["po_number"]) if inv["po_number"] else None
        receipt = receipt_by_no.get(inv["po_number"]) if inv["po_number"] else None
        out.append({
            "id": inv["id"],
            "vendor": inv["vendor"],
            "invoice_number": inv["invoice_number"],
            "po_number": inv["po_number"],
            "currency": inv["currency"],
            "line_items": inv["line_items"],
            "total": _total(inv["line_items"]),
            "audit": audit_by_id.get(inv["id"]),
            "source_docs": {"po": po, "receipt": receipt},
            "reviews": reviews_by_id.get(inv["id"], []),
        })
    return out


@app.post("/api/review/{invoice_id}")
def review(invoice_id: str, body: ReviewRequest) -> dict:
    if not any(inv["id"] == invoice_id for inv in _read("invoices.json")):
        raise HTTPException(status_code=404, detail=f"unknown invoice_id '{invoice_id}'")

    record = {
        "invoice_id": invoice_id,
        "verdict": body.verdict,
        "reason": body.reason,
        "reviewer": "demo",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    reviews = _read_reviews()
    reviews.append(record)
    with open(Path(DATA_DIR) / REVIEWS_FILE, "w", encoding="utf-8") as fh:
        json.dump(reviews, fh, indent=2)
        fh.write("\n")
    return record
