import { CompletionCard } from "@/components/dashboard/completion-card";
import { CountGrid, type CountItem } from "@/components/dashboard/count-grid";
import {
  NextToOpen,
  type NextPackEntry,
} from "@/components/dashboard/next-to-open";
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
  const [summary, packEv, catalog, sync, syncEnabled] = await Promise.all([
    dataSource.getCollectionSummary(),
    dataSource.getPackEv(),
    dataSource.getCatalog(),
    dataSource.getSyncStatus(),
    isSyncEnabled(),
  ]);

  const { stats, reviewQueue, delta, history } = sync;

  // "What to open next": every purchasable pack (so series/type filters have the
  // full set to work with), joined to its strongest unowned pull targets resolved
  // to full catalog cards (types + enlarge info). Ranking happens client-side.
  const catalogByCoord = new Map(
    catalog.map((c) => [`${c.set_code}:${c.card_number}`, c]),
  );
  const nextEntries: NextPackEntry[] = packEv.packs
    .filter((p) => p.purchasable && !p.blocked)
    .map((pack) => ({
      pack,
      targets: pack.top_power_cards
        .map((t) => catalogByCoord.get(`${t.set_code}:${t.card_number}`))
        .filter((c): c is NonNullable<typeof c> => c != null),
    }));
  const currency = stats
    ? {
        pack_hourglasses: stats.pack_hourglasses,
        wonder_hourglasses: stats.wonder_hourglasses,
        shop_tickets: stats.shop_tickets,
      }
    : null;

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

      {/* State band: completion ring beside the headline total. */}
      <section className="grid gap-4 lg:grid-cols-2">
        <CompletionCard
          total={{ owned: totalOwned, total: catalog.length }}
          base={{ owned: baseOwned, total: baseCards.length }}
          recentGain={recentGain}
        />
        <Card className="ring-2 ring-primary/30">
          <CardContent className="flex h-full flex-col items-center justify-center py-2 text-center">
            <div className="text-7xl font-bold tabular-nums leading-none text-primary">
              {formatNumber(summary.total_quantity)}
            </div>
            <div className="mt-3 text-sm font-medium text-muted-foreground">
              Total cards
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              {formatNumber(summary.unique_entries)} unique entries
            </p>
          </CardContent>
        </Card>
      </section>

      {/* Centerpiece: what to open next (filters + pack-hourglass balance). */}
      <NextToOpen entries={nextEntries} currency={currency} />

      {/* Collection: secondary counts, then compact type/rarity/stage breakdowns. */}
      <section className="space-y-4">
        <h2 className="text-lg font-medium">Collection</h2>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <StatCard
            title="Pokémon"
            value={formatNumber(summary.by_card_type.Pokemon ?? 0)}
            href="/cards?category=Pokemon"
            align="center"
          />
          <StatCard
            title="Trainers"
            value={formatNumber(summary.by_card_type.Trainer ?? 0)}
            href="/cards?category=Trainer"
            align="center"
          />
          <StatCard
            title="ex cards"
            value={formatNumber(summary.ex_quantity)}
            hint={`${formatNumber(summary.ex_entries)} unique`}
            href="/cards?class=ex"
            align="center"
          />
          <StatCard
            title="Mega ex cards"
            value={formatNumber(megaQuantity)}
            hint={`${formatNumber(megaUnique)} of ${formatNumber(megaCards.length)} unique`}
            href="/cards?class=mega"
            align="center"
          />
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">By type</CardTitle>
            </CardHeader>
            <CardContent>
              <TypePieChart data={summary.by_pokemon_type} />
            </CardContent>
          </Card>
          <CountGrid title="By rarity · collected" items={rarityItems} />
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
