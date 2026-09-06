"use client";

import { useState } from "react";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  CircleHelp,
  Inbox,
  Landmark,
  ShieldAlert,
} from "lucide-react";
import { reviewInvoice } from "@/lib/api";
import {
  evidenceOf,
  controlForFinding,
  findingLabel,
  formatMoney,
  formatTimestamp,
  lastReview,
  severityTone,
  statusOf,
  titleCase,
} from "@/lib/control";
import type { Invoice } from "@/types/ap";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

const DECISIONS = [
  {
    verdict: "approve" as const,
    label: "Approve exception",
    hint: "Accept the discrepancy and post the invoice.",
    className: "bg-success text-success-foreground hover:bg-success/90",
  },
  {
    verdict: "hold" as const,
    label: "Hold payment",
    hint: "Keep the invoice open and stop payment.",
    className: "border border-accent/40 bg-card text-accent hover:bg-accent/10",
  },
  {
    verdict: "escalate" as const,
    label: "Escalate",
    hint: "Send to a senior approver for a ruling.",
    className: "border border-danger/40 bg-card text-danger hover:bg-danger/10",
  },
];

export function InvoiceDetail({
  invoice,
  onResolved,
}: {
  invoice?: Invoice;
  onResolved: (message: string) => Promise<void>;
}) {
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  if (!invoice) {
    return (
      <section className="panel grid min-h-96 place-items-center p-8 text-center">
        <div className="max-w-sm">
          <Inbox size={28} aria-hidden="true" className="mx-auto text-muted-foreground" />
          <h2 className="mt-3 font-serif text-xl">No invoice selected</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Pick an invoice from the review queue to see its posting status, the control that failed,
            and the evidence to decide.
          </p>
        </div>
      </section>
    );
  }

  const status = statusOf(invoice);
  const evidence = evidenceOf(invoice);
  const findings = invoice.audit?.findings ?? [];
  const last = lastReview(invoice);
  const owner = invoice.owner?.trim() || "Unassigned";
  const canDecide = status.bucket === "unresolved";

  const decide = async (verdict: (typeof DECISIONS)[number]["verdict"]) => {
    if (!reason.trim()) {
      setError("A reason is required before recording a decision.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await reviewInvoice(invoice.id, verdict, reason.trim());
      await onResolved(
        `INV ${invoice.id} recorded as “${DECISIONS.find((d) => d.verdict === verdict)?.label ?? verdict}”.`
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to save the decision.");
    } finally {
      setBusy(false);
    }
  };

  const variance =
    evidence.poTotal !== null ? invoice.total - evidence.poTotal : null;

  return (
    <article className="panel min-w-0 overflow-hidden" aria-label={`Invoice ${invoice.id} detail`}>
      {/* Header */}
      <div className="border-b border-border p-5 sm:p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone={status.tone} className="px-3 py-1">
                {status.label}
              </Badge>
              {findings.length > 0 && (
                <Badge tone="clay" className="gap-1">
                  <ShieldAlert size={12} aria-hidden="true" /> Control failed
                </Badge>
              )}
            </div>
            <h2 className="mt-3 font-serif text-2xl tracking-tight sm:text-3xl">{invoice.vendor}</h2>
            <p className="mt-1 text-xs text-muted-foreground sm:text-sm">
              {invoice.id} · Invoice {invoice.invoice_number}
              {invoice.po_number ? ` · PO ${invoice.po_number}` : " · No PO referenced"}
            </p>
          </div>
          <p className="font-serif text-2xl tracking-tight sm:text-3xl">
            {formatMoney(invoice.total, invoice.currency)}
          </p>
        </div>

        <dl className="mt-4 grid grid-cols-2 gap-3 border-t border-border pt-4 sm:grid-cols-4">
          <div>
            <dt className="label-overline">Owner</dt>
            <dd className="mt-1 text-sm font-medium">{owner}</dd>
          </div>
          <div>
            <dt className="label-overline">Line items</dt>
            <dd className="mt-1 text-sm font-medium">{invoice.line_items.length}</dd>
          </div>
          <div>
            <dt className="label-overline">Currency</dt>
            <dd className="mt-1 text-sm font-medium">{invoice.currency}</dd>
          </div>
          <div>
            <dt className="label-overline">Recommended action</dt>
            <dd className="mt-1 text-sm font-medium leading-snug">
              {invoice.audit?.suggested_resolution ?? "Human review required"}
            </dd>
          </div>
        </dl>
      </div>

      <div className="space-y-6 p-5 sm:p-6">
        {/* Failed policy / findings */}
        <section aria-labelledby="findings-heading">
          <h3 id="findings-heading" className="label-overline">
            Why this is flagged
          </h3>
          {findings.length === 0 ? (
            <p className="mt-2 flex items-center gap-2 rounded-lg border border-success/20 bg-success/5 px-3 py-2.5 text-sm text-success">
              <CheckCircle2 size={16} aria-hidden="true" />
              No control failures — every check passed.
            </p>
          ) : (
            <ul className="mt-2 space-y-2">
              {findings.map((finding, index) => {
                const control = controlForFinding(finding.type);
                const tone = severityTone(finding.severity);
                return (
                  <li
                    key={index}
                    className="rounded-lg border border-border bg-muted/30 p-3"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="flex items-center gap-2 text-sm font-semibold">
                        <AlertTriangle size={15} aria-hidden="true" className="text-accent" />
                        {findingLabel(finding.type)}
                      </span>
                      <span className="flex items-center gap-1.5">
                        {control && <Badge tone="slate">{control.name}</Badge>}
                        <Badge tone={tone}>{titleCase(String(finding.severity))}</Badge>
                      </span>
                    </div>
                    {finding.detail && (
                      <p className="mt-1.5 text-xs text-muted-foreground sm:text-sm">{finding.detail}</p>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </section>

        {/* Actual vs expected evidence */}
        <section aria-labelledby="evidence-heading">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 id="evidence-heading" className="label-overline">
              Evidence — actual vs expected
            </h3>
            {evidence.poTotal !== null && (
              <p className="text-xs text-muted-foreground">
                PO total {formatMoney(evidence.poTotal, invoice.currency)}
                {variance !== null && variance !== 0 && (
                  <span className={cn("ml-1 font-semibold", variance > 0 ? "text-danger" : "text-success")}>
                    ({variance > 0 ? "+" : ""}
                    {formatMoney(variance, invoice.currency)} vs invoice)
                  </span>
                )}
              </p>
            )}
          </div>

          <div className="mt-2 overflow-x-auto rounded-lg border border-border">
            <table className="w-full min-w-[560px] text-left text-sm">
              <caption className="sr-only">
                Per-line comparison of the invoice against the purchase order and goods receipt.
              </caption>
              <thead>
                <tr className="border-b border-border bg-muted/50 text-xs uppercase tracking-wide text-muted-foreground">
                  <th scope="col" className="px-3 py-2 font-semibold">SKU</th>
                  <th scope="col" className="px-3 py-2 font-semibold">Actual — invoice</th>
                  <th scope="col" className="px-3 py-2 font-semibold">Expected — PO</th>
                  <th scope="col" className="px-3 py-2 font-semibold">Received qty</th>
                  <th scope="col" className="px-3 py-2 font-semibold">
                    <span className="sr-only">Difference</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {evidence.rows.map((row) => {
                  const invCell =
                    row.invQty === null
                      ? null
                      : `${row.invQty} × ${formatMoney(row.invPrice, invoice.currency)}`;
                  const poCell =
                    row.poQty === null
                      ? null
                      : `${row.poQty} × ${formatMoney(row.poPrice, invoice.currency)}`;
                  const diffLabel =
                    row.issue === "price"
                      ? "Price differs from PO"
                      : row.issue === "qty"
                        ? "Qty differs from PO"
                        : row.issue === "missing-po"
                          ? "Not on PO"
                          : row.issue === "missing-receipt"
                            ? "No receipt for this SKU"
                            : null;
                  return (
                    <tr key={row.sku} className="border-b border-border last:border-0">
                      <th scope="row" className="px-3 py-2.5 font-medium">{row.sku}</th>
                      <td
                        className={cn(
                          "px-3 py-2.5 tabular-nums",
                          row.issue === "price" && "bg-danger/5 font-semibold text-danger"
                        )}
                      >
                        {invCell ?? <span className="text-muted-foreground">—</span>}
                      </td>
                      <td
                        className={cn(
                          "px-3 py-2.5 tabular-nums",
                          (row.issue === "qty" || row.issue === "missing-po") &&
                            "bg-accent/10 font-semibold text-accent"
                        )}
                      >
                        {poCell ?? <span className="text-muted-foreground">—</span>}
                      </td>
                      <td
                        className={cn(
                          "px-3 py-2.5 tabular-nums",
                          row.issue === "missing-receipt" && "bg-danger/5 font-semibold text-danger"
                        )}
                      >
                        {row.recvQty === null ? (
                          <span className="text-muted-foreground">—</span>
                        ) : (
                          row.recvQty
                        )}
                      </td>
                      <td className="px-3 py-2.5 text-right">
                        {diffLabel && (
                          <span
                            title={diffLabel}
                            className={cn(
                              "inline-flex items-center gap-1 text-xs font-medium",
                              row.issue === "qty" ? "text-accent" : "text-danger"
                            )}
                          >
                            <CircleHelp size={13} aria-hidden="true" />
                            <span className="sr-only">{diffLabel}</span>
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <p className="mt-2 text-xs text-muted-foreground">
            {evidence.missingReceipt
              ? "No goods receipt has been recorded for this PO yet."
              : evidence.receivedOk
                ? "Received quantities cover every billed line."
                : "Received quantities do not cover every billed line."}
          </p>
        </section>

        {/* Recommended action */}
        {invoice.audit?.suggested_resolution && (
          <section
            aria-labelledby="resolution-heading"
            className="rounded-lg border border-accent/30 bg-accent/5 p-4"
          >
            <h3 id="resolution-heading" className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-[0.14em] text-accent">
              <ArrowRight size={14} aria-hidden="true" />
              Recommended action
            </h3>
            <p className="mt-1.5 text-sm leading-relaxed text-foreground">
              {invoice.audit.suggested_resolution}
            </p>
          </section>
        )}

        {/* Decision */}
        {canDecide ? (
          <section
            aria-labelledby="decision-heading"
            className="rounded-lg border border-border bg-muted/30 p-4"
          >
            <h3 id="decision-heading" className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-[0.14em] text-muted-foreground">
              <Landmark size={14} aria-hidden="true" />
              Decide this exception
            </h3>
            <label htmlFor="decision-reason" className="mt-3 block text-sm font-medium">
              Reason <span className="font-normal text-muted-foreground">(required)</span>
            </label>
            <Textarea
              id="decision-reason"
              value={reason}
              onChange={(e) => {
                setReason(e.target.value);
                if (error) setError("");
              }}
              className="mt-1.5"
              placeholder="Explain the decision — it is written to the audit trail."
              disabled={busy}
            />
            {error && (
              <p role="alert" className="mt-2 text-xs font-medium text-danger">
                {error}
              </p>
            )}
            <div className="mt-3 flex flex-wrap gap-2">
              {DECISIONS.map((d) => (
                <Button
                  key={d.verdict}
                  type="button"
                  disabled={busy || reason.trim().length === 0}
                  onClick={() => void decide(d.verdict)}
                  className={d.className}
                  title={reason.trim() ? d.hint : "Enter a reason to enable this decision"}
                >
                  {d.label}
                </Button>
              ))}
            </div>
            <p className="mt-2 text-xs text-muted-foreground">
              Each decision requires a recorded reason. The invoice leaves the unresolved queue as
              soon as a decision is saved.
            </p>
          </section>
        ) : (
          <section className="rounded-lg border border-border bg-muted/30 p-4">
            <h3 className="label-overline">Review trail</h3>
            {last ? (
              <div className="mt-2 text-sm">
                <p className="font-semibold capitalize">
                  {titleCase(String(last.verdict))}
                  {last.reviewer ? ` by ${last.reviewer}` : ""}
                  {last.timestamp ? (
                    <span className="ml-2 font-normal text-muted-foreground">
                      {formatTimestamp(last.timestamp)}
                    </span>
                  ) : null}
                </p>
                {last.reason && <p className="mt-1 text-muted-foreground">“{last.reason}”</p>}
              </div>
            ) : (
              <p className="mt-1 text-sm text-muted-foreground">No human decision has been recorded.</p>
            )}
          </section>
        )}
      </div>
    </article>
  );
}
