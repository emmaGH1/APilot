"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { FileSearch, RadioTower, ShieldCheck, Workflow } from "lucide-react";
import { getContext, getInvoices, type DeskContext } from "@/lib/api";
import { statusOf, type Bucket } from "@/lib/control";
import type { Invoice } from "@/types/ap";
import { DeskHeader } from "@/components/desk-header";
import { SummaryCards, type Metrics } from "@/components/summary-cards";
import { InvoiceQueue } from "@/components/invoice-queue";
import { InvoiceDetail } from "@/components/invoice-detail";
import { PolicyPanel } from "@/components/policy-panel";
import { ExtractionCard } from "@/components/extraction-card";

const PROPOSITIONS = [
  {
    Icon: Workflow,
    title: "Auto-post clean invoices",
    text: "Invoices that match PO and receipt evidence post themselves.",
  },
  {
    Icon: FileSearch,
    title: "Three-way-match controls",
    text: "Price, quantity and receipt checks run before anything posts.",
  },
  {
    Icon: RadioTower,
    title: "Exceptions, framed",
    text: "Each hold arrives with the failed control, the evidence and a recommendation.",
  },
];

export default function Home() {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [bucket, setBucket] = useState<Bucket>("unresolved");
  const [selectedId, setSelectedId] = useState<string | undefined>();
  const [context, setContext] = useState<DeskContext | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [updatedAt, setUpdatedAt] = useState<Date | undefined>();
  const noticeTimer = useRef<number | undefined>(undefined);

  const load = useCallback(async (viaRefresh = false) => {
    if (viaRefresh) setRefreshing(true);
    else setLoading(true);
    setError("");
    try {
      const [data, ctx] = await Promise.all([getInvoices(), getContext()]);
      setInvoices(data);
      setContext(ctx);
      setUpdatedAt(new Date());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to load the control desk.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const showNotice = useCallback((message: string) => {
    setNotice(message);
    window.clearTimeout(noticeTimer.current);
    noticeTimer.current = window.setTimeout(() => setNotice(""), 6000);
  }, []);

  useEffect(() => () => window.clearTimeout(noticeTimer.current), []);

  const selected = useMemo(
    () => invoices.find((inv) => inv.id === selectedId),
    [invoices, selectedId]
  );

  // Keep the selection valid for the active bucket (a resolved item leaves the
  // unresolved queue, so advance to the next unresolved invoice).
  useEffect(() => {
    if (loading || invoices.length === 0) return;
    const inBucket = invoices.filter((inv) => statusOf(inv).bucket === bucket);
    const stillValid =
      selectedId !== undefined && invoices.some((inv) => inv.id === selectedId);
    const inBucketValid = selectedId !== undefined && inBucket.some((inv) => inv.id === selectedId);
    if (!stillValid || !inBucketValid) {
      setSelectedId(inBucket[0]?.id ?? undefined);
    }
  }, [invoices, bucket, selectedId, loading]);

  const counts = useMemo(() => {
    const acc = { auto: 0, unresolved: 0, reviewed: 0 };
    for (const inv of invoices) acc[statusOf(inv).bucket] += 1;
    return acc;
  }, [invoices]);

  const metrics: Metrics = useMemo(
    () => ({
      processed: invoices.length,
      autoPosted: counts.auto,
      unresolved: counts.unresolved,
      reviewed: counts.reviewed,
    }),
    [invoices, counts]
  );

  const companyName = context?.company?.name;
  const extractionCapability = useMemo(() => {
    const extraction = context?.extraction;
    return {
      available: extraction ? (extraction.enabled ?? false) : true,
      note: extraction?.note,
    };
  }, [context]);

  const handleBucket = (next: Bucket) => {
    setBucket(next);
    const first = invoices.find((inv) => statusOf(inv).bucket === next);
    setSelectedId(first?.id ?? undefined);
  };

  const handleResolved = async (message: string) => {
    showNotice(message);
    await load(true);
  };

  return (
    <main className="min-h-screen">
      <DeskHeader
        companyName={companyName}
        updatedAt={updatedAt}
        refreshing={refreshing}
        onRefresh={() => void load(true)}
      />

      {notice && (
        <div className="mx-auto w-full max-w-[1440px] px-4 pt-4 sm:px-6">
          <div
            role="status"
            className="flex items-center justify-between gap-3 rounded-lg border border-success/30 bg-success/5 px-4 py-2.5 text-sm text-success"
          >
            <span>{notice}</span>
            <button
              type="button"
              onClick={() => setNotice("")}
              aria-label="Dismiss"
              className="rounded p-0.5 text-success hover:bg-success/10"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      <div className="mx-auto w-full max-w-[1440px] space-y-6 px-4 py-6 sm:px-6 lg:py-8">
        {/* Value proposition */}
        <section aria-labelledby="desk-title" className="max-w-3xl">
          <p className="label-overline text-accent">APilot · Control Desk</p>
          <h1
            id="desk-title"
            className="mt-2 font-serif text-3xl leading-tight tracking-tight sm:text-4xl"
          >
            Every invoice controlled. Only genuine exceptions reach your team.
          </h1>
          <p className="mt-3 text-sm leading-relaxed text-muted-foreground sm:text-base">
            APilot checks each invoice against purchase-order and goods-receipt evidence, posts the
            clean ones automatically, and hands your team only the exceptions — each one with the
            failed policy, the evidence, and a recommended action.
          </p>
          <ul className="mt-4 grid gap-3 sm:grid-cols-3">
            {PROPOSITIONS.map(({ Icon, title, text }) => (
              <li key={title} className="flex items-start gap-2.5">
                <span className="grid size-8 shrink-0 place-items-center rounded-md bg-primary/10 text-primary">
                  <Icon size={16} aria-hidden="true" />
                </span>
                <div>
                  <p className="text-sm font-semibold leading-tight">{title}</p>
                  <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">{text}</p>
                </div>
              </li>
            ))}
          </ul>
        </section>

        {error && invoices.length === 0 ? (
          <section
            role="alert"
            className="panel grid place-items-center gap-3 p-10 text-center"
          >
            <div className="max-w-md">
              <p className="text-lg font-semibold">Could not load the control desk</p>
              <p className="mt-1 text-sm text-muted-foreground">
                {error}. Make sure the APilot API is running at the configured origin, then retry.
              </p>
              <button
                type="button"
                onClick={() => void load()}
                className="mt-4 rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground"
              >
                Retry
              </button>
            </div>
          </section>
        ) : (
          <>
            <SummaryCards metrics={metrics} activeBucket={bucket} onSelectBucket={handleBucket} />

            {loading && invoices.length === 0 ? (
              <div className="grid place-items-center py-24 text-sm text-muted-foreground">
                Loading invoices…
              </div>
            ) : (
              <div className="grid items-start gap-6 xl:grid-cols-[minmax(340px,5fr)_minmax(0,7fr)]">
                <InvoiceQueue
                  invoices={invoices}
                  bucket={bucket}
                  onBucketChange={handleBucket}
                  selected={selectedId}
                  onSelect={(inv) => setSelectedId(inv.id)}
                />
                <InvoiceDetail invoice={selected} onResolved={handleResolved} />
              </div>
            )}

            {!loading && (
              <div className="grid items-start gap-6 lg:grid-cols-2">
                <PolicyPanel invoices={invoices} companyName={companyName} />
                <ExtractionCard capability={extractionCapability} />
              </div>
            )}
          </>
        )}

        <footer className="flex items-center justify-between gap-2 border-t border-border pt-4 text-xs text-muted-foreground">
          <p>APilot — deterministic demo data. Invoices, vendors and evidence are fictitious.</p>
          <p className="flex items-center gap-1.5">
            <ShieldCheck size={13} aria-hidden="true" className="text-success" />
            Decisions require a recorded reason
          </p>
        </footer>
      </div>
    </main>
  );
}
