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
        expansion: z.string().nullable(),
        is_ex: z.boolean().nullable(),
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

/** One catalog card as the UI consumes it. */
export interface CatalogCard {
  set_code: string;
  card_number: number;
  name: string;
  rarity: string | null;
  pokemon_type: string | null;
  card_category: string | null;
  trainer_subtype: string | null;
  expansion: string;
  is_ex: boolean;
  owned: number;
}
