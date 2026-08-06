"use client";

import { useState } from "react";

import { cardImageCandidates, type CardImageInput } from "@/lib/domain/card-image";
import { cn } from "@/lib/utils";

/**
 * Card artwork hot-linked from a CDN. Tries each candidate URL in turn (TCGdex →
 * Limitless) and only falls back to the card number once all fail. In grid
 * thumbnails (size="sm") not-owned cards are desaturated — pass `dimUnowned={false}`
 * to keep previews in full color (e.g. pull-target thumbnails).
 */
export function CardImage({
  card,
  size = "sm",
  dimUnowned = true,
}: {
  card: CardImageInput;
  size?: "sm" | "lg";
  dimUnowned?: boolean;
}) {
  const candidates = cardImageCandidates(card, size);
  const [idx, setIdx] = useState(0);
  const src = candidates[idx];

  if (!src) {
    return (
      <span className="flex size-full items-center justify-center text-sm font-semibold tabular-nums text-muted-foreground/60">
        {card.card_number != null ? `#${card.card_number}` : "?"}
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
        dimUnowned && size === "sm" && !card.dex_owned && "grayscale",
      )}
    />
  );
}
