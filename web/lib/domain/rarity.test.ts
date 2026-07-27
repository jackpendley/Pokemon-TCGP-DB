import { describe, expect, it } from "vitest";

import {
  RARITY_ORDER,
  compareRarity,
  compareRevealRarity,
  revealRank,
} from "@/lib/domain/rarity";

/** Sort helper mirroring how RevealGrid orders a sync's additions. */
const sortForReveal = (rarities: (string | null)[]) =>
  [...rarities].sort(compareRevealRarity);

describe("revealRank", () => {
  it("ranks real tiers by their display ladder position", () => {
    expect(revealRank("common")).toBeLessThan(revealRank("rare"));
    expect(revealRank("rare")).toBeLessThan(revealRank("immersive"));
    expect(revealRank("immersive")).toBeLessThan(revealRank("ultra_rare"));
  });

  it("ranks promo below every real tier", () => {
    // Regression: promo is index 11 in RARITY_ORDER — above ultra_rare — so a
    // plain descending sort of that ladder led the grid with promos.
    expect(RARITY_ORDER.indexOf("promo")).toBeGreaterThan(
      RARITY_ORDER.indexOf("ultra_rare"),
    );
    expect(revealRank("promo")).toBeLessThan(revealRank("common"));
  });

  it("ranks missing and unrecognised rarities last of all", () => {
    for (const missing of [null, undefined, ""]) {
      expect(revealRank(missing)).toBeLessThan(revealRank("promo"));
    }
    expect(revealRank("not_a_rarity")).toBeLessThan(revealRank("promo"));
  });
});

describe("compareRevealRarity", () => {
  it("puts the rarest card first", () => {
    expect(sortForReveal(["common", "ultra_rare", "rare"])).toEqual([
      "ultra_rare",
      "rare",
      "common",
    ]);
  });

  it("sends promos to the back rather than the front", () => {
    expect(sortForReveal(["promo", "ultra_rare", "common"])).toEqual([
      "ultra_rare",
      "common",
      "promo",
    ]);
  });

  it("sends cards with no rarity to the very back", () => {
    // A delta entry whose coord missed the catalog join arrives as null and
    // used to sort ahead of every chase card.
    expect(sortForReveal([null, "ultra_rare", "promo", "common"])).toEqual([
      "ultra_rare",
      "common",
      "promo",
      null,
    ]);
  });

  it("keeps promos ahead of unknowns", () => {
    expect(sortForReveal([null, "promo"])).toEqual(["promo", null]);
  });
});

describe("compareRarity", () => {
  it("is unchanged — the display ladder still ends with promo", () => {
    // Pinned because the pack EV model and the rarity breakdowns depend on it;
    // the reveal ordering had to be fixed without touching this.
    expect([...RARITY_ORDER].sort(compareRarity)).toEqual(RARITY_ORDER);
  });
});
