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

/**
 * Mega-Evolution ex card. Detected by the "Mega " name prefix (every such card
 * is is_ex); name-substring matching is unsafe ("Yanmega ex" is not a Mega).
 */
export function isMegaEx(card: CatalogCard): boolean {
  return card.is_ex && card.name.startsWith("Mega ");
}
