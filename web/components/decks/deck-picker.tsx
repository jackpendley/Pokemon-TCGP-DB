"use client";

import { useMemo, useState } from "react";
import { Search } from "lucide-react";

import { CardImage } from "@/components/cards/card-image";
import { ENERGY_TYPES, TypeSymbol } from "@/components/cards/type-symbol";
import { MultiSelect } from "@/components/ui/multi-select";
import { displayType } from "@/lib/domain/card";
import { MAX_COPIES_PER_NAME } from "@/lib/domain/deck";
import { cn } from "@/lib/utils";
import type { CatalogCard } from "@/types";

/** Rendered at once; the catalog is ~3.5k cards and the picker is for browsing. */
const PAGE = 60;

const STAGES = ["Basic", "Stage1", "Stage2"];
const stageLabel = (s: string) => s.replace(/^Stage(\d)/, "Stage $1");

/**
 * Card picker for the deck builder.
 *
 * Browsable rather than search-only: decks are built around a type, so the type
 * filter has to be reachable without knowing what you're looking for. Filters
 * mirror the Cards page (type, stage, category, ownership) using the same
 * MultiSelect primitive, but stay deliberately smaller — set and rarity aren't
 * deck-building decisions.
 */
export function DeckPicker({
  catalog,
  countFor,
  disabled,
  onAdd,
}: {
  catalog: CatalogCard[];
  countFor: (card: CatalogCard) => number;
  disabled: boolean;
  onAdd: (card: CatalogCard) => void;
}) {
  const [query, setQuery] = useState("");
  const [types, setTypes] = useState<string[]>([]);
  const [stages, setStages] = useState<string[]>([]);
  const [category, setCategory] = useState<string[]>([]);
  const [ownedOnly, setOwnedOnly] = useState(false);
  const [shown, setShown] = useState(PAGE);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return catalog.filter((c) => {
      if (q && !c.name.toLowerCase().includes(q)) return false;
      if (types.length > 0 && !types.includes(displayType(c))) return false;
      if (stages.length > 0 && !(c.stage && stages.includes(c.stage))) return false;
      if (category.length > 0 && !(c.card_category && category.includes(c.card_category)))
        return false;
      // Ownership is per printing here — you can only build with copies you hold.
      if (ownedOnly && c.owned <= 0) return false;
      return true;
    });
  }, [catalog, query, types, stages, category, ownedOnly]);

  const visible = filtered.slice(0, shown);

  function reset<T>(setter: (v: T) => void, value: T) {
    setter(value);
    setShown(PAGE);
  }

  return (
    <div className="space-y-3">
      <label className="flex items-center gap-2 rounded-md border px-3">
        <Search className="size-4 shrink-0 text-muted-foreground" />
        <input
          value={query}
          onChange={(e) => reset(setQuery, e.target.value)}
          placeholder="Search cards by name…"
          aria-label="Search cards by name"
          className="h-10 w-full bg-transparent text-sm outline-none"
        />
      </label>

      <div className="flex flex-wrap items-center gap-2">
        <MultiSelect
          label="types"
          options={ENERGY_TYPES.map((t) => ({ value: t, label: t }))}
          selected={types}
          onChange={(v) => reset(setTypes, v)}
        />
        <MultiSelect
          label="stages"
          options={STAGES.map((s) => ({ value: s, label: stageLabel(s) }))}
          selected={stages}
          onChange={(v) => reset(setStages, v)}
        />
        <MultiSelect
          label="categories"
          options={[
            { value: "Pokemon", label: "Pokémon" },
            { value: "Trainer", label: "Trainer" },
          ]}
          selected={category}
          onChange={(v) => reset(setCategory, v)}
        />
        <button
          type="button"
          onClick={() => reset(setOwnedOnly, !ownedOnly)}
          aria-pressed={ownedOnly}
          className={cn(
            "h-9 rounded-md border px-3 text-sm font-medium transition-colors",
            ownedOnly
              ? "border-primary bg-primary/10 text-foreground"
              : "text-muted-foreground hover:text-foreground",
          )}
        >
          Owned only
        </button>
      </div>

      <p className="text-xs text-muted-foreground">
        Showing {visible.length} of {filtered.length}
      </p>

      {filtered.length === 0 ? (
        <p className="py-6 text-center text-sm text-muted-foreground">
          No cards match these filters.
        </p>
      ) : (
        <div className="grid grid-cols-3 gap-3 sm:grid-cols-5 lg:grid-cols-6">
          {visible.map((card) => {
            const count = countFor(card);
            const maxed = count >= MAX_COPIES_PER_NAME;
            return (
              <button
                key={`${card.set_code}:${card.card_number}`}
                type="button"
                onClick={() => onAdd(card)}
                disabled={disabled || maxed}
                title={
                  maxed
                    ? `${card.name} — already at ${MAX_COPIES_PER_NAME} copies`
                    : `Add ${card.name}`
                }
                className="flex flex-col text-left disabled:opacity-45"
              >
                <div className="relative aspect-[5/7] overflow-hidden rounded-md border">
                  <CardImage card={card} />
                  {count > 0 ? (
                    <span className="absolute top-1 right-1 rounded bg-primary px-1.5 text-[10px] font-bold text-primary-foreground tabular-nums">
                      ×{count}
                    </span>
                  ) : null}
                </div>
                <span className="mt-1 truncate text-xs font-medium">{card.name}</span>
                <span className="flex items-center gap-1 text-[10px] text-muted-foreground">
                  <TypeSymbol type={displayType(card)} className="size-3" />
                  <span className="truncate">{card.set_code}</span>
                </span>
              </button>
            );
          })}
        </div>
      )}

      {shown < filtered.length ? (
        <button
          type="button"
          onClick={() => setShown((n) => n + PAGE)}
          className="w-full rounded-md border py-2 text-sm font-medium text-muted-foreground hover:text-foreground"
        >
          Show more
        </button>
      ) : null}
    </div>
  );
}
