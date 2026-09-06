"use client";

import { useState } from "react";
import { CheckCircle2, LoaderCircle, ScanText, Sparkles } from "lucide-react";
import { extractInvoice } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { severityTone, titleCase } from "@/lib/control";
import type { ExtractionResult, Finding } from "@/types/ap";

export type ExtractionCapability = {
  available: boolean;
  note?: string;
};

export function ExtractionCard({ capability }: { capability: ExtractionCapability }) {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<ExtractionResult | null>(null);
  const [error, setError] = useState("");
  const [disabled, setDisabled] = useState<ExtractionCapability>(capability);

  const run = async () => {
    setBusy(true);
    setError("");
    setResult(null);
    try {
      setResult(await extractInvoice(text));
    } catch (e) {
      const message = e instanceof Error ? e.message : "Unable to extract the invoice.";
      setError(message);
      // Capability-driven disable: a backend without the LLM key cannot extract.
      if (/APILOT_LLM_KEY is not set/i.test(message)) {
        setDisabled({
          available: false,
          note: "The API server has no LLM API key configured, so extraction is unavailable.",
        });
      }
    } finally {
      setBusy(false);
    }
  };

  const unavailable = !disabled.available;
  const findings: Finding[] = result?.findings ?? [];
  const extractedTotal =
    result?.invoice?.total ??
    (result?.invoice?.line_items ?? []).reduce(
      (sum, line) => sum + line.qty * line.unit_price,
      0
    );

  return (
    <section className="panel flex min-w-0 flex-col p-5" aria-labelledby="extract-heading">
      <div className="flex items-center gap-2">
        <Sparkles size={17} aria-hidden="true" className="text-accent" />
        <h2 id="extract-heading" className="font-serif text-xl tracking-tight">
          Try invoice extraction
        </h2>
      </div>
      <p className="mt-1.5 text-sm text-muted-foreground">
        Paste raw invoice text and let APilot extract it, match it to evidence, and decide whether it
        would auto-post. Extractions are dry runs and never enter the queue.
      </p>

      {unavailable ? (
        <div
          role="status"
          className="mt-4 flex items-start gap-2 rounded-lg border border-accent/30 bg-accent/5 p-3 text-sm text-foreground"
        >
          <ScanText size={16} aria-hidden="true" className="mt-0.5 shrink-0 text-accent" />
          <span>
            <strong className="block text-xs font-bold uppercase tracking-[0.12em] text-accent">
              Extraction unavailable
            </strong>
            {disabled.note ??
              "This capability has not been enabled for the current environment."}
          </span>
        </div>
      ) : (
        <>
          <label htmlFor="extract-text" className="sr-only">
            Raw invoice text
          </label>
          <Textarea
            id="extract-text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            className="mt-4 min-h-28 font-mono text-xs"
            placeholder={"Meridian Supplies\nInvoice 204-991 · PO-0451\nSKU-2017  12 x $84.50"}
            disabled={busy}
          />
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <Button onClick={() => void run()} disabled={busy || text.trim().length === 0} aria-busy={busy}>
              {busy ? (
                <>
                  <LoaderCircle size={15} aria-hidden="true" className="animate-spin" />
                  Extracting…
                </>
              ) : (
                "Extract & decide"
              )}
            </Button>
            {result && (
              <Button variant="ghost" size="sm" onClick={() => setResult(null)} disabled={busy}>
                New extraction
              </Button>
            )}
          </div>
        </>
      )}

      {error && (
        <p role="alert" className="mt-3 rounded-lg border border-danger/25 bg-danger/5 p-3 text-sm text-danger">
          {error}
        </p>
      )}

      {result && (
        <div className="mt-4 rounded-lg border border-border bg-muted/20 p-4" aria-live="polite">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="label-overline">Extraction decision</p>
            <Badge tone={result.action === "AUTO_POST" ? "leaf" : "brass"} className="px-3 py-1">
              {result.action === "AUTO_POST" ? "Auto-post recommended" : "Human review required"}
            </Badge>
          </div>

          {result.invoice && (
            <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-sm sm:grid-cols-3">
              {(
                [
                  ["Vendor", result.invoice.vendor],
                  ["Invoice", result.invoice.invoice_number],
                  ["PO", result.invoice.po_number || "—"],
                  ["ID", result.invoice.id],
                  ["Lines", String(result.invoice.line_items?.length ?? 0)],
                ] as const
              ).map(([label, value]) => (
                <div key={label}>
                  <dt className="text-[11px] uppercase tracking-wide text-muted-foreground">{label}</dt>
                  <dd className="truncate font-medium">{value}</dd>
                </div>
              ))}
              <div>
                <dt className="text-[11px] uppercase tracking-wide text-muted-foreground">Total</dt>
                <dd className="truncate font-medium tabular-nums">
                  {extractedTotal ? `$${extractedTotal.toFixed(2)}` : "—"}
                </dd>
              </div>
            </dl>
          )}

          {typeof result.confidence === "number" && (
            <p className="mt-2 text-xs text-muted-foreground">
              Confidence {Math.round(result.confidence * 100)}%
            </p>
          )}

          {findings.length === 0 ? (
            <p className="mt-3 flex items-center gap-1.5 text-sm text-success">
              <CheckCircle2 size={15} aria-hidden="true" />
              Matches PO and receipt evidence — no findings.
            </p>
          ) : (
            <ul className="mt-3 space-y-1.5">
              {findings.map((finding, index) => (
                <li key={index} className="flex items-start gap-2 text-sm">
                  <Badge tone={severityTone(finding.severity)} className="mt-0.5 shrink-0">
                    {titleCase(String(finding.severity))}
                  </Badge>
                  <span>
                    <span className="font-semibold">{titleCase(finding.type)}</span>
                    {finding.detail ? <span className="text-muted-foreground"> — {finding.detail}</span> : null}
                  </span>
                </li>
              ))}
            </ul>
          )}

          {result.suggested_resolution && (
            <p className="mt-3 border-t border-border pt-2.5 text-sm">
              <span className="font-semibold text-accent">Recommended:</span> {result.suggested_resolution}
            </p>
          )}
        </div>
      )}
    </section>
  );
}
