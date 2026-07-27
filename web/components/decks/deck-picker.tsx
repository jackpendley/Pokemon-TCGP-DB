"use client";

import { useMemo, useState } from "react";
import { Info, Search } from "lucide-react";

import { CardDialog } from "@/components/cards/card-dialog";
import { CardImage } from "@/components/cards/card-image";
import { OwnedChip } from "@/components/cards/owned-chip";
import { ENERGY_TYPES, TypeSymbol } from "@/components/cards/type-symbol";
import { SetLogo } from "@/components/sets/set-logo";
import {
  FilterCheck,
  FilterDropdown,
  toggleValue,
} from "@/components/ui/filter-dropdown";
import { MultiSelect } from "@/components/ui/multi-select";
import { compareRarity } from "@/lib/domain/rarity";
import { displayType } from "@/lib/domain/card";
import { MAX_COPIES_PER_NAME } from "@/lib/domain/deck";
import { cn } from "@/lib/utils";
import type { CatalogCard } from "@/types";

/** Rendered at once; the catalog is ~3.5k cards and the picker is for browsing. */
const PAGE = 60;

const STAGES = ["Basic", "Stage1", "Stage2"];

type Sort = "default" | "score" | "owned" | "rarity" | "name";

const SORTS: { value: Sort; label: string }[] = [
  { value: "default", label: "Sort: set order" },
  { value: "score", label: "Sort: score" },
  { value: "owned", label: "Sort: owned" },
  { value: "rarity", label: "Sort: rarity" },
  { value: "name", label: "Sort: name" },
];
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
  const [sets, setSets] = useState<string[]>([]);
  const [ownedOnly, setOwnedOnly] = useState(false);
  const [sort, setSort] = useState<Sort>("default");
  const [inspecting, setInspecting] = useState<CatalogCard | null>(null);
  const [shown, setShown] = useState(PAGE);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return catalog.filter((c) => {
      if (q && !c.name.toLowerCase().includes(q)) return false;
      if (types.length > 0 && !types.includes(displayType(c))) return false;
      if (stages.length > 0 && !(c.stage && stages.includes(c.stage))) return false;
      if (category.length > 0 && !(c.card_category && category.includes(c.card_category)))
        return false;
      if (sets.length > 0 && !sets.includes(c.set_code)) return false;
      // Ownership is per printing here — you can only build with copies you hold.
      if (ownedOnly && c.owned <= 0) return false;
      return true;
    });
  }, [catalog, query, types, stages, category, sets, ownedOnly]);

  /**
   * Pokémon power and Trainer utility come from different models, so sorting by
   * "score" groups by kind first and ranks within the group — the same rule the
   * Cards page uses. Ranking a Supporter against a Charizard would be nonsense.
   */
  const ordered = useMemo(() => {
    if (sort === "default") return filtered;
    const copy = [...filtered];
    if (sort === "name") return copy.sort((a, b) => a.name.localeCompare(b.name));
    if (sort === "owned") return copy.sort((a, b) => b.owned - a.owned);
    // Rarest first, reusing the display ladder the rest of the app sorts by.
    if (sort === "rarity")
      return copy.sort((a, b) => compareRarity(b.rarity ?? "", a.rarity ?? ""));
    const kindRank = (c: CatalogCard) =>
      c.power_score == null ? 2 : c.power_score_kind === "trainer" ? 1 : 0;
    return copy.sort(
      (a, b) =>
        kindRank(a) - kindRank(b) || (b.power_score ?? -1) - (a.power_score ?? -1),
    );
  }, [filtered, sort]);

  const setOptions = useMemo(() => {
    const seen = new Map<string, string>();
    for (const c of catalog) if (!seen.has(c.set_code)) seen.set(c.set_code, c.expansion);
    return [...seen].map(([value, label]) => ({ value, label: `${label} · ${value}` }));
  }, [catalog]);

  const visible = ordered.slice(0, shown);

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
        {/* Types and sets carry icons, so they use the same FilterDropdown the
            Cards page uses; MultiSelect's renderOption returns a string and so
            can't hold a <TypeSymbol>. Stages and categories need no icon. */}
        <FilterDropdown
          label="types"
          count={types.length}
          onClear={() => reset(setTypes, [])}
          panelClassName="w-72"
        >
          <div className="grid grid-cols-2 gap-x-2">
            {ENERGY_TYPES.map((t) => (
              <FilterCheck
                key={t}
                checked={types.includes(t)}
                onToggle={() => reset(setTypes, toggleValue(types, t))}
              >
                <TypeSymbol type={t} />
                <span>{t}</span>
              </FilterCheck>
            ))}
          </div>
        </FilterDropdown>
        <MultiSelect
          label="stages"
          options={STAGES.map((s) => ({ value: s, label: stageLabel(s) }))}
          selected={stages}
          onChange={(v) => reset(setStages, v)}
        />
        <FilterDropdown
          label="sets"
          count={sets.length}
          onClear={() => reset(setSets, [])}
          panelClassName="w-[22rem]"
        >
          {setOptions.map((o) => (
            <FilterCheck
              key={o.value}
              checked={sets.includes(o.value)}
              onToggle={() => reset(setSets, toggleValue(sets, o.value))}
            >
              <SetLogo
                setCode={o.value}
                label={o.value}
                className="h-4 w-8 shrink-0"
              />
              <span className="truncate">{o.label}</span>
            </FilterCheck>
          ))}
        </FilterDropdown>
        <MultiSelect
          label="categories"
          options={[
            { value: "Pokemon", label: "Pokémon" },
            { value: "Trainer", label: "Trainer" },
          ]}
          selected={category}
          onChange={(v) => reset(setCategory, v)}
        />
        <select
          value={sort}
          onChange={(e) => setSort(e.target.value as Sort)}
          aria-label="Sort cards"
          className="h-9 rounded-md border bg-transparent px-2 text-sm"
        >
          {SORTS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
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
              <div key={`${card.set_code}:${card.card_number}`} className="relative">
              <button
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
                  {/* key remounts on card change so the CDN-fallback index resets:
                      a sort or filter change remaps a tile onto a different card,
                      and without this the new card inherits the old one's
                      already-advanced index and can render the wrong art. */}
                  <CardImage
                    key={`${card.set_code}-${card.card_number}`}
                    card={card}
                  />
                  {count > 0 ? (
                    <span className="absolute top-1 left-1 rounded bg-primary px-1.5 text-[10px] font-bold text-primary-foreground tabular-nums">
                      ×{count}
                    </span>
                  ) : null}
                </div>
                {/*
                  One line: name, then how many copies you hold as a chip on the
                  right. Deck-building is constrained by copies you actually hold,
                  so the count earns its place — but as "2x" rather than a wordy
                  "2 owned" second line. Unowned cards show no chip: the art is
                  already greyscaled, so a "0x" would only repeat that.
                */}
                <span className="mt-1 flex items-baseline gap-1.5">
                  <span className="min-w-0 flex-1 truncate text-xs font-medium">
                    {card.name}
                  </span>
                  {card.owned > 0 ? (
                    <OwnedChip owned={card.owned} />
                  ) : null}
                </span>
              </button>
              {/* Inspect: evolution line, other printings and related cards —
                  the same dialog the Cards page uses. */}
              <button
                type="button"
                aria-label={`Details for ${card.name}`}
                title={`Details for ${card.name}`}
                onClick={() => setInspecting(card)}
                className="absolute top-1 right-1 rounded-full bg-background/85 p-1 text-muted-foreground hover:text-foreground"
              >
                <Info className="size-3.5" />
              </button>
              </div>
            );
          })}
        </div>
      )}

      <CardDialog
        card={inspecting}
        onClose={() => setInspecting(null)}
        allCards={catalog}
        onSelect={setInspecting}
        // Adding from the dialog keeps it open, so an evolution line can be built
        // in one visit instead of reopening the dialog per card.
        onAdd={disabled ? undefined : onAdd}
        canAdd={(c) => countFor(c) < MAX_COPIES_PER_NAME}
      />

      {shown < ordered.length ? (
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
