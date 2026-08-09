import { Suspense } from "react";

import {
  CardsBrowser,
  type CardsFilter,
} from "@/components/cards/cards-browser";
import { Skeleton } from "@/components/ui/skeleton";
import { CardTileGridSkeleton } from "@/components/ui/skeletons";
import { getCachedCatalog } from "@/lib/data/cached";

export const metadata = { title: "Cards · TCGP Optimizer" };

async function CardsContent({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  // Await searchParams (per-request) FIRST so prerender bails here — otherwise
  // getCachedCatalog() would run at build and fail on the local-json CI's
  // missing artifacts. At runtime this streams and the catalog read is a hit.
  const sp = await searchParams;
  const catalog = await getCachedCatalog();

  const pick = (k: string): string | undefined =>
    typeof sp[k] === "string" ? (sp[k] as string) : undefined;
  const initial: CardsFilter = {
    q: pick("q"),
    set: pick("set"),
    type: pick("type"),
    rarity: pick("rarity"),
    stage: pick("stage"),
    class: pick("class"),
    category: pick("category"),
    owned: pick("owned"),
    scope: pick("scope"),
    sort: pick("sort"),
  };

  return <CardsBrowser cards={catalog} initial={initial} />;
}

/**
 * Mirrors CardsBrowser's own layout — summary bar, filter chips, then the tile
 * grid at the same breakpoints as CardGrid — so the streamed content lands in
 * place instead of reflowing.
 */
function CardsBrowserSkeleton() {
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-lg border bg-card p-4">
        <div className="flex items-center gap-4">
          <Skeleton className="size-12 rounded-full" />
          <div className="space-y-2">
            <Skeleton className="h-6 w-32" />
            <Skeleton className="h-4 w-24" />
          </div>
        </div>
        <Skeleton className="h-8 w-40" />
      </div>
      <div className="flex flex-wrap gap-3">
        {[36, 28, 28, 24, 32, 24].map((w, i) => (
          <Skeleton key={i} className="h-9" style={{ width: `${w * 4}px` }} />
        ))}
      </div>
      <CardTileGridSkeleton
        count={24}
        className="grid-cols-3 gap-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 2xl:grid-cols-10"
      />
    </div>
  );
}

export default function CardsPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold tracking-tight">Cards</h1>
      <Suspense fallback={<CardsBrowserSkeleton />}>
        <CardsContent searchParams={searchParams} />
      </Suspense>
    </div>
  );
}
