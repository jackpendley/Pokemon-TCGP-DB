/**
 * Expansion logo for a set, used as a pack icon and on the Sets pages. Limitless
 * hosts a logo for every TCG Pocket set (TCGdex is missing several, e.g. Crimson
 * Blaze / Eevee Grove), so it's the single reliable source:
 *   https://s3.limitlesstcg.com/pocket/sets/{SET}.webp
 * Promo sets are keyed as P-A / P-B there. A load failure still degrades to a
 * set-code chip in <SetLogo>.
 */
const LIMITLESS_SET_ID: Record<string, string> = {
  "PROMO-A": "P-A",
  "PROMO-B": "P-B",
};

export function setLogoUrl(setCode: string): string {
  const id = LIMITLESS_SET_ID[setCode] ?? setCode;
  return `https://s3.limitlesstcg.com/pocket/sets/${id}.webp`;
}
