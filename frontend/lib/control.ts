import type { Invoice, LineItem, Review } from "@/types/ap";

/** Posting buckets used by the queue and the metrics. */
export type Bucket = "unresolved" | "reviewed" | "auto";

export type InvoiceStatus = {
  bucket: Bucket;
  label: string;
  /** Semitone used for badges/chips: leaf | brass | clay | slate */
  tone: "leaf" | "brass" | "clay" | "slate";
  verdict?: string;
};

export const BUCKETS: Array<{ id: Bucket; label: string }> = [
  { id: "unresolved", label: "Unresolved" },
  { id: "reviewed", label: "Reviewed" },
  { id: "auto", label: "Auto-posted" },
];

export const REVIEW_LABELS: Record<string, { label: string; tone: InvoiceStatus["tone"] }> = {
  approve: { label: "Exception approved", tone: "leaf" },
  hold: { label: "Payment held", tone: "brass" },
  escalate: { label: "Escalated", tone: "clay" },
};

/** Demo-company control catalog (additive /api/context may override). */
export type Control = { id: string; name: string; rule: string; findingTypes: string[] };

export const CONTROLS: Control[] = [
  {
    id: "match",
    name: "Three-way match",
    rule: "Quantity, unit price and total must match the purchase order.",
    findingTypes: ["PRICE_MISMATCH", "QTY_MISMATCH", "TAX_MISMATCH"],
  },
  {
    id: "po-vendor",
    name: "PO & approved vendor",
    rule: "Every invoice must reference an open purchase order from an approved vendor.",
    findingTypes: ["MISSING_PO", "UNKNOWN_VENDOR"],
  },
  {
    id: "receipt",
    name: "Goods-receipt evidence",
    rule: "The goods receipt must be on file before payment is scheduled.",
    findingTypes: ["MISSING_RECEIPT"],
  },
  {
    id: "duplicate",
    name: "Duplicate detection",
    rule: "No invoice may bill goods or services that were already paid.",
    findingTypes: ["DUPLICATE_INVOICE"],
  },
];

export const FINDING_LABELS: Record<string, string> = {
  PRICE_MISMATCH: "Unit price differs from the PO",
  QTY_MISMATCH: "Billed quantity differs from the PO",
  TAX_MISMATCH: "Tax-inclusive total differs from the PO",
  MISSING_PO: "No matching purchase order",
  MISSING_RECEIPT: "No goods receipt recorded",
  UNKNOWN_VENDOR: "Vendor is not on the approved list",
  DUPLICATE_INVOICE: "Possible duplicate invoice",
};

export function findingLabel(type: string): string {
  return FINDING_LABELS[type] ?? type.replaceAll("_", " ").toLowerCase().replace(/^./, (c) => c.toUpperCase());
}

export function controlForFinding(type: string): Control | undefined {
  return CONTROLS.find((c) => c.findingTypes.includes(type));
}

export function lastReview(invoice: Invoice): Review | undefined {
  const reviews = invoice.reviews ?? [];
  return reviews.length ? reviews[reviews.length - 1] : undefined;
}

export function statusOf(invoice: Invoice): InvoiceStatus {
  const action = invoice.audit?.action;
  if (action === "AUTO_POST") {
    return { bucket: "auto", label: "Auto-posted", tone: "leaf" };
  }
  const last = lastReview(invoice);
  if (!last) {
    return { bucket: "unresolved", label: "Unresolved · awaiting decision", tone: "brass" };
  }
  const meta = REVIEW_LABELS[last.verdict] ?? { label: `Reviewed · ${last.verdict}`, tone: "slate" as const };
  return { bucket: "reviewed", label: meta.label, tone: meta.tone, verdict: last.verdict };
}

export function bucketCounts(invoices: Invoice[]) {
  return invoices.reduce(
    (acc, inv) => {
      acc[statusOf(inv).bucket] += 1;
      return acc;
    },
    { unresolved: 0, reviewed: 0, auto: 0 } as Record<Bucket, number>
  );
}

/** Open (unresolved) controls -> count of exceptions currently failing them. */
export function openControlCounts(invoices: Invoice[]) {
  const counts = new Map<string, number>(CONTROLS.map((c) => [c.id, 0]));
  for (const inv of invoices) {
    if (statusOf(inv).bucket !== "unresolved") continue;
    for (const finding of inv.audit?.findings ?? []) {
      const control = controlForFinding(finding.type);
      if (control) counts.set(control.id, (counts.get(control.id) ?? 0) + 1);
    }
  }
  return counts;
}

export type EvidenceRow = {
  sku: string;
  invQty: number | null;
  invPrice: number | null;
  poQty: number | null;
  poPrice: number | null;
  recvQty: number | null;
  issue: "price" | "qty" | "missing-po" | "missing-receipt" | null;
};

export type Evidence = {
  rows: EvidenceRow[];
  poTotal: number | null;
  invoiceTotal: number;
  receivedOk: boolean;
  missingReceipt: boolean;
};

export function evidenceOf(invoice: Invoice): Evidence {
  const poLines = invoice.source_docs?.po?.line_items ?? [];
  const received = invoice.source_docs?.receipt?.received ?? {};
  const poBySku = new Map<string, LineItem>();
  for (const line of poLines) poBySku.set(line.sku, line);
  const invBySku = new Map<string, LineItem>();
  for (const line of invoice.line_items) invBySku.set(line.sku, line);

  const skus = Array.from(new Set([...invBySku.keys(), ...poBySku.keys()]));
  const rows: EvidenceRow[] = skus.map((sku) => {
    const inv = invBySku.get(sku);
    const po = poBySku.get(sku);
    const recvQty = sku in received ? (received[sku] as number) : null;
    let issue: EvidenceRow["issue"] = null;
    if (inv && po) {
      if (po.unit_price !== inv.unit_price) issue = "price";
      else if (po.qty !== inv.qty) issue = "qty";
    } else if (inv && !po) {
      issue = "missing-po";
    }
    if (invoice.source_docs?.receipt && inv && recvQty === null && issue === null) issue = "missing-receipt";
    return {
      sku,
      invQty: inv?.qty ?? null,
      invPrice: inv?.unit_price ?? null,
      poQty: po?.qty ?? null,
      poPrice: po?.unit_price ?? null,
      recvQty,
      issue,
    };
  });

  const poTotal =
    invoice.source_docs?.po?.total ??
    (poLines.length ? round2(poLines.reduce((s, l) => s + l.qty * l.unit_price, 0)) : null);

  const invoiceSkus = invoice.line_items;
  const receivedOk = invoiceSkus.every((l) => (received[l.sku] ?? 0) >= l.qty);
  const missingReceipt = !invoice.source_docs?.receipt;

  return {
    rows,
    poTotal,
    invoiceTotal: invoice.total,
    receivedOk,
    missingReceipt,
  };
}

export function severityTone(severity: string): "clay" | "brass" | "slate" {
  if (severity === "high") return "clay";
  if (severity === "medium") return "brass";
  return "slate";
}

export function round2(n: number): number {
  return Math.round(n * 100) / 100;
}

export function formatMoney(value: number | null | undefined, currency = "USD"): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

export function formatTimestamp(value?: string): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function titleCase(value: string): string {
  return value.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase());
}
