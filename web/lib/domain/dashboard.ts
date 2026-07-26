import type { CatalogCard, PackEvRecord, SyncDeltaEntry } from "@/types";
import { isMegaEx } from "@/lib/domain/card";
import { isBaseRarity } from "@/lib/domain/rarity";

/**
 * Pure derivations behind the dashboard.
 *
 * These live here rather than in app/page.tsx because the dashboard streams as
 * several independent Suspense boundaries, and more than one of them needs the
 * same derivation (the catalog index feeds both "what to open next" and the sync
 * join; set totals feed both the reveal popup and history). Keeping them pure
 * also makes them unit-testable without rendering.
 */

export type CoordIndex = Map<string, CatalogCard>;

const coordKey = (setCode: string, cardNumber: string | number) =>
  `${setCode}:${cardNumber}`;

/** Catalog keyed by "SET:number" — the join key used by pack targets and sync deltas. */
export function indexByCoord(catalog: CatalogCard[]): CoordIndex {
  return new Map(catalog.map((c) => [coordKey(c.set_code, c.card_number), c]));
}

/**
 * Sync delta entries carry a nullable set_code/card_number (an unresolved coord),
 * so this takes the loose shape and returns null rather than forcing callers to
 * narrow at every site.
 */
export function lookupCoord(
  index: CoordIndex,
  setCode: string | null,
  cardNumber: string | number | null,
): CatalogCard | null {
  if (setCode == null || cardNumber == null) return null;
  return index.get(coordKey(setCode, cardNumber)) ?? null;
}

export interface CompletionStat {
  owned: number;
  total: number;
}

/** Unique-card completion, overall and restricted to base rarities. */
export function completionStats(catalog: CatalogCard[]): {
  total: CompletionStat;
  base: CompletionStat;
} {
  const baseCards = catalog.filter((c) => isBaseRarity(c.rarity));
  return {
    total: {
      owned: catalog.filter((c) => c.owned > 0).length,
      total: catalog.length,
    },
    base: {
      owned: baseCards.filter((c) => c.owned > 0).length,
      total: baseCards.length,
    },
  };
}

/** Mega-ex counts: copies held, uniques held, uniques that exist. */
export function megaStats(catalog: CatalogCard[]): {
  quantity: number;
  unique: number;
  total: number;
} {
  const mega = catalog.filter(isMegaEx);
  return {
    quantity: mega.reduce((n, c) => n + c.owned, 0),
    unique: mega.filter((c) => c.owned > 0).length,
    total: mega.length,
  };
}

export interface CountBucket {
  key: string;
  owned: number;
  total: number;
}

/** Unique owned / total per rarity, in the given rarity order. */
export function rarityBreakdown(
  catalog: CatalogCard[],
  compare: (a: string, b: string) => number,
): CountBucket[] {
  return tally(catalog, (c) => c.rarity ?? "unknown").sort((a, b) =>
    compare(a.key, b.key),
  );
}

const STAGE_ORDER = ["Basic", "Stage1", "Stage2", "Stage3"];
const stageRank = (s: string) =>
  STAGE_ORDER.indexOf(s) === -1 ? 99 : STAGE_ORDER.indexOf(s);

/** Unique owned / total per evolution stage, in play order. Cards with no stage are skipped. */
export function stageBreakdown(catalog: CatalogCard[]): CountBucket[] {
  return tally(
    catalog.filter((c) => c.stage),
    (c) => c.stage!,
  ).sort((a, b) => stageRank(a.key) - stageRank(b.key));
}

function tally(
  catalog: CatalogCard[],
  keyOf: (c: CatalogCard) => string,
): CountBucket[] {
  const by = new Map<string, CountBucket>();
  for (const c of catalog) {
    const key = keyOf(c);
    const e = by.get(key) ?? { key, owned: 0, total: 0 };
    e.total += 1;
    if (c.owned > 0) e.owned += 1;
    by.set(key, e);
  }
  return [...by.values()];
}

/**
 * Owned-quantity distribution by Pokémon type, plus the Pokémon/Trainer split.
 * Derived from the catalog rather than the collection summary so it matches the
 * /cards type filter and has no "Unknown" bucket (some collection.json entries
 * miscategorize Trainers as Pokémon).
 */
export function typeBreakdown(catalog: CatalogCard[]): {
  byPokemonType: Record<string, number>;
  pokemonQuantity: number;
  trainerQuantity: number;
} {
  const byPokemonType: Record<string, number> = {};
  let pokemonQuantity = 0;
  let trainerQuantity = 0;
  for (const c of catalog) {
    if (c.owned <= 0) continue;
    if (c.pokemon_type)
      byPokemonType[c.pokemon_type] =
        (byPokemonType[c.pokemon_type] ?? 0) + c.owned;
    if (c.card_category === "Pokemon") pokemonQuantity += c.owned;
    else if (c.card_category === "Trainer") trainerQuantity += c.owned;
  }
  return { byPokemonType, pokemonQuantity, trainerQuantity };
}

export interface SetTotal {
  total: number;
  owned: number;
  expansion: string;
}

/** Current owned/total per set — the denominator for each sync's progress bars. */
export function buildSetTotals(catalog: CatalogCard[]): Map<string, SetTotal> {
  const totals = new Map<string, SetTotal>();
  for (const c of catalog) {
    const s = totals.get(c.set_code) ?? {
      total: 0,
      owned: 0,
      expansion: c.expansion,
    };
    s.total += 1;
    if (c.owned > 0) s.owned += 1;
    totals.set(c.set_code, s);
  }
  return totals;
}

export interface SetProgress {
  set_code: string;
  expansion: string;
  total: number;
  after: number;
  before: number;
  gained: number;
}

/**
 * Per-sync set progress (sets that gained, ranked by gain) with a before→after
 * fill. `ownedAfter` supplies the per-set owned count as of that sync's
 * completion, so replaying history backwards shows each sync as it stood then.
 */
export function setProgressFor(
  added: SyncDeltaEntry[],
  ownedAfter: Map<string, number>,
  setTotals: Map<string, SetTotal>,
): SetProgress[] {
  const gained = new Map<string, number>();
  for (const e of added)
    if (e.is_new && e.set_code)
      gained.set(e.set_code, (gained.get(e.set_code) ?? 0) + 1);
  return [...gained.entries()]
    .map(([set_code, g]) => {
      const t = setTotals.get(set_code);
      const after = ownedAfter.get(set_code) ?? 0;
      return {
        set_code,
        expansion: t?.expansion ?? set_code,
        total: t?.total ?? 0,
        after,
        before: Math.max(0, after - g),
        gained: g,
      };
    })
    .sort((a, b) => b.gained - a.gained);
}

/** Current owned counts keyed by set — the starting point for replaying history. */
export function ownedBySet(setTotals: Map<string, SetTotal>): Map<string, number> {
  return new Map([...setTotals].map(([code, t]) => [code, t.owned]));
}

/**
 * Every purchasable, unblocked pack joined to its strongest unowned pull targets
 * resolved to full catalog cards. The full list is returned so the client-side
 * series/type filters have everything to work with; ranking happens there.
 */
export function nextPackEntries(
  packs: PackEvRecord[],
  index: CoordIndex,
): { pack: PackEvRecord; targets: CatalogCard[] }[] {
  return packs
    .filter((p) => p.purchasable && !p.blocked)
    .map((pack) => ({
      pack,
      targets: pack.top_power_cards
        .map((t) => lookupCoord(index, t.set_code, t.card_number))
        .filter((c): c is CatalogCard => c != null),
    }));
}
