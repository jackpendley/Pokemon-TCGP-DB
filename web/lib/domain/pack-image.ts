/**
 * Expansion logo for a set, used as a pack icon and on the Sets pages. Limitless
 * hosts a logo for every TCG Pocket set (TCGdex is missing several, e.g. Crimson
 * Blaze / Eevee Grove), so it's the single reliable source:
 *   https://s3.limitlesstcg.com/pocket/sets/{SET}.webp
 * A load failure still degrades to a set-code chip in <SetLogo>.
 */
export function setLogoUrl(setCode: string): string {
  return `https://s3.limitlesstcg.com/pocket/sets/${setCode}.webp`;
}
