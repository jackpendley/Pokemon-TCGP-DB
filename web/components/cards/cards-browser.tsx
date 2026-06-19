"use client";

import { useMemo, useState } from "react";

import { CardGrid } from "@/components/cards/card-grid";
import { displayType } from "@/lib/domain/card";
import type { CatalogCard } from "@/types";

const SHOW_LIMIT = 300;

export function CardsBrowser({ cards }: { cards: CatalogCard[] }) {
  const [query, setQuery] = useState("");
  const [setFilter, setSetFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [ownership, setOwnership] = useState<"all" | "owned" | "missing">("all");

  const setCodes = useMemo(
    () => [...new Set(cards.map((c) => c.set_code))],
    [cards],
  );
  const types = useMemo(
    () => [...new Set(cards.map((c) => displayType(c)))].sort(),
    [cards],
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return cards.filter((c) => {
      if (q && !c.name.toLowerCase().includes(q)) return false;
      if (setFilter && c.set_code !== setFilter) return false;
      if (typeFilter && displayType(c) !== typeFilter) return false;
      if (ownership === "owned" && c.owned <= 0) return false;
      if (ownership === "missing" && c.owned > 0) return false;
      return true;
    });
  }, [cards, query, setFilter, typeFilter, ownership]);

  const shown = filtered.slice(0, SHOW_LIMIT);

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
          className="h-9 rounded-md border bg-background px-2 text-sm"
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
          className="h-9 rounded-md border bg-background px-2 text-sm"
        >
          <option value="">All types</option>
          {types.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
        <select
          value={ownership}
          onChange={(e) =>
            setOwnership(e.target.value as "all" | "owned" | "missing")
          }
          className="h-9 rounded-md border bg-background px-2 text-sm"
        >
          <option value="all">All</option>
          <option value="owned">Owned</option>
          <option value="missing">Missing</option>
        </select>
      </div>

      <p className="text-sm text-muted-foreground">
        Showing {shown.length} of {filtered.length}
        {filtered.length > SHOW_LIMIT ? " (refine filters to see more)" : ""}
      </p>

      <CardGrid cards={shown} />
    </div>
  );
}
