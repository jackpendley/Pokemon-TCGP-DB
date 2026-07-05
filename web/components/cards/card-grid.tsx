"use client";

import { useState } from "react";

import { CardDialog } from "@/components/cards/card-dialog";
import { CardImage } from "@/components/cards/card-image";
import { TypeBadge } from "@/components/cards/type-badge";
import { displayType } from "@/lib/domain/card";
import { typeColor } from "@/lib/domain/type-colors";
import { cn } from "@/lib/utils";
import type { CatalogCard } from "@/types";

/**
 * Responsive grid of card tiles, shared by the Cards page and the Set detail
 * page. Clicking a tile opens an enlarged view (full-resolution image + details).
 */
export function CardGrid({
  cards,
  allCards,
}: {
  cards: CatalogCard[];
  /** Full catalog for the evolution/versions tabs (defaults to `cards`). */
  allCards?: CatalogCard[];
}) {
  const [selected, setSelected] = useState<CatalogCard | null>(null);

  if (cards.length === 0) {
    return (
      <p className="py-10 text-center text-sm text-muted-foreground">
        No cards match these filters.
      </p>
    );
  }

  return (
    <>
      <div className="grid grid-cols-3 gap-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 2xl:grid-cols-10">
        {cards.map((c) => (
          <CardTile
            key={`${c.set_code}-${c.card_number}`}
            card={c}
            onClick={() => setSelected(c)}
          />
        ))}
      </div>
      <CardDialog
        card={selected}
        onClose={() => setSelected(null)}
        allCards={allCards ?? cards}
        onSelect={setSelected}
      />
    </>
  );
}

function CardTile({
  card,
  onClick,
}: {
  card: CatalogCard;
  onClick: () => void;
}) {
  const owned = card.owned > 0;
  const type = displayType(card);

  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex flex-col text-left transition-transform hover:scale-[1.03]",
        !owned && "opacity-55",
      )}
    >
      <div
        className="flex aspect-[5/7] items-center justify-center overflow-hidden rounded-md border"
        style={{ backgroundColor: `${typeColor(type)}22` }}
      >
        <CardImage card={card} />
      </div>
      {/* Name + owned count on one line; type + set code below. Not-owned cards
          are already signalled by the grayscale art, so no "missing" badge. */}
      <div className="mt-1 flex items-center justify-between gap-1">
        <span className="truncate text-xs font-medium" title={card.name}>
          {card.name}
        </span>
        {owned ? (
          <span className="shrink-0 rounded bg-primary px-1 text-[10px] font-medium text-primary-foreground tabular-nums">
            ×{card.owned}
          </span>
        ) : null}
      </div>
      <div className="flex items-center justify-between gap-1">
        <TypeBadge type={type} />
        <span className="shrink-0 text-[10px] text-muted-foreground tabular-nums">
          {card.set_code}
        </span>
      </div>
    </button>
  );
}
