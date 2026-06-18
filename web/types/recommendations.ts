import { z } from "zod";

import { packRecordSchema } from "@/types/pack-ev";

/**
 * Mirrors data/current/inferred_pack_recommendations.json.
 * Kept in sync with tests/test_output_contract.py.
 */
export const recommendationsSchema = z.object({
  generated_at: z.string(),
  generated_by: z.string(),
  model_confidence: z.string(),
  collection_total: z.number(),
  collection_mutated: z.boolean(),
  inputs_hash: z.string(),
  disclaimer: z.string(),
  top_packs_unified: z.array(packRecordSchema),
  cost_efficiency_ranking: z.array(packRecordSchema),
  chase_deck_packs: z.unknown(),
});
export type Recommendations = z.infer<typeof recommendationsSchema>;
