import type { CatalogCard } from "@/types";

/**
 * The single "type" label shown for a card: a Pokémon's energy type, or a
 * Trainer's subtype (Item/Supporter/Stadium/Pokemon Tool). card_reference now
 * guarantees one of these, so "—" should never appear.
 */
export function displayType(card: CatalogCard): string {
  return (
    card.pokemon_type ?? card.trainer_subtype ?? card.card_category ?? "—"
  );
}
