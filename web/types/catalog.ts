import { z } from "zod";

/**
 * Card catalog = data/reference/card_reference.json merged with owned counts
 * from data/current/collection_normalized.json. Powers the Cards and Sets pages.
 */

export const cardReferenceFileSchema = z.object({
  records: z.array(
    z
      .object({
        set_code: z.string(),
        card_number: z.number(),
        name: z.string(),
        rarity: z.string().nullable(),
        pokemon_type: z.string().nullable(),
        card_category: z.string().nullable(),
        trainer_subtype: z.string().nullable().optional(),
        stage: z.string().nullable().optional(),
        expansion: z.string().nullable(),
        is_ex: z.boolean().nullable(),
        evolves_from: z.string().nullable().optional(),
      })
      .loose(),
  ),
});

export const collectionFileSchema = z.object({
  collection: z.array(
    z
      .object({
        set_code: z.string(),
        card_number: z.number(),
        count: z.number(),
      })
      .loose(),
  ),
});

/**
 * Which Pokémon a Trainer is restricted to helping — names it calls out
 * ("your Ninetales, Rapidash, or Magmar") and energy types it calls out
 * ("your {W} Pokémon"). Both lists empty means it works in any deck, which is the
 * common case; that is deliberately represented by emptiness, not by a flag.
 */
export const trainerBoostsSchema = z.object({
  names: z.array(z.string()),
  types: z.array(z.string()),
});

export type TrainerBoosts = z.infer<typeof trainerBoostsSchema>;

/**
 * data/reference/card_power_scores.json — two models sharing one file.
 *
 * `score_kind: "pokemon"` is the HP + attack + ability model and carries the
 * combat fields. `score_kind: "trainer"` is scored from rule text instead
 * (scripts/trainer_power.py) and has none of them, so those fields are optional
 * here. Entries written before score_kind existed were all Pokémon, hence the
 * default.
 */
export const powerScoresFileSchema = z.object({
  generated_at: z.string(),
  scores: z.record(
    z.string(),
    z
      .object({
        power_score: z.number(),
        score_kind: z.enum(["pokemon", "trainer"]).default("pokemon"),
        hp: z.number().nullable().optional(),
        effective_damage: z.number().nullable().optional(),
        has_ability: z.boolean().optional(),
        estimated: z.boolean().optional(),
        trainer_subtype: z.string().nullable().optional(),
        boosts: trainerBoostsSchema.optional(),
      })
      .loose(),
  ),
});

/**
 * data/reference/printing_groups.json — coords that are the same physical card.
 * Written by scripts/build_printing_groups.py; optional, since a checkout that
 * predates it still has to render.
 */
export const printingGroupsFileSchema = z.object({
  groups: z.array(
    z.object({
      id: z.string(),
      coords: z.array(z.tuple([z.string(), z.number()])),
    }),
  ),
});

/** One catalog card as the UI consumes it. */
export interface CatalogCard {
  set_code: string;
  card_number: number;
  name: string;
  rarity: string | null;
  pokemon_type: string | null;
  card_category: string | null;
  trainer_subtype: string | null;
  stage: string | null;
  expansion: string;
  is_ex: boolean;
  /**
   * Physical copies held at THIS coord, as Pokémon Zone reports them. Use this
   * for anything counting cards ("×3", quantity totals, deck copy limits) — it
   * is never inflated by multi-expansion registration.
   */
  owned: number;
  /**
   * Whether this dex slot is filled. Since the 2026-07-29 update a card obtained
   * from any pack registers under every expansion it appears in, so a slot can
   * read filled while `owned` at this coord is 0 (the copy sits at a sibling
   * printing). Use this for completion, ownership filters and owned styling.
   */
  dex_owned: boolean;
  /**
   * Group shared by every coord that is the same physical card; null for a
   * single-printing card. See scripts/build_printing_groups.py.
   */
  printing_group: string | null;
  /** 0–100 power/value score; null when the card could not be scored. */
  power_score: number | null;
  /**
   * Which model produced `power_score`. Pokémon are scored on HP and attack
   * damage, Trainers on their rule text — the two share a range but measure
   * different things, so never rank one against the other.
   */
  power_score_kind: "pokemon" | "trainer" | null;
  /**
   * Trainers only: which Pokémon this card is restricted to helping. Both lists
   * empty means it works in any deck (Giovanni, Poké Ball); null means the card
   * is not a scored Trainer at all.
   */
  boosts: TrainerBoosts | null;
  /** Name of the Pokémon this evolves from (for the evolution tabs); null for Basics. */
  evolves_from: string | null;
}
