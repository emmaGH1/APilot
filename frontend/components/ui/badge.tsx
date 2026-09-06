import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export type BadgeTone = "leaf" | "brass" | "clay" | "slate" | "neutral";

const toneClasses: Record<BadgeTone, string> = {
  leaf: "border-success/20 bg-success/10 text-success",
  brass: "border-accent/30 bg-accent/10 text-accent",
  clay: "border-danger/25 bg-danger/10 text-danger",
  slate: "border-border bg-muted text-muted-foreground",
  neutral: "border-border bg-card text-foreground",
};

export function Badge({
  className,
  tone = "neutral",
  ...props
}: HTMLAttributes<HTMLSpanElement> & { tone?: BadgeTone }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-semibold",
        toneClasses[tone],
        className
      )}
      {...props}
    />
  );
}
