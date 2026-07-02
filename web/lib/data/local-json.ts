import { readFile } from "node:fs/promises";
import path from "node:path";

import type { ZodType } from "zod";

import { env } from "@/lib/env";
import {
  cardReferenceFileSchema,
  collectionFileSchema,
  collectionSummarySchema,
  packEvSchema,
  playerStatsSchema,
  powerScoresFileSchema,
  recommendationsSchema,
  reviewQueueSchema,
  syncDeltaSchema,
  syncHistoryFileSchema,
} from "@/types";
import type { CatalogCard, SyncStatus } from "@/types";
import type { DataSource } from "@/lib/data/source";

const CURRENT_DIR = path.join(env.PIPELINE_ROOT, "data", "current");
const REFERENCE_DIR = path.join(env.PIPELINE_ROOT, "data", "reference");
const SYNC_DIR = path.join(env.PIPELINE_ROOT, "data", "sync");

/** Like readArtifact but returns null if the (gitignored) file is absent. */
async function readOptional<T>(
  dir: string,
  file: string,
  schema: ZodType<T>,
): Promise<T | null> {
  let raw: string;
  try {
    raw = await readFile(path.join(dir, file), "utf-8");
  } catch {
    return null;
  }
  const parsed = schema.safeParse(JSON.parse(raw));
  if (!parsed.success) {
    throw new Error(`${file} failed schema validation:\n${parsed.error.message}`);
  }
  return parsed.data;
}

/**
 * Reads + validates a pipeline artifact. Validation at this boundary means a
 * changed/corrupt contract throws here with a clear message instead of
 * surfacing as `undefined` deep in the UI.
 */
async function readArtifact<T>(
  dir: string,
  file: string,
  schema: ZodType<T>,
): Promise<T> {
  const full = path.join(dir, file);
  let raw: string;
  try {
    raw = await readFile(full, "utf-8");
  } catch {
    throw new Error(
      `Pipeline artifact not found: ${full}. Run \`python3 scripts/run_recommendations.py --skip-sync\` in the repo root, or set PIPELINE_ROOT.`,
    );
  }
  const parsed = schema.safeParse(JSON.parse(raw));
  if (!parsed.success) {
    throw new Error(
      `Pipeline artifact ${file} failed schema validation:\n${parsed.error.message}`,
    );
  }
  return parsed.data;
}

async function loadCatalog(): Promise<CatalogCard[]> {
  const [ref, coll, power] = await Promise.all([
    readArtifact(REFERENCE_DIR, "card_reference.json", cardReferenceFileSchema),
    readArtifact(CURRENT_DIR, "collection_normalized.json", collectionFileSchema),
    readOptional(REFERENCE_DIR, "card_power_scores.json", powerScoresFileSchema),
  ]);

  const ownedByCoord = new Map<string, number>();
  for (const entry of coll.collection) {
    const key = `${entry.set_code.toUpperCase()}:${entry.card_number}`;
    ownedByCoord.set(key, (ownedByCoord.get(key) ?? 0) + entry.count);
  }
  const scores = power?.scores ?? {};

  return ref.records.map((r) => ({
    set_code: r.set_code,
    card_number: r.card_number,
    name: r.name,
    rarity: r.rarity,
    pokemon_type: r.pokemon_type,
    card_category: r.card_category,
    trainer_subtype: r.trainer_subtype ?? null,
    stage: r.stage ?? null,
    expansion: r.expansion ?? r.set_code,
    is_ex: r.is_ex ?? false,
    owned: ownedByCoord.get(`${r.set_code.toUpperCase()}:${r.card_number}`) ?? 0,
    power_score: scores[`${r.set_code}:${r.card_number}`]?.power_score ?? null,
  }));
}

export const localJsonSource: DataSource = {
  getCollectionSummary: () =>
    readArtifact(CURRENT_DIR, "collection_summary.json", collectionSummarySchema),
  getPackEv: () => readArtifact(CURRENT_DIR, "pack_ev.json", packEvSchema),
  getRecommendations: () =>
    readArtifact(
      CURRENT_DIR,
      "inferred_pack_recommendations.json",
      recommendationsSchema,
    ),
  getCatalog: loadCatalog,
  getSyncStatus: async (): Promise<SyncStatus> => {
    const [stats, reviewQueue, delta, historyFile] = await Promise.all([
      readOptional(SYNC_DIR, "player_stats.json", playerStatsSchema),
      readOptional(SYNC_DIR, "sync_review_queue.json", reviewQueueSchema),
      readOptional(SYNC_DIR, "last_sync_delta.json", syncDeltaSchema),
      readOptional(SYNC_DIR, "sync_history.json", syncHistoryFileSchema),
    ]);
    return { stats, reviewQueue, delta, history: historyFile?.entries ?? [] };
  },
};
