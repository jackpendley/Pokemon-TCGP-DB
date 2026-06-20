import { StatCard } from "@/components/dashboard/stat-card";
import { SyncButton } from "@/components/sync/sync-button";
import {
  SyncReveal,
  type AdditionItem,
  type SetProgressItem,
} from "@/components/sync/sync-reveal";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { dataSource } from "@/lib/data";
import { formatNumber } from "@/lib/domain/format";
import { isSyncEnabled } from "@/app/sync/actions";

export const dynamic = "force-dynamic";
export const metadata = { title: "Sync Status · TCGP Optimizer" };

export default async function SyncPage() {
  const [{ stats, reviewQueue, delta }, enabled, catalog] = await Promise.all([
    dataSource.getSyncStatus(),
    isSyncEnabled(),
    dataSource.getCatalog(),
  ]);

  const reviewItems = reviewQueue
    ? reviewQueue.new_cards.length +
      reviewQueue.ambiguous_matches.length +
      reviewQueue.missing_from_pz.length
    : 0;

  // Join the sync delta to the catalog (for images/type) by coordinate.
  const byCoord = new Map(
    catalog.map((c) => [`${c.set_code}:${c.card_number}`, c]),
  );
  const additions: AdditionItem[] = (delta?.added ?? []).map((entry) => ({
    entry,
    card: byCoord.get(`${entry.set_code}:${entry.card_number}`) ?? null,
  }));

  // Per-set completion gain: a card going 0→owned (is_new) adds one unique to
  // its set. "after" is current owned-unique from the catalog; "before" backs
  // out this sync's new uniques.
  const setTotals = new Map<string, { total: number; owned: number; expansion: string }>();
  for (const c of catalog) {
    const s = setTotals.get(c.set_code) ?? {
      total: 0,
      owned: 0,
      expansion: c.expansion,
    };
    s.total += 1;
    if (c.owned > 0) s.owned += 1;
    setTotals.set(c.set_code, s);
  }
  const gainedBySet = new Map<string, number>();
  for (const e of delta?.added ?? []) {
    if (e.is_new && e.set_code) {
      gainedBySet.set(e.set_code, (gainedBySet.get(e.set_code) ?? 0) + 1);
    }
  }
  const setProgress: SetProgressItem[] = [...gainedBySet.entries()]
    .map(([set_code, gained]) => {
      const t = setTotals.get(set_code);
      const after = t?.owned ?? 0;
      return {
        set_code,
        expansion: t?.expansion ?? set_code,
        total: t?.total ?? 0,
        after,
        before: Math.max(0, after - gained),
        gained,
      };
    })
    .sort((a, b) => b.gained - a.gained);

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

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center justify-between text-base">
            <span>Added in the last sync</span>
            {delta ? (
              <Badge variant="secondary">{delta.added_count} cards</Badge>
            ) : null}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {!delta ? (
            <p className="text-sm text-muted-foreground">
              No sync has run yet — added cards will appear here after your next
              sync.
            </p>
          ) : (
            <SyncReveal items={additions} setProgress={setProgress} />
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
