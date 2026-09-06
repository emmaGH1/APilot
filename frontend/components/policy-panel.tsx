"use client";

import { ScrollText, ShieldCheck } from "lucide-react";
import { CONTROLS, openControlCounts } from "@/lib/control";
import type { Invoice } from "@/types/ap";
import { Badge } from "@/components/ui/badge";

export function PolicyPanel({ invoices, companyName }: { invoices: Invoice[]; companyName?: string }) {
  const openCounts = openControlCounts(invoices);
  return (
    <section className="panel p-5" aria-labelledby="policy-heading">
      <div className="flex items-center justify-between gap-2">
        <h2 id="policy-heading" className="flex items-center gap-2 font-serif text-xl tracking-tight">
          <ShieldCheck size={18} aria-hidden="true" className="text-primary" />
          Control policy
        </h2>
        <Badge tone="slate">{companyName ?? "Demo company"}</Badge>
      </div>
      <p className="mt-1.5 text-sm text-muted-foreground">
        APilot posts an invoice only when every control below passes. Any failed control holds the
        invoice for a documented human decision.
      </p>
      <ul className="mt-4 space-y-3">
        {CONTROLS.map((control) => {
          const open = openCounts.get(control.id) ?? 0;
          return (
            <li key={control.id} className="flex items-start justify-between gap-3 rounded-lg border border-border bg-muted/20 p-3">
              <div className="min-w-0">
                <p className="text-sm font-semibold">
                  {control.id.toUpperCase()} · {control.name}
                </p>
                <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">{control.rule}</p>
              </div>
              <Badge tone={open > 0 ? "brass" : "leaf"} className="mt-0.5 shrink-0 tabular-nums">
                {open > 0 ? `${open} open` : "passing"}
              </Badge>
            </li>
          );
        })}
      </ul>
      <p className="mt-3 flex items-start gap-1.5 text-xs text-muted-foreground">
        <ScrollText size={13} aria-hidden="true" className="mt-0.5 shrink-0" />
        Every decision and its reason is written to the audit trail and attached to the invoice.
      </p>
    </section>
  );
}
