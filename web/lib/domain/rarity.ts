/**
 * "Base set" rarities — the standard pull tiers, matching build_pack_ev.py's
 * base_* definition. Everything else (illustration/super/special-illustration
 * rare, immersive, ultra/shiny, promo) is a secret/chase card excluded from a
 * "base set" completion count.
 */
export const BASE_RARITIES = new Set([
  "common",
  "uncommon",
  "rare",
  "double_rare",
]);

export function isBaseRarity(rarity: string | null): boolean {
  return rarity != null && BASE_RARITIES.has(rarity);
}

/**
 * Rarity symbol descriptor mirroring the in-app visual language (1–4 diamonds,
 * 1–3 stars, crown, shiny stars). Rendered as composed icons by
 * components/dashboard/rarity-symbol.tsx rather than bundling game art.
 * Super Rare and Special Illustration Rare share the ★★ tier (see build_pack_ev.py).
 */
export type RaritySymbol = {
  kind: "diamond" | "star" | "crown" | "sparkle" | "promo";
  count: number;
};

const RARITY_SYMBOLS: Record<string, RaritySymbol> = {
  common: { kind: "diamond", count: 1 },
  uncommon: { kind: "diamond", count: 2 },
  rare: { kind: "diamond", count: 3 },
  double_rare: { kind: "diamond", count: 4 },
  illustration_rare: { kind: "star", count: 1 },
  super_rare: { kind: "star", count: 2 },
  special_illustration_rare: { kind: "star", count: 2 },
  immersive: { kind: "star", count: 3 },
  shiny_rare: { kind: "sparkle", count: 1 },
  shiny_super_rare: { kind: "sparkle", count: 2 },
  ultra_rare: { kind: "crown", count: 1 },
  promo: { kind: "promo", count: 1 },
};

/** Display order, low → high tier (promo last). */
export const RARITY_ORDER: string[] = [
  "common",
  "uncommon",
  "rare",
  "double_rare",
  "illustration_rare",
  "super_rare",
  "special_illustration_rare",
  "immersive",
  "shiny_rare",
  "shiny_super_rare",
  "ultra_rare",
  "promo",
];

export function raritySymbol(rarity: string | null): RaritySymbol {
  return RARITY_SYMBOLS[rarity ?? ""] ?? { kind: "diamond", count: 1 };
}

/** Sort known rarities by tier; unknown rarities fall to the end alphabetically. */
export function compareRarity(a: string, b: string): number {
  const ia = RARITY_ORDER.indexOf(a);
  const ib = RARITY_ORDER.indexOf(b);
  if (ia === -1 && ib === -1) return a.localeCompare(b);
  if (ia === -1) return 1;
  if (ib === -1) return -1;
  return ia - ib;
}
