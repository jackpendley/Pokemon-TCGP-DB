import { readFileSync } from "node:fs";
import path from "node:path";

import type { SupabaseClient } from "@supabase/supabase-js";
import { describe, expect, it, vi } from "vitest";

vi.mock("@supabase/supabase-js", () => ({
  createClient: vi.fn(() => ({}) as unknown),
}));

import { verifyDataSourceContract } from "@/lib/data/contract";
import {
  createSupabaseSource,
  fetchOwnerSyncMeta,
  fetchRecommendationHistory,
} from "@/lib/data/supabase";
import {
  collectionSummarySchema,
  packEvSchema,
  recommendationsSchema,
} from "@/types";
import type { CatalogCard } from "@/types";

const FIXTURES = path.join(__dirname, "..", "..", "types", "__fixtures__");

function loadFixture(name: string): unknown {
  return JSON.parse(readFileSync(path.join(FIXTURES, name), "utf-8"));
}

/**
 * Minimal in-memory fake of the supabase-js fluent query builder, covering
 * only the chains supabase.ts uses. The builder is a thenable resolving to
 * PostgREST's { data, error } — awaiting it mid-chain works like the real
 * client. Exercises the real row→shape mapping code against the same fixture
 * seed data as contract.test.ts (roadmap §4.4: same shape on identical seed).
 */
type Row = Record<string, unknown>;

class FakeQueryBuilder implements PromiseLike<{ data: Row[]; error: null }> {
  private rows: Row[];
  private columns: string[] = [];

  constructor(rows: Row[]) {
    this.rows = [...rows];
  }

  select(columns: string) {
    this.columns = columns.split(",").map((c) => c.trim());
    return this;
  }

  order(column: string) {
    const key = column as keyof Row;
    this.rows.sort((a, b) =>
      (a[key] as never) < (b[key] as never)
        ? -1
        : (a[key] as never) > (b[key] as never)
          ? 1
          : 0,
    );
    return this;
  }

  limit(n: number) {
    this.rows = this.rows.slice(0, n);
    return this;
  }

  range(from: number, to: number) {
    this.rows = this.rows.slice(from, to + 1);
    return this;
  }

  then<R1, R2>(
    onfulfilled?: (value: { data: Row[]; error: null }) => R1 | PromiseLike<R1>,
    onrejected?: (reason: unknown) => R2 | PromiseLike<R2>,
  ): PromiseLike<R1 | R2> {
    const data = this.rows.map((row) =>
      Object.fromEntries(this.columns.map((c) => [c, row[c]])),
    );
    return Promise.resolve({ data, error: null }).then(onfulfilled, onrejected);
  }
}

function fakeClient(tables: Record<string, Row[]>): SupabaseClient {
  return {
    from(table: string) {
      const rows = tables[table];
      if (!rows) throw new Error(`fakeClient: unseeded table ${table}`);
      return new FakeQueryBuilder(rows);
    },
  } as unknown as SupabaseClient;
}

const collectionSummaryFixture = loadFixture("collection_summary.json");
const packEvFixture = loadFixture("pack_ev.json");
const recommendationsFixture = loadFixture(
  "inferred_pack_recommendations.json",
);

/** Same seed card as contract.test.ts's catalogStub, as a cards-table row. */
const bulbasaurRow: Row = {
  set_code: "A1",
  card_number: 1,
  name: "Bulbasaur",
  rarity: "common",
  pokemon_type: "Grass",
  card_category: "Pokemon",
  trainer_subtype: null,
  stage: "Basic",
  expansion: "Genetic Apex",
  is_ex: false,
  evolves_from: null,
  power_score: 42,
  power_score_kind: "pokemon",
  boosts: null,
};

const seededTables: Record<string, Row[]> = {
  collection_summaries: [{ payload: collectionSummaryFixture }],
  pack_ev: [{ payload: packEvFixture }],
  recommendations: [{ payload: recommendationsFixture }],
  cards: [bulbasaurRow],
  collections: [{ set_code: "A1", card_number: 1, count: 2 }],
  sync_status: [],
  sync_history: [],
};

describe("SupabaseSource", () => {
  const source = createSupabaseSource(fakeClient(seededTables));

  it("passes the shared DataSource contract", async () => {
    const verified = await verifyDataSourceContract(source);
    expect(verified.length).toBe(5);
  });

  it("returns documents identical to what localJsonSource yields", async () => {
    // localJsonSource returns schema.parse(artifact); the JSONB round-trip
    // must produce the exact same value.
    expect(await source.getCollectionSummary()).toEqual(
      collectionSummarySchema.parse(collectionSummaryFixture),
    );
    expect(await source.getPackEv()).toEqual(packEvSchema.parse(packEvFixture));
    expect(await source.getRecommendations()).toEqual(
      recommendationsSchema.parse(recommendationsFixture),
    );
  });

  it("merges cards + collections like loadCatalog", async () => {
    const expected: CatalogCard[] = [
      {
        set_code: "A1",
        card_number: 1,
        name: "Bulbasaur",
        rarity: "common",
        pokemon_type: "Grass",
        card_category: "Pokemon",
        trainer_subtype: null,
        stage: "Basic",
        expansion: "Genetic Apex",
        is_ex: false,
        owned: 2,
        dex_owned: true,
        printing_group: null,
        power_score: 42,
        power_score_kind: "pokemon",
        boosts: null,
        evolves_from: null,
      },
    ];
    expect(await source.getCatalog()).toEqual(expected);
  });

  it("paginates past the 1000-row response cap", async () => {
    const manyCards = Array.from({ length: 2500 }, (_, i) => ({
      ...bulbasaurRow,
      card_number: i + 1,
      name: `Card ${i + 1}`,
    }));
    const bigSource = createSupabaseSource(
      fakeClient({ ...seededTables, cards: manyCards }),
    );
    const catalog = await bigSource.getCatalog();
    expect(catalog.length).toBe(2500);
    expect(catalog[2499].name).toBe("Card 2500");
  });

  it("maps an empty sync_status table to the all-null contract state", async () => {
    expect(await source.getSyncStatus()).toEqual({
      stats: null,
      reviewQueue: null,
      delta: null,
      history: [],
    });
  });

  it("maps populated sync rows onto the SyncStatus shape", async () => {
    const stats = {
      fetched_at: "2026-01-01T00:00:00",
      pack_hourglasses: 10,
      wonder_hourglasses: 5,
      shop_tickets: 3,
    };
    const entry = { synced_at: "2026-01-02T03:04:05", added_count: 0, added: [] };
    const syncedSource = createSupabaseSource(
      fakeClient({
        ...seededTables,
        sync_status: [{ stats, review_queue: null, delta: null }],
        sync_history: [entry],
      }),
    );
    const status = await syncedSource.getSyncStatus();
    expect(status.stats).toEqual(stats);
    expect(status.history).toEqual([entry]);
  });

  it("surfaces PostgREST errors loudly with the table name", async () => {
    const failing = {
      from: () => ({
        select: () => ({
          limit: () =>
            Promise.resolve({ data: null, error: { message: "boom" } }),
        }),
      }),
    } as unknown as SupabaseClient;
    await expect(
      createSupabaseSource(failing).getCollectionSummary(),
    ).rejects.toThrow(/collection_summaries.*boom/);
  });

  it("fails loudly when no document has been published", async () => {
    const empty = createSupabaseSource(
      fakeClient({ ...seededTables, pack_ev: [] }),
    );
    await expect(empty.getPackEv()).rejects.toThrow(
      /publish_to_supabase\.py/,
    );
  });
});

describe("fetchOwnerSyncMeta", () => {
  it("returns published_at and the full last_run marker", async () => {
    const client = fakeClient({
      sync_status: [
        {
          published_at: "2026-07-23T19:00:00.000Z",
          last_run: {
            finished_at: "2026-07-23T18:59:40.000Z",
            outcome: "ok",
            mode: "live",
          },
        },
      ],
    });
    expect(await fetchOwnerSyncMeta(client)).toEqual({
      publishedAt: "2026-07-23T19:00:00.000Z",
      lastRun: {
        finishedAt: "2026-07-23T18:59:40.000Z",
        outcome: "ok",
        mode: "live",
      },
      catalogMisses: null,
      playerSynced: null,
      pendingSets: [],
    });
  });

  it("returns nulls when last_run is absent", async () => {
    const client = fakeClient({
      sync_status: [{ published_at: null, last_run: null }],
    });
    expect(await fetchOwnerSyncMeta(client)).toEqual({
      publishedAt: null,
      lastRun: null,
      catalogMisses: null,
      playerSynced: null,
      pendingSets: [],
    });
  });

  it("surfaces a detected but unregistered set", async () => {
    // Drives the dashboard's "new set detected" banner: PZ is serving an
    // expansion SET_REGISTRY has never heard of.
    const client = fakeClient({
      sync_status: [
        {
          published_at: "2026-08-05T00:00:00.000Z",
          last_run: null,
          pending_sets: [{ set_code: "B5", card_count: 210, copies: 240 }],
        },
      ],
    });
    const meta = await fetchOwnerSyncMeta(client);
    expect(meta.pendingSets).toEqual([
      { setCode: "B5", cardCount: 210, copies: 240 },
    ]);
  });

  it("reads a sync_status row published before pending_sets existed", async () => {
    const client = fakeClient({
      sync_status: [{ published_at: "2026-07-01T00:00:00.000Z", last_run: null }],
    });
    expect((await fetchOwnerSyncMeta(client)).pendingSets).toEqual([]);
  });

  it("surfaces cards the PZ catalog could not name", async () => {
    const client = fakeClient({
      sync_status: [
        {
          published_at: "2026-08-04T05:04:00.000Z",
          last_run: null,
          stats: {
            pack_hourglasses: 12,
            catalog_misses: { count: 41, copies: 63, card_ids: ["x"] },
          },
        },
      ],
    });
    const meta = await fetchOwnerSyncMeta(client);
    expect(meta.catalogMisses).toEqual({ count: 41, copies: 63 });
  });

  it("returns nulls when the sync_status row is missing", async () => {
    const client = fakeClient({ sync_status: [] });
    expect(await fetchOwnerSyncMeta(client)).toEqual({
      publishedAt: null,
      lastRun: null,
      catalogMisses: null,
      playerSynced: null,
      pendingSets: [],
    });
  });
});

describe("fetchRecommendationHistory", () => {
  const snap = (capturedAt: string, total: number, score: number) => ({
    captured_at: capturedAt,
    payload: {
      pack_ev: {
        meta: { collection_total: total },
        packs: [
          {
            pack_name: "Mewtwo pack",
            unified_score: score,
            pack_total_ev: score / 2,
            purchasable: true,
            blocked: false,
          },
        ],
      },
    },
  });

  it("returns entries oldest→newest with charted fields extracted", async () => {
    const client = fakeClient({
      recommendation_snapshots: [
        snap("2026-07-20T00:00:00Z", 1800, 9.0),
        snap("2026-07-10T00:00:00Z", 1700, 8.0),
      ],
    });
    const history = await fetchRecommendationHistory(client);
    expect(history.map((h) => h.capturedAt)).toEqual([
      "2026-07-10T00:00:00Z",
      "2026-07-20T00:00:00Z",
    ]);
    expect(history[0]).toEqual({
      capturedAt: "2026-07-10T00:00:00Z",
      collectionTotal: 1700,
      packs: [
        {
          packName: "Mewtwo pack",
          unifiedScore: 8.0,
          totalEv: 4.0,
          purchasable: true,
          blocked: false,
        },
      ],
    });
  });

  it("returns an empty array when there are no snapshots", async () => {
    const client = fakeClient({ recommendation_snapshots: [] });
    expect(await fetchRecommendationHistory(client)).toEqual([]);
  });
});

describe("createDefaultSupabaseSource", () => {
  it("builds the client with the service-role key (Phase 6)", async () => {
    vi.stubEnv("DATA_SOURCE", "supabase");
    vi.stubEnv("SUPABASE_URL", "https://example.supabase.co");
    vi.stubEnv("SUPABASE_SERVICE_ROLE_KEY", "service-key");
    vi.stubEnv("SUPABASE_ANON_KEY", "anon-key");
    vi.stubEnv("OWNER_USER_ID", "49aa8ac8-41ff-4ec1-9a11-2a7e4c171464");
    vi.resetModules();
    try {
      // env.ts parses process.env at module load, so import after stubbing.
      const { createDefaultSupabaseSource } = await import(
        "@/lib/data/supabase"
      );
      const { createClient } = await import("@supabase/supabase-js");
      createDefaultSupabaseSource();
      expect(createClient).toHaveBeenCalledWith(
        "https://example.supabase.co",
        "service-key",
        { auth: { persistSession: false } },
      );
    } finally {
      vi.unstubAllEnvs();
      vi.resetModules();
    }
  });
});
