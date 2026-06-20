import { CardImage } from "@/components/cards/card-image";
import { Badge } from "@/components/ui/badge";
import type { CatalogCard, SyncDeltaEntry } from "@/types";

export interface AdditionItem {
  entry: SyncDeltaEntry;
  card: CatalogCard | null;
}

/** Cards added by the most recent sync, with a NEW badge for brand-new cards. */
export function SyncAdditions({ items }: { items: AdditionItem[] }) {
  if (items.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No cards were added in the last sync.
      </p>
    );
  }

  return (
    <div className="grid grid-cols-3 gap-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8">
      {items.map(({ entry, card }) => (
        <div key={`${entry.set_code}-${entry.card_number}`} className="flex flex-col">
          <div className="relative flex aspect-[5/7] items-center justify-center overflow-hidden rounded-md border bg-muted">
            {card ? (
              <CardImage card={card} />
            ) : (
              <span className="text-sm font-semibold tabular-nums text-muted-foreground/60">
                #{entry.card_number}
              </span>
            )}
            {entry.is_new ? (
              <span className="absolute right-1 top-1 rounded bg-primary px-1 text-[10px] font-semibold text-primary-foreground">
                NEW
              </span>
            ) : null}
            <Badge
              variant="secondary"
              className="absolute bottom-1 left-1 px-1 text-[10px]"
            >
              +{entry.added}
            </Badge>
          </div>
          <div className="mt-1 truncate text-xs font-medium" title={entry.name ?? ""}>
            {entry.name ?? `#${entry.card_number}`}
          </div>
          <span className="text-[10px] text-muted-foreground tabular-nums">
            {entry.set_code}
          </span>
        </div>
      ))}
    </div>
  );
}
