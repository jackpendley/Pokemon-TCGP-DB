import { Suspense } from "react";
import { connection } from "next/server";

import { SetsGrid, type SetProgress } from "@/components/sets/sets-grid";
import { Skeleton } from "@/components/ui/skeleton";
import { getCachedCatalog } from "@/lib/data/cached";
import { isBaseRarity } from "@/lib/domain/rarity";

export const metadata = { title: "Sets · TCGP Optimizer" };

async function SetsContent() {
  await connection();
  const catalog = await getCachedCatalog();

  // Preserve first-seen order (≈ release order) while aggregating per set.
  const bySet = new Map<string, SetProgress>();
  for (const c of catalog) {
    let s = bySet.get(c.set_code);
    if (!s) {
      s = {
        set_code: c.set_code,
        expansion: c.expansion,
        total: 0,
        owned: 0,
        baseTotal: 0,
        baseOwned: 0,
      };
      bySet.set(c.set_code, s);
    }
    s.total += 1;
    if (c.owned > 0) s.owned += 1;
    if (isBaseRarity(c.rarity)) {
      s.baseTotal += 1;
      if (c.owned > 0) s.baseOwned += 1;
    }
  }
  const sets = [...bySet.values()];

  return (
    <>
      <p className="text-sm text-muted-foreground">
        Unique cards owned per set ({sets.length} sets). Toggle between the full
        set and the base set (no secret/chase rarities).
      </p>
      <SetsGrid sets={sets} />
    </>
  );
}

export default function SetsPage() {
  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">Set Completion</h1>
      </header>
      <Suspense fallback={<Skeleton className="h-96 w-full" />}>
        <SetsContent />
      </Suspense>
    </div>
  );
}
