"use client";

import { useState } from "react";

import { cardImageUrl } from "@/lib/domain/card-image";
import { cn } from "@/lib/utils";
import type { CatalogCard } from "@/types";

/**
 * Card artwork hot-linked from a CDN, with a graceful fallback to the card
 * number when the request fails. In grid thumbnails (size="sm") not-owned cards
 * are desaturated; the enlarged view (size="lg") always shows full color.
 */
export function CardImage({
  card,
  size = "sm",
}: {
  card: CatalogCard;
  size?: "sm" | "lg";
}) {
  const [errored, setErrored] = useState(false);

  if (errored) {
    return (
      <span className="flex size-full items-center justify-center text-sm font-semibold tabular-nums text-muted-foreground/60">
        #{card.card_number}
      </span>
    );
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element -- external CDN hot-link with onError fallback; next/image optimization is unnecessary here.
    <img
      src={cardImageUrl(card, size)}
      alt={card.name}
      loading="lazy"
      onError={() => setErrored(true)}
      className={cn(
        "size-full object-cover",
        size === "sm" && card.owned <= 0 && "grayscale",
      )}
    />
  );
}
