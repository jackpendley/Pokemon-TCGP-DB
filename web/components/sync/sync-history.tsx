"use client";

import { useEffect, useState } from "react";

import { CardImage } from "@/components/cards/card-image";
import { type AdditionItem } from "@/components/sync/reveal-grid";
import { type SetProgressItem } from "@/components/sync/sync-reveal";
import { SyncRevealDialog } from "@/components/sync/sync-reveal-dialog";
import { SetLogo } from "@/components/sets/set-logo";
import type { CatalogCard } from "@/types";

export interface HistoryEntryView {
  syncedAt: string;
  addedCount: number;
  items: AdditionItem[];
  /** Per-set progress for this sync (also drives the row's rings; top 3 shown). */
  setProgress: SetProgressItem[];
  /** Strongest newly-acquired cards (by power), for the row preview. */
  bestCards: CatalogCard[];
}

/**
 * Past syncs, newest first. Each row is a trigger that opens the same large popup
 * as the fresh sync; the row itself previews the date, best pulls, top set-progress
 * rings, and the added-card count.
 */
export function SyncHistory({ entries }: { entries: HistoryEntryView[] }) {
  if (entries.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No sync history yet — past additions will accumulate here after each sync.
      </p>
    );
  }

  return (
    <ol className="space-y-3">
      {entries.map((entry, i) => (
        <li key={`${entry.syncedAt}-${i}`}>
          <SyncRevealDialog
            title={new Date(entry.syncedAt).toLocaleString()}
            count={entry.addedCount}
            items={entry.items}
            setProgress={entry.setProgress}
            triggerClassName="flex w-full items-center gap-4 rounded-xl border px-4 py-3 transition-colors hover:bg-muted/40"
            trigger={<RowPreview entry={entry} />}
          />
        </li>
      ))}
    </ol>
  );
}

function RowPreview({ entry }: { entry: HistoryEntryView }) {
  return (
    <>
      <span className="text-base font-semibold tabular-nums sm:text-lg">
        {new Date(entry.syncedAt).toLocaleString()}
      </span>

      <div className="hidden flex-1 items-center justify-center gap-4 sm:flex">
        {entry.bestCards.length > 0 ? (
          <div className="flex items-center gap-1.5">
            {entry.bestCards.map((c) => (
              <div
                key={`${c.set_code}-${c.card_number}`}
                className="aspect-[5/7] w-10 shrink-0 overflow-hidden rounded border"
                title={`${c.name}${c.power_score != null ? ` · power ${c.power_score.toFixed(0)}` : ""}`}
              >
                <CardImage card={c} dimUnowned={false} />
              </div>
            ))}
          </div>
        ) : null}
        {entry.setProgress.length > 0 ? (
          <div className="flex items-center gap-3">
            {entry.setProgress.slice(0, 3).map((s) => (
              <SetRing key={s.set_code} s={s} />
            ))}
          </div>
        ) : null}
      </div>

      <span className="ml-auto text-2xl font-bold tabular-nums text-primary sm:ml-0">
        +{entry.addedCount}
      </span>
    </>
  );
}

const R = 44;
const CIRC = 2 * Math.PI * R;

/** Small progress circle for a set, animating from its before→after fill on mount. */
function SetRing({ s }: { s: SetProgressItem }) {
  const after = s.total > 0 ? s.after / s.total : 0;
  const before = s.total > 0 ? Math.max(0, s.before) / s.total : 0;
  const [filled, setFilled] = useState(false);
  useEffect(() => {
    const id = requestAnimationFrame(() => setFilled(true));
    return () => cancelAnimationFrame(id);
  }, []);
  const ratio = filled ? after : before;
  return (
    <span
      className="flex flex-col items-center gap-0.5"
      title={`${s.expansion}: ${s.after}/${s.total} (+${s.gained})`}
    >
      <span className="relative size-9">
        <svg viewBox="0 0 100 100" className="size-full -rotate-90">
          <circle cx="50" cy="50" r={R} fill="none" strokeWidth="12" className="stroke-muted" />
          <circle
            cx="50"
            cy="50"
            r={R}
            fill="none"
            strokeWidth="12"
            strokeLinecap="round"
            strokeDasharray={CIRC}
            strokeDashoffset={CIRC * (1 - ratio)}
            className="stroke-primary transition-[stroke-dashoffset] duration-700 ease-out"
          />
        </svg>
        <span className="absolute inset-0 flex items-center justify-center text-[9px] font-semibold tabular-nums">
          {Math.round(after * 100)}
        </span>
      </span>
      <SetLogo setCode={s.set_code} label={s.expansion} className="h-3 w-8" />
    </span>
  );
}
