export type InvoiceStatus = "pending" | "approved" | "exception";

export type Invoice = { id: string; vendor: string; amount: number; status: InvoiceStatus; dueDate: string };
