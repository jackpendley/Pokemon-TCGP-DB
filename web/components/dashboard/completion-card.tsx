"use client";

import { useEffect, useState } from "react";

import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { formatNumber, formatPercent } from "@/lib/domain/format";

export interface CompletionStat {
  owned: number;
  total: number;
}

/** Unique cards a recent sync added, per scope — used to animate the ring up. */
export interface RecentGain {
  total: number;
  base: number;
}

type Mode = "total" | "base";

const R = 44;
const CIRC = 2 * Math.PI * R;

/** Radial progress ring with the percentage centred. */
function Ring({ ratio }: { ratio: number }) {
  return (
    <div className="relative size-52">
      <svg viewBox="0 0 100 100" className="size-full -rotate-90">
        <circle
          cx="50"
          cy="50"
          r={R}
          fill="none"
          strokeWidth="8"
          className="stroke-muted"
        />
        <circle
          cx="50"
          cy="50"
          r={R}
          fill="none"
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={CIRC}
          strokeDashoffset={CIRC * (1 - ratio)}
          className="stroke-primary transition-[stroke-dashoffset] duration-700 ease-out"
        />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center text-3xl font-semibold tabular-nums">
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
  recentGain,
}: {
  total: CompletionStat;
  base: CompletionStat;
  recentGain?: RecentGain;
}) {
  const [mode, setMode] = useState<Mode>("total");
  const stat = mode === "base" ? base : total;
  const ratio = stat.total > 0 ? stat.owned / stat.total : 0;

  // Animate the ring up from its pre-sync value when a recent sync added cards.
  const gain = recentGain ? (mode === "base" ? recentGain.base : recentGain.total) : 0;
  const fromRatio =
    stat.total > 0 ? Math.max(0, stat.owned - gain) / stat.total : 0;
  const [displayRatio, setDisplayRatio] = useState(gain > 0 ? fromRatio : ratio);
  useEffect(() => {
    const id = requestAnimationFrame(() => setDisplayRatio(ratio));
    return () => cancelAnimationFrame(id);
  }, [ratio]);

  return (
    <Card className="h-full">
      <CardContent className="flex h-full flex-col gap-3 pt-4 pb-5">
        <div className="flex items-center justify-between gap-2">
          <h2 className="font-heading text-base font-medium">
            Collection completion
          </h2>
          <div className="inline-flex shrink-0 rounded-md border p-0.5">
            {(["total", "base"] as Mode[]).map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => setMode(m)}
                className={cn(
                  "h-7 rounded px-3 text-sm font-medium transition-colors",
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
        <div className="flex flex-1 flex-col items-center justify-center gap-3">
          <Ring ratio={displayRatio} />
          <p className="text-sm text-muted-foreground tabular-nums">
            {formatNumber(stat.owned)} / {formatNumber(stat.total)} cards
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
