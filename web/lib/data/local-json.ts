import { readFile, stat } from "node:fs/promises";
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

/**
 * Artifacts are immutable between pipeline runs, so parse + Zod results are
 * memoized on file mtime+size: one fs.stat per read replaces re-parsing and
 * re-validating multi-MB JSON on every navigation. Cached values are shared
 * across requests — treat them as read-only.
 */
const artifactCache = new Map<
  string,
  { mtimeMs: number; size: number; value: unknown }
>();

/** True only for "file absent" — other fs failures (EACCES, EISDIR…) must
 * surface loudly rather than read as "no sync data yet". */
function isFileAbsent(err: unknown): boolean {
  return (
    typeof err === "object" &&
    err !== null &&
    "code" in err &&
    (err.code === "ENOENT" || err.code === "ENOTDIR")
  );
}

async function readValidated<T>(
  full: string,
  file: string,
  schema: ZodType<T>,
): Promise<T> {
  const s = await stat(full); // fs errors (ENOENT…) propagate to callers
  const hit = artifactCache.get(full);
  if (hit && hit.mtimeMs === s.mtimeMs && hit.size === s.size) {
    return hit.value as T;
  }
  const raw = await readFile(full, "utf-8");
  const parsed = schema.safeParse(JSON.parse(raw));
  if (!parsed.success) {
    throw new Error(
      `Pipeline artifact ${file} failed schema validation:\n${parsed.error.message}`,
    );
  }
  artifactCache.set(full, { mtimeMs: s.mtimeMs, size: s.size, value: parsed.data });
  return parsed.data;
}

/** Like readArtifact but returns null if the (gitignored) file is absent. */
async function readOptional<T>(
  dir: string,
  file: string,
  schema: ZodType<T>,
): Promise<T | null> {
  try {
    return await readValidated(path.join(dir, file), file, schema);
  } catch (err) {
    if (isFileAbsent(err)) return null;
    throw err; // schema failures still surface loudly
  }
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
  try {
    return await readValidated(full, file, schema);
  } catch (err) {
    if (isFileAbsent(err)) {
      throw new Error(
        `Pipeline artifact not found: ${full}. Run \`python3 scripts/run_recommendations.py --skip-sync\` in the repo root, or set PIPELINE_ROOT.`,
      );
    }
    throw err;
  }
}

/** Rebuilt only when one of its three source artifacts re-parses (see cache above). */
let catalogMemo: {
  ref: unknown;
  coll: unknown;
  power: unknown;
  value: CatalogCard[];
} | null = null;

async function loadCatalog(): Promise<CatalogCard[]> {
  const [ref, coll, power] = await Promise.all([
    readArtifact(REFERENCE_DIR, "card_reference.json", cardReferenceFileSchema),
    readArtifact(CURRENT_DIR, "collection_normalized.json", collectionFileSchema),
    readOptional(REFERENCE_DIR, "card_power_scores.json", powerScoresFileSchema),
  ]);

  if (
    catalogMemo &&
    catalogMemo.ref === ref &&
    catalogMemo.coll === coll &&
    catalogMemo.power === power
  ) {
    return catalogMemo.value;
  }

  const ownedByCoord = new Map<string, number>();
  for (const entry of coll.collection) {
    const key = `${entry.set_code.toUpperCase()}:${entry.card_number}`;
    ownedByCoord.set(key, (ownedByCoord.get(key) ?? 0) + entry.count);
  }
  const scores = power?.scores ?? {};

  const value: CatalogCard[] = ref.records.map((r) => ({
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
    power_score_kind:
      scores[`${r.set_code}:${r.card_number}`]?.score_kind ?? null,
    evolves_from: r.evolves_from ?? null,
  }));
  catalogMemo = { ref, coll, power, value };
  return value;
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
