import { readFileSync } from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

import { verifyDataSourceContract } from "@/lib/data/contract";
import type { DataSource } from "@/lib/data/source";
import type { CatalogCard } from "@/types";

const FIXTURES = path.join(__dirname, "..", "..", "types", "__fixtures__");

function loadFixture(name: string): unknown {
  return JSON.parse(readFileSync(path.join(FIXTURES, name), "utf-8"));
}

/**
 * In-memory DataSource built from the committed fixtures + minimal valid stubs
 * for the artifacts without a fixture. Runs in CI with no pipeline artifacts.
 * Phase 4's SupabaseSource will be run through the same verifyDataSourceContract.
 */
const catalogStub: CatalogCard[] = [
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
    power_score: 42,
    evolves_from: null,
  },
];

const fixtureSource: DataSource = {
  getCollectionSummary: async () =>
    loadFixture("collection_summary.json") as never,
  getPackEv: async () => loadFixture("pack_ev.json") as never,
  getRecommendations: async () =>
    loadFixture("inferred_pack_recommendations.json") as never,
  getCatalog: async () => catalogStub,
  getSyncStatus: async () => ({
    stats: null,
    reviewQueue: null,
    delta: null,
    history: [],
  }),
};

describe("DataSource contract", () => {
  it("a conforming source passes every method", async () => {
    const verified = await verifyDataSourceContract(fixtureSource);
    expect(verified).toContain("getCollectionSummary");
    expect(verified).toContain("getCatalog");
    expect(verified.length).toBe(5);
  });

  it("catches a drifting implementation", async () => {
    const broken: DataSource = {
      ...fixtureSource,
      getCatalog: async () => [{ set_code: "A1" }] as never, // missing required fields
    };
    await expect(verifyDataSourceContract(broken)).rejects.toThrow(
      /getCatalog violated the contract/,
    );
  });
});
