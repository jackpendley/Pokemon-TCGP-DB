import type { CatalogCard } from "@/types";

/**
 * Trainer → Pokémon boost relationships.
 *
 * A Trainer whose rule text only works with certain Pokémon carries that
 * restriction as `boosts` (see scripts/trainer_power.py `trainer_boosts`). The
 * same restriction that makes such a card score lower is what makes it worth
 * recommending: "your {W} Pokémon" is precisely the card a Water deck wants.
 *
 * Two conventions matter here:
 *
 *  - **Empty lists mean universal.** Giovanni boosts every deck, so it carries
 *    `{names: [], types: []}`. Those cards are excluded from these results, which
 *    are about *specific* affinity — a list of "Trainers that boost this deck"
 *    that included every generic Supporter would say nothing.
 *  - **Names join across printings.** `boosts.names` holds card names, so a
 *    Trainer that boosts "Ninetales" boosts every printing of Ninetales.
 */

/** True when this Trainer names a specific Pokémon or energy type. */
export function hasBoosts(card: CatalogCard): boolean {
  const b = card.boosts;
  return b != null && (b.names.length > 0 || b.types.length > 0);
}

/** True when `trainer`'s restriction covers `target`. */
export function boostsPokemon(trainer: CatalogCard, target: CatalogCard): boolean {
  const b = trainer.boosts;
  if (b == null) return false;
  if (b.names.includes(target.name)) return true;
  return target.pokemon_type != null && b.types.includes(target.pokemon_type);
}

/** Trainers that specifically boost this Pokémon, best-scoring first. */
export function trainersBoosting(
  catalog: CatalogCard[],
  target: CatalogCard,
): CatalogCard[] {
  if (target.card_category !== "Pokemon") return [];
  return catalog
    .filter((c) => hasBoosts(c) && boostsPokemon(c, target))
    .sort(byUtilityThenName);
}

/** Pokémon this Trainer boosts, owned first so the useful ones lead. */
export function pokemonBoostedBy(
  catalog: CatalogCard[],
  trainer: CatalogCard,
): CatalogCard[] {
  if (!hasBoosts(trainer)) return [];
  return catalog
    .filter((c) => c.card_category === "Pokemon" && boostsPokemon(trainer, c))
    .sort(
      (a, b) =>
        Number(b.owned > 0) - Number(a.owned > 0) ||
        (b.power_score ?? 0) - (a.power_score ?? 0) ||
        a.name.localeCompare(b.name),
    );
}

/**
 * Trainers worth adding to a deck built from these Pokémon names and energy
 * types, best-scoring first and one row per card name (a reprint is the same
 * card). Anything already in the deck is excluded — `inDeck` is a set of names.
 */
export function recommendedTrainers(
  catalog: CatalogCard[],
  {
    names,
    types,
    inDeck,
  }: { names: Iterable<string>; types: Iterable<string>; inDeck?: Set<string> },
): CatalogCard[] {
  const wantNames = new Set(names);
  const wantTypes = new Set(types);
  if (wantNames.size === 0 && wantTypes.size === 0) return [];

  const best = new Map<string, CatalogCard>();
  for (const card of catalog) {
    if (!hasBoosts(card) || inDeck?.has(card.name)) continue;
    const b = card.boosts!;
    const matches =
      b.names.some((n) => wantNames.has(n)) ||
      b.types.some((t) => wantTypes.has(t));
    if (!matches) continue;
    // One row per name: prefer a printing you own, then the higher score.
    const held = best.get(card.name);
    if (
      held == null ||
      Number(card.owned > 0) - Number(held.owned > 0) > 0 ||
      (card.power_score ?? 0) > (held.power_score ?? 0)
    ) {
      best.set(card.name, card);
    }
  }
  return [...best.values()].sort(byUtilityThenName);
}

/** Utility score descending; Trainer scores only, so they are comparable. */
function byUtilityThenName(a: CatalogCard, b: CatalogCard): number {
  return (b.power_score ?? 0) - (a.power_score ?? 0) || a.name.localeCompare(b.name);
}
