"use client";

import { useState } from "react";

import { cardImageCandidates } from "@/lib/domain/card-image";
import { cn } from "@/lib/utils";
import type { CatalogCard } from "@/types";

/**
 * Card artwork hot-linked from a CDN. Tries each candidate URL in turn (TCGdex →
 * Limitless) and only falls back to the card number once all fail. In grid
 * thumbnails (size="sm") not-owned cards are desaturated.
 */
export function CardImage({
  card,
  size = "sm",
}: {
  card: CatalogCard;
  size?: "sm" | "lg";
}) {
  const candidates = cardImageCandidates(card, size);
  const [idx, setIdx] = useState(0);
  const src = candidates[idx];

  if (!src) {
    return (
      <span className="flex size-full items-center justify-center text-sm font-semibold tabular-nums text-muted-foreground/60">
        #{card.card_number}
      </span>
    );
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element -- external CDN hot-link with onError fallback; next/image optimization is unnecessary here.
    <img
      src={src}
      alt={card.name}
      loading="lazy"
      onError={() => setIdx((i) => i + 1)}
      className={cn(
        "size-full object-cover",
        size === "sm" && card.owned <= 0 && "grayscale",
      )}
    />
  );
}
