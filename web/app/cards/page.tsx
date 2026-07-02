import {
  CardsBrowser,
  type CardsFilter,
} from "@/components/cards/cards-browser";
import { dataSource } from "@/lib/data";

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
