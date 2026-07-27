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

/**
 * How to label a card's power score.
 *
 * Pokémon are scored on HP and attack damage; Trainers on their rule text
 * (scripts/trainer_power.py). The two share a 0–100 range but measure different
 * things, so the label says which one the number is — showing a bare "Power
 * score" on both would invite comparing a Supporter to a Charizard.
 */
export function powerScoreLabel(card: CatalogCard): string {
  return card.power_score_kind === "trainer" ? "Utility score" : "Power score";
}
