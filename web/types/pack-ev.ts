import { z } from "zod";

/**
 * Schemas mirroring the Python pipeline's data/current/pack_ev.json contract.
 * Kept in sync with tests/test_output_contract.py (PACK_RECORD_FIELDS etc.).
 *
 * Objects use Zod's default behaviour (unknown keys are stripped, not rejected),
 * so the front end stays resilient to additive pipeline changes while still
 * failing loudly if a field it depends on is removed or changes type.
 */

export const topEvCardSchema = z.object({
  name: z.string(),
  rarity: z.string().nullable(),
  owned: z.number(),
  pull_prob: z.number(),
  value: z.number(),
  ev_contribution: z.number(),
  is_deck_target: z.boolean(),
  rate_source: z.string(),
});
export type TopEvCard = z.infer<typeof topEvCardSchema>;

/** Strongest missing cards obtainable from a pack, ranked by power score. */
export const topPowerCardSchema = z.object({
  name: z.string(),
  set_code: z.string().nullable(),
  card_number: z.number().nullable(),
  rarity: z.string().nullable(),
  power_score: z.number(),
  pull_prob: z.number(),
});
export type TopPowerCard = z.infer<typeof topPowerCardSchema>;

/** Per-pack EV fields shared by pack_ev.json packs[] and recommendations. */
export const packRecordSchema = z.object({
  pack_name: z.string(),
  expansion: z.string(),
  set_code: z.string(),
  source_status: z.string(),
  slot_rates_confidence: z.string(),
  confidence_weight: z.number(),
  blocked: z.boolean(),
  blocked_reason: z.string().nullable(),
  purchasable: z.boolean(),
  cards_in_pool: z.number(),
  owned_in_pool: z.number(),
  missing_in_pool: z.number(),
  base_cards_in_pool: z.number(),
  base_owned_in_pool: z.number(),
  new_card_ev: z.number(),
  new_card_ev_10x: z.number(),
  copy_ev: z.number(),
  deck_target_ev: z.number(),
  missing_rare_plus: z.number(),
  rare_plus_ev_10x: z.number(),
  pack_total_ev: z.number(),
  confidence_adjusted_ev: z.number(),
  unified_score: z.number(),
  ev_diminishing_returns_ratio: z.number(),
  cost_per_unique_card_1x: z.number(),
  cost_per_unique_card_10x: z.number(),
  pz_coverage: z.number(),
  deck_target_cards: z.array(z.string()),
  notes: z.string(),
});
export type PackRecord = z.infer<typeof packRecordSchema>;

/** pack_ev.json packs[] additionally carries the top-cards breakdowns. */
export const packEvRecordSchema = packRecordSchema.extend({
  top_ev_cards: z.array(topEvCardSchema),
  top_power_cards: z.array(topPowerCardSchema).default([]),
});
export type PackEvRecord = z.infer<typeof packEvRecordSchema>;

export const packEvSchema = z.object({
  generated_at: z.string(),
  generated_by: z.string(),
  meta: z
    .object({
      collection_total: z.number(),
      model_confidence: z.string().optional(),
      inputs_hash: z.string().optional(),
    })
    .loose(),
  scoring_weights: z.record(z.string(), z.number()),
  packs: z.array(packEvRecordSchema),
  blocked_packs: z.array(z.unknown()),
});
export type PackEv = z.infer<typeof packEvSchema>;
