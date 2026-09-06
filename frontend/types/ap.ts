export type FindingSeverity = "high" | "medium" | "low" | string;

export type Finding = {
  type: string;
  detail?: string;
  severity: FindingSeverity;
};

export type LineItem = {
  sku: string;
  description?: string;
  qty: number;
  unit_price: number;
};

export type SourceDocument = {
  po?: {
    po_number?: string;
    vendor?: string;
    line_items?: LineItem[];
    total?: number;
  } | null;
  receipt?: {
    po_number?: string;
    received?: Record<string, number>;
  } | null;
};

export type Review = {
  invoice_id: string;
  verdict: "approve" | "hold" | "escalate" | string;
  reason?: string;
  reviewer?: string;
  timestamp?: string;
};

export type Audit = {
  action: "AUTO_POST" | "HUMAN_REVIEW" | string;
  confidence?: number;
  findings?: Finding[];
  suggested_resolution?: string;
  policy_rule?: string;
  review_owner?: string;
  recommended_action?: string;
  posting_status?: string;
};

export type Invoice = {
  id: string;
  vendor: string;
  invoice_number: string;
  po_number: string | null;
  currency: string;
  line_items: LineItem[];
  total: number;
  audit?: Audit | null;
  source_docs: SourceDocument;
  reviews: Review[];
  // Policy-aware additive fields from the API (apilot/policy.py). The frontend
  // falls back to the audit/action/reviews when they are absent.
  policy_rule?: string | null;
  review_owner?: string | null;
  recommended_action?: string | null;
  posting_status?: string | null;
};

export type ExtractionResult = {
  invoice?: Partial<Invoice> | null;
  findings?: Finding[];
  action?: string;
  confidence?: number;
  policy_rule?: string;
  review_owner?: string;
  recommended_action?: string;
  posting_status?: string;
  suggested_resolution?: string;
  po?: SourceDocument["po"];
  receipt?: SourceDocument["receipt"];
};
