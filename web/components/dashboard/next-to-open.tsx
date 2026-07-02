"use client";

import { useMemo, useState } from "react";
import Link from "next/link";

import { NextPackCard } from "@/components/dashboard/next-pack-card";
import { cn } from "@/lib/utils";
import { formatNumber } from "@/lib/domain/format";
import type { CatalogCard, PackRecord } from "@/types";

export interface NextPackEntry {
  pack: PackRecord;
  targets: CatalogCard[];
}

export interface Currency {
  pack_hourglasses: number;
  wonder_hourglasses: number;
  shop_tickets: number;
}

type Series = "all" | "A" | "B";
type Focus = "unified" | "value" | "cheap" | "rares";

const seriesOf = (code: string) => {
  const u = code.toUpperCase();
  if (u.startsWith("PROMO-A")) return "A";
  if (u.startsWith("PROMO-B")) return "B";
  return u[0];
};

const FOCUS_OPTIONS: { value: Focus; label: string }[] = [
  { value: "unified", label: "Best overall" },
  { value: "value", label: "Best value (10×)" },
  { value: "cheap", label: "Cheapest per card" },
  { value: "rares", label: "Chase rares" },
];

const focusValue = (p: PackRecord, focus: Focus): number => {
  switch (focus) {
    case "value":
      return p.new_card_ev_10x;
    case "cheap":
      return -p.cost_per_unique_card_10x; // ascending → negate for desc sort
    case "rares":
      return p.rare_plus_ev_10x;
    default:
      return p.unified_score;
  }
};

/**
 * "What to open next": Pack-hourglass balance + filters (series / type / focus)
 * over all ranked packs, showing the top 3 picks with enlargeable pull targets.
 */
export function NextToOpen({
  entries,
  currency,
}: {
  entries: NextPackEntry[];
  currency: Currency | null;
}) {
  const [series, setSeries] = useState<Series>("all");
  const [type, setType] = useState<string>("all");
  const [focus, setFocus] = useState<Focus>("unified");

  const typeOptions = useMemo(() => {
    const set = new Set<string>();
    for (const e of entries)
      for (const t of e.targets) if (t.pokemon_type) set.add(t.pokemon_type);
    return [...set].sort();
  }, [entries]);

  const shown = useMemo(() => {
    return entries
      .filter((e) => series === "all" || seriesOf(e.pack.set_code) === series)
      .filter(
        (e) => type === "all" || e.targets.some((t) => t.pokemon_type === type),
      )
      .sort((a, b) => focusValue(b.pack, focus) - focusValue(a.pack, focus))
      .slice(0, 3);
  }, [entries, series, type, focus]);

  const selectCls =
    "h-8 rounded-md border bg-background px-2 text-sm text-foreground";

  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex items-end gap-4">
          <h2 className="text-lg font-medium">What to open next</h2>
          {currency ? (
            <div className="flex items-end gap-3">
              <div className="leading-none">
                <span className="text-2xl font-semibold tabular-nums text-primary">
                  {formatNumber(currency.pack_hourglasses)}
                </span>
                <span className="ml-1 text-xs text-muted-foreground">
                  pack ⧗
                </span>
              </div>
              <span className="pb-0.5 text-xs text-muted-foreground/80 tabular-nums">
                {formatNumber(currency.wonder_hourglasses)} wonder ⧗ ·{" "}
                {formatNumber(currency.shop_tickets)} tickets
              </span>
            </div>
          ) : null}
        </div>
        <Link
          href="/packs"
          className="text-sm font-medium text-primary hover:underline"
        >
          View all packs →
        </Link>
      </div>

      {/* Filters: series toggle · type · focus/sort. */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="inline-flex rounded-md border p-0.5">
          {(["all", "A", "B"] as Series[]).map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => setSeries(s)}
              className={cn(
                "h-7 rounded px-3 text-sm font-medium transition-colors",
                series === s
                  ? "bg-secondary text-secondary-foreground"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              {s === "all" ? "All" : `Series ${s}`}
            </button>
          ))}
        </div>
        <select
          value={type}
          onChange={(e) => setType(e.target.value)}
          className={selectCls}
          aria-label="Filter by pull-target type"
        >
          <option value="all">All types</option>
          {typeOptions.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
        <select
          value={focus}
          onChange={(e) => setFocus(e.target.value as Focus)}
          className={selectCls}
          aria-label="Rank by"
        >
          {FOCUS_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </div>

      {shown.length > 0 ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {shown.map((e, i) => (
            <NextPackCard
              key={e.pack.pack_name}
              pack={e.pack}
              targets={e.targets}
              rank={i + 1}
            />
          ))}
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">
          No packs match these filters.
        </p>
      )}
    </section>
  );
}
