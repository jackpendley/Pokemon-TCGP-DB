import type { CatalogCard } from "@/types";

/**
 * Card image URL. TCGdex carries 15 sets at high quality; for the sets it
 * doesn't cover (A4b, B2b, B3, B3a, B3b, PROMO-B) we fall back to the Limitless CDN,
 * which covers every set. Either way a failed load degrades to a placeholder
 * (see CardImage's onError). Patterns verified against the live CDNs:
 *   TCGdex:    https://assets.tcgdex.net/en/tcgp/{setId}/{NNN}/high.webp
 *   Limitless: https://limitlesstcg.nyc3.cdn.digitaloceanspaces.com/pocket/{set}/{set}_{NNN}_EN_SM.webp
 * with the card number zero-padded to 3 digits and promos mapped to P-A / P-B.
 */
export const TCGDEX_COVERED = new Set([
  "A1", "A1a", "A2", "A2a", "A2b", "A3", "A3a", "A3b", "A4", "A4a",
  "B1", "B1a", "B2", "B2a", "PROMO-A",
]);

export const TCGDEX_SET_ID: Record<string, string> = { "PROMO-A": "P-A" };
const LIMITLESS_SET_ID: Record<string, string> = {
  "PROMO-A": "P-A",
  "PROMO-B": "P-B",
};
const LIMITLESS_BASE =
  "https://limitlesstcg.nyc3.cdn.digitaloceanspaces.com/pocket";

/**
 * Ordered image URLs to try for a card. TCGdex is preferred where it has the set,
 * but its coverage is patchy within a set (e.g. PROMO-A only goes up to ~#73), so
 * Limitless — which carries every card — is always appended as a fallback. The
 * <CardImage> advances through these on error before showing a placeholder.
 */
export function cardImageCandidates(
  card: CatalogCard,
  size: "sm" | "lg" = "sm",
): string[] {
  const num = String(card.card_number).padStart(3, "0");
  const urls: string[] = [];

  if (TCGDEX_COVERED.has(card.set_code)) {
    const setId = TCGDEX_SET_ID[card.set_code] ?? card.set_code;
    const quality = size === "lg" ? "high" : "low";
    urls.push(`https://assets.tcgdex.net/en/tcgp/${setId}/${num}/${quality}.webp`);
  }

  const lset = LIMITLESS_SET_ID[card.set_code] ?? card.set_code;
  const file = size === "lg" ? `${lset}_${num}_EN.png` : `${lset}_${num}_EN_SM.webp`;
  urls.push(`${LIMITLESS_BASE}/${lset}/${file}`);

  return urls;
}

/** First-choice image URL (kept for non-fallback callers). */
export function cardImageUrl(card: CatalogCard, size: "sm" | "lg" = "sm"): string {
  return cardImageCandidates(card, size)[0];
}
