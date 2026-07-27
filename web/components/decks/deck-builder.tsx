"use client";

import { useMemo, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Minus, Plus, Save, Search } from "lucide-react";

import { CardImage } from "@/components/cards/card-image";
import { TypeSymbol } from "@/components/cards/type-symbol";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { saveDeck } from "@/app/decks/actions";
import {
  DECK_SIZE,
  MAX_ENERGY_TYPES,
  SELECTABLE_ENERGY_TYPES,
  deckCardCount,
  deckSummary,
  isDeckLegal,
  validateDeck,
  type Deck,
  type DeckIssue,
  type DeckSlot,
  type DeckSummary,
} from "@/lib/domain/deck";
import { cn } from "@/lib/utils";
import type { CatalogCard, DeckCardRef, StoredDeck } from "@/types";

const coord = (c: { set_code: string; card_number: number }) =>
  `${c.set_code}:${c.card_number}`;

/**
 * The deck builder.
 *
 * All legality logic comes from lib/domain/deck.ts — this component only
 * collects input and renders what the rules engine says. Validation runs on
 * every change rather than on save, so the deck tells you what's wrong while
 * you build it.
 */
export function DeckBuilder({
  catalog,
  existing,
  canEdit,
}: {
  catalog: CatalogCard[];
  existing: StoredDeck | null;
  canEdit: boolean;
}) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState(existing?.name ?? "New deck");
  const [query, setQuery] = useState("");

  const byCoord = useMemo(
    () => new Map(catalog.map((c) => [coord(c), c])),
    [catalog],
  );

  const [counts, setCounts] = useState<Map<string, number>>(() => {
    const initial = new Map<string, number>();
    for (const ref of existing?.cards ?? []) {
      initial.set(coord(ref), ref.count);
    }
    return initial;
  });
  const [energyTypes, setEnergyTypes] = useState<string[]>(
    existing?.energy_types ?? [],
  );

  const deck: Deck = useMemo(() => {
    const entries: DeckSlot[] = [];
    for (const [key, count] of counts) {
      const card = byCoord.get(key);
      if (card && count > 0) entries.push({ card, count });
    }
    return { entries, energyTypes };
  }, [counts, byCoord, energyTypes]);

  const issues = useMemo(() => validateDeck(deck), [deck]);
  const summary = useMemo(() => deckSummary(deck, catalog), [deck, catalog]);
  const total = deckCardCount(deck);
  const legal = isDeckLegal(deck);

  function adjust(card: CatalogCard, delta: number) {
    setCounts((prev) => {
      const next = new Map(prev);
      const key = coord(card);
      const value = (next.get(key) ?? 0) + delta;
      if (value <= 0) next.delete(key);
      else next.set(key, value);
      return next;
    });
  }

  function toggleEnergy(type: string) {
    setEnergyTypes((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type],
    );
  }

  function onSave() {
    setError(null);
    const cards: DeckCardRef[] = deck.entries.map((e) => ({
      set_code: e.card.set_code,
      card_number: e.card.card_number,
      count: e.count,
    }));
    startTransition(async () => {
      const res = await saveDeck(existing?.id ?? null, {
        name,
        cards,
        energyTypes,
      });
      if (!res.ok) {
        setError(res.error);
        return;
      }
      router.push(`/decks/${res.id}`);
    });
  }

  // Search is capped: the picker is a browsing aid, not a second /cards page.
  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return [];
    return catalog.filter((c) => c.name.toLowerCase().includes(q)).slice(0, 36);
  }, [catalog, query]);

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_22rem]">
      <div className="space-y-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Add cards</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <label className="flex items-center gap-2 rounded-md border px-3">
              <Search className="size-4 shrink-0 text-muted-foreground" />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search cards by name…"
                aria-label="Search cards by name"
                className="h-10 w-full bg-transparent text-sm outline-none"
              />
            </label>

            {query.trim() && results.length === 0 ? (
              <p className="text-sm text-muted-foreground">No cards match.</p>
            ) : null}

            <div className="grid grid-cols-3 gap-3 sm:grid-cols-5 lg:grid-cols-6">
              {results.map((card) => (
                <PickerTile
                  key={coord(card)}
                  card={card}
                  count={counts.get(coord(card)) ?? 0}
                  disabled={!canEdit}
                  onAdd={() => adjust(card, 1)}
                />
              ))}
            </div>
          </CardContent>
        </Card>

        <DeckList deck={deck} canEdit={canEdit} onAdjust={adjust} />
      </div>

      <div className="space-y-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center justify-between gap-2 text-base">
              <span>Deck</span>
              <Badge variant={total === DECK_SIZE ? "secondary" : "outline"}>
                {total} / {DECK_SIZE}
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              aria-label="Deck name"
              disabled={!canEdit}
              className="h-10 w-full rounded-md border bg-transparent px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />

            <div className="space-y-2">
              <p className="text-xs font-medium text-muted-foreground">
                Energy Zone ({energyTypes.length}/{MAX_ENERGY_TYPES})
              </p>
              <div className="flex flex-wrap gap-1.5">
                {SELECTABLE_ENERGY_TYPES.map((type) => (
                  <button
                    key={type}
                    type="button"
                    disabled={!canEdit}
                    onClick={() => toggleEnergy(type)}
                    aria-pressed={energyTypes.includes(type)}
                    title={type}
                    className={cn(
                      "flex size-9 items-center justify-center rounded-full border transition-colors",
                      energyTypes.includes(type)
                        ? "border-primary bg-primary/10"
                        : "opacity-50 hover:opacity-100",
                    )}
                  >
                    <TypeSymbol type={type} />
                  </button>
                ))}
              </div>
            </div>

            <IssueList issues={issues} />

            {canEdit ? (
              <div className="space-y-2">
                <Button onClick={onSave} disabled={pending} className="w-full">
                  <Save className="size-4" />
                  {pending ? "Saving…" : existing ? "Save changes" : "Save deck"}
                </Button>
                {!legal ? (
                  <p className="text-xs text-muted-foreground">
                    You can save an incomplete deck and finish it later.
                  </p>
                ) : null}
                {error ? <p className="text-xs text-destructive">{error}</p> : null}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">
                Sign in as the owner to edit decks.
              </p>
            )}
          </CardContent>
        </Card>

        <SummaryCard summary={summary} />
      </div>
    </div>
  );
}

function PickerTile({
  card,
  count,
  disabled,
  onAdd,
}: {
  card: CatalogCard;
  count: number;
  disabled: boolean;
  onAdd: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onAdd}
      disabled={disabled}
      title={`Add ${card.name}`}
      className="flex flex-col text-left disabled:opacity-60"
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
    </button>
  );
}

function DeckList({
  deck,
  canEdit,
  onAdjust,
}: {
  deck: Deck;
  canEdit: boolean;
  onAdjust: (card: CatalogCard, delta: number) => void;
}) {
  if (deck.entries.length === 0) {
    return (
      <Card>
        <CardContent className="py-10 text-center text-sm text-muted-foreground">
          Search above to add your first card.
        </CardContent>
      </Card>
    );
  }
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Cards in this deck</CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="divide-y">
          {deck.entries.map(({ card, count }) => (
            <li key={coord(card)} className="flex items-center gap-3 py-2">
              <div className="aspect-[5/7] w-9 shrink-0 overflow-hidden rounded border">
                <CardImage card={card} />
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium">{card.name}</p>
                <p className="text-xs text-muted-foreground">
                  {card.set_code} · {card.stage ?? card.trainer_subtype ?? "—"}
                </p>
              </div>
              <div className="flex items-center gap-1">
                <Button
                  variant="ghost"
                  size="icon-sm"
                  aria-label={`Remove one ${card.name}`}
                  disabled={!canEdit}
                  onClick={() => onAdjust(card, -1)}
                >
                  <Minus className="size-4" />
                </Button>
                <span className="w-6 text-center text-sm font-semibold tabular-nums">
                  {count}
                </span>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  aria-label={`Add one ${card.name}`}
                  disabled={!canEdit}
                  onClick={() => onAdjust(card, 1)}
                >
                  <Plus className="size-4" />
                </Button>
              </div>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

function IssueList({ issues }: { issues: DeckIssue[] }) {
  if (issues.length === 0) {
    return (
      <p className="rounded-md bg-primary/10 px-3 py-2 text-xs font-medium text-primary">
        This deck is legal.
      </p>
    );
  }
  return (
    <ul className="space-y-1.5">
      {issues.map((issue) => (
        <li
          key={issue.code}
          className={cn(
            "rounded-md px-3 py-2 text-xs",
            issue.severity === "error"
              ? "bg-destructive/10 text-destructive"
              : "bg-muted text-muted-foreground",
          )}
        >
          {issue.message}
        </li>
      ))}
    </ul>
  );
}

function SummaryCard({ summary }: { summary: DeckSummary }) {
  const stages = Object.entries(summary.stageCounts);
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Summary</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <Line label="Pokémon" value={String(summary.pokemon)} />
        <Line label="Trainers" value={String(summary.trainers)} />
        {stages.map(([stage, n]) => (
          <Line key={stage} label={stage} value={String(n)} muted />
        ))}
        <Line
          label="Avg Pokémon power"
          value={summary.averagePokemonPower?.toFixed(1) ?? "—"}
        />
        {/* Labelled apart from power on purpose — different model, different scale. */}
        <Line
          label="Avg Trainer utility"
          value={summary.averageTrainerUtility?.toFixed(1) ?? "—"}
        />
        {summary.missing.length > 0 ? (
          <div className="space-y-1 border-t pt-3">
            <p className="text-xs font-medium text-muted-foreground">
              You&rsquo;re short {summary.missing.length}{" "}
              {summary.missing.length === 1 ? "card" : "cards"}
            </p>
            <ul className="space-y-0.5">
              {summary.missing.slice(0, 6).map((m) => (
                <li key={m.name} className="flex justify-between text-xs">
                  <span className="truncate">{m.name}</span>
                  <span className="tabular-nums text-muted-foreground">
                    {m.owned}/{m.needed}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

function Line({
  label,
  value,
  muted,
}: {
  label: string;
  value: string;
  muted?: boolean;
}) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span
        className={cn(
          "text-xs",
          muted ? "text-muted-foreground/70" : "text-muted-foreground",
        )}
      >
        {label}
      </span>
      <span className="font-medium tabular-nums">{value}</span>
    </div>
  );
}
