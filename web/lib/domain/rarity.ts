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
