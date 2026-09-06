"use client";

import { ScrollText, ShieldCheck } from "lucide-react";
import { CLEAN_RULE, CONTROLS, openControlCounts } from "@/lib/control";
import type { Invoice } from "@/types/ap";
import { Badge } from "@/components/ui/badge";

export function PolicyPanel({ invoices }: { invoices: Invoice[] }) {
  const openCounts = openControlCounts(invoices);
  return (
    <section className="panel p-5" aria-labelledby="policy-heading">
      <div className="flex items-center justify-between gap-2">
        <h2 id="policy-heading" className="flex items-center gap-2 font-serif text-xl tracking-tight">
          <ShieldCheck size={18} aria-hidden="true" className="text-primary" />
          Control policy
        </h2>
        <Badge tone="slate">Demo company</Badge>
      </div>
      <p className="mt-1.5 text-sm text-muted-foreground">
        A clean three-way match (invoice vs. PO vs. goods receipt) auto-posts. Any failed control
        below routes the invoice to its finance owner with a recommended action — held until a human
        records a decision.
      </p>
      <ul className="mt-4 space-y-2.5">
        {CONTROLS.map((control) => {
          const open = openCounts.get(control.id) ?? 0;
          return (
            <li
              key={control.id}
              className="flex items-start justify-between gap-3 rounded-lg border border-border bg-muted/20 p-3"
            >
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                  <p className="text-sm font-semibold">{control.rule}</p>
                  {open > 0 ? (
                    <Badge tone="brass" className="tabular-nums">
                      {open} open
                    </Badge>
                  ) : (
                    <Badge tone="leaf">passing</Badge>
                  )}
                </div>
                <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                  <span className="font-medium text-foreground">{control.owner}</span> ·{" "}
                  {control.action}
                </p>
              </div>
            </li>
          );
        })}
      </ul>
      <p className="mt-3 border-t border-border pt-3 text-xs text-muted-foreground">
        Clean invoices (no findings) post under “{CLEAN_RULE}” with no human touch.
      </p>
      <p className="mt-2 flex items-start gap-1.5 text-xs text-muted-foreground">
        <ScrollText size={13} aria-hidden="true" className="mt-0.5 shrink-0" />
        Every decision and its reason is written to the audit trail and attached to the invoice.
      </p>
    </section>
  );
}
