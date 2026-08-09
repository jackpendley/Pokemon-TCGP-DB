/**
 * Multi-expansion dex registration (game update 2026-07-29).
 *
 * "When you obtain a card that is included in multiple booster packs, it will now
 * be registered in your card dex under each of those expansions" — and
 * retroactively, for cards already obtained. So one physical copy fills several
 * dex slots.
 *
 * Copies stay stored per coord, exactly as Pokémon Zone reports them: you own
 * three cards, not six, and every quantity in the app must keep saying so. What
 * this adds is `dex_owned` — whether the slot is filled, which is true for every
 * coord in a group as soon as any one of them is held.
 *
 * Both data sources call this so local-json and Supabase stay in contract parity.
 */
export function creditPrintingGroups<
  T extends { owned: number; printing_group: string | null },
>(cards: T[]): (T & { dex_owned: boolean })[] {
  const heldGroups = new Set<string>();
  for (const c of cards) {
    if (c.owned > 0 && c.printing_group) heldGroups.add(c.printing_group);
  }
  return cards.map((c) => ({
    ...c,
    dex_owned:
      c.owned > 0 || (c.printing_group !== null && heldGroups.has(c.printing_group)),
  }));
}

/**
 * Keeps one card per printing group — the debut printing, which is the earliest
 * coord in catalog order.
 *
 * The same update split how My Cards lists a multi-expansion card: under
 * expansion order or collector number it appears in every expansion it belongs
 * to, but "for all other sorting and filtering options, the card will only be
 * displayed in the expansion in which it first appeared."
 *
 * Relies on the catalog arriving in set-then-number order, which is how
 * build_card_reference.py writes it and how both data sources preserve it.
 */
export function collapseToDebutPrinting<
  T extends { printing_group: string | null },
>(cards: T[]): T[] {
  const seen = new Set<string>();
  return cards.filter((c) => {
    if (!c.printing_group) return true;
    if (seen.has(c.printing_group)) return false;
    seen.add(c.printing_group);
    return true;
  });
}
