import type { Invoice, LineItem, Review } from "@/types/ap";

/** Posting buckets used by the queue and the metrics. */
export type Bucket = "unresolved" | "reviewed" | "auto";

export type InvoiceStatus = {
  bucket: Bucket;
  label: string;
  /** Semitone used for badges/chips: leaf | brass | clay | slate */
  tone: "leaf" | "brass" | "clay" | "slate";
  postingStatus?: string;
};

export const BUCKETS: Array<{ id: Bucket; label: string }> = [
  { id: "unresolved", label: "Unresolved" },
  { id: "reviewed", label: "Reviewed" },
  { id: "auto", label: "Auto-posted" },
];

/** Posting statuses from apilot/policy.py (same spelling as the API). */
export const POSTING_AUTO_POSTED = "AUTO_POSTED";
export const POSTING_BLOCKED = "BLOCKED_FOR_REVIEW";
export const POSTING_OVERRIDE_APPROVED = "OVERRIDE_APPROVED";
export const POSTING_ON_HOLD = "ON_HOLD";
export const POSTING_ESCALATED = "ESCALATED";

const POSTING_STATUS_META: Record<
  string,
  { bucket: Bucket; label: string; tone: InvoiceStatus["tone"] }
> = {
  [POSTING_AUTO_POSTED]: { bucket: "auto", label: "Auto-posted", tone: "leaf" },
  [POSTING_BLOCKED]: { bucket: "unresolved", label: "Blocked for review", tone: "brass" },
  [POSTING_OVERRIDE_APPROVED]: { bucket: "reviewed", label: "Exception approved", tone: "leaf" },
  [POSTING_ON_HOLD]: { bucket: "reviewed", label: "Payment on hold", tone: "brass" },
  [POSTING_ESCALATED]: { bucket: "reviewed", label: "Escalated", tone: "clay" },
};

/** Review verdict -> posting status (apilot.policy.VERDICT_TO_STATUS). */
const VERDICT_TO_POSTING: Record<string, string> = {
  approve: POSTING_OVERRIDE_APPROVED,
  hold: POSTING_ON_HOLD,
  escalate: POSTING_ESCALATED,
};

/**
 * Effective posting state for an invoice. Prefers the API's live
 * `posting_status`; falls back to the audit action + latest review when the
 * field is not supplied by an older backend.
 */
export function statusOf(invoice: Invoice): InvoiceStatus {
  const live = invoice.posting_status;
  if (live && POSTING_STATUS_META[live]) {
    return { ...POSTING_STATUS_META[live], postingStatus: live };
  }

  const action = invoice.audit?.action;
  if (action === "AUTO_POST") {
    return {
      bucket: "auto",
      label: "Auto-posted",
      tone: "leaf",
      postingStatus: POSTING_AUTO_POSTED,
    };
  }
  const last = lastReview(invoice);
  if (!last) {
    return {
      bucket: "unresolved",
      label: "Blocked for review",
      tone: "brass",
      postingStatus: POSTING_BLOCKED,
    };
  }
  const posting = VERDICT_TO_POSTING[last.verdict];
  const fallback = REVIEW_LABELS[last.verdict] ?? {
    label: `Reviewed · ${last.verdict}`,
    tone: "slate" as const,
  };
  return {
    bucket: fallback.bucket,
    label: fallback.label,
    tone: fallback.tone,
    postingStatus: posting,
  };
}

export const REVIEW_LABELS: Record<
  string,
  { bucket: Bucket; label: string; tone: InvoiceStatus["tone"] }
> = {
  approve: { bucket: "reviewed", label: "Exception approved", tone: "leaf" },
  hold: { bucket: "reviewed", label: "Payment on hold", tone: "brass" },
  escalate: { bucket: "reviewed", label: "Escalated", tone: "clay" },
};

export function bucketCounts(invoices: Invoice[]) {
  return invoices.reduce(
    (acc, inv) => {
      acc[statusOf(inv).bucket] += 1;
      return acc;
    },
    { unresolved: 0, reviewed: 0, auto: 0 } as Record<Bucket, number>
  );
}

/**
 * Demo-company control catalog, mirroring apilot/policy.py ROUTES so the UI
 * and the API speak the same rule/owner/action names.
 */
export type Control = {
  id: string;
  rule: string; // policy_rule name (title-cased in the UI)
  findingTypes: string[];
  owner: string; // review_owner
  action: string; // recommended_action
};

export const CLEAN_RULE = "Clean three-way match";
export const CLEAN_ACTION = "Post to ERP";

export const CONTROLS: Control[] = [
  {
    id: "price",
    rule: "Price tolerance",
    findingTypes: ["PRICE_MISMATCH"],
    owner: "AP / Procurement",
    action: "Reconcile unit price with procurement",
  },
  {
    id: "qty",
    rule: "Quantity match",
    findingTypes: ["QTY_MISMATCH"],
    owner: "Receiving",
    action: "Verify received quantity",
  },
  {
    id: "receipt",
    rule: "Receipt check",
    findingTypes: ["MISSING_RECEIPT"],
    owner: "Receiving",
    action: "Confirm goods receipt",
  },
  {
    id: "po",
    rule: "PO check",
    findingTypes: ["MISSING_PO"],
    owner: "Procurement / AP",
    action: "Locate or create the purchase order",
  },
  {
    id: "duplicate",
    rule: "Duplicate check",
    findingTypes: ["DUPLICATE_INVOICE"],
    owner: "AP Manager",
    action: "Review the duplicate invoice pair",
  },
  {
    id: "tax",
    rule: "Tax uplift check",
    findingTypes: ["TAX_MISMATCH"],
    owner: "Tax / Controller",
    action: "Confirm tax handling with Tax/Controller",
  },
  {
    id: "vendor",
    rule: "Vendor & currency check",
    findingTypes: ["UNKNOWN_VENDOR"],
    owner: "Vendor Master / AP Manager",
    action: "Validate vendor master and currency",
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
  return FINDING_LABELS[type] ?? titleCase(type);
}

export function controlForFinding(type: string): Control | undefined {
  return CONTROLS.find((c) => c.findingTypes.includes(type));
}

/** Humanized name of an invoice's failing control (API policy_rule). */
export function controlLabel(invoice: Invoice): string {
  const rule = invoice.policy_rule?.trim();
  if (rule) return titleCase(rule);
  const finding = invoice.audit?.findings?.[0];
  return finding ? (controlForFinding(finding.type)?.rule ?? findingLabel(finding.type)) : CLEAN_RULE;
}

export function recommendedActionOf(invoice: Invoice): string {
  const action = invoice.recommended_action?.trim();
  if (action) return action;
  if (invoice.audit?.suggested_resolution) return invoice.audit.suggested_resolution;
  return CLEAN_ACTION;
}

export function lastReview(invoice: Invoice): Review | undefined {
  const reviews = invoice.reviews ?? [];
  return reviews.length ? reviews[reviews.length - 1] : undefined;
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
