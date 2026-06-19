import type { CatalogCard } from "@/types";

/**
 * TCGdex hot-link image URL for a card, or null when TCGdex doesn't carry the
 * set (A4b, B2b, B3, B3a, PROMO-B). Pattern verified against the live CDN:
 *   https://assets.tcgdex.net/en/tcgp/{setId}/{NNN}/high.webp
 * where the card number is zero-padded to 3 digits and PROMO-A maps to "P-A".
 */
const TCGDEX_COVERED = new Set([
  "A1", "A1a", "A2", "A2a", "A2b", "A3", "A3a", "A3b", "A4", "A4a",
  "B1", "B1a", "B2", "B2a", "PROMO-A",
]);

const TCGDEX_SET_ID: Record<string, string> = { "PROMO-A": "P-A" };

export function cardImageUrl(card: CatalogCard): string | null {
  if (!TCGDEX_COVERED.has(card.set_code)) return null;
  const setId = TCGDEX_SET_ID[card.set_code] ?? card.set_code;
  const num = String(card.card_number).padStart(3, "0");
  return `https://assets.tcgdex.net/en/tcgp/${setId}/${num}/high.webp`;
}
