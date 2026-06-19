import { TypeBadge } from "@/components/cards/type-badge";
import { displayType } from "@/lib/domain/card";
import { typeColor } from "@/lib/domain/type-colors";
import { cn } from "@/lib/utils";
import type { CatalogCard } from "@/types";

/**
 * Responsive grid of card tiles, shared by the Cards page and the Set detail
 * page. The tile's visual is a card-shaped placeholder tinted by type; #7
 * swaps that placeholder for the real card image.
 */
export function CardGrid({ cards }: { cards: CatalogCard[] }) {
  if (cards.length === 0) {
    return (
      <p className="py-10 text-center text-sm text-muted-foreground">
        No cards match these filters.
      </p>
    );
  }

  return (
    <div className="grid grid-cols-3 gap-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 2xl:grid-cols-10">
      {cards.map((c) => (
        <CardTile key={`${c.set_code}-${c.card_number}`} card={c} />
      ))}
    </div>
  );
}

function CardTile({ card }: { card: CatalogCard }) {
  const owned = card.owned > 0;
  const type = displayType(card);

  return (
    <div className={cn("flex flex-col", !owned && "opacity-55")}>
      <div
        className="relative flex aspect-[5/7] items-center justify-center overflow-hidden rounded-md border"
        style={{ backgroundColor: `${typeColor(type)}22` }}
      >
        <span className="text-sm font-semibold text-muted-foreground/60 tabular-nums">
          #{card.card_number}
        </span>
        {owned ? (
          <span className="absolute left-1 top-1 rounded bg-primary px-1 text-[10px] font-medium text-primary-foreground">
            ×{card.owned}
          </span>
        ) : (
          <span className="absolute left-1 top-1 rounded border bg-background/80 px-1 text-[10px] text-muted-foreground">
            missing
          </span>
        )}
      </div>
      <div className="mt-1 truncate text-xs font-medium" title={card.name}>
        {card.name}
      </div>
      <div className="flex items-center justify-between gap-1">
        <TypeBadge type={type} />
        <span className="shrink-0 text-[10px] text-muted-foreground tabular-nums">
          {card.set_code}
        </span>
      </div>
    </div>
  );
}
