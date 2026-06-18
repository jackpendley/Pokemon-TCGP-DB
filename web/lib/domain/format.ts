/**
 * Pure presentation helpers. No EV recomputation — these only format values the
 * Python pipeline already produced.
 */

export function formatNumber(n: number): string {
  return n.toLocaleString("en-US");
}

export function formatEv(n: number, digits = 2): string {
  return n.toFixed(digits);
}

export function formatPercent(ratio: number, digits = 0): string {
  return `${(ratio * 100).toFixed(digits)}%`;
}

/** Human label for a raw rarity/confidence token like "ultra_rare". */
export function titleCase(token: string | null | undefined): string {
  if (!token) return "—";
  return token
    .split(/[_\s]+/)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

/** URL-safe slug for a pack name (used for /packs/[slug] routing). */
export function packSlug(packName: string): string {
  return packName
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}
