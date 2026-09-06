import type { Invoice } from "@/types/ap";
export type Summary = { total: number; auto_post: number; human_review: number };
export type Review = { invoice_id: string; verdict: "approve" | "hold" | "escalate"; reason: string; reviewer: string; timestamp: string };
export async function getSummary(): Promise<Summary> { const r = await fetch("/api/summary"); if (!r.ok) throw Error("Unable to load summary"); return r.json(); }

export async function getInvoices(): Promise<Invoice[]> {
  const response = await fetch("/api/invoices", { next: { revalidate: 30 } });
  if (!response.ok) throw new Error("Unable to load invoices");
  return response.json();
}
export async function reviewInvoice(id: string, verdict: Review["verdict"], reason: string) { const r = await fetch(`/api/review/${id}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ verdict, reason }) }); if (!r.ok) throw Error("Unable to save review"); return r.json() as Promise<Review>; }
export async function extractInvoice(text: string) { const r = await fetch("/api/extract", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text }) }); if (!r.ok) throw Error("Unable to extract invoice"); return r.json(); }
