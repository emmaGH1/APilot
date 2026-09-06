import type { Invoice } from "@/types/ap";

export async function getInvoices(): Promise<Invoice[]> {
  const response = await fetch("/api/invoices", { next: { revalidate: 30 } });
  if (!response.ok) throw new Error("Unable to load invoices");
  return response.json();
}
