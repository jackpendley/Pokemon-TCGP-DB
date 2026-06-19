import { StatCard } from "@/components/dashboard/stat-card";
import { SyncButton } from "@/components/sync/sync-button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { dataSource } from "@/lib/data";
import { formatNumber } from "@/lib/domain/format";
import { isSyncEnabled } from "@/app/sync/actions";

export const dynamic = "force-dynamic";
export const metadata = { title: "Sync Status · TCGP Optimizer" };

export default async function SyncPage() {
  const [{ stats, reviewQueue }, enabled] = await Promise.all([
    dataSource.getSyncStatus(),
    isSyncEnabled(),
  ]);

  const reviewItems = reviewQueue
    ? reviewQueue.new_cards.length +
      reviewQueue.ambiguous_matches.length +
      reviewQueue.missing_from_pz.length
    : 0;

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">Sync Status</h1>
          <p className="text-sm text-muted-foreground">
            {stats
              ? `Last synced ${new Date(stats.fetched_at).toLocaleString()}`
              : "No sync data yet — run the pipeline to populate."}
          </p>
        </div>
        <SyncButton enabled={enabled} />
      </header>

      {stats ? (
        <section className="grid gap-4 sm:grid-cols-3">
          <StatCard
            title="Pack hourglasses"
            value={formatNumber(stats.pack_hourglasses)}
          />
          <StatCard
            title="Wonder hourglasses"
            value={formatNumber(stats.wonder_hourglasses)}
          />
          <StatCard
            title="Shop tickets"
            value={formatNumber(stats.shop_tickets)}
          />
        </section>
      ) : null}

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center justify-between text-base">
            <span>Review queue</span>
            {reviewQueue ? (
              <Badge variant={reviewItems === 0 ? "secondary" : "outline"}>
                {reviewItems === 0 ? "Clear" : `${reviewItems} items`}
              </Badge>
            ) : null}
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          {!reviewQueue ? (
            "No review queue file found."
          ) : reviewItems === 0 ? (
            "Nothing needs attention."
          ) : (
            <ul className="space-y-1">
              <li>New cards: {reviewQueue.new_cards.length}</li>
              <li>Ambiguous matches: {reviewQueue.ambiguous_matches.length}</li>
              <li>Missing from PZ: {reviewQueue.missing_from_pz.length}</li>
            </ul>
          )}
        </CardContent>
      </Card>

      <p className="text-xs text-muted-foreground">
        {enabled
          ? "Sync runs the local Python pipeline (scripts/run_recommendations.py) and refreshes the data when it finishes."
          : "Sync is available only in local dev; in production this is handled by the cloud sync worker."}
      </p>
    </div>
  );
}
