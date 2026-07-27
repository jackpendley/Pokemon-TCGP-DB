"use client";

import { useEffect, useRef, useState } from "react";

import { RevealGrid, type AdditionItem } from "@/components/sync/reveal-grid";
import { CountUp } from "@/components/ui/count-up";
import { usePrefersReducedMotion } from "@/lib/hooks/use-reduced-motion";
import { BARS_FILL_MS, barsStartMs } from "@/lib/domain/reveal-timing";

export type { AdditionItem } from "@/components/sync/reveal-grid";

export interface SetProgressItem {
  set_code: string;
  expansion: string;
  total: number;
  before: number;
  after: number;
  gained: number;
}

export function SyncReveal({
  items,
  setProgress,
}: {
  items: AdditionItem[];
  setProgress: SetProgressItem[];
}) {
  // Bars fill after the cards have revealed.
  const barsAt = barsStartMs(items.length);
  const [barsFilled, setBarsFilled] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setBarsFilled(true), barsAt);
    return () => clearTimeout(t);
  }, [barsAt]);

  const rootRef = useRef<HTMLDivElement>(null);
  const barsRef = useRef<HTMLElement>(null);
  const reduced = usePrefersReducedMotion();

  /**
   * Tail of the auto-scroll the grid starts: bring the set-progress bars into
   * view for their fill, then return to the top so the popup is left where the
   * user can read it from the beginning.
   */
  useEffect(() => {
    if (reduced || setProgress.length === 0) return;
    const toBars = setTimeout(() => {
      barsRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }, barsAt);
    const toTop = setTimeout(() => {
      rootRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, barsAt + BARS_FILL_MS + 600);
    return () => {
      clearTimeout(toBars);
      clearTimeout(toTop);
    };
  }, [barsAt, reduced, setProgress.length]);

  return (
    <div ref={rootRef} className="space-y-6">
      <RevealGrid items={items} />

      {setProgress.length > 0 ? (
        <section ref={barsRef} className="space-y-3">
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
                    <CountUp
                      value={(barsFilled ? afterPct : beforePct) * 100}
                      format={(n) => `${Math.round(n)}%`}
                    />
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
