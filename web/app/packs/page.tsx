import { Suspense } from "react";
import { connection } from "next/server";

import { PacksTable } from "@/components/packs/packs-table";
import { TableSkeleton, TextLinesSkeleton } from "@/components/ui/skeletons";
import { getCachedPackEv, getCachedRecommendations } from "@/lib/data/cached";

export const metadata = { title: "Pack Recommendations · TCGP Optimizer" };

async function PacksContent() {
  // Runtime-only: skips prerender so the local-json CI build never reads the
  // gitignored artifacts; the cached reads below are hits in production.
  await connection();
  const [packEv, recs] = await Promise.all([
    getCachedPackEv(),
    getCachedRecommendations(),
  ]);

  // Exclude non-purchasable packs (e.g. "Deluxe Pack: ex"), which aren't a
  // normal hourglass purchase and would skew the ranking.
  const packs = packEv.packs.filter((p) => p.purchasable);

  return (
    <>
      <p className="text-sm text-muted-foreground">
        All {packs.length} purchasable packs ranked by unified score. Click a
        column to re-sort.
      </p>
      <p className="text-xs text-muted-foreground">{recs.disclaimer}</p>
      <PacksTable packs={packs} />
    </>
  );
}

export default function PacksPage() {
  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">
          Pack Recommendations
        </h1>
      </header>
      <Suspense
        fallback={
          <>
            <TextLinesSkeleton lines={2} width="w-[32rem] max-w-full" />
            <TableSkeleton rows={10} columns={6} />
          </>
        }
      >
        <PacksContent />
      </Suspense>
    </div>
  );
}
