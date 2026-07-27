"use client";

import { useMemo, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Save } from "lucide-react";

import { DeckPicker } from "@/components/decks/deck-picker";
import { DeckSlots } from "@/components/decks/deck-slots";
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

  /** Copies held of a card's *name* — the limit is per name, not per printing. */
  const countByName = useMemo(() => {
    const by = new Map<string, number>();
    for (const { card, count } of deck.entries) {
      by.set(card.name, (by.get(card.name) ?? 0) + count);
    }
    return by;
  }, [deck]);

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_22rem]">
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
          <CardContent>
            <DeckSlots
              deck={deck}
              canEdit={canEdit}
              onRemove={(card) => adjust(card, -1)}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Add cards</CardTitle>
          </CardHeader>
          <CardContent>
            <DeckPicker
              catalog={catalog}
              countFor={(card) => countByName.get(card.name) ?? 0}
              disabled={!canEdit}
              onAdd={(card) => adjust(card, 1)}
            />
          </CardContent>
        </Card>
      </div>

      <div className="space-y-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Details</CardTitle>
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
