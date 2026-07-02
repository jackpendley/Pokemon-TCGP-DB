import Link from "next/link";

import { CompletionCard } from "@/components/dashboard/completion-card";
import { CountGrid, type CountItem } from "@/components/dashboard/count-grid";
import { NextPackCard } from "@/components/dashboard/next-pack-card";
import { RaritySymbol } from "@/components/dashboard/rarity-symbol";
import { StatCard } from "@/components/dashboard/stat-card";
import { TypePieChart } from "@/components/dashboard/type-pie-chart";
import { SyncButton } from "@/components/sync/sync-button";
import {
  SyncHistory,
  type HistoryEntryView,
} from "@/components/sync/sync-history";
import {
  SyncReveal,
  type AdditionItem,
  type SetProgressItem,
} from "@/components/sync/sync-reveal";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { dataSource } from "@/lib/data";
import { isSyncEnabled } from "@/app/sync/actions";
import { isMegaEx } from "@/lib/domain/card";
import { formatNumber, titleCase } from "@/lib/domain/format";
import { compareRarity, isBaseRarity } from "@/lib/domain/rarity";
import type { SyncDeltaEntry } from "@/types";

export const dynamic = "force-dynamic";

const STAGE_ORDER = ["Basic", "Stage1", "Stage2", "Stage3"];
const stageLabel = (s: string) => s.replace(/^Stage(\d)/, "Stage $1");
// Animate sync results on the dashboard only right after a sync, not every visit.
const RECENT_SYNC_MS = 10 * 60 * 1000;

export default async function DashboardPage() {
  const [summary, recs, packEv, catalog, sync, syncEnabled] = await Promise.all([
    dataSource.getCollectionSummary(),
    dataSource.getRecommendations(),
    dataSource.getPackEv(),
    dataSource.getCatalog(),
    dataSource.getSyncStatus(),
    isSyncEnabled(),
  ]);

  const { stats, reviewQueue, delta, history } = sync;

  // "What to open next": the top unified picks, each joined to its strongest
  // unowned pull targets (top_power_cards live on pack_ev, not recommendations).
  const powerByPack = new Map(
    packEv.packs.map((p) => [p.pack_name, p.top_power_cards]),
  );
  const topPacks = recs.top_packs_unified.slice(0, 3);

  // Completion — derived web-side from the catalog (owned counts merged in).
  const totalOwned = catalog.filter((c) => c.owned > 0).length;
  const baseCards = catalog.filter((c) => isBaseRarity(c.rarity));
  const baseOwned = baseCards.filter((c) => c.owned > 0).length;

  const megaCards = catalog.filter(isMegaEx);
  const megaQuantity = megaCards.reduce((n, c) => n + c.owned, 0);
  const megaUnique = megaCards.filter((c) => c.owned > 0).length;

  // Per-rarity collected (unique owned / total).
  const byRarity = new Map<string, { owned: number; total: number }>();
  for (const c of catalog) {
    const key = c.rarity ?? "unknown";
    const e = byRarity.get(key) ?? { owned: 0, total: 0 };
    e.total += 1;
    if (c.owned > 0) e.owned += 1;
    byRarity.set(key, e);
  }
  const rarityItems: CountItem[] = [...byRarity.keys()]
    .sort(compareRarity)
    .map((rarity) => ({
      key: rarity,
      label: titleCase(rarity),
      value: byRarity.get(rarity)!.owned,
      total: byRarity.get(rarity)!.total,
      icon: <RaritySymbol rarity={rarity} />,
      href: `/cards?rarity=${encodeURIComponent(rarity)}`,
    }));

  // Per-stage collected (unique owned / total) — same shape as rarity.
  const byStage = new Map<string, { owned: number; total: number }>();
  for (const c of catalog) {
    if (!c.stage) continue;
    const e = byStage.get(c.stage) ?? { owned: 0, total: 0 };
    e.total += 1;
    if (c.owned > 0) e.owned += 1;
    byStage.set(c.stage, e);
  }
  const stageItems: CountItem[] = [...byStage.keys()]
    .sort(
      (a, b) =>
        (STAGE_ORDER.indexOf(a) === -1 ? 99 : STAGE_ORDER.indexOf(a)) -
        (STAGE_ORDER.indexOf(b) === -1 ? 99 : STAGE_ORDER.indexOf(b)),
    )
    .map((stage) => ({
      key: stage,
      label: stageLabel(stage),
      value: byStage.get(stage)!.owned,
      total: byStage.get(stage)!.total,
      href: `/cards?stage=${encodeURIComponent(stage)}`,
    }));

  // ── Sync data surfaced on the dashboard ────────────────────────────────
  const byCoord = new Map(
    catalog.map((c) => [`${c.set_code}:${c.card_number}`, c]),
  );
  const join = (entry: SyncDeltaEntry): AdditionItem => ({
    entry,
    card: byCoord.get(`${entry.set_code}:${entry.card_number}`) ?? null,
  });
  const additions: AdditionItem[] = (delta?.added ?? []).map(join);
  const historyEntries: HistoryEntryView[] = [...history].reverse().map((h) => ({
    syncedAt: h.synced_at,
    addedCount: h.added_count,
    items: h.added.map(join),
  }));
  const reviewItems = reviewQueue
    ? reviewQueue.new_cards.length +
      reviewQueue.ambiguous_matches.length +
      reviewQueue.missing_from_pz.length
    : 0;

  const setTotals = new Map<string, { total: number; owned: number; expansion: string }>();
  for (const c of catalog) {
    const s = setTotals.get(c.set_code) ?? { total: 0, owned: 0, expansion: c.expansion };
    s.total += 1;
    if (c.owned > 0) s.owned += 1;
    setTotals.set(c.set_code, s);
  }
  const gainedBySet = new Map<string, number>();
  for (const e of delta?.added ?? []) {
    if (e.is_new && e.set_code)
      gainedBySet.set(e.set_code, (gainedBySet.get(e.set_code) ?? 0) + 1);
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

  // Request-time check in this async Server Component; the purity rule targets
  // client render, where Date.now() would be non-deterministic.
  // eslint-disable-next-line react-hooks/purity
  const now = Date.now();
  const isRecentSync =
    !!stats && now - new Date(stats.fetched_at).getTime() < RECENT_SYNC_MS;
  const newOnes = additions.filter((a) => a.entry.is_new);
  const newUnique = {
    total: newOnes.length,
    base: newOnes.filter((a) => isBaseRarity(a.card?.rarity ?? null)).length,
  };
  const recentGain = isRecentSync ? newUnique : undefined;
  const showReveal = isRecentSync && additions.length > 0;

  return (
    <div className="space-y-8">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
          <p className="text-sm text-muted-foreground">
            {stats
              ? `Last synced ${new Date(stats.fetched_at).toLocaleString()}`
              : `Collection snapshot · updated ${summary.meta.last_updated}`}
          </p>
        </div>
        <SyncButton enabled={syncEnabled} />
      </header>

      {/* Right after a sync: the cards you just got, with the reveal animation. */}
      {showReveal ? (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center justify-between text-base">
              <span>Added in your latest sync</span>
              {delta ? (
                <Badge variant="secondary">{delta.added_count} cards</Badge>
              ) : null}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <SyncReveal
              key={stats?.fetched_at}
              items={additions}
              setProgress={setProgress}
            />
          </CardContent>
        </Card>
      ) : null}

      {/* State band: completion ring · headline total · spendable currency. */}
      <section className="grid gap-4 lg:grid-cols-3">
        <CompletionCard
          total={{ owned: totalOwned, total: catalog.length }}
          base={{ owned: baseOwned, total: baseCards.length }}
          recentGain={recentGain}
        />
        <Card className="ring-2 ring-primary/30">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total cards
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-4xl font-bold tabular-nums text-primary">
              {formatNumber(summary.total_quantity)}
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              {formatNumber(summary.unique_entries)} unique entries
            </p>
          </CardContent>
        </Card>
        {stats ? (
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Currency
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="flex items-baseline justify-between">
                <span className="text-sm text-muted-foreground">
                  Pack hourglasses
                </span>
                <span className="text-2xl font-semibold tabular-nums text-primary">
                  {formatNumber(stats.pack_hourglasses)}
                </span>
              </div>
              <div className="flex items-baseline justify-between text-sm">
                <span className="text-muted-foreground">Wonder hourglasses</span>
                <span className="tabular-nums">
                  {formatNumber(stats.wonder_hourglasses)}
                </span>
              </div>
              <div className="flex items-baseline justify-between text-sm">
                <span className="text-muted-foreground">Shop tickets</span>
                <span className="tabular-nums">
                  {formatNumber(stats.shop_tickets)}
                </span>
              </div>
            </CardContent>
          </Card>
        ) : (
          <StatCard
            title="Unique entries"
            value={formatNumber(summary.unique_entries)}
            hint={`${formatNumber(summary.ex_quantity)} ex cards`}
          />
        )}
      </section>

      {/* Centerpiece: what to open next. */}
      {topPacks.length > 0 ? (
        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-medium">What to open next</h2>
            <Link
              href="/packs"
              className="text-sm font-medium text-primary hover:underline"
            >
              View all packs →
            </Link>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {topPacks.map((p, i) => (
              <NextPackCard
                key={p.pack_name}
                pack={p}
                powerCards={powerByPack.get(p.pack_name) ?? []}
                rank={i + 1}
              />
            ))}
          </div>
        </section>
      ) : null}

      {/* Collection: secondary counts, then compact type/rarity/stage breakdowns. */}
      <section className="space-y-4">
        <h2 className="text-lg font-medium">Collection</h2>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <StatCard
            title="Pokémon"
            value={formatNumber(summary.by_card_type.Pokemon ?? 0)}
          />
          <StatCard
            title="Trainers"
            value={formatNumber(summary.by_card_type.Trainer ?? 0)}
          />
          <StatCard
            title="ex cards"
            value={formatNumber(summary.ex_quantity)}
            hint={`${formatNumber(summary.ex_entries)} unique`}
          />
          <StatCard
            title="Mega ex cards"
            value={formatNumber(megaQuantity)}
            hint={`${formatNumber(megaUnique)} of ${formatNumber(megaCards.length)} unique`}
          />
        </div>
        <div className="grid gap-4 lg:grid-cols-3">
          <Card className="lg:col-span-1">
            <CardHeader className="pb-2">
              <CardTitle className="text-base">By type</CardTitle>
            </CardHeader>
            <CardContent>
              <TypePieChart data={summary.by_pokemon_type} />
            </CardContent>
          </Card>
          <CountGrid
            title="By rarity · collected"
            items={rarityItems}
            className="lg:col-span-2"
          />
        </div>
        <CountGrid title="By stage · collected" items={stageItems} />
      </section>

      {/* Recent activity: sync history (+ review-queue chip). */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center justify-between gap-2 text-base">
            <span>Sync history</span>
            <span className="flex items-center gap-2">
              {reviewItems > 0 ? (
                <Badge variant="outline">{reviewItems} to review</Badge>
              ) : null}
              {history.length > 0 ? (
                <Badge variant="secondary">{history.length} syncs</Badge>
              ) : null}
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <SyncHistory entries={historyEntries} />
        </CardContent>
      </Card>
    </div>
  );
}
