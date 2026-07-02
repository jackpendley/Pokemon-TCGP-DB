import { z } from "zod";

import {
  collectionSummarySchema,
  packEvSchema,
  recommendationsSchema,
  spendingPlanSchema,
} from "@/types";
import type { DataSource } from "@/lib/data/source";

/**
 * Reusable parity contract for any DataSource implementation. Today only
 * localJsonSource exists; when SupabaseSource lands (hosted phase) it is run
 * through the SAME harness so the two are guaranteed to expose identical shapes
 * to the UI — the read seam stays swappable without UI/domain changes.
 */

/** CatalogCard is a plain interface in types/catalog.ts; mirror it as a schema here. */
const catalogCardSchema = z.object({
  set_code: z.string(),
  card_number: z.number(),
  name: z.string(),
  rarity: z.string().nullable(),
  pokemon_type: z.string().nullable(),
  card_category: z.string().nullable(),
  trainer_subtype: z.string().nullable(),
  stage: z.string().nullable(),
  expansion: z.string(),
  is_ex: z.boolean(),
  owned: z.number(),
  power_score: z.number().nullable(),
});

const syncStatusSchema = z.object({
  stats: z.unknown().nullable(),
  reviewQueue: z.unknown().nullable(),
  delta: z.unknown().nullable(),
});

/** Each DataSource method mapped to the schema its return value must satisfy. */
const methodSchemas = {
  getCollectionSummary: collectionSummarySchema,
  getPackEv: packEvSchema,
  getRecommendations: recommendationsSchema,
  getSpendingPlan: spendingPlanSchema,
  getCatalog: z.array(catalogCardSchema),
  getSyncStatus: syncStatusSchema,
} as const;

/**
 * Calls every DataSource method and validates its output against the contract.
 * Throws (with the offending method + Zod error) on the first violation, so a
 * drifting implementation fails loudly. Returns the method names verified.
 */
export async function verifyDataSourceContract(
  source: DataSource,
): Promise<string[]> {
  const verified: string[] = [];
  for (const [method, schema] of Object.entries(methodSchemas)) {
    const value = await source[method as keyof DataSource]();
    const result = (schema as z.ZodType).safeParse(value);
    if (!result.success) {
      throw new Error(
        `DataSource.${method} violated the contract:\n${result.error.message}`,
      );
    }
    verified.push(method);
  }
  return verified;
}
