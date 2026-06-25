"use client";

import { useState } from "react";

import { CardDialog } from "@/components/cards/card-dialog";
import { CardImage } from "@/components/cards/card-image";
import { cn } from "@/lib/utils";
import type { CatalogCard, SyncDeltaEntry } from "@/types";

export interface AdditionItem {
  entry: SyncDeltaEntry;
  card: CatalogCard | null;
}

const STAGGER_MS = 90;
const PHASE_GAP_MS = 350;

/**
 * Staggered reveal of the cards a sync added — new cards first, then extra
 * copies. Tiles are clickable (open the same enlarged card view as the Cards
 * page) and lift on hover. Shared by the latest-sync reveal and each expanded
 * history entry, so both animate identically on mount.
 */
export function RevealGrid({ items }: { items: AdditionItem[] }) {
  const [selected, setSelected] = useState<CatalogCard | null>(null);

  if (items.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No cards were added in this sync.
      </p>
    );
  }

  const newItems = items.filter((i) => i.entry.is_new);
  const ownedItems = items.filter((i) => !i.entry.is_new);
  const ownedStartMs = newItems.length * STAGGER_MS + PHASE_GAP_MS;

  return (
    <>
      <div className="space-y-4">
        {newItems.length > 0 ? (
          <section className="space-y-2">
            <h4 className="text-xs font-medium">New to your collection</h4>
            <Grid>
              {newItems.map((item, i) => (
                <RevealTile
                  key={`${item.entry.set_code}-${item.entry.card_number}`}
                  item={item}
                  delayMs={i * STAGGER_MS}
                  isNew
                  onSelect={setSelected}
                />
              ))}
            </Grid>
          </section>
        ) : null}

        {ownedItems.length > 0 ? (
          <section className="space-y-2">
            <h4 className="text-xs font-medium text-muted-foreground">
              More copies of cards you owned
            </h4>
            <Grid>
              {ownedItems.map((item, i) => (
                <RevealTile
                  key={`${item.entry.set_code}-${item.entry.card_number}`}
                  item={item}
                  delayMs={ownedStartMs + i * STAGGER_MS}
                  onSelect={setSelected}
                />
              ))}
            </Grid>
          </section>
        ) : null}
      </div>

      <CardDialog card={selected} onClose={() => setSelected(null)} />
    </>
  );
}

function Grid({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-3 gap-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8">
      {children}
    </div>
  );
}

function RevealTile({
  item,
  delayMs,
  isNew = false,
  onSelect,
}: {
  item: AdditionItem;
  delayMs: number;
  isNew?: boolean;
  onSelect: (card: CatalogCard) => void;
}) {
  const { entry, card } = item;
  return (
    <button
      type="button"
      onClick={() => card && onSelect(card)}
      disabled={!card}
      className={cn(
        "animate-card-reveal flex flex-col text-left",
        card && "transition-transform hover:scale-[1.03]",
      )}
      style={{ animationDelay: `${delayMs}ms` }}
    >
      {/* NEW badge sits ABOVE the art so it never covers it. */}
      {isNew ? (
        <span className="mx-auto mb-1 rounded-full bg-primary px-2 py-0.5 text-[10px] font-bold tracking-wide text-primary-foreground">
          NEW
        </span>
      ) : null}
      <div className="relative flex aspect-[5/7] items-center justify-center overflow-hidden rounded-md border bg-muted">
        {card ? (
          <CardImage card={card} />
        ) : (
          <span className="text-sm font-semibold tabular-nums text-muted-foreground/60">
            #{entry.card_number}
          </span>
        )}
      </div>
      <div className="mt-1 truncate text-xs font-medium" title={entry.name ?? ""}>
        {entry.name ?? `#${entry.card_number}`}
      </div>
      <span className="text-[10px] text-muted-foreground tabular-nums">
        {isNew
          ? entry.set_code
          : `${entry.previous_count} → ${entry.new_count} (+${entry.added})`}
      </span>
    </button>
  );
}
