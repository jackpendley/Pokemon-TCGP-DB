import type { CatalogCard } from "@/types";
import { baseSpecies } from "@/lib/domain/evolution";

/**
 * Deck construction rules for Pokémon TCG Pocket, and the derived stats a deck
 * list is worth showing.
 *
 * Pure and React-free on purpose: the rules are the interesting part and they
 * deserve to be testable without rendering anything.
 *
 * Two distinctions this module is careful about:
 *
 *  - **Copies are counted by card *name*, not by printing.** A deck mixing the
 *    A1 and PROMO-A printings of the same card still holds two copies of that
 *    card. The pipeline has the same note pending in build_pack_ev.py.
 *  - **Errors make a deck illegal; warnings do not.** The game rejects a deck
 *    that isn't exactly 20 cards, but it will happily let you register an
 *    evolution with no Basic to evolve from — that's merely unplayable, and
 *    saying "illegal" would be wrong.
 */

export const DECK_SIZE = 20;
export const MAX_COPIES_PER_NAME = 2;
export const MAX_ENERGY_TYPES = 3;

/**
 * Energy types the Energy Zone can generate. Dragon and Colorless are excluded
 * deliberately: no Energy Zone produces them — Dragon attacks are paid with
 * other types, and Colorless costs accept anything.
 */
export const SELECTABLE_ENERGY_TYPES = [
  "Grass",
  "Fire",
  "Water",
  "Lightning",
  "Psychic",
  "Fighting",
  "Darkness",
  "Metal",
] as const;

export type EnergyType = (typeof SELECTABLE_ENERGY_TYPES)[number];

/** A card in a deck, with how many copies of it are included. */
export interface DeckSlot {
  card: CatalogCard;
  count: number;
}

export interface Deck {
  entries: DeckSlot[];
  /** Types chosen for the Energy Zone. */
  energyTypes: string[];
}

export type DeckIssueCode =
  | "deck-size"
  | "copy-limit"
  | "no-basic"
  | "unverifiable-basic"
  | "energy-none"
  | "energy-too-many"
  | "energy-unused"
  | "energy-mismatch"
  | "missing-evolution-parent";

export interface DeckIssue {
  code: DeckIssueCode;
  /** Errors block registration; warnings are advisory. */
  severity: "error" | "warning";
  message: string;
  /** Card names the issue points at, when it's card-specific. */
  cards?: string[];
}

/** Total cards in the deck, counting copies. */
export function deckCardCount(deck: Deck): number {
  return deck.entries.reduce((n, e) => n + e.count, 0);
}

/** Copies held per card name, aggregated across printings. */
export function copiesByName(deck: Deck): Map<string, number> {
  const by = new Map<string, number>();
  for (const { card, count } of deck.entries) {
    by.set(card.name, (by.get(card.name) ?? 0) + count);
  }
  return by;
}

const isPokemon = (c: CatalogCard) => c.card_category === "Pokemon";
const isBasic = (c: CatalogCard) => c.stage === "Basic";
/**
 * 190 Pokémon in the reference carry no stage (concentrated in B3b and the
 * promo sets), so "is there a Basic?" can be genuinely unanswerable rather than
 * false. Those cards are reported separately instead of being treated as
 * non-Basic, which would produce a confidently wrong error.
 */
const stageUnknown = (c: CatalogCard) => isPokemon(c) && !c.stage;

/** Every rule violation in a deck, most severe first. */
export function validateDeck(deck: Deck): DeckIssue[] {
  const issues: DeckIssue[] = [];
  const total = deckCardCount(deck);

  if (total !== DECK_SIZE) {
    issues.push({
      code: "deck-size",
      severity: "error",
      message:
        total < DECK_SIZE
          ? `Deck has ${total} cards — add ${DECK_SIZE - total} more.`
          : `Deck has ${total} cards — remove ${total - DECK_SIZE}.`,
    });
  }

  const overLimit = [...copiesByName(deck)]
    .filter(([, n]) => n > MAX_COPIES_PER_NAME)
    .map(([name]) => name);
  if (overLimit.length > 0) {
    issues.push({
      code: "copy-limit",
      severity: "error",
      message: `More than ${MAX_COPIES_PER_NAME} copies of the same card: ${overLimit.join(", ")}.`,
      cards: overLimit,
    });
  }

  const pokemon = deck.entries.filter((e) => isPokemon(e.card));
  const hasBasic = pokemon.some((e) => isBasic(e.card));
  const unknown = pokemon.filter((e) => stageUnknown(e.card)).map((e) => e.card.name);
  if (!hasBasic) {
    if (unknown.length > 0) {
      issues.push({
        code: "unverifiable-basic",
        severity: "warning",
        message:
          "No confirmed Basic Pokémon. Some cards in this deck have no recorded " +
          "evolution stage, so this can't be checked automatically.",
        cards: unknown,
      });
    } else {
      issues.push({
        code: "no-basic",
        severity: "error",
        message: "A deck needs at least 1 Basic Pokémon to start the game.",
      });
    }
  }

  issues.push(...energyIssues(deck, pokemon));
  issues.push(...evolutionIssues(deck, pokemon));

  return issues.sort((a, b) => severityRank(a) - severityRank(b));
}

const severityRank = (i: DeckIssue) => (i.severity === "error" ? 0 : 1);

function energyIssues(deck: Deck, pokemon: DeckSlot[]): DeckIssue[] {
  const issues: DeckIssue[] = [];
  const chosen = new Set(deck.energyTypes);

  if (chosen.size === 0) {
    issues.push({
      code: "energy-none",
      severity: "error",
      message: "Choose at least 1 energy type for the Energy Zone.",
    });
    return issues;
  }
  if (chosen.size > MAX_ENERGY_TYPES) {
    issues.push({
      code: "energy-too-many",
      severity: "error",
      message: `The Energy Zone holds at most ${MAX_ENERGY_TYPES} energy types.`,
    });
  }

  // Colorless Pokémon pay their costs with anything, so they never mismatch.
  const mismatched = [
    ...new Set(
      pokemon
        .filter(
          (e) =>
            e.card.pokemon_type &&
            e.card.pokemon_type !== "Colorless" &&
            !chosen.has(e.card.pokemon_type),
        )
        .map((e) => e.card.name),
    ),
  ];
  if (mismatched.length > 0) {
    issues.push({
      code: "energy-mismatch",
      severity: "warning",
      message:
        "These Pokémon need an energy type the Energy Zone won't generate: " +
        `${mismatched.join(", ")}.`,
      cards: mismatched,
    });
  }

  const used = new Set(
    pokemon.map((e) => e.card.pokemon_type).filter((t): t is string => t != null),
  );
  const unused = [...chosen].filter((t) => !used.has(t));
  if (unused.length > 0 && unused.length < chosen.size) {
    issues.push({
      code: "energy-unused",
      severity: "warning",
      message:
        `No Pokémon in this deck uses ${unused.join(", ")} energy — ` +
        "dropping it makes the Energy Zone more consistent.",
    });
  }
  return issues;
}

/**
 * An evolution with no Basic to evolve from is legal but dead weight, so this
 * warns rather than errors. Matching is by base species name (shared with the
 * evolution tabs), so "Mega Venusaur ex" still resolves to its line.
 */
function evolutionIssues(deck: Deck, pokemon: DeckSlot[]): DeckIssue[] {
  const present = new Set(pokemon.map((e) => baseSpecies(e.card.name)));
  const orphans = [
    ...new Set(
      pokemon
        .filter((e) => e.card.evolves_from && !present.has(baseSpecies(e.card.evolves_from)))
        .map((e) => e.card.name),
    ),
  ];
  if (orphans.length === 0) return [];
  return [
    {
      code: "missing-evolution-parent",
      severity: "warning",
      message:
        "These Pokémon have nothing to evolve from in this deck: " +
        `${orphans.join(", ")}.`,
      cards: orphans,
    },
  ];
}

/** A deck is legal when nothing blocks registration. Warnings are allowed. */
export function isDeckLegal(deck: Deck): boolean {
  return !validateDeck(deck).some((i) => i.severity === "error");
}

// ── Summary ────────────────────────────────────────────────────────────────

export interface MissingCard {
  name: string;
  needed: number;
  owned: number;
  short: number;
}

export interface DeckSummary {
  total: number;
  pokemon: number;
  trainers: number;
  /** Counts per evolution stage, with unrecorded stages under "Unknown". */
  stageCounts: Record<string, number>;
  /** Mean power score of the deck's Pokémon, weighted by copies. */
  averagePokemonPower: number | null;
  /** Mean utility score of the deck's Trainers — a different scale; never compare. */
  averageTrainerUtility: number | null;
  /** Cards you don't own enough copies of to actually build this. */
  missing: MissingCard[];
}

/**
 * Copies owned per card name, across every printing.
 *
 * Ownership is stored per set coordinate, but a deck cares about the card: two
 * copies of one Pokémon from different sets are two copies for deck-building.
 */
export function ownedByName(catalog: CatalogCard[]): Map<string, number> {
  const by = new Map<string, number>();
  for (const c of catalog) {
    if (c.owned > 0) by.set(c.name, (by.get(c.name) ?? 0) + c.owned);
  }
  return by;
}

export function deckSummary(deck: Deck, catalog: CatalogCard[]): DeckSummary {
  const owned = ownedByName(catalog);
  const stageCounts: Record<string, number> = {};
  let pokemon = 0;
  let trainers = 0;
  let powerSum = 0;
  let powerCount = 0;
  let utilitySum = 0;
  let utilityCount = 0;

  for (const { card, count } of deck.entries) {
    if (isPokemon(card)) {
      pokemon += count;
      const stage = card.stage ?? "Unknown";
      stageCounts[stage] = (stageCounts[stage] ?? 0) + count;
      if (card.power_score != null && card.power_score_kind !== "trainer") {
        powerSum += card.power_score * count;
        powerCount += count;
      }
    } else {
      trainers += count;
      if (card.power_score != null && card.power_score_kind === "trainer") {
        utilitySum += card.power_score * count;
        utilityCount += count;
      }
    }
  }

  const missing: MissingCard[] = [...copiesByName(deck)]
    .map(([name, needed]) => {
      const have = owned.get(name) ?? 0;
      return { name, needed, owned: have, short: needed - have };
    })
    .filter((m) => m.short > 0)
    .sort((a, b) => b.short - a.short || a.name.localeCompare(b.name));

  const mean = (sum: number, n: number) =>
    n > 0 ? Math.round((sum / n) * 10) / 10 : null;

  return {
    total: deckCardCount(deck),
    pokemon,
    trainers,
    stageCounts,
    averagePokemonPower: mean(powerSum, powerCount),
    averageTrainerUtility: mean(utilitySum, utilityCount),
    missing,
  };
}
