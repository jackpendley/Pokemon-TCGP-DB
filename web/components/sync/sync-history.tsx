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
  const newCount = entry.items.filter((i) => i.entry.is_new).length;
  return (
    <li
      className={cn(
        "overflow-hidden rounded-xl border transition-colors",
        open ? "bg-muted/30" : "hover:bg-muted/40",
      )}
    >
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-3 px-4 py-3.5 text-left"
      >
        <span className="flex items-center gap-3">
          <ChevronDown
            className={cn(
              "size-5 text-muted-foreground transition-transform duration-300",
              open && "rotate-180",
            )}
          />
          <span>
            <span className="block text-sm font-medium">
              {new Date(entry.syncedAt).toLocaleString()}
            </span>
            {newCount > 0 ? (
              <span className="text-xs text-muted-foreground">
                {newCount} new · {entry.addedCount - newCount} more copies
              </span>
            ) : null}
          </span>
        </span>
        <Badge variant="secondary" className="tabular-nums">
          +{entry.addedCount} {entry.addedCount === 1 ? "card" : "cards"}
        </Badge>
      </button>
      {open ? (
        <div className="animate-in fade-in slide-in-from-top-1 border-t px-4 py-4 duration-300">
          <RevealGrid items={entry.items} />
        </div>
      ) : null}
    </li>
  );
}
