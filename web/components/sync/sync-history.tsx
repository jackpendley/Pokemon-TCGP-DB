"use client";

import { type AdditionItem } from "@/components/sync/reveal-grid";
import { type SetProgressItem } from "@/components/sync/sync-reveal";
import { SyncRevealDialog } from "@/components/sync/sync-reveal-dialog";

export interface HistoryEntryView {
  syncedAt: string;
  addedCount: number;
  items: AdditionItem[];
  /** Per-set progress for this sync — shown inside the popup. */
  setProgress: SetProgressItem[];
}

/**
 * Past syncs, newest first. Each row is a trigger that opens the same popup as the
 * fresh sync (with the Dialog's appear/fade animation): the row shows the date and
 * the added-card count.
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
            triggerClassName="flex w-full items-center justify-between gap-4 rounded-xl border px-4 py-3.5 transition-colors hover:bg-muted/40"
            trigger={
              <>
                <span className="text-base font-semibold tabular-nums sm:text-lg">
                  {new Date(entry.syncedAt).toLocaleString()}
                </span>
                <span className="text-2xl font-bold tabular-nums text-primary">
                  +{entry.addedCount}
                </span>
              </>
            }
          />
        </li>
      ))}
    </ol>
  );
}
