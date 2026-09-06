"use client";

import { Building2, RefreshCw } from "lucide-react";
import { APilotMark } from "@/components/apilot-mark";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export function DeskHeader({
  companyName,
  updatedAt,
  onRefresh,
  refreshing,
}: {
  companyName?: string;
  updatedAt?: Date;
  onRefresh: () => void;
  refreshing: boolean;
}) {
  return (
    <header className="sticky top-0 z-20 border-b border-border bg-card/95 shadow-[0_4px_16px_-14px_hsl(156_20%_20%_/_0.35)]">
      <div className="mx-auto flex w-full max-w-[1440px] flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6">
        <div className="flex items-center gap-3">
          <span className="grid size-9 shrink-0 place-items-center rounded-lg bg-primary text-primary-foreground shadow-[0_2px_6px_-2px_hsl(156_33%_20%_/_0.55)] ring-1 ring-black/5">
            <APilotMark size={20} />
          </span>
          <div className="leading-tight">
            <p className="text-lg font-semibold tracking-tight">
              APilot{" "}
              <span className="ml-1 rounded bg-muted px-1.5 py-0.5 align-middle font-sans text-[10px] font-bold uppercase tracking-[0.18em] text-muted-foreground">
                Control Desk
              </span>
            </p>
            <p className="text-xs text-muted-foreground">Accounts-payable exception control</p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Badge tone="slate" className="gap-1.5 px-3 py-1">
            <Building2 size={13} aria-hidden="true" />
            {companyName ?? "Demo company"}
          </Badge>
          <span className="hidden text-xs text-muted-foreground sm:inline" aria-live="off">
            Updated {updatedAt?.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={onRefresh}
            disabled={refreshing}
            aria-label="Refresh dashboard data"
          >
            <RefreshCw size={14} aria-hidden="true" className={refreshing ? "animate-spin" : undefined} />
            {refreshing ? "Refreshing" : "Refresh"}
          </Button>
        </div>
      </div>
    </header>
  );
}
