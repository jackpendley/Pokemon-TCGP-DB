import { Suspense } from "react";

import {
  CardsBrowser,
  type CardsFilter,
} from "@/components/cards/cards-browser";
import { Skeleton } from "@/components/ui/skeleton";
import { getCachedCatalog } from "@/lib/data/cached";

export const metadata = { title: "Cards · TCGP Optimizer" };

async function CardsContent({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  // searchParams is per-request (dynamic), so this streams at runtime; the
  // catalog read below is a cache hit.
  const [catalog, sp] = await Promise.all([getCachedCatalog(), searchParams]);

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

export default function CardsPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold tracking-tight">Cards</h1>
      <Suspense fallback={<Skeleton className="h-96 w-full" />}>
        <CardsContent searchParams={searchParams} />
      </Suspense>
    </div>
  );
}
