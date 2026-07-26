"use client";

import { useDeferredValue, useEffect, useMemo, useRef, useState } from "react";
import { usePathname } from "next/navigation";

import { CardGrid } from "@/components/cards/card-grid";
import { TypeSymbol, ENERGY_TYPES } from "@/components/cards/type-symbol";
import { RaritySymbol } from "@/components/dashboard/rarity-symbol";
import { SetLogo } from "@/components/sets/set-logo";
import { FilterDropdown, FilterCheck } from "@/components/ui/filter-dropdown";
import { MultiSelect } from "@/components/ui/multi-select";
import { displayType, isMegaEx } from "@/lib/domain/card";
import { formatNumber, formatPercent, titleCase } from "@/lib/domain/format";
import { compareRarity, isBaseRarity } from "@/lib/domain/rarity";
import { cn } from "@/lib/utils";
import type { CatalogCard } from "@/types";

/** Toggle a value in a string[] filter state. */
const toggleValue = (arr: string[], v: string) =>
  arr.includes(v) ? arr.filter((x) => x !== v) : [...arr, v];

const BATCH = 150;
const STAGE_ORDER = ["Basic", "Stage1", "Stage2", "Stage3"];
const stageLabel = (s: string) => s.replace(/^Stage(\d)/, "Stage $1");
type CardClass = "all" | "ex" | "mega";
type Ownership = "all" | "owned" | "missing";
type Scope = "total" | "base";
type Sort = "default" | "power";

type Category = "all" | "Pokemon" | "Trainer";

export interface CardsFilter {
  q?: string;
  set?: string;
  type?: string;
  rarity?: string;
  stage?: string;
  class?: string;
  category?: string;
  owned?: string;
  scope?: string;
  sort?: string;
}

const splitCsv = (v?: string) => (v ? v.split(",").filter(Boolean) : []);

/** Series of a set code for the "all Series A/B" quick actions. */
const seriesOf = (code: string) => {
  const u = code.toUpperCase();
  if (u.startsWith("PROMO-A")) return "A";
  if (u.startsWith("PROMO-B")) return "B";
  return u[0];
};

function Ring({ ratio, size = 64 }: { ratio: number; size?: number }) {
  const r = 44;
  const circ = 2 * Math.PI * r;
  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg viewBox="0 0 100 100" className="size-full -rotate-90">
        <circle cx="50" cy="50" r={r} fill="none" strokeWidth="10" className="stroke-muted" />
        <circle
          cx="50"
          cy="50"
          r={r}
          fill="none"
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={circ}
          strokeDashoffset={circ * (1 - ratio)}
          className="stroke-primary transition-[stroke-dashoffset] duration-500 ease-out"
        />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center text-xs font-semibold tabular-nums">
        {formatPercent(ratio, 0)}
      </span>
    </div>
  );
}

export function CardsBrowser({
  cards,
  initial,
}: {
  cards: CatalogCard[];
  initial?: CardsFilter;
}) {
  const pathname = usePathname();
  const [query, setQuery] = useState(initial?.q ?? "");
  const [sets, setSets] = useState<string[]>(splitCsv(initial?.set));
  const [types, setTypes] = useState<string[]>(splitCsv(initial?.type));
  const [rarities, setRarities] = useState<string[]>(splitCsv(initial?.rarity));
  const [stages, setStages] = useState<string[]>(splitCsv(initial?.stage));
  const [classFilter, setClassFilter] = useState<CardClass>(
    (initial?.class as CardClass) ?? "all",
  );
  const [category, setCategory] = useState<Category>(
    (initial?.category as Category) ?? "all",
  );
  const [ownership, setOwnership] = useState<Ownership>(
    (initial?.owned as Ownership) ?? "all",
  );
  const [scope, setScope] = useState<Scope>(
    initial?.scope === "base" ? "base" : "total",
  );
  const [sort, setSort] = useState<Sort>(
    initial?.sort === "power" ? "power" : "default",
  );
  const [visible, setVisible] = useState(BATCH);
  // Defer the search text so each keystroke keeps the input responsive while the
  // ~3,500-card filter recompute runs at a lower priority (INP).
  const deferredQuery = useDeferredValue(query);

  const setCodes = useMemo(() => [...new Set(cards.map((c) => c.set_code))], [cards]);
  const typeOpts = useMemo(
    () => [...new Set(cards.map((c) => displayType(c)))].sort(),
    [cards],
  );
  const rarityOpts = useMemo(
    () =>
      [...new Set(cards.map((c) => c.rarity).filter((r): r is string => !!r))].sort(
        compareRarity,
      ),
    [cards],
  );
  const stageOpts = useMemo(
    () =>
      [...new Set(cards.map((c) => c.stage).filter((s): s is string => !!s))].sort(
        (a, b) =>
          (STAGE_ORDER.indexOf(a) === -1 ? 99 : STAGE_ORDER.indexOf(a)) -
          (STAGE_ORDER.indexOf(b) === -1 ? 99 : STAGE_ORDER.indexOf(b)),
      ),
    [cards],
  );

  const aSets = useMemo(() => setCodes.filter((s) => seriesOf(s) === "A"), [setCodes]);
  const bSets = useMemo(() => setCodes.filter((s) => seriesOf(s) === "B"), [setCodes]);
  // Type filter splits Pokémon energy types (canonical order) from Trainer subtypes.
  const pokeTypes = useMemo(
    () => ENERGY_TYPES.filter((t) => typeOpts.includes(t)),
    [typeOpts],
  );
  const trainerTypes = useMemo(
    () => typeOpts.filter((t) => !ENERGY_TYPES.includes(t)).sort(),
    [typeOpts],
  );

  const filtered = useMemo(() => {
    const q = deferredQuery.trim().toLowerCase();
    return cards.filter((c) => {
      if (q && !c.name.toLowerCase().includes(q)) return false;
      if (sets.length && !sets.includes(c.set_code)) return false;
      if (types.length && !types.includes(displayType(c))) return false;
      if (rarities.length && !(c.rarity && rarities.includes(c.rarity))) return false;
      if (stages.length && !(c.stage && stages.includes(c.stage))) return false;
      if (scope === "base" && !isBaseRarity(c.rarity)) return false;
      if (category !== "all" && c.card_category !== category) return false;
      if (classFilter === "ex" && !c.is_ex) return false;
      if (classFilter === "mega" && !isMegaEx(c)) return false;
      if (ownership === "owned" && c.owned <= 0) return false;
      if (ownership === "missing" && c.owned > 0) return false;
      return true;
    });
  }, [cards, deferredQuery, sets, types, rarities, stages, scope, category, classFilter, ownership]);

  const ordered = useMemo(
    () =>
      sort === "power"
        ? // Grouped by which model produced the score, then ranked within the
          // group. Pokémon are scored on HP and damage, Trainers on rule text —
          // interleaving them would rank a Supporter against a Charizard on
          // scales that only share their range.
          [...filtered].sort((a, b) => {
            const kindRank = (c: CatalogCard) =>
              c.power_score == null ? 2 : c.power_score_kind === "trainer" ? 1 : 0;
            const byKind = kindRank(a) - kindRank(b);
            if (byKind !== 0) return byKind;
            return (b.power_score ?? -1) - (a.power_score ?? -1);
          })
        : filtered,
    [filtered, sort],
  );

  const ownedShown = filtered.filter((c) => c.owned > 0).length;
  const ratio = filtered.length > 0 ? ownedShown / filtered.length : 0;
  const singleSet = sets.length === 1 ? sets[0] : null;
  const singleSetName = singleSet
    ? cards.find((c) => c.set_code === singleSet)?.expansion ?? singleSet
    : null;

  const filterKey = `${query}|${sets}|${types}|${rarities}|${stages}|${category}|${classFilter}|${ownership}|${scope}|${sort}`;
  const [prevKey, setPrevKey] = useState(filterKey);
  if (filterKey !== prevKey) {
    setPrevKey(filterKey);
    setVisible(BATCH);
  }

  const firstSync = useRef(true);
  useEffect(() => {
    if (firstSync.current) {
      firstSync.current = false;
      return;
    }
    const p = new URLSearchParams();
    if (query.trim()) p.set("q", query.trim());
    if (sets.length) p.set("set", sets.join(","));
    if (types.length) p.set("type", types.join(","));
    if (rarities.length) p.set("rarity", rarities.join(","));
    if (stages.length) p.set("stage", stages.join(","));
    if (category !== "all") p.set("category", category);
    if (classFilter !== "all") p.set("class", classFilter);
    if (ownership !== "all") p.set("owned", ownership);
    if (scope === "base") p.set("scope", scope);
    if (sort !== "default") p.set("sort", sort);
    const qs = p.toString();
    window.history.replaceState(null, "", qs ? `${pathname}?${qs}` : pathname);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterKey]);

  const sentinel = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    const el = sentinel.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting)
          setVisible((v) => Math.min(v + BATCH, filtered.length));
      },
      { rootMargin: "600px" },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [filtered.length]);

  const shown = ordered.slice(0, visible);
  const selectCls = "h-9 rounded-md border bg-background px-2 text-sm";

  return (
    <div className="space-y-4">
      {/* Live progress for the active filter, plus a set header when one set is shown. */}
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-lg border bg-card p-4">
        <div className="flex items-center gap-4">
          {singleSet ? (
            <SetLogo
              setCode={singleSet}
              label={singleSetName ?? singleSet}
              className="h-12 w-20 shrink-0"
            />
          ) : null}
          <div>
            {singleSet ? (
              <div className="font-heading text-lg font-semibold">
                {singleSetName}{" "}
                <span className="text-sm font-normal text-muted-foreground">
                  {singleSet}
                </span>
              </div>
            ) : null}
            <div className="text-sm text-muted-foreground tabular-nums">
              <span className="font-medium text-foreground">
                {formatNumber(ownedShown)}
              </span>{" "}
              of {formatNumber(filtered.length)} owned
            </div>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="inline-flex rounded-md border p-0.5">
            {(["total", "base"] as Scope[]).map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => setScope(s)}
                className={cn(
                  "h-7 rounded px-3 text-sm font-medium transition-colors",
                  scope === s
                    ? "bg-secondary text-secondary-foreground"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                {s === "total" ? "Full" : "Base"}
              </button>
            ))}
          </div>
          <Ring ratio={ratio} />
        </div>
      </div>

      <div className="flex flex-wrap gap-3">
        <input
          type="search"
          placeholder="Search cards…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="h-9 w-56 rounded-md border bg-background px-3 text-sm"
        />
        {/* Sets: Series A on the left, Series B on the right. */}
        <FilterDropdown
          label="sets"
          count={sets.length}
          onClear={() => setSets([])}
          panelClassName="w-[24rem]"
        >
          <div className="grid grid-cols-2 gap-3">
            {[
              { series: "A", list: aSets },
              { series: "B", list: bSets },
            ].map(({ series, list }) => (
              <div key={series}>
                <button
                  type="button"
                  onClick={() => setSets([...new Set([...sets, ...list])])}
                  className="mb-1 w-full rounded bg-muted px-2 py-1 text-left text-xs font-medium hover:bg-muted/70"
                >
                  All Series {series}
                </button>
                {list.map((s) => (
                  <FilterCheck
                    key={s}
                    checked={sets.includes(s)}
                    onToggle={() => setSets(toggleValue(sets, s))}
                  >
                    <SetLogo setCode={s} label={s} className="h-4 w-8 shrink-0" />
                    <span>{s}</span>
                  </FilterCheck>
                ))}
              </div>
            ))}
          </div>
        </FilterDropdown>

        {/* Types: Pokémon energy types (with icons), then Trainer subtypes. */}
        <FilterDropdown
          label="types"
          count={types.length}
          onClear={() => setTypes([])}
          panelClassName="w-72"
        >
          <div className="grid grid-cols-2 gap-x-2">
            {pokeTypes.map((t) => (
              <FilterCheck
                key={t}
                checked={types.includes(t)}
                onToggle={() => setTypes(toggleValue(types, t))}
              >
                <TypeSymbol type={t} />
                <span>{t}</span>
              </FilterCheck>
            ))}
          </div>
          {trainerTypes.length > 0 ? (
            <>
              <div className="mt-2 border-t px-2 pt-2 pb-1 text-xs font-medium text-muted-foreground">
                Trainers
              </div>
              <div className="grid grid-cols-2 gap-x-2">
                {trainerTypes.map((t) => (
                  <FilterCheck
                    key={t}
                    checked={types.includes(t)}
                    onToggle={() => setTypes(toggleValue(types, t))}
                  >
                    <span>{t}</span>
                  </FilterCheck>
                ))}
              </div>
            </>
          ) : null}
        </FilterDropdown>

        {/* Rarities: multi-column with the rarity symbols. */}
        <FilterDropdown
          label="rarities"
          count={rarities.length}
          onClear={() => setRarities([])}
          panelClassName="w-[26rem]"
        >
          <div className="grid grid-cols-2 gap-x-2 sm:grid-cols-3">
            {rarityOpts.map((r) => (
              <FilterCheck
                key={r}
                checked={rarities.includes(r)}
                onToggle={() => setRarities(toggleValue(rarities, r))}
              >
                <RaritySymbol rarity={r} />
                <span>{titleCase(r)}</span>
              </FilterCheck>
            ))}
          </div>
        </FilterDropdown>

        <MultiSelect
          label="stages"
          options={stageOpts.map((s) => ({ value: s, label: stageLabel(s) }))}
          selected={stages}
          onChange={setStages}
        />
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value as Category)}
          className={selectCls}
          aria-label="Category"
        >
          <option value="all">All categories</option>
          <option value="Pokemon">Pokémon</option>
          <option value="Trainer">Trainers</option>
        </select>
        <select
          value={classFilter}
          onChange={(e) => setClassFilter(e.target.value as CardClass)}
          className={selectCls}
        >
          <option value="all">All cards</option>
          <option value="ex">ex</option>
          <option value="mega">Mega ex</option>
        </select>
        <select
          value={ownership}
          onChange={(e) => setOwnership(e.target.value as Ownership)}
          className={selectCls}
        >
          <option value="all">All</option>
          <option value="owned">Owned</option>
          <option value="missing">Missing</option>
        </select>
        <select
          value={sort}
          onChange={(e) => setSort(e.target.value as Sort)}
          className={selectCls}
          aria-label="Sort"
        >
          <option value="default">Sort: default</option>
          <option value="power">Sort: power ▾</option>
        </select>
      </div>

      <p className="text-sm text-muted-foreground">
        Showing {shown.length} of {filtered.length}
      </p>

      <CardGrid cards={shown} allCards={cards} />

      {shown.length < filtered.length ? (
        <div ref={sentinel} className="h-1" aria-hidden />
      ) : null}
    </div>
  );
}
