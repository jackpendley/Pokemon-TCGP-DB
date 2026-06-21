import { TCGDEX_COVERED, TCGDEX_SET_ID } from "@/lib/domain/card-image";

/**
 * Expansion logo used as a pack icon. TCGdex hosts per-set logos but not
 * individual booster art, and PZ's CDN blocks hot-linking — so the set logo is
 * the most reliable icon, shared by every pack in the same expansion. Uncovered
 * sets (A4b, B2b, B3, B3a) return null → the PackLogo falls back to the set code.
 *   https://assets.tcgdex.net/en/tcgp/{setId}/logo.webp
 */
export function packLogoUrl(setCode: string): string | null {
  if (!TCGDEX_COVERED.has(setCode)) return null;
  const id = TCGDEX_SET_ID[setCode] ?? setCode;
  return `https://assets.tcgdex.net/en/tcgp/${id}/logo.webp`;
}
