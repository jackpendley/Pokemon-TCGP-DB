"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatNumber, formatPercent } from "@/lib/domain/format";

export interface CompletionStat {
  owned: number;
  total: number;
}

type Mode = "total" | "base";

/**
 * Overall collection completion with a Full-set / Base-set toggle. Mirrors the
 * sets-grid toggle so the two read the same. Base = base-rarity cards only.
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
    <Card>
      <CardHeader className="flex-row items-center justify-between gap-2 pb-2">
        <CardTitle className="text-base">Collection completion</CardTitle>
        <div className="inline-flex rounded-md border p-0.5">
          {(["total", "base"] as Mode[]).map((m) => (
            <Button
              key={m}
              type="button"
              size="sm"
              variant={mode === m ? "secondary" : "ghost"}
              className="h-7"
              onClick={() => setMode(m)}
            >
              {m === "total" ? "Full" : "Base"}
            </Button>
          ))}
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-end justify-between">
          <span className="text-3xl font-semibold tabular-nums">
            {formatPercent(ratio, 1)}
          </span>
          <span className="text-sm text-muted-foreground tabular-nums">
            {formatNumber(stat.owned)} / {formatNumber(stat.total)} cards
          </span>
        </div>
        <div className="h-2.5 overflow-hidden rounded-full bg-muted">
          <div
            className="h-full rounded-full bg-primary transition-all duration-500"
            style={{ width: `${ratio * 100}%` }}
          />
        </div>
      </CardContent>
    </Card>
  );
}
