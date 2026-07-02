"use client";

import { useState } from "react";

import { CardImage } from "@/components/cards/card-image";
import { CardDialog } from "@/components/cards/card-dialog";
import { cn } from "@/lib/utils";
import type { CatalogCard } from "@/types";

/**
 * A color card thumbnail that opens the enlarged CardDialog (set / rarity / type /
 * owned / power score) on click. Reused by the dashboard and the pack tables.
 * Size is controlled by `className` (defaults to a small 5/7 tile).
 */
export function EnlargeableCard({
  card,
  className,
}: {
  card: CatalogCard;
  className?: string;
}) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        title={`${card.name} — click to enlarge`}
        className={cn(
          "aspect-[5/7] w-14 shrink-0 overflow-hidden rounded-md border transition-transform hover:scale-[1.04] hover:shadow-md focus:outline-none focus-visible:ring-2 focus-visible:ring-ring",
          className,
        )}
      >
        <CardImage card={card} dimUnowned={false} />
      </button>
      <CardDialog card={open ? card : null} onClose={() => setOpen(false)} />
    </>
  );
}
