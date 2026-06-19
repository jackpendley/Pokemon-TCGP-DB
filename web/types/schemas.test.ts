import { readFileSync } from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

import { collectionSummarySchema } from "@/types/collection-summary";
import { packEvSchema } from "@/types/pack-ev";
import { recommendationsSchema } from "@/types/recommendations";

const FIXTURES = path.join(__dirname, "__fixtures__");

function loadFixture(name: string): unknown {
  return JSON.parse(readFileSync(path.join(FIXTURES, name), "utf-8"));
}

/**
 * TS mirror of tests/test_output_contract.py: the committed fixtures are frozen
 * pipeline snapshots, so these run deterministically in CI without a pipeline
 * run and fail if a Zod schema drifts from the real artifact shape.
 */
describe("artifact schemas parse real fixtures", () => {
  it("validates pack_ev.json", () => {
    const result = packEvSchema.safeParse(loadFixture("pack_ev.json"));
    expect(result.success, result.error?.message).toBe(true);
  });

  it("validates inferred_pack_recommendations.json", () => {
    const result = recommendationsSchema.safeParse(
      loadFixture("inferred_pack_recommendations.json"),
    );
    expect(result.success, result.error?.message).toBe(true);
  });

  it("validates collection_summary.json", () => {
    const result = collectionSummarySchema.safeParse(
      loadFixture("collection_summary.json"),
    );
    expect(result.success, result.error?.message).toBe(true);
  });
});
