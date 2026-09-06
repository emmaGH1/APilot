"use client";

import {
  CheckCircle2,
  FileCheck2,
  FileClock,
  Files,
  type LucideIcon,
} from "lucide-react";
import type { Bucket } from "@/lib/control";
import { cn } from "@/lib/utils";

export type Metrics = {
  processed: number;
  autoPosted: number;
  unresolved: number;
  reviewed: number;
};

export function SummaryCards({
  metrics,
  onSelectBucket,
  activeBucket,
}: {
  metrics: Metrics;
  onSelectBucket: (bucket: Bucket) => void;
  activeBucket: Bucket;
}) {
  const cards: Array<{
    id?: Bucket;
    label: string;
    value: number;
    hint: string;
    Icon: LucideIcon;
    accent: string;
    iconWrap: string;
  }> = [
    {
      label: "Processed",
      value: metrics.processed,
      hint: "invoices in this cycle",
      Icon: Files,
      accent: "text-foreground",
      iconWrap: "bg-muted text-muted-foreground",
    },
    {
      id: "auto",
      label: "Auto-posted",
      value: metrics.autoPosted,
      hint: "clean, no human touch",
      Icon: CheckCircle2,
      accent: "text-success",
      iconWrap: "bg-success/10 text-success",
    },
    {
      id: "unresolved",
      label: "Unresolved",
      value: metrics.unresolved,
      hint: "awaiting your decision",
      Icon: FileClock,
      accent: "text-accent",
      iconWrap: "bg-accent/10 text-accent",
    },
    {
      id: "reviewed",
      label: "Reviewed",
      value: metrics.reviewed,
      hint: "exceptions with a decision",
      Icon: FileCheck2,
      accent: "text-primary",
      iconWrap: "bg-primary/10 text-primary",
    },
  ];

  return (
    <section aria-label="Cycle metrics" className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {cards.map((card) => {
        const interactive = Boolean(card.id);
        const inner = (
          <>
            <div className="flex items-start justify-between gap-2">
              <span
                className={cn(
                  "label-overline",
                  interactive && card.id === activeBucket && "text-foreground"
                )}
              >
                {card.label}
              </span>
              <span
                className={cn(
                  "grid size-7 shrink-0 place-items-center rounded-md",
                  card.iconWrap
                )}
              >
                <card.Icon size={15} aria-hidden="true" />
              </span>
            </div>
            <p
              className={cn(
                "mt-3 font-serif text-3xl tabular-nums tracking-tight sm:text-4xl",
                card.accent
              )}
            >
              {card.value}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">{card.hint}</p>
          </>
        );

        const className = cn(
          "panel p-4 text-left sm:p-5",
          interactive && "transition-colors hover:border-accent/50 hover:bg-card",
          interactive && card.id === activeBucket && "border-accent/60 ring-1 ring-accent/30"
        );

        return interactive && card.id ? (
          <button
            key={card.label}
            type="button"
            className={className}
            onClick={() => onSelectBucket(card.id!)}
            aria-pressed={activeBucket === card.id}
            aria-label={`${card.label}: ${card.value}. Show ${card.label.toLowerCase()} invoices.`}
          >
            {inner}
          </button>
        ) : (
          <div key={card.label} className={className}>
            {inner}
          </div>
        );
      })}
    </section>
  );
}
