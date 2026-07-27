"use client";

import { useMemo } from "react";

import { CardImage } from "@/components/cards/card-image";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { pokemonBoostedBy, trainersBoosting } from "@/lib/domain/boosts";
import { buildEvolution } from "@/lib/domain/evolution";
import { cn } from "@/lib/utils";
import type { CatalogCard } from "@/types";

/** A type restriction covers hundreds of Pokémon; show a useful slice, not all. */
const BOOST_LIMIT = 12;

/**
 * Context for the enlarged card: its line-mates in the same set, its other
 * printings (base/ex/Mega), the whole line across all sets, and — for cards in a
 * boost relationship — the Trainers that support it or the Pokémon it supports.
 * Unowned cards are greyed (CardImage default); clicking one navigates the dialog
 * to it.
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
  const boosts = useMemo(() => {
    // A Pokémon wants to know which Trainers support it; a Trainer wants to know
    // what it supports. Only one of the two can ever be non-empty.
    const trainers = trainersBoosting(allCards, card);
    if (trainers.length > 0) {
      return { label: "Trainers that help", cards: trainers, total: trainers.length };
    }
    const supported = pokemonBoostedBy(allCards, card);
    // A type restriction ("your {W} Pokémon") covers hundreds of cards; show the
    // ones you own and the strongest, and say so rather than listing the lot.
    return {
      label: "Boosts",
      cards: supported.slice(0, BOOST_LIMIT),
      total: supported.length,
    };
  }, [allCards, card]);

  const tabs = [
    { value: "set", label: "Set evolution", cards: evo.setEvolution(card) },
    { value: "versions", label: "Other versions", cards: evo.otherVersions(card) },
    { value: "related", label: "Related cards", cards: evo.relatedCards(card) },
    { value: "boosts", label: boosts.label, cards: boosts.cards },
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
          {t.value === "boosts" && boosts.total > t.cards.length ? (
            <p className="mt-2 text-xs text-muted-foreground">
              Showing {t.cards.length} of {boosts.total} — owned and
              highest-scoring first.
            </p>
          ) : null}
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
