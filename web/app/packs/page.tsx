import { PacksTable } from "@/components/packs/packs-table";
import { dataSource } from "@/lib/data";

export const dynamic = "force-dynamic";
export const metadata = { title: "Pack Recommendations · TCGP Optimizer" };

export default async function PacksPage() {
  const [packEv, recs] = await Promise.all([
    dataSource.getPackEv(),
    dataSource.getRecommendations(),
  ]);

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">
          Pack Recommendations
        </h1>
        <p className="text-sm text-muted-foreground">
          All {packEv.packs.length} packs ranked by unified score. Click a column
          to re-sort.
        </p>
        <p className="text-xs text-muted-foreground">{recs.disclaimer}</p>
      </header>

      <PacksTable packs={packEv.packs} />
    </div>
  );
}
