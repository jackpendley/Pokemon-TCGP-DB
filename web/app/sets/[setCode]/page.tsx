import Link from "next/link";
import { notFound } from "next/navigation";

import { SetDetailView } from "@/components/sets/set-detail-view";
import { dataSource } from "@/lib/data";

export const dynamic = "force-dynamic";

export default async function SetDetailPage({
  params,
}: {
  params: Promise<{ setCode: string }>;
}) {
  const { setCode } = await params;
  const decoded = decodeURIComponent(setCode);

  const catalog = await dataSource.getCatalog();
  const cards = catalog
    .filter((c) => c.set_code === decoded)
    .sort((a, b) => a.card_number - b.card_number);

  if (cards.length === 0) notFound();

  return (
    <div className="space-y-6">
      <div>
        <Link
          href="/sets"
          className="text-sm text-muted-foreground hover:underline"
        >
          ← Sets
        </Link>
        <h1 className="mt-2 flex items-baseline gap-3 text-2xl font-semibold tracking-tight">
          {cards[0].expansion}
          <span className="text-base font-normal text-muted-foreground">
            {decoded}
          </span>
        </h1>
      </div>

      <SetDetailView cards={cards} />
    </div>
  );
}
