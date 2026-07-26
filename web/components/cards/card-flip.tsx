"use client";

import { CardImage } from "@/components/cards/card-image";
import { displayType, powerScoreLabel } from "@/lib/domain/card";
import { titleCase } from "@/lib/domain/format";
import { readableInk, typeColor } from "@/lib/domain/type-colors";
import { cn } from "@/lib/utils";
import type { CatalogCard } from "@/types";

/**
 * A card that flips between its artwork and its details.
 *
 * The back is filled with the card's own type color — the same palette the
 * grid tiles and the type pie chart use — with ink chosen per color so the
 * lighter types (Lightning) stay readable. Metadata is a single column at a
 * generous size, because the back exists to be read at arm's length on a phone.
 *
 * Purely presentational: the parent owns `flipped` so a swipe, a tap and a
 * keypress can all drive it.
 */
export function CardFlip({
  card,
  flipped,
  onToggle,
  className,
}: {
  card: CatalogCard;
  flipped: boolean;
  onToggle: () => void;
  className?: string;
}) {
  const type = displayType(card);
  const bg = typeColor(type);
  const ink = readableInk(bg);

  return (
    <div className={cn("flip-scene aspect-[5/7]", className)}>
      <button
        type="button"
        onClick={onToggle}
        aria-label={
          flipped
            ? `Show artwork for ${card.name}`
            : `Show details for ${card.name}`
        }
        aria-pressed={flipped}
        className="block size-full rounded-xl text-left outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <span className="flip-inner block" data-flipped={flipped}>
          <span className="flip-face block rounded-xl border bg-muted">
            {/* key remounts on card change so the CDN-fallback error state resets */}
            <CardImage
              key={`${card.set_code}-${card.card_number}`}
              card={card}
              size="lg"
              dimUnowned={false}
            />
          </span>

          <span
            className="flip-face flip-face-back flex flex-col gap-7 rounded-xl border p-5"
            style={{ backgroundColor: bg, color: ink }}
          >
            <span className="block">
              <span className="block font-heading text-xl leading-tight font-semibold">
                {card.name}
              </span>
              <span className="mt-0.5 block text-sm opacity-80">
                {card.expansion}
              </span>
            </span>

            <dl className="flex flex-col gap-2.5 text-base">
              <BackRow label="Number" ink={ink}>
                {card.set_code} · #{card.card_number}
              </BackRow>
              <BackRow label="Rarity" ink={ink}>
                {titleCase(card.rarity)}
              </BackRow>
              <BackRow label="Type" ink={ink}>
                {type}
              </BackRow>
              <BackRow label="Owned" ink={ink}>
                {card.owned > 0 ? `×${card.owned}` : "Not owned"}
              </BackRow>
              {card.power_score != null ? (
                <BackRow label={powerScoreLabel(card)} ink={ink}>
                  <span className="tabular-nums">
                    {card.power_score.toFixed(1)}
                  </span>
                  <span className="opacity-70"> / 100</span>
                </BackRow>
              ) : null}
            </dl>
          </span>
        </span>
      </button>
    </div>
  );
}

function BackRow({
  label,
  ink,
  children,
}: {
  label: string;
  ink: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-baseline justify-between gap-4 border-b border-current/20 pb-1.5 last:border-b-0">
      <dt className="text-xs tracking-wide uppercase opacity-70">{label}</dt>
      <dd className="font-semibold" style={{ color: ink }}>
        {children}
      </dd>
    </div>
  );
}
