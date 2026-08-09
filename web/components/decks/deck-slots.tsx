"use client";

import { X } from "lucide-react";

import { CardImage } from "@/components/cards/card-image";
import { DECK_SIZE, type Deck } from "@/lib/domain/deck";
import { typeColor } from "@/lib/domain/type-colors";
import { displayType } from "@/lib/domain/card";
import { cn } from "@/lib/utils";
import type { CatalogCard } from "@/types";

/**
 * The deck as 20 fixed slots.
 *
 * A list of what you've added tells you what you have; twenty slots tell you
 * what you still need — which is the actual question while building. Empty
 * slots stay visible so the shape of the deck is legible at a glance, and each
 * copy occupies its own slot because that is how the 20-card limit is counted.
 */
export function DeckSlots({
  deck,
  canEdit,
  onRemove,
}: {
  deck: Deck;
  canEdit: boolean;
  onRemove: (card: CatalogCard) => void;
}) {
  // One entry per copy, so two copies of a card fill two slots.
  const filled = deck.entries.flatMap(({ card, count }) =>
    Array.from({ length: count }, () => card),
  );
  const empties = Math.max(0, DECK_SIZE - filled.length);

  return (
    <div className="grid grid-cols-5 gap-2 sm:grid-cols-10 lg:grid-cols-5 xl:grid-cols-10">
      {filled.map((card, i) => (
        <button
          key={`${card.set_code}:${card.card_number}:${i}`}
          type="button"
          disabled={!canEdit}
          onClick={() => onRemove(card)}
          title={canEdit ? `Remove ${card.name}` : card.name}
          className="group relative aspect-[5/7] overflow-hidden rounded-md border disabled:cursor-default"
          style={{ backgroundColor: `${typeColor(displayType(card))}22` }}
        >
          {/* key remounts on card change so the CDN-fallback index resets —
              removing a card shifts every later slot onto a different card. */}
          <CardImage
            key={`${card.set_code}-${card.card_number}`}
            card={card}
            dimUnowned={false}
          />
          {canEdit ? (
            <span className="absolute inset-0 hidden items-center justify-center bg-black/55 group-hover:flex">
              <X className="size-5 text-white" />
            </span>
          ) : null}
        </button>
      ))}

      {Array.from({ length: empties }, (_, i) => (
        <div
          key={`empty-${i}`}
          aria-hidden
          className={cn(
            "flex aspect-[5/7] items-center justify-center rounded-md border border-dashed",
            "text-xs text-muted-foreground/50 tabular-nums",
          )}
        >
          {filled.length + i + 1}
        </div>
      ))}
    </div>
  );
}
