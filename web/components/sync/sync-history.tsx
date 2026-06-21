import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { SyncHistoryEntry } from "@/types";

const NAME_CAP = 14; // names shown per entry before "+N more"

/**
 * Past sync additions, newest first. Each entry lists the cards added that sync;
 * brand-new cards (0→owned) are highlighted, additional copies are muted.
 */
export function SyncHistory({ entries }: { entries: SyncHistoryEntry[] }) {
  if (entries.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No sync history yet — past additions will accumulate here after each sync.
      </p>
    );
  }

  const ordered = [...entries].reverse();

  return (
    <ol className="space-y-4">
      {ordered.map((entry, i) => {
        const names = entry.added.filter((a) => a.name);
        const shown = names.slice(0, NAME_CAP);
        const extra = names.length - shown.length;
        return (
          <li
            key={`${entry.synced_at}-${i}`}
            className="border-b pb-4 last:border-b-0 last:pb-0"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="text-sm font-medium">
                {new Date(entry.synced_at).toLocaleString()}
              </span>
              <Badge variant="secondary" className="tabular-nums">
                +{entry.added_count} {entry.added_count === 1 ? "card" : "cards"}
              </Badge>
            </div>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {shown.map((a, j) => (
                <span
                  key={`${a.set_code}-${a.card_number}-${j}`}
                  className={cn(
                    "inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-xs",
                    a.is_new
                      ? "bg-primary/10 font-medium text-primary"
                      : "bg-muted text-muted-foreground",
                  )}
                >
                  {a.name}
                  {a.is_new ? (
                    <span className="text-[9px] font-semibold uppercase">new</span>
                  ) : (
                    <span className="tabular-nums">×{a.added}</span>
                  )}
                </span>
              ))}
              {extra > 0 ? (
                <span className="inline-flex items-center px-1.5 py-0.5 text-xs text-muted-foreground">
                  +{extra} more
                </span>
              ) : null}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
