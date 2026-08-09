import { describe, expect, it } from "vitest";

import { TYPE_COLORS, readableInk, typeColor } from "@/lib/domain/type-colors";

describe("typeColor", () => {
  it("falls back for unknown and missing types", () => {
    expect(typeColor("Grass")).toBe(TYPE_COLORS.Grass);
    expect(typeColor("Nonsense")).toBe(typeColor(null));
    expect(typeColor(undefined)).toBe(typeColor(null));
  });
});

describe("readableInk", () => {
  it("picks dark ink on the light types and light ink on the dark ones", () => {
    // Lightning is the palette's brightest fill and the reason this exists —
    // white text on it fails contrast.
    expect(readableInk(TYPE_COLORS.Lightning)).toBe("#141414");
    expect(readableInk(TYPE_COLORS.Darkness)).toBe("#ffffff");
    expect(readableInk(TYPE_COLORS.Water)).toBe("#ffffff");
  });

  it("handles the extremes", () => {
    expect(readableInk("#ffffff")).toBe("#141414");
    expect(readableInk("#000000")).toBe("#ffffff");
  });

  it("accepts hex with or without the leading hash", () => {
    expect(readableInk("5fb35a")).toBe(readableInk("#5fb35a"));
  });

  it("defaults to light ink when the color can't be parsed", () => {
    expect(readableInk("not-a-color")).toBe("#ffffff");
  });

  it("returns a usable ink for every type in the palette", () => {
    for (const hex of Object.values(TYPE_COLORS)) {
      expect(["#141414", "#ffffff"]).toContain(readableInk(hex));
    }
  });
});
