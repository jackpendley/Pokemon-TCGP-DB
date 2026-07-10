import "server-only";

import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import { z } from "zod";

import { env } from "@/lib/env";
import {
  collectionSummarySchema,
  packEvSchema,
  playerStatsSchema,
  recommendationsSchema,
  reviewQueueSchema,
  syncDeltaSchema,
  syncHistoryEntrySchema,
} from "@/types";
import type { CatalogCard, SyncStatus } from "@/types";
import type { DataSource } from "@/lib/data/source";

/**
 * DataSource backed by the Supabase schema from supabase/migrations/0001_init.sql
 * (populated by scripts/publish_to_supabase.py). Reads use the service-role
 * key server-side (Phase 6 dropped the anon RLS policies); RLS still guards
 * anon/browser access, and this module is server-only so the key can never
 * reach a client bundle.
 *
 * Derived artifacts are stored as whole JSONB documents, so every method ends
 * in the same Zod parse localJsonSource uses: identical validation at the
 * boundary guarantees identical shapes (the Phase 4 parity gate).
 */

/** Rows fetched per page; PostgREST caps unranged selects at 1000. */
const PAGE_SIZE = 1000;

const cardRowSchema = z.object({
  set_code: z.string(),
  card_number: z.number(),
  name: z.string(),
  rarity: z.string().nullable(),
  pokemon_type: z.string().nullable(),
  card_category: z.string().nullable(),
  trainer_subtype: z.string().nullable(),
  stage: z.string().nullable(),
  expansion: z.string().nullable(),
  is_ex: z.boolean().nullable(),
  evolves_from: z.string().nullable(),
  power_score: z.number().nullable(),
});

const CARD_COLUMNS =
  "set_code, card_number, name, rarity, pokemon_type, card_category, " +
  "trainer_subtype, stage, expansion, is_ex, evolves_from, power_score";

const collectionRowSchema = z.object({
  set_code: z.string(),
  card_number: z.number(),
  count: z.number(),
});

const syncStatusRowSchema = z.object({
  stats: playerStatsSchema.nullable(),
  review_queue: reviewQueueSchema.nullable(),
  delta: syncDeltaSchema.nullable(),
});

function parseRows<T>(table: string, rows: unknown[], schema: z.ZodType<T>): T[] {
  const parsed = z.array(schema).safeParse(rows);
  if (!parsed.success) {
    throw new Error(
      `Supabase rows from ${table} failed schema validation:\n${parsed.error.message}`,
    );
  }
  return parsed.data;
}

export function createSupabaseSource(client: SupabaseClient): DataSource {
  function unwrap<T>(
    table: string,
    result: { data: T[] | null; error: { message: string } | null },
  ): T[] {
    if (result.error) {
      throw new Error(`Supabase read from ${table} failed: ${result.error.message}`);
    }
    return result.data ?? [];
  }

  /** All rows of a table, paginated past PostgREST's 1000-row response cap.
   * Ordered by the table's PK so pages are stable. */
  async function fetchAll(
    table: string,
    columns: string,
    orderBy: string[],
  ): Promise<unknown[]> {
    const rows: unknown[] = [];
    for (let from = 0; ; from += PAGE_SIZE) {
      let query = client.from(table).select(columns);
      for (const column of orderBy) query = query.order(column);
      const page = unwrap(table, await query.range(from, from + PAGE_SIZE - 1));
      rows.push(...page);
      if (page.length < PAGE_SIZE) return rows;
    }
  }

  /** The single JSONB document row of a per-user artifact table. */
  async function fetchDocument<T>(table: string, schema: z.ZodType<T>): Promise<T> {
    const rows = unwrap<{ payload: unknown }>(
      table,
      await client.from(table).select("payload").limit(1),
    );
    if (rows.length === 0) {
      throw new Error(
        `No ${table} row in Supabase. Run \`python3 scripts/publish_to_supabase.py\`.`,
      );
    }
    const parsed = schema.safeParse(rows[0].payload);
    if (!parsed.success) {
      throw new Error(
        `Supabase ${table} payload failed schema validation:\n${parsed.error.message}`,
      );
    }
    return parsed.data;
  }

  return {
    getCollectionSummary: () =>
      fetchDocument("collection_summaries", collectionSummarySchema),
    getPackEv: () => fetchDocument("pack_ev", packEvSchema),
    getRecommendations: () => fetchDocument("recommendations", recommendationsSchema),

    async getCatalog(): Promise<CatalogCard[]> {
      const [cardRows, collectionRows] = await Promise.all([
        fetchAll("cards", CARD_COLUMNS, ["set_code", "card_number"]),
        fetchAll("collections", "set_code, card_number, count", [
          "set_code",
          "card_number",
        ]),
      ]);
      const cards = parseRows("cards", cardRows, cardRowSchema);
      const collection = parseRows("collections", collectionRows, collectionRowSchema);

      // Same merge as localJsonSource's loadCatalog.
      const ownedByCoord = new Map<string, number>();
      for (const entry of collection) {
        const key = `${entry.set_code.toUpperCase()}:${entry.card_number}`;
        ownedByCoord.set(key, (ownedByCoord.get(key) ?? 0) + entry.count);
      }
      return cards.map((r) => ({
        set_code: r.set_code,
        card_number: r.card_number,
        name: r.name,
        rarity: r.rarity,
        pokemon_type: r.pokemon_type,
        card_category: r.card_category,
        trainer_subtype: r.trainer_subtype,
        stage: r.stage,
        expansion: r.expansion ?? r.set_code,
        is_ex: r.is_ex ?? false,
        owned:
          ownedByCoord.get(`${r.set_code.toUpperCase()}:${r.card_number}`) ?? 0,
        power_score: r.power_score,
        evolves_from: r.evolves_from,
      }));
    },

    async getSyncStatus(): Promise<SyncStatus> {
      const [statusRows, historyRows] = await Promise.all([
        client.from("sync_status").select("stats, review_queue, delta").limit(1),
        client
          .from("sync_history")
          .select("synced_at, added_count, added")
          .order("synced_at"),
      ]);
      const status = parseRows(
        "sync_status",
        unwrap("sync_status", statusRows),
        syncStatusRowSchema,
      )[0];
      const history = parseRows(
        "sync_history",
        unwrap("sync_history", historyRows),
        syncHistoryEntrySchema,
      );
      return {
        stats: status?.stats ?? null,
        reviewQueue: status?.review_queue ?? null,
        delta: status?.delta ?? null,
        history,
      };
    },
  };
}

/** Default source from validated env (service-role key, server-only). */
export function createDefaultSupabaseSource(): DataSource {
  if (!env.SUPABASE_URL || !env.SUPABASE_SERVICE_ROLE_KEY) {
    // env.ts already rejects this combination at startup; this narrows types.
    throw new Error("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required.");
  }
  return createSupabaseSource(
    createClient(env.SUPABASE_URL, env.SUPABASE_SERVICE_ROLE_KEY, {
      auth: { persistSession: false },
    }),
  );
}
