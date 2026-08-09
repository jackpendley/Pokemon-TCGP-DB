import type { CatalogCard } from "@/types";

/**
 * Base species key for grouping printings: strips a leading "Mega " and a trailing
 * " ex" so `Mega Venusaur ex` / `Venusaur ex` / `Venusaur` all collapse to
 * `Venusaur`. (Mirrors the `Mega ` rule in `lib/domain/card.ts`.)
 */
export function baseSpecies(name: string): string {
  let s = name.trim();
  if (s.startsWith("Mega ")) s = s.slice(5);
  if (s.toLowerCase().endsWith(" ex")) s = s.slice(0, -3);
  return s.trim();
}

export interface EvolutionIndex {
  /** Line members in the *same set* as `card` (excludes `card`). */
  setEvolution(card: CatalogCard): CatalogCard[];
  /** Other printings of the *same* species, all sets (excludes `card`). */
  otherVersions(card: CatalogCard): CatalogCard[];
  /** Every card in the whole evolution line, all sets (excludes `card`). */
  relatedCards(card: CatalogCard): CatalogCard[];
}

const cache = new WeakMap<CatalogCard[], EvolutionIndex>();

function sortCards(cards: CatalogCard[]): CatalogCard[] {
  return [...cards].sort(
    (a, b) =>
      Number(b.dex_owned) - Number(a.dex_owned) ||
      a.set_code.localeCompare(b.set_code) ||
      a.card_number - b.card_number,
  );
}

/**
 * Builds evolution families from each card's `evolves_from` link (union-find over
 * base-species names → connected components). Memoized by catalog reference.
 */
export function buildEvolution(catalog: CatalogCard[]): EvolutionIndex {
  const hit = cache.get(catalog);
  if (hit) return hit;

  const bySpecies = new Map<string, CatalogCard[]>();
  for (const c of catalog) {
    const s = baseSpecies(c.name);
    const list = bySpecies.get(s);
    if (list) list.push(c);
    else bySpecies.set(s, [c]);
  }

  // Union-find over species.
  const parent = new Map<string, string>();
  const find = (x: string): string => {
    if (!parent.has(x)) parent.set(x, x);
    let root = x;
    while (parent.get(root) !== root) root = parent.get(root)!;
    let cur = x;
    while (parent.get(cur) !== root) {
      const nxt = parent.get(cur)!;
      parent.set(cur, root);
      cur = nxt;
    }
    return root;
  };
  const union = (a: string, b: string) => {
    const ra = find(a);
    const rb = find(b);
    if (ra !== rb) parent.set(ra, rb);
  };

  for (const s of bySpecies.keys()) find(s);
  for (const c of catalog) {
    if (c.evolves_from) union(baseSpecies(c.name), baseSpecies(c.evolves_from));
  }

  const membersByRoot = new Map<string, string[]>();
  for (const s of bySpecies.keys()) {
    const r = find(s);
    const list = membersByRoot.get(r);
    if (list) list.push(s);
    else membersByRoot.set(r, [s]);
  }
  const familyCards = (species: string): CatalogCard[] =>
    (membersByRoot.get(find(species)) ?? [species]).flatMap(
      (s) => bySpecies.get(s) ?? [],
    );
  const isSame = (a: CatalogCard, b: CatalogCard) =>
    a.set_code === b.set_code && a.card_number === b.card_number;

  const index: EvolutionIndex = {
    setEvolution: (card) =>
      sortCards(
        familyCards(baseSpecies(card.name)).filter(
          (c) => c.set_code === card.set_code && !isSame(c, card),
        ),
      ),
    otherVersions: (card) =>
      sortCards(
        (bySpecies.get(baseSpecies(card.name)) ?? []).filter(
          (c) => !isSame(c, card),
        ),
      ),
    relatedCards: (card) =>
      sortCards(
        familyCards(baseSpecies(card.name)).filter((c) => !isSame(c, card)),
      ),
  };
  cache.set(catalog, index);
  return index;
}
