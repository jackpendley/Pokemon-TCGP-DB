"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";

import { RevealGrid, type AdditionItem } from "@/components/sync/reveal-grid";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export interface HistoryEntryView {
  syncedAt: string;
  addedCount: number;
  items: AdditionItem[];
}

/**
 * Past syncs, newest first. Each row expands to reveal that sync's cards with
 * the same animation + clickable enlarged view as the latest-sync reveal.
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
        <HistoryRow key={`${entry.syncedAt}-${i}`} entry={entry} />
      ))}
    </ol>
  );
}

function HistoryRow({ entry }: { entry: HistoryEntryView }) {
  const [open, setOpen] = useState(false);
  return (
    <li className="overflow-hidden rounded-lg border">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-2 px-3 py-2.5 text-left transition-colors hover:bg-muted/50"
      >
        <span className="flex items-center gap-2">
          <ChevronDown
            className={cn(
              "size-4 text-muted-foreground transition-transform",
              open && "rotate-180",
            )}
          />
          <span className="text-sm font-medium">
            {new Date(entry.syncedAt).toLocaleString()}
          </span>
        </span>
        <Badge variant="secondary" className="tabular-nums">
          +{entry.addedCount} {entry.addedCount === 1 ? "card" : "cards"}
        </Badge>
      </button>
      {open ? (
        <div className="border-t px-3 py-3">
          <RevealGrid items={entry.items} />
        </div>
      ) : null}
    </li>
  );
}
