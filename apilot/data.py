import json
import random
from pathlib import Path

from apilot.models import GoodsReceipt, Invoice, LineItem, PurchaseOrder

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

VENDORS = [
    "Acme Supplies",
    "Bolt Hardware",
    "CircuitCo",
    "Delta Logistics",
    "Ember Packaging",
    "Ferrum Steel",
]
SKUS = [f"SKU-{n}" for n in range(1001, 1051)]

N_POS = 80
N_UNRECEIVED = 8          # ~90% of POs get a receipt
N_EXTRA_CLEAN = 27        # POs may be invoiced more than once (still CLEAN)
N_MISSING_PO = 6
N_LABELED_EXCEPTIONS = 40


def _clone_lines(po: PurchaseOrder) -> list[LineItem]:
    return [LineItem(sku=li.sku, qty=li.qty, unit_price=li.unit_price) for li in po.line_items]


def generate() -> None:
    random.seed(42)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # --- Purchase orders: 80 POs, 1-3 line items each ---------------------
    pos: list[PurchaseOrder] = []
    for n in range(1, N_POS + 1):
        vendor = random.choice(VENDORS)
        skus = random.sample(SKUS, random.randint(1, 3))
        lines = [
            LineItem(sku=sku, qty=random.randint(1, 50), unit_price=round(random.uniform(5.0, 500.0), 2))
            for sku in skus
        ]
        pos.append(PurchaseOrder(po_number=f"PO-{n:04d}", vendor=vendor, line_items=lines))

    # --- Goods receipts for ~90% of POs (received = ordered) --------------
    unreceived_idx = set(random.sample(range(N_POS), N_UNRECEIVED))
    received_idx = [i for i in range(N_POS) if i not in unreceived_idx]

    receipts = [
        GoodsReceipt(po_number=pos[i].po_number, received={li.sku: li.qty for li in pos[i].line_items})
        for i in received_idx
    ]

    # --- PO budget: exception POs (all received except MISSING_RECEIPT) ---
    pool = random.sample(received_idx, 26)
    price_idx, qty_idx, dup_idx, tax_idx = pool[:7], pool[7:13], pool[13:20], pool[20:26]
    clean_idx = [i for i in received_idx if i not in set(pool)]

    invoices: list[Invoice] = []
    labels: dict[str, str] = {}
    next_id = {"n": 1}   # INV-0001 ...
    next_no = {"n": 1}   # supplier invoice number (unique; shared by a dup pair)

    def take_no() -> str:
        no = f"{next_no['n']:06d}"
        next_no["n"] += 1
        return no

    def new_invoice(po_idx: int, invoice_number: str, lines: list[LineItem], label: str) -> None:
        po = pos[po_idx]
        inv = Invoice(
            id=f"INV-{next_id['n']:04d}",
            vendor=po.vendor,
            invoice_number=invoice_number,
            po_number=po.po_number,
            line_items=lines,
        )
        next_id["n"] += 1
        invoices.append(inv)
        labels[inv.id] = label

    def new_invoice_no_po(vendor: str, lines: list[LineItem], label: str) -> None:
        inv = Invoice(
            id=f"INV-{next_id['n']:04d}",
            vendor=vendor,
            invoice_number=take_no(),
            po_number=None,
            line_items=lines,
        )
        next_id["n"] += 1
        invoices.append(inv)
        labels[inv.id] = label

    # CLEAN: one per remaining received PO...
    for i in clean_idx:
        new_invoice(i, take_no(), _clone_lines(pos[i]), "CLEAN")

    # ...plus extra CLEAN invoices (each still matches its PO exactly)
    for i in random.sample(clean_idx, N_EXTRA_CLEAN):
        new_invoice(i, take_no(), _clone_lines(pos[i]), "CLEAN")

    # PRICE_MISMATCH: one line priced >0.5% above PO; qty equal to PO
    for i in price_idx:
        lines = _clone_lines(pos[i])
        j = random.randrange(len(lines))
        lines[j].unit_price = round(lines[j].unit_price * random.uniform(1.03, 1.08), 2)
        new_invoice(i, take_no(), lines, "PRICE_MISMATCH")

    # QTY_MISMATCH: one line over-invoiced; price equal to PO
    for i in qty_idx:
        lines = _clone_lines(pos[i])
        j = random.randrange(len(lines))
        lines[j].qty += random.randint(1, 3)
        new_invoice(i, take_no(), lines, "QTY_MISMATCH")

    # DUPLICATE_INVOICE: same vendor + invoice_number twice; first is CLEAN
    for i in dup_idx:
        no = take_no()
        new_invoice(i, no, _clone_lines(pos[i]), "CLEAN")
        new_invoice(i, no, _clone_lines(pos[i]), "DUPLICATE_INVOICE")

    # MISSING_RECEIPT: invoice for a PO that has no GoodsReceipt
    for i in sorted(unreceived_idx):
        new_invoice(i, take_no(), _clone_lines(pos[i]), "MISSING_RECEIPT")

    # TAX_MISMATCH: every line price scaled by 1.10, so the invoice total
    # lands ~10% above the PO total while the invoice's own line math holds.
    for i in tax_idx:
        lines = _clone_lines(pos[i])
        for li in lines:
            li.unit_price = round(li.unit_price * 1.1, 2)
        new_invoice(i, take_no(), lines, "TAX_MISMATCH")

    # MISSING_PO: no PO referenced at all
    for _ in range(N_MISSING_PO):
        vendor = random.choice(VENDORS)
        skus = random.sample(SKUS, random.randint(1, 3))
        lines = [
            LineItem(sku=sku, qty=random.randint(1, 50), unit_price=round(random.uniform(5.0, 500.0), 2))
            for sku in skus
        ]
        new_invoice_no_po(vendor, lines, "MISSING_PO")

    # --- Write outputs ------------------------------------------------------
    def dump(name: str, obj) -> None:
        with open(DATA_DIR / name, "w", encoding="utf-8") as fh:
            json.dump(obj, fh, indent=2)
            fh.write("\n")

    dump("pos.json", [po.model_dump() for po in pos])
    dump("receipts.json", [r.model_dump() for r in receipts])
    dump("invoices.json", [inv.model_dump() for inv in invoices])
    dump("labels.json", labels)


if __name__ == "__main__":
    generate()
