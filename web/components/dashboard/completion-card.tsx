"use client";

import { useState } from "react";

import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { formatNumber, formatPercent } from "@/lib/domain/format";

export interface CompletionStat {
  owned: number;
  total: number;
}

type Mode = "total" | "base";

const R = 44;
const CIRC = 2 * Math.PI * R;

/** Radial progress ring with the percentage centred. */
function Ring({ ratio }: { ratio: number }) {
  return (
    <div className="relative size-32 shrink-0">
      <svg viewBox="0 0 100 100" className="size-full -rotate-90">
        <circle
          cx="50"
          cy="50"
          r={R}
          fill="none"
          strokeWidth="9"
          className="stroke-muted"
        />
        <circle
          cx="50"
          cy="50"
          r={R}
          fill="none"
          strokeWidth="9"
          strokeLinecap="round"
          strokeDasharray={CIRC}
          strokeDashoffset={CIRC * (1 - ratio)}
          className="stroke-primary transition-[stroke-dashoffset] duration-700 ease-out"
        />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center text-2xl font-semibold tabular-nums">
        {formatPercent(ratio, 1)}
      </span>
    </div>
  );
}

/**
 * Overall collection completion as a radial ring with a Full / Base toggle.
 * Base = base-rarity cards only.
 */
export function CompletionCard({
  total,
  base,
}: {
  total: CompletionStat;
  base: CompletionStat;
}) {
  const [mode, setMode] = useState<Mode>("total");
  const stat = mode === "base" ? base : total;
  const ratio = stat.total > 0 ? stat.owned / stat.total : 0;

  return (
    <Card className="h-full">
      <CardContent className="flex h-full items-center gap-6 py-2">
        <Ring ratio={ratio} />
        <div className="space-y-3">
          <div>
            <h2 className="font-heading text-base font-medium">
              Collection completion
            </h2>
            <p className="text-sm text-muted-foreground tabular-nums">
              {formatNumber(stat.owned)} / {formatNumber(stat.total)} cards
            </p>
          </div>
          <div className="inline-flex rounded-md border p-0.5">
            {(["total", "base"] as Mode[]).map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => setMode(m)}
                className={cn(
                  "h-7 w-16 rounded text-sm font-medium transition-colors",
                  mode === m
                    ? "bg-secondary text-secondary-foreground"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                {m === "total" ? "Full" : "Base"}
              </button>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
