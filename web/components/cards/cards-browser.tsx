"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { usePathname } from "next/navigation";

import { CardGrid } from "@/components/cards/card-grid";
import { SetLogo } from "@/components/sets/set-logo";
import { MultiSelect, type MSGroup } from "@/components/ui/multi-select";
import { displayType, isMegaEx } from "@/lib/domain/card";
import { formatNumber, formatPercent, titleCase } from "@/lib/domain/format";
import { compareRarity, isBaseRarity } from "@/lib/domain/rarity";
import { cn } from "@/lib/utils";
import type { CatalogCard } from "@/types";

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

  const setGroups: MSGroup[] = useMemo(() => {
    const a = setCodes.filter((s) => seriesOf(s) === "A");
    const b = setCodes.filter((s) => seriesOf(s) === "B");
    return [
      ...(a.length ? [{ label: "All Series A", values: a }] : []),
      ...(b.length ? [{ label: "All Series B", values: b }] : []),
    ];
  }, [setCodes]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
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
  }, [cards, query, sets, types, rarities, stages, scope, category, classFilter, ownership]);

  const ordered = useMemo(
    () =>
      sort === "power"
        ? [...filtered].sort(
            (a, b) => (b.power_score ?? -1) - (a.power_score ?? -1),
          )
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
        <MultiSelect
          label="sets"
          options={setCodes.map((s) => ({ value: s, label: s }))}
          selected={sets}
          onChange={setSets}
          groups={setGroups}
        />
        <MultiSelect
          label="types"
          options={typeOpts.map((t) => ({ value: t, label: t }))}
          selected={types}
          onChange={setTypes}
        />
        <MultiSelect
          label="rarities"
          options={rarityOpts.map((r) => ({ value: r, label: titleCase(r) }))}
          selected={rarities}
          onChange={setRarities}
        />
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

      <CardGrid cards={shown} />

      {shown.length < filtered.length ? (
        <div ref={sentinel} className="h-1" aria-hidden />
      ) : null}
    </div>
  );
}
