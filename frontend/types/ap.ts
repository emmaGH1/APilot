export type InvoiceStatus = "pending" | "approved" | "exception";
export type Finding = { type: string; detail: string; severity: "high" | "medium" | "low" | string };
export type LineItem = { sku: string; description?: string; qty: number; unit_price: number };
export type SourceDocument = { po?: { po_number?: string; vendor?: string; line_items?: LineItem[] } | null; receipt?: { po_number?: string; received?: Record<string, number> } | null };
export type Review = { invoice_id: string; verdict: "approve" | "hold" | "escalate"; reason: string; reviewer: string; timestamp: string };
export type Audit = { action: "AUTO_POST" | "HUMAN_REVIEW" | string; confidence: number; findings: Finding[]; suggested_resolution: string };
export type Invoice = { id: string; vendor: string; invoice_number: string; po_number: string | null; currency: string; line_items: LineItem[]; total: number; audit?: Audit | null; source_docs: SourceDocument; reviews: Review[] };
