import { describe, expect, it } from "vitest";

import {
  collapseToDebutPrinting,
  creditPrintingGroups,
} from "@/lib/domain/printing-groups";

/** Minimal shape — the helpers only read `owned` and `printing_group`. */
function coord(
  set_code: string,
  card_number: number,
  owned: number,
  printing_group: string | null,
) {
  return { set_code, card_number, owned, printing_group };
}

describe("creditPrintingGroups", () => {
  it("fills every dex slot in a group from a single held copy", () => {
    // One Cubone, obtained from Genetic Apex, now registers under A4b too.
    const out = creditPrintingGroups([
      coord("A1", 151, 1, "g0042"),
      coord("A4b", 194, 0, "g0042"),
      coord("A4b", 195, 0, "g0042"),
    ]);

    expect(out.map((c) => c.dex_owned)).toEqual([true, true, true]);
  });

  it("never inflates copy counts", () => {
    // You own one card, not three: quantity totals must not move.
    const out = creditPrintingGroups([
      coord("A1", 151, 1, "g0042"),
      coord("A4b", 194, 0, "g0042"),
      coord("A4b", 195, 0, "g0042"),
    ]);

    expect(out.reduce((n, c) => n + c.owned, 0)).toBe(1);
  });

  it("leaves an unheld group entirely unowned", () => {
    const out = creditPrintingGroups([
      coord("A1", 151, 0, "g0042"),
      coord("A4b", 194, 0, "g0042"),
    ]);

    expect(out.every((c) => !c.dex_owned)).toBe(true);
  });

  it("does not leak ownership between different groups", () => {
    const out = creditPrintingGroups([
      coord("A1", 1, 2, "g0001"),
      coord("A4b", 1, 0, "g0001"),
      coord("A1", 2, 0, "g0002"),
      coord("A4b", 3, 0, "g0002"),
    ]);

    expect(out.map((c) => c.dex_owned)).toEqual([true, true, false, false]);
  });

  it("treats ungrouped cards as owned only by their own count", () => {
    // printing_group null must never join the "held" set — otherwise every
    // single-printing card in the catalog would credit every other one.
    const out = creditPrintingGroups([
      coord("B4", 1, 3, null),
      coord("B4", 2, 0, null),
    ]);

    expect(out.map((c) => c.dex_owned)).toEqual([true, false]);
  });
});

describe("collapseToDebutPrinting", () => {
  it("keeps only the first printing of each group", () => {
    const kept = collapseToDebutPrinting([
      coord("A1", 151, 1, "g0042"),
      coord("A4b", 194, 0, "g0042"),
      coord("A4b", 195, 0, "g0042"),
    ]);

    expect(kept).toHaveLength(1);
    expect(kept[0].set_code).toBe("A1");
  });

  it("keeps every ungrouped card", () => {
    const kept = collapseToDebutPrinting([
      coord("B4", 1, 0, null),
      coord("B4", 2, 0, null),
      coord("B4", 3, 0, null),
    ]);

    expect(kept).toHaveLength(3);
  });

  it("preserves input order", () => {
    const kept = collapseToDebutPrinting([
      coord("A1", 1, 0, "g0001"),
      coord("A1", 2, 0, null),
      coord("A4b", 1, 0, "g0001"),
      coord("A1", 3, 0, null),
    ]);

    expect(kept.map((c) => c.card_number)).toEqual([1, 2, 3]);
  });
});
