import { z } from "zod";

/**
 * Mirrors data/current/collection_summary.json (dashboard + sets pages).
 * Kept in sync with tests/test_output_contract.py.
 */

export const evolutionGroupSchema = z.object({
  line: z.array(z.string()),
  owned: z.array(z.string()),
  missing: z.array(z.string()),
  complete: z.boolean(),
});
export type EvolutionGroup = z.infer<typeof evolutionGroupSchema>;

/** top_cards_by_count entries are [name, count] tuples. */
export const topCardSchema = z.tuple([z.string(), z.number()]);
export type TopCard = z.infer<typeof topCardSchema>;

export const collectionSummarySchema = z.object({
  meta: z
    .object({
      total_cards: z.number(),
      last_updated: z.string(),
      format: z.string(),
    })
    .loose(),
  total_quantity: z.number(),
  meta_total_cards: z.number(),
  count_matches_meta: z.boolean(),
  unique_entries: z.number(),
  by_card_type: z.record(z.string(), z.number()),
  by_pokemon_type: z.record(z.string(), z.number()),
  by_stage: z.record(z.string(), z.number()),
  ex_entries: z.number(),
  ex_quantity: z.number(),
  trainer_subtypes: z.record(z.string(), z.number()),
  top_cards_by_count: z.array(topCardSchema),
  variant_names: z.record(z.string(), z.number()),
  evolution_groups: z.array(evolutionGroupSchema),
});
export type CollectionSummary = z.infer<typeof collectionSummarySchema>;
