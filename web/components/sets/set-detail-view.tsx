"use client";

import { useMemo, useState } from "react";

import { CardGrid } from "@/components/cards/card-grid";
import {
  SetScopeToggle,
  type SetScope,
} from "@/components/sets/set-scope-toggle";
import { CountUp } from "@/components/ui/count-up";
import { isBaseRarity } from "@/lib/domain/rarity";
import type { CatalogCard } from "@/types";

/**
 * A single set's card grid with a Full-set / Base-set toggle. Base scope shows
 * only base-rarity cards and counts owned/total over that subset.
 */
export function SetDetailView({ cards }: { cards: CatalogCard[] }) {
  const [scope, setScope] = useState<SetScope>("total");

  const shown = useMemo(
    () => (scope === "base" ? cards.filter((c) => isBaseRarity(c.rarity)) : cards),
    [cards, scope],
  );

  const owned = shown.filter((c) => c.owned > 0).length;
  const ratio = shown.length > 0 ? owned / shown.length : 0;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm text-muted-foreground tabular-nums">
          <CountUp value={owned} /> / {shown.length} owned (
          <CountUp value={ratio * 100} format={(n) => `${Math.round(n)}%`} />)
        </p>
        <SetScopeToggle scope={scope} onChange={setScope} />
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-muted">
        <div
          className="h-full rounded-full bg-primary transition-[width] duration-500 ease-out"
          style={{ width: `${ratio * 100}%` }}
        />
      </div>
      <CardGrid cards={shown} />
    </div>
  );
}
