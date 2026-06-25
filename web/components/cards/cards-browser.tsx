"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { usePathname } from "next/navigation";

import { CardGrid } from "@/components/cards/card-grid";
import { displayType, isMegaEx } from "@/lib/domain/card";
import { titleCase } from "@/lib/domain/format";
import { compareRarity } from "@/lib/domain/rarity";
import type { CatalogCard } from "@/types";

// Cards render in batches as the user scrolls (IntersectionObserver), so the
// full ~3,400-card catalog is reachable without dropping a 300-item cap and
// without mounting every tile at once. Images already lazy-load.
const BATCH = 150;

// card_reference stores stages as "Basic" / "Stage1" / "Stage2" (no space).
const STAGE_ORDER = ["Basic", "Stage1", "Stage2", "Stage3"];
const stageLabel = (s: string) => s.replace(/^Stage(\d)/, "Stage $1");
type CardClass = "all" | "ex" | "mega";
type Ownership = "all" | "owned" | "missing";

/** Filters that can be seeded from the URL (set/type/rarity links, etc.). */
export interface CardsFilter {
  q?: string;
  set?: string;
  type?: string;
  rarity?: string;
  stage?: string;
  class?: string;
  owned?: string;
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
  const [setFilter, setSetFilter] = useState(initial?.set ?? "");
  const [typeFilter, setTypeFilter] = useState(initial?.type ?? "");
  const [rarityFilter, setRarityFilter] = useState(initial?.rarity ?? "");
  const [stageFilter, setStageFilter] = useState(initial?.stage ?? "");
  const [classFilter, setClassFilter] = useState<CardClass>(
    (initial?.class as CardClass) ?? "all",
  );
  const [ownership, setOwnership] = useState<Ownership>(
    (initial?.owned as Ownership) ?? "all",
  );
  const [visible, setVisible] = useState(BATCH);

  const setCodes = useMemo(
    () => [...new Set(cards.map((c) => c.set_code))],
    [cards],
  );
  const types = useMemo(
    () => [...new Set(cards.map((c) => displayType(c)))].sort(),
    [cards],
  );
  const rarities = useMemo(
    () =>
      [...new Set(cards.map((c) => c.rarity).filter((r): r is string => !!r))].sort(
        compareRarity,
      ),
    [cards],
  );
  const stages = useMemo(
    () =>
      [...new Set(cards.map((c) => c.stage).filter((s): s is string => !!s))].sort(
        (a, b) => {
          const ia = STAGE_ORDER.indexOf(a);
          const ib = STAGE_ORDER.indexOf(b);
          return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib);
        },
      ),
    [cards],
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return cards.filter((c) => {
      if (q && !c.name.toLowerCase().includes(q)) return false;
      if (setFilter && c.set_code !== setFilter) return false;
      if (typeFilter && displayType(c) !== typeFilter) return false;
      if (rarityFilter && c.rarity !== rarityFilter) return false;
      if (stageFilter && c.stage !== stageFilter) return false;
      if (classFilter === "ex" && !c.is_ex) return false;
      if (classFilter === "mega" && !isMegaEx(c)) return false;
      if (ownership === "owned" && c.owned <= 0) return false;
      if (ownership === "missing" && c.owned > 0) return false;
      return true;
    });
  }, [
    cards,
    query,
    setFilter,
    typeFilter,
    rarityFilter,
    stageFilter,
    classFilter,
    ownership,
  ]);

  // Reset the window when filters change — adjust state during render (the
  // React-recommended alternative to a reset effect) keyed on the filter combo.
  const filterKey = `${query}|${setFilter}|${typeFilter}|${rarityFilter}|${stageFilter}|${classFilter}|${ownership}`;
  const [prevKey, setPrevKey] = useState(filterKey);
  if (filterKey !== prevKey) {
    setPrevKey(filterKey);
    setVisible(BATCH);
  }

  // Reflect the active filters in the URL (shareable / back-navigable) without a
  // server round-trip — history.replaceState avoids re-fetching the catalog.
  const firstSync = useRef(true);
  useEffect(() => {
    if (firstSync.current) {
      firstSync.current = false;
      return;
    }
    const params = new URLSearchParams();
    if (query.trim()) params.set("q", query.trim());
    if (setFilter) params.set("set", setFilter);
    if (typeFilter) params.set("type", typeFilter);
    if (rarityFilter) params.set("rarity", rarityFilter);
    if (stageFilter) params.set("stage", stageFilter);
    if (classFilter !== "all") params.set("class", classFilter);
    if (ownership !== "all") params.set("owned", ownership);
    const qs = params.toString();
    window.history.replaceState(null, "", qs ? `${pathname}?${qs}` : pathname);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterKey]);

  // Grow the window when the sentinel scrolls into view.
  const sentinel = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    const el = sentinel.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) {
          setVisible((v) => Math.min(v + BATCH, filtered.length));
        }
      },
      { rootMargin: "600px" },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [filtered.length]);

  const shown = filtered.slice(0, visible);
  const selectClass = "h-9 rounded-md border bg-background px-2 text-sm";

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-3">
        <input
          type="search"
          placeholder="Search cards…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="h-9 w-56 rounded-md border bg-background px-3 text-sm"
        />
        <select
          value={setFilter}
          onChange={(e) => setSetFilter(e.target.value)}
          className={selectClass}
        >
          <option value="">All sets</option>
          {setCodes.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className={selectClass}
        >
          <option value="">All types</option>
          {types.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
        <select
          value={rarityFilter}
          onChange={(e) => setRarityFilter(e.target.value)}
          className={selectClass}
        >
          <option value="">All rarities</option>
          {rarities.map((r) => (
            <option key={r} value={r}>
              {titleCase(r)}
            </option>
          ))}
        </select>
        <select
          value={stageFilter}
          onChange={(e) => setStageFilter(e.target.value)}
          className={selectClass}
        >
          <option value="">All stages</option>
          {stages.map((s) => (
            <option key={s} value={s}>
              {stageLabel(s)}
            </option>
          ))}
        </select>
        <select
          value={classFilter}
          onChange={(e) => setClassFilter(e.target.value as CardClass)}
          className={selectClass}
        >
          <option value="all">All cards</option>
          <option value="ex">ex</option>
          <option value="mega">Mega ex</option>
        </select>
        <select
          value={ownership}
          onChange={(e) =>
            setOwnership(e.target.value as "all" | "owned" | "missing")
          }
          className={selectClass}
        >
          <option value="all">All</option>
          <option value="owned">Owned</option>
          <option value="missing">Missing</option>
        </select>
      </div>

      <p className="text-sm text-muted-foreground">
        Showing {shown.length} of {filtered.length}
      </p>

      <CardGrid cards={shown} />

      {/* Sentinel: when it scrolls near the viewport, render the next batch. */}
      {shown.length < filtered.length ? (
        <div ref={sentinel} className="h-1" aria-hidden />
      ) : null}
    </div>
  );
}
