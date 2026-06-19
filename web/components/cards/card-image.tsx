"use client";

import { useState } from "react";

import { cardImageUrl } from "@/lib/domain/card-image";
import { cn } from "@/lib/utils";
import type { CatalogCard } from "@/types";

/**
 * Card artwork hot-linked from TCGdex, with a graceful fallback to the card
 * number when no image exists (uncovered sets) or the request fails. Not-owned
 * cards are desaturated so the collection state reads at a glance.
 */
export function CardImage({ card }: { card: CatalogCard }) {
  const url = cardImageUrl(card);
  const [errored, setErrored] = useState(false);

  if (!url || errored) {
    return (
      <span className="flex size-full items-center justify-center text-sm font-semibold tabular-nums text-muted-foreground/60">
        #{card.card_number}
      </span>
    );
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element -- external CDN hot-link with onError fallback; next/image optimization is unnecessary here.
    <img
      src={url}
      alt={card.name}
      loading="lazy"
      onError={() => setErrored(true)}
      className={cn("size-full object-cover", card.owned <= 0 && "grayscale")}
    />
  );
}
