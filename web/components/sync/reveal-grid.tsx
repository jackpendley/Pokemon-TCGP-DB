"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { CardDialog } from "@/components/cards/card-dialog";
import { CardImage } from "@/components/cards/card-image";
import { usePrefersReducedMotion } from "@/lib/hooks/use-reduced-motion";
import { compareRevealRarity } from "@/lib/domain/rarity";
import { ownedStartMs, staggerMs } from "@/lib/domain/reveal-timing";
import { cn } from "@/lib/utils";
import type { CatalogCard, SyncDeltaEntry } from "@/types";

export interface AdditionItem {
  entry: SyncDeltaEntry;
  card: CatalogCard | null;
}

/**
 * Staggered reveal of the cards a sync added — new cards first, then extra
 * copies. Tiles are clickable (open the same enlarged card view as the Cards
 * page) and lift on hover. Shared by the latest-sync reveal and each expanded
 * history entry, so both animate identically on mount.
 */
export function RevealGrid({ items }: { items: AdditionItem[] }) {
  const [selected, setSelected] = useState<CatalogCard | null>(null);
  const followRevealed = useFollowReveal(items.length);

  if (items.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No cards were added in this sync.
      </p>
    );
  }

  // Rarest first, with promos and unrecognised rarities trailing — see
  // compareRevealRarity for why RARITY_ORDER can't be sorted directly.
  const byRarityDesc = (a: AdditionItem, b: AdditionItem) =>
    compareRevealRarity(a.card?.rarity, b.card?.rarity);
  const newItems = items.filter((i) => i.entry.is_new).sort(byRarityDesc);
  const ownedItems = items.filter((i) => !i.entry.is_new).sort(byRarityDesc);
  const stagger = staggerMs(items.length);
  const ownedStart = ownedStartMs(items.length, newItems.length);

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
                  delayMs={i * stagger}
                  isNew
                  onSelect={setSelected}
                  onRevealed={followRevealed}
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
                  delayMs={ownedStart + i * stagger}
                  onSelect={setSelected}
                  onRevealed={followRevealed}
                />
              ))}
            </Grid>
          </section>
        ) : null}
      </div>

      <CardDialog
        card={selected}
        onClose={() => setSelected(null)}
        onSelect={setSelected}
      />
    </>
  );
}

function Grid({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
      {children}
    </div>
  );
}

/**
 * Keeps the animating tile on screen while the reveal runs.
 *
 * `block: "nearest"` is what makes this unobtrusive: it scrolls only when the
 * tile is actually out of view, so the popup advances a row at a time instead of
 * jumping on every card. Disabled entirely under reduced-motion.
 */
function useFollowReveal(count: number) {
  const reduced = usePrefersReducedMotion();
  // Ignore late callbacks once the user takes over by scrolling themselves.
  const cancelled = useRef(false);
  useEffect(() => {
    cancelled.current = false;
  }, [count]);

  return useCallback(
    (el: HTMLElement | null) => {
      if (reduced || cancelled.current || !el) return;
      el.scrollIntoView({ behavior: "smooth", block: "nearest" });
    },
    [reduced],
  );
}

function RevealTile({
  item,
  delayMs,
  isNew = false,
  onSelect,
  onRevealed,
}: {
  item: AdditionItem;
  delayMs: number;
  isNew?: boolean;
  onSelect: (card: CatalogCard) => void;
  onRevealed?: (el: HTMLElement | null) => void;
}) {
  const { entry, card } = item;
  const ref = useRef<HTMLButtonElement>(null);

  // Fire when this tile's turn comes up, on the same schedule as its CSS delay.
  useEffect(() => {
    if (!onRevealed) return;
    const t = setTimeout(() => onRevealed(ref.current), delayMs);
    return () => clearTimeout(t);
  }, [delayMs, onRevealed]);

  return (
    <button
      ref={ref}
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
