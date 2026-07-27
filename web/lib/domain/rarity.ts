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

// Ranks below every real tier, so descending order puts these last.
const RANK_PROMO = -1;
const RANK_UNKNOWN = -2;

/**
 * Tier rank for the post-sync reveal, where the intent is "rarest first".
 *
 * Two cases need special handling and neither is served by RARITY_ORDER, which
 * is a *display* ladder used by the pack EV model and must not be reordered:
 *
 *  - `promo` sits at the top of RARITY_ORDER (index 11, above ultra_rare), so
 *    sorting that ladder descending puts promos ahead of every chase card.
 *  - Cards with no rarity — including a delta entry whose coord missed the
 *    catalog join — should trail everything, but compareRarity's unknown-last
 *    handling inverts when its arguments are swapped to sort descending.
 *
 * Both are pushed below the real tiers here instead.
 */
export function revealRank(rarity: string | null | undefined): number {
  if (!rarity) return RANK_UNKNOWN;
  if (rarity === "promo") return RANK_PROMO;
  const i = RARITY_ORDER.indexOf(rarity);
  return i === -1 ? RANK_UNKNOWN : i;
}

/** Comparator for the reveal grid: rarest first, then promos, then unknowns. */
export function compareRevealRarity(
  a: string | null | undefined,
  b: string | null | undefined,
): number {
  return revealRank(b) - revealRank(a);
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
