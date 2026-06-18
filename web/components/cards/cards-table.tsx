"use client";

import { useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { CatalogCard } from "@/types";
import { titleCase } from "@/lib/domain/format";

const ROW_LIMIT = 300;

export function CardsTable({ cards }: { cards: CatalogCard[] }) {
  const [query, setQuery] = useState("");
  const [setFilter, setSetFilter] = useState("");
  const [ownership, setOwnership] = useState<"all" | "owned" | "missing">("all");

  const setCodes = useMemo(
    () => [...new Set(cards.map((c) => c.set_code))],
    [cards],
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return cards.filter((c) => {
      if (q && !c.name.toLowerCase().includes(q)) return false;
      if (setFilter && c.set_code !== setFilter) return false;
      if (ownership === "owned" && c.owned <= 0) return false;
      if (ownership === "missing" && c.owned > 0) return false;
      return true;
    });
  }, [cards, query, setFilter, ownership]);

  const shown = filtered.slice(0, ROW_LIMIT);

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
        Showing {Math.min(shown.length, filtered.length)} of {filtered.length}
        {filtered.length > ROW_LIMIT ? " (refine filters to see more)" : ""}
      </p>

      <div className="rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Card</TableHead>
              <TableHead>Set</TableHead>
              <TableHead>Rarity</TableHead>
              <TableHead>Type</TableHead>
              <TableHead className="text-right">Owned</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {shown.map((c) => (
              <TableRow key={`${c.set_code}-${c.card_number}`}>
                <TableCell className="font-medium">{c.name}</TableCell>
                <TableCell className="tabular-nums text-muted-foreground">
                  {c.set_code} · {c.card_number}
                </TableCell>
                <TableCell>{titleCase(c.rarity)}</TableCell>
                <TableCell>{c.pokemon_type ?? titleCase(c.card_category)}</TableCell>
                <TableCell className="text-right">
                  {c.owned > 0 ? (
                    <span className="tabular-nums">{c.owned}</span>
                  ) : (
                    <Badge variant="outline">missing</Badge>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
