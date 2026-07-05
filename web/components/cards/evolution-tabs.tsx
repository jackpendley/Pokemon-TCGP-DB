"use client";

import { useMemo } from "react";

import { CardImage } from "@/components/cards/card-image";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { buildEvolution } from "@/lib/domain/evolution";
import { cn } from "@/lib/utils";
import type { CatalogCard } from "@/types";

/**
 * Evolution context for the enlarged card: its line-mates in the same set, its
 * other printings (base/ex/Mega), and the whole line across all sets. Unowned
 * cards are greyed (CardImage default); clicking one navigates the dialog to it.
 */
export function EvolutionTabs({
  card,
  allCards,
  onSelect,
}: {
  card: CatalogCard;
  allCards: CatalogCard[];
  onSelect: (c: CatalogCard) => void;
}) {
  const evo = useMemo(() => buildEvolution(allCards), [allCards]);
  const tabs = [
    { value: "set", label: "Set evolution", cards: evo.setEvolution(card) },
    { value: "versions", label: "Other versions", cards: evo.otherVersions(card) },
    { value: "related", label: "Related cards", cards: evo.relatedCards(card) },
  ].filter((t) => t.cards.length > 0);

  if (tabs.length === 0) return null;

  return (
    <Tabs defaultValue={tabs[0].value} className="gap-3">
      <TabsList variant="line" className="flex-wrap">
        {tabs.map((t) => (
          <TabsTrigger key={t.value} value={t.value}>
            {t.label}
            <span className="ml-1 text-xs text-muted-foreground tabular-nums">
              {t.cards.length}
            </span>
          </TabsTrigger>
        ))}
      </TabsList>
      {tabs.map((t) => (
        <TabsContent key={t.value} value={t.value}>
          <div className="grid grid-cols-4 gap-2 sm:grid-cols-5">
            {t.cards.map((c) => (
              <MiniCard
                key={`${c.set_code}-${c.card_number}`}
                card={c}
                onSelect={onSelect}
              />
            ))}
          </div>
        </TabsContent>
      ))}
    </Tabs>
  );
}

function MiniCard({
  card,
  onSelect,
}: {
  card: CatalogCard;
  onSelect: (c: CatalogCard) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onSelect(card)}
      title={`${card.name} · ${card.set_code}`}
      className={cn(
        "flex flex-col text-left transition-transform hover:scale-[1.04]",
        card.owned <= 0 && "opacity-60",
      )}
    >
      <div className="aspect-[5/7] overflow-hidden rounded border">
        <CardImage card={card} />
      </div>
      <span className="mt-0.5 truncate text-[10px] font-medium" title={card.name}>
        {card.name}
      </span>
      <span className="truncate text-[10px] text-muted-foreground tabular-nums">
        {card.set_code}
      </span>
    </button>
  );
}
