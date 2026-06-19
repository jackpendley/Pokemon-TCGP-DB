import { CardsBrowser } from "@/components/cards/cards-browser";
import { dataSource } from "@/lib/data";
import { formatNumber } from "@/lib/domain/format";

export const dynamic = "force-dynamic";
export const metadata = { title: "Cards · TCGP Optimizer" };

export default async function CardsPage() {
  const catalog = await dataSource.getCatalog();
  const owned = catalog.filter((c) => c.owned > 0).length;

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">Cards</h1>
        <p className="text-sm text-muted-foreground">
          {formatNumber(owned)} of {formatNumber(catalog.length)} unique cards
          owned
        </p>
      </header>

      <CardsBrowser cards={catalog} />
    </div>
  );
}
