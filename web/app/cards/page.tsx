import {
  CardsBrowser,
  type CardsFilter,
} from "@/components/cards/cards-browser";
import { dataSource } from "@/lib/data";
import { formatNumber } from "@/lib/domain/format";

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
  const owned = catalog.filter((c) => c.owned > 0).length;

  const pick = (k: string): string | undefined =>
    typeof sp[k] === "string" ? (sp[k] as string) : undefined;
  const initial: CardsFilter = {
    q: pick("q"),
    set: pick("set"),
    type: pick("type"),
    rarity: pick("rarity"),
    stage: pick("stage"),
    class: pick("class"),
    owned: pick("owned"),
  };

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">Cards</h1>
        <p className="text-sm text-muted-foreground">
          {formatNumber(owned)} of {formatNumber(catalog.length)} unique cards
          owned
        </p>
      </header>

      <CardsBrowser cards={catalog} initial={initial} />
    </div>
  );
}
