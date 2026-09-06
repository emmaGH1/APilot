"use client";

import { useMemo, useState } from "react";
import { Search } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  BUCKETS,
  CONTROLS,
  bucketCounts,
  controlLabel,
  formatMoney,
  findingLabel,
  statusOf,
  type Bucket,
} from "@/lib/control";
import type { Invoice } from "@/types/ap";
import { cn } from "@/lib/utils";

const QUEUE_LIMIT = 40;

export function InvoiceQueue({
  invoices,
  bucket,
  onBucketChange,
  selected,
  onSelect,
}: {
  invoices: Invoice[];
  bucket: Bucket;
  onBucketChange: (bucket: Bucket) => void;
  selected?: string;
  onSelect: (invoice: Invoice) => void;
}) {
  const [query, setQuery] = useState("");
  const [controlFilter, setControlFilter] = useState<string>("all");

  const counts = useMemo(() => bucketCounts(invoices), [invoices]);

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return invoices
      .filter((inv) => statusOf(inv).bucket === bucket)
      .filter((inv) => {
        if (controlFilter !== "all") {
          const types = inv.audit?.findings?.map((f) => f.type) ?? [];
          const control = CONTROLS.find((c) => c.id === controlFilter);
          const hit = control ? types.some((t) => control.findingTypes.includes(t)) : false;
          if (!hit) return false;
        }
        if (!q) return true;
        const haystack = [inv.id, inv.vendor, inv.invoice_number, inv.po_number ?? ""]
          .join(" ")
          .toLowerCase();
        return haystack.includes(q);
      });
  }, [invoices, bucket, query, controlFilter]);

  const shown = visible.slice(0, QUEUE_LIMIT);
  const hiddenCount = visible.length - shown.length;

  return (
    <section className="panel flex min-h-0 flex-col overflow-hidden" aria-label="Review queue">
      <div className="border-b border-border p-4 sm:p-5">
        <div className="flex items-center justify-between gap-3">
          <h2 className="font-serif text-xl tracking-tight sm:text-2xl">Review queue</h2>
          <Badge tone="neutral" className="tabular-nums">
            {counts[bucket]} in view
          </Badge>
        </div>

        <div className="mt-4 flex flex-wrap gap-1 rounded-lg bg-muted/60 p-1" aria-label="Queue scope">
          {BUCKETS.map((b) => (
            <button
              key={b.id}
              type="button"
              aria-pressed={bucket === b.id}
              onClick={() => onBucketChange(b.id)}
              className={cn(
                "flex-1 whitespace-nowrap rounded-md px-2 py-1.5 text-xs font-semibold transition-colors sm:px-3",
                bucket === b.id
                  ? "bg-card text-foreground shadow-sm ring-1 ring-border"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              {b.label}
              <span className={cn("ml-1.5 tabular-nums", bucket === b.id ? "text-accent" : "text-muted-foreground")}>
                {counts[b.id]}
              </span>
            </button>
          ))}
        </div>

        <div className="mt-3 flex flex-col gap-2 sm:flex-row">
          <div className="relative min-w-0 flex-1">
            <Search
              size={16}
              aria-hidden="true"
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
            />
            <label htmlFor="queue-search" className="sr-only">
              Search invoices
            </label>
            <Input
              id="queue-search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="pl-9"
              placeholder="Search vendor, invoice, or PO…"
              autoComplete="off"
            />
          </div>
          <label htmlFor="control-filter" className="sr-only">
            Filter by failed control
          </label>
          <select
            id="control-filter"
            value={controlFilter}
            onChange={(e) => setControlFilter(e.target.value)}
            className="h-10 rounded-md border bg-card px-3 text-sm outline-none"
          >
            <option value="all">All controls</option>
            {CONTROLS.map((c) => (
              <option key={c.id} value={c.id}>
                {c.rule}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {shown.length === 0 ? (
          <div className="grid min-h-48 place-items-center p-6 text-center">
            <div>
              <p className="text-sm font-semibold text-foreground">
                {bucket === "unresolved"
                  ? "Queue cleared — no unresolved exceptions."
                  : bucket === "reviewed"
                    ? "No reviewed invoices yet."
                    : "No auto-posted invoices."}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                {bucket === "unresolved"
                  ? "Every exception now has a recorded decision."
                  : "Try a different filter or search."}
              </p>
            </div>
          </div>
        ) : (
          <ul className="divide-y divide-border">
            {shown.map((inv) => {
              const status = statusOf(inv);
              const finding = inv.audit?.findings?.[0];
              const active = selected === inv.id;
              return (
                <li key={inv.id}>
                  <button
                    type="button"
                    onClick={() => onSelect(inv)}
                    aria-current={active ? "true" : undefined}
                    className={cn(
                      "block w-full px-4 py-3.5 text-left transition-colors hover:bg-muted/40 sm:px-5",
                      active && "border-l-[3px] border-l-primary bg-primary/5 hover:bg-primary/5"
                    )}
                  >
                    <div className="flex items-baseline justify-between gap-3">
                      <span className="truncate text-sm font-semibold">{inv.vendor}</span>
                      <span className="shrink-0 text-sm font-semibold tabular-nums">
                        {formatMoney(inv.total, inv.currency)}
                      </span>
                    </div>
                    <div className="mt-0.5 flex items-center justify-between gap-3 text-xs text-muted-foreground">
                      <span className="truncate">
                        {inv.id} · {inv.invoice_number}
                        {inv.po_number ? ` · PO ${inv.po_number}` : ""}
                      </span>
                      {status.bucket === "auto" ? (
                        <Badge tone="leaf">Auto-posted</Badge>
                      ) : status.bucket === "reviewed" ? (
                        <Badge tone={status.tone}>{status.label}</Badge>
                      ) : (
                        <span className="shrink-0 text-accent">{controlLabel(inv)}</span>
                      )}
                    </div>
                    {status.bucket === "unresolved" && finding && (
                      <p className="mt-1.5 truncate text-xs text-muted-foreground">
                        {findingLabel(finding.type)}
                        {finding.detail ? ` — ${finding.detail}` : ""}
                      </p>
                    )}
                  </button>
                </li>
              );
            })}
          </ul>
        )}
        {hiddenCount > 0 && (
          <p className="border-t border-border px-5 py-3 text-xs text-muted-foreground" role="status">
            {hiddenCount} more match — narrow your search to see them.
          </p>
        )}
      </div>
    </section>
  );
}
