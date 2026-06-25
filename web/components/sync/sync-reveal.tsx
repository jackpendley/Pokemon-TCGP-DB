"use client";

import { useEffect, useState } from "react";

import { RevealGrid, type AdditionItem } from "@/components/sync/reveal-grid";
import { formatPercent } from "@/lib/domain/format";

export type { AdditionItem } from "@/components/sync/reveal-grid";

export interface SetProgressItem {
  set_code: string;
  expansion: string;
  total: number;
  before: number;
  after: number;
  gained: number;
}

const STAGGER_MS = 90;
const PHASE_GAP_MS = 350;

export function SyncReveal({
  items,
  setProgress,
}: {
  items: AdditionItem[];
  setProgress: SetProgressItem[];
}) {
  // Bars fill after the cards have revealed.
  const barsStartMs = items.length * STAGGER_MS + 2 * PHASE_GAP_MS;
  const [barsFilled, setBarsFilled] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setBarsFilled(true), barsStartMs);
    return () => clearTimeout(t);
  }, [barsStartMs]);

  return (
    <div className="space-y-6">
      <RevealGrid items={items} />

      {setProgress.length > 0 ? (
        <section className="space-y-3">
          <h3 className="text-sm font-medium">Set progress</h3>
          <div className="space-y-3">
            {setProgress.map((s) => {
              const beforePct = s.total > 0 ? s.before / s.total : 0;
              const afterPct = s.total > 0 ? s.after / s.total : 0;
              return (
                <div key={s.set_code} className="space-y-1">
                  <div className="flex justify-between text-sm">
                    <span>
                      {s.expansion}{" "}
                      <span className="text-muted-foreground">{s.set_code}</span>
                    </span>
                    <span className="tabular-nums text-muted-foreground">
                      {s.before} → <span className="text-foreground">{s.after}</span>/
                      {s.total}{" "}
                      <span className="text-primary">(+{s.gained})</span>
                    </span>
                  </div>
                  <div className="relative h-2 overflow-hidden rounded-full bg-muted">
                    <div
                      className="absolute inset-y-0 left-0 rounded-full bg-primary/40"
                      style={{ width: `${beforePct * 100}%` }}
                    />
                    <div
                      className="absolute inset-y-0 left-0 rounded-full bg-primary transition-[width] duration-1000 ease-out"
                      style={{
                        width: `${(barsFilled ? afterPct : beforePct) * 100}%`,
                      }}
                    />
                  </div>
                  <div className="text-right text-[10px] text-muted-foreground tabular-nums">
                    {formatPercent(afterPct)}
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      ) : null}
    </div>
  );
}
