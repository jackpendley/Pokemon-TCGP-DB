import { z } from "zod";

/** Mirrors data/current/final_hourglass_spending_plan.json (Plan page). */
export const spendingBatchSchema = z.object({
  batch_number: z.number(),
  pack_name: z.string(),
  expansion: z.string(),
  set_code: z.string(),
  packs_to_open: z.number(),
  hourglass_cost: z.number(),
  unified_score: z.number(),
  new_card_ev_10x: z.number(),
  cost_per_unique_card_10x: z.number(),
  missing_in_pool: z.number(),
  rerun_after: z.boolean(),
  notes: z.string(),
});
export type SpendingBatch = z.infer<typeof spendingBatchSchema>;

export const spendingPlanSchema = z.object({
  generated_at: z.string(),
  collection_total: z.number(),
  hourglass_per_pack: z.number(),
  spending_plan: z.object({
    label: z.string(),
    description: z.string(),
    batches: z.array(spendingBatchSchema),
    total_batches: z.number(),
    total_hourglasses: z.number(),
    stopping_condition: z.string(),
    top_pack_name: z.string(),
  }),
});
export type SpendingPlan = z.infer<typeof spendingPlanSchema>;
