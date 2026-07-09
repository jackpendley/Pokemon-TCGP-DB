import {
  CardsBrowser,
  type CardsFilter,
} from "@/components/cards/cards-browser";
import { dataSource } from "@/lib/data";

// Pages render per-request (not ISR): pipeline artifacts are gitignored, so CI
// and fresh checkouts build without them — prerendering would fail there. The
// mtime-keyed cache in lib/data/local-json.ts makes the per-request cost a few
// fs.stat calls; the full-catalog RSC payload this page ships is a localhost
// concern only until the hosted phase (docs/hosting-roadmap.md), where this
// should move to cached rendering with on-demand invalidation.
export const dynamic = "force-dynamic";
export const metadata = { title: "Cards · TCGP Optimizer" };

export default async function CardsPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const [catalog, sp] = await Promise.all([
    dataSource.getCatalog(),
    searchParams,
  ]);

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

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold tracking-tight">Cards</h1>
      <CardsBrowser cards={catalog} initial={initial} />
    </div>
  );
}
