import { afterEach, describe, expect, it, vi } from "vitest";

/**
 * The cache-tag contract.
 *
 * Under Vitest the `"use cache"` directive is an inert string, so each wrapper
 * simply delegates. That's exactly what makes this testable: we can assert the
 * *tagging* is consistent — every pipeline read carries the one DATA_TAG, so a
 * single revalidateTag after a publish invalidates all of them, and decks carry
 * a separate tag so a publish can't wipe them and a deck save can't wipe the
 * catalog.
 */
const { cacheTag, cacheLife, source, fetchRecommendationHistory, fetchDecks, fetchDeck } =
  vi.hoisted(() => ({
    cacheTag: vi.fn(),
    cacheLife: vi.fn(),
    source: {
      getCatalog: vi.fn(async () => "catalog"),
      getPackEv: vi.fn(async () => "packEv"),
      getRecommendations: vi.fn(async () => "recs"),
      getCollectionSummary: vi.fn(async () => "summary"),
      getSyncStatus: vi.fn(async () => "sync"),
    },
    fetchRecommendationHistory: vi.fn(async () => "history"),
    fetchDecks: vi.fn(async () => "decks"),
    fetchDeck: vi.fn(async () => "deck"),
  }));

vi.mock("next/cache", () => ({ cacheTag, cacheLife }));
vi.mock("@/lib/data", () => ({ dataSource: source }));
vi.mock("@/lib/data/supabase", () => ({ fetchRecommendationHistory }));
vi.mock("@/lib/data/decks", () => ({ fetchDecks, fetchDeck }));
// Recommendation history only exists in supabase mode; the local-json
// short-circuit gets its own test below.
const { env } = vi.hoisted(() => ({
  env: { PIPELINE_ROOT: "/tmp", DATA_SOURCE: "supabase" as string },
}));
vi.mock("@/lib/env", () => ({ env }));

import {
  DATA_TAG,
  DECKS_TAG,
  getCachedCatalog,
  getCachedCollectionSummary,
  getCachedDeck,
  getCachedDecks,
  getCachedPackEv,
  getCachedRecommendationHistory,
  getCachedRecommendations,
  getCachedSyncStatus,
} from "@/lib/data/cached";

afterEach(() => vi.clearAllMocks());

/** Every wrapper, with the tag it must carry and what it must delegate to. */
const PIPELINE_READS = [
  ["getCachedCatalog", getCachedCatalog, source.getCatalog, "catalog"],
  ["getCachedPackEv", getCachedPackEv, source.getPackEv, "packEv"],
  [
    "getCachedRecommendations",
    getCachedRecommendations,
    source.getRecommendations,
    "recs",
  ],
  [
    "getCachedCollectionSummary",
    getCachedCollectionSummary,
    source.getCollectionSummary,
    "summary",
  ],
  ["getCachedSyncStatus", getCachedSyncStatus, source.getSyncStatus, "sync"],
  [
    "getCachedRecommendationHistory",
    getCachedRecommendationHistory,
    fetchRecommendationHistory,
    "history",
  ],
] as const;

describe("pipeline data wrappers", () => {
  it.each(PIPELINE_READS)(
    "%s tags DATA_TAG, lives forever, and delegates",
    async (_name, wrapper, delegate, expected) => {
      await expect(wrapper()).resolves.toBe(expected);
      expect(delegate).toHaveBeenCalledTimes(1);
      expect(cacheTag).toHaveBeenCalledWith(DATA_TAG);
      expect(cacheLife).toHaveBeenCalledWith("max");
    },
  );

  it("uses one shared tag, so a single publish invalidates everything", async () => {
    for (const [, wrapper] of PIPELINE_READS) await wrapper();
    const tags = new Set(cacheTag.mock.calls.map(([tag]) => tag));
    expect(tags).toEqual(new Set([DATA_TAG]));
    expect(cacheTag).toHaveBeenCalledTimes(PIPELINE_READS.length);
  });
});

describe("recommendation history", () => {
  it("skips the Supabase read entirely in local-json mode", async () => {
    env.DATA_SOURCE = "local-json";
    try {
      await expect(getCachedRecommendationHistory()).resolves.toEqual([]);
      expect(fetchRecommendationHistory).not.toHaveBeenCalled();
      // Still tagged, so the empty result is invalidated like everything else.
      expect(cacheTag).toHaveBeenCalledWith(DATA_TAG);
    } finally {
      env.DATA_SOURCE = "supabase";
    }
  });
});

describe("deck wrappers", () => {
  it("getCachedDecks tags DECKS_TAG and delegates", async () => {
    await expect(getCachedDecks()).resolves.toBe("decks");
    expect(fetchDecks).toHaveBeenCalledTimes(1);
    expect(cacheTag).toHaveBeenCalledWith(DECKS_TAG);
    expect(cacheLife).toHaveBeenCalledWith("max");
  });

  it("getCachedDeck passes the id through and tags DECKS_TAG", async () => {
    await expect(getCachedDeck("abc")).resolves.toBe("deck");
    expect(fetchDeck).toHaveBeenCalledWith("abc");
    expect(cacheTag).toHaveBeenCalledWith(DECKS_TAG);
  });

  it("keeps decks off DATA_TAG", async () => {
    // A publish must not invalidate user-authored decks, and saving a deck must
    // not dump the catalog cache.
    await getCachedDecks();
    await getCachedDeck("abc");
    const tags = new Set(cacheTag.mock.calls.map(([tag]) => tag));
    expect(tags).toEqual(new Set([DECKS_TAG]));
    expect(DECKS_TAG).not.toBe(DATA_TAG);
  });
});
