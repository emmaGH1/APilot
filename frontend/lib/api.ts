import type { ExtractionResult, Invoice } from "@/types/ap";

export type Summary = { total: number; auto_post: number; human_review: number };

export type Review = {
  invoice_id: string;
  verdict: "approve" | "hold" | "escalate" | string;
  reason?: string;
  reviewer?: string;
  timestamp?: string;
};

/** Optional additive API context (company/policy/extraction capability). */
export type DeskContext = {
  company?: { name?: string } | null;
  policy?: Array<{ id?: string; name?: string; rule?: string }> | null;
  extraction?: { enabled?: boolean; note?: string } | null;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init);
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      /* keep the default message */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export async function getSummary(): Promise<Summary> {
  return request<Summary>("/api/summary");
}

export async function getInvoices(): Promise<Invoice[]> {
  return request<Invoice[]>("/api/invoices");
}

/** Additive context endpoint; returns null when the backend does not provide it. */
export async function getContext(): Promise<DeskContext | null> {
  try {
    return await request<DeskContext>("/api/context");
  } catch {
    return null;
  }
}

export async function reviewInvoice(
  id: string,
  verdict: Review["verdict"],
  reason: string
): Promise<Review> {
  return request<Review>(`/api/review/${encodeURIComponent(id)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ verdict, reason }),
  });
}

export async function extractInvoice(text: string): Promise<ExtractionResult> {
  return request<ExtractionResult>("/api/extract", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
}
