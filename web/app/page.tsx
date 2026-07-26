import { Suspense } from "react";
import { connection } from "next/server";

import { CompletionCard } from "@/components/dashboard/completion-card";
import { CountGrid, type CountItem } from "@/components/dashboard/count-grid";
import { OwnerStatusCard } from "@/components/dashboard/owner-status-card";
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
import { SyncRevealDialog } from "@/components/sync/sync-reveal-dialog";
import { type AdditionItem } from "@/components/sync/sync-reveal";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  CountGridSkeleton,
  PanelSkeleton,
  StatTilesSkeleton,
  TextLinesSkeleton,
} from "@/components/ui/skeletons";
import {
  getCachedCatalog,
  getCachedCollectionSummary,
  getCachedPackEv,
  getCachedSyncStatus,
} from "@/lib/data/cached";
import { fetchOwnerSyncMeta } from "@/lib/data/supabase";
import { isOwner } from "@/lib/auth/server";
import { canTriggerSync, isSyncEnabled } from "@/app/sync/actions";
import {
  buildSetTotals,
  completionStats,
  indexByCoord,
  lookupCoord,
  megaStats,
  nextPackEntries,
  ownedBySet,
  rarityBreakdown,
  setProgressFor,
  stageBreakdown,
  typeBreakdown,
} from "@/lib/domain/dashboard";
import { formatNumber, titleCase } from "@/lib/domain/format";
import { compareRarity, isBaseRarity } from "@/lib/domain/rarity";
import type { SyncDeltaEntry } from "@/types";

const stageLabel = (s: string) => s.replace(/^Stage(\d)/, "Stage $1");
// Animate sync results on the dashboard only right after a sync, not every visit.
const RECENT_SYNC_MS = 10 * 60 * 1000;

/**
 * Whether a sync completed recently enough to animate its results. Read at
 * request time inside async Server Components; the purity rule targets client
 * render, where Date.now() would be non-deterministic.
 */
function isRecentSync(fetchedAt: string | null | undefined): boolean {
  if (!fetchedAt) return false;
  const now = Date.now();
  return now - new Date(fetchedAt).getTime() < RECENT_SYNC_MS;
}

/**
 * The dashboard streams as several independent Suspense boundaries rather than
 * one. Each section below awaits only the data it needs, so the completion ring
 * does not wait on sync history and none of them wait on the owner cookie check.
 * The page shell (headings, section structure) is outside every boundary, so PPR
 * serves it as static HTML immediately.
 *
 * Every section starts with `await connection()` before its cached reads — see
 * web/AGENTS.md; without it the data-free CI build would prerender these and hit
 * the missing local-json artifacts.
 */

// ── Header ────────────────────────────────────────────────────────────────

async function LastSyncedLine() {
  await connection();
  const [summary, sync] = await Promise.all([
    getCachedCollectionSummary(),
    getCachedSyncStatus(),
  ]);
  return (
    <p className="text-sm text-muted-foreground">
      {sync.stats
        ? `Last synced ${new Date(sync.stats.fetched_at).toLocaleString()}`
        : `Collection snapshot · updated ${summary.meta.last_updated}`}
    </p>
  );
}

/** Owner-only; renders nothing for everyone else, so it needs no placeholder. */
async function SyncControl() {
  await connection();
  const [syncEnabled, ownerCanSync] = await Promise.all([
    isSyncEnabled(),
    canTriggerSync(),
  ]);
  return ownerCanSync ? <SyncButton enabled={syncEnabled} /> : null;
}

// ── Owner-only operator panel ─────────────────────────────────────────────

async function OwnerPanel() {
  await connection();
  const owner = await isOwner();
  // Never fetched in local-json dev, where isOwner() is false and no Supabase exists.
  if (!owner) return null;
  const [ownerMeta, summary, packEv, catalog] = await Promise.all([
    fetchOwnerSyncMeta(),
    getCachedCollectionSummary(),
    getCachedPackEv(),
    getCachedCatalog(),
  ]);
  if (!ownerMeta) return null;

  return (
    <OwnerStatusCard
      publishedAt={ownerMeta.publishedAt}
      lastRun={ownerMeta.lastRun}
      counts={{
        cards: catalog.length,
        packs: packEv.packs.length,
        uniqueEntries: summary.unique_entries,
        totalQuantity: summary.total_quantity,
      }}
    />
  );
}

// ── Post-sync reveal popup ────────────────────────────────────────────────

/**
 * Right after a sync: a dismissable popup of the cards you just got. Shown once
 * per sync (dismissal remembered client-side); the sync stays listed in Sync
 * history below.
 */
async function RevealSlot() {
  await connection();
  const [sync, catalog] = await Promise.all([
    getCachedSyncStatus(),
    getCachedCatalog(),
  ]);
  const { stats, delta } = sync;
  if (!stats || !delta) return null;

  if (!isRecentSync(stats.fetched_at)) return null;

  const index = indexByCoord(catalog);
  const additions: AdditionItem[] = delta.added.map((entry) => ({
    entry,
    card: lookupCoord(index, entry.set_code, entry.card_number),
  }));
  if (additions.length === 0) return null;

  const setTotals = buildSetTotals(catalog);
  return (
    <SyncRevealDialog
      key={stats.fetched_at}
      items={additions}
      setProgress={setProgressFor(delta.added, ownedBySet(setTotals), setTotals)}
      count={delta.added_count}
      revealId={stats.fetched_at}
    />
  );
}

// ── Completion band ───────────────────────────────────────────────────────

async function StateBand() {
  await connection();
  const [catalog, summary, sync] = await Promise.all([
    getCachedCatalog(),
    getCachedCollectionSummary(),
    getCachedSyncStatus(),
  ]);
  const completion = completionStats(catalog);

  // Animate the ring up from its pre-sync value, but only right after a sync.
  const { stats, delta } = sync;
  const isRecent = isRecentSync(stats?.fetched_at);
  const index = isRecent ? indexByCoord(catalog) : null;
  const newOnes =
    isRecent && delta ? delta.added.filter((e: SyncDeltaEntry) => e.is_new) : [];
  const recentGain =
    isRecent && newOnes.length > 0
      ? {
          total: newOnes.length,
          base: newOnes.filter((e) =>
            isBaseRarity(
              lookupCoord(index!, e.set_code, e.card_number)?.rarity ?? null,
            ),
          ).length,
        }
      : undefined;

  return (
    <>
      <CompletionCard
        total={completion.total}
        base={completion.base}
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
    </>
  );
}

// ── What to open next ─────────────────────────────────────────────────────

async function NextToOpenSection() {
  await connection();
  const [packEv, catalog, sync] = await Promise.all([
    getCachedPackEv(),
    getCachedCatalog(),
    getCachedSyncStatus(),
  ]);
  const entries: NextPackEntry[] = nextPackEntries(
    packEv.packs,
    indexByCoord(catalog),
  );
  const stats = sync.stats;
  const currency = stats
    ? {
        pack_hourglasses: stats.pack_hourglasses,
        wonder_hourglasses: stats.wonder_hourglasses,
        shop_tickets: stats.shop_tickets,
      }
    : null;

  return <NextToOpen entries={entries} currency={currency} />;
}

// ── Collection breakdowns ─────────────────────────────────────────────────

async function CollectionTiles() {
  await connection();
  const [catalog, summary] = await Promise.all([
    getCachedCatalog(),
    getCachedCollectionSummary(),
  ]);
  const { pokemonQuantity, trainerQuantity } = typeBreakdown(catalog);
  const mega = megaStats(catalog);

  return (
    <>
      <StatCard
        title="Pokémon"
        value={formatNumber(pokemonQuantity)}
        href="/cards?category=Pokemon"
        align="center"
      />
      <StatCard
        title="Trainers"
        value={formatNumber(trainerQuantity)}
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
        value={formatNumber(mega.quantity)}
        hint={`${formatNumber(mega.unique)} of ${formatNumber(mega.total)} unique`}
        href="/cards?class=mega"
        align="center"
      />
    </>
  );
}

async function TypeAndRarity() {
  await connection();
  const catalog = await getCachedCatalog();
  const { byPokemonType } = typeBreakdown(catalog);
  const rarityItems: CountItem[] = rarityBreakdown(catalog, compareRarity).map(
    (b) => ({
      key: b.key,
      label: titleCase(b.key),
      value: b.owned,
      total: b.total,
      icon: <RaritySymbol rarity={b.key} />,
      href: `/cards?rarity=${encodeURIComponent(b.key)}`,
    }),
  );

  return (
    <>
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">By type</CardTitle>
        </CardHeader>
        <CardContent>
          <TypePieChart data={byPokemonType} />
        </CardContent>
      </Card>
      <CountGrid title="By rarity · collected" items={rarityItems} />
    </>
  );
}

async function StageGrid() {
  await connection();
  const catalog = await getCachedCatalog();
  const stageItems: CountItem[] = stageBreakdown(catalog).map((b) => ({
    key: b.key,
    label: stageLabel(b.key),
    value: b.owned,
    total: b.total,
    href: `/cards?stage=${encodeURIComponent(b.key)}`,
  }));
  return <CountGrid title="By stage · collected" items={stageItems} />;
}

// ── Sync history ──────────────────────────────────────────────────────────

async function SyncHistorySection() {
  await connection();
  const [sync, catalog] = await Promise.all([
    getCachedSyncStatus(),
    getCachedCatalog(),
  ]);
  const { reviewQueue, history } = sync;

  const index = indexByCoord(catalog);
  const setTotals = buildSetTotals(catalog);
  const join = (entry: SyncDeltaEntry): AdditionItem => ({
    entry,
    card: lookupCoord(index, entry.set_code, entry.card_number),
  });

  // History is stored oldest→newest; walk newest→oldest rolling the owned counts
  // back by each sync's gains, so every entry shows the totals as they stood at
  // that sync rather than today's.
  const runningOwned = ownedBySet(setTotals);
  const entries: HistoryEntryView[] = [...history].reverse().map((h) => {
    const progress = setProgressFor(h.added, runningOwned, setTotals);
    for (const p of progress) runningOwned.set(p.set_code, p.before);
    return {
      syncedAt: h.synced_at,
      addedCount: h.added_count,
      items: h.added.map(join),
      setProgress: progress,
    };
  });

  const reviewItems = reviewQueue
    ? reviewQueue.new_cards.length +
      reviewQueue.ambiguous_matches.length +
      reviewQueue.missing_from_pz.length
    : 0;

  return (
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
        <SyncHistory entries={entries} />
      </CardContent>
    </Card>
  );
}

// ── Page shell (static; served immediately by PPR) ────────────────────────

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
          <Suspense fallback={<TextLinesSkeleton width="w-64" />}>
            <LastSyncedLine />
          </Suspense>
        </div>
        <Suspense fallback={null}>
          <SyncControl />
        </Suspense>
      </header>

      {/* Absent for every visitor except the signed-in owner, so it streams with
          no placeholder — a skeleton here would flash a box that then vanishes. */}
      <Suspense fallback={null}>
        <OwnerPanel />
      </Suspense>
      <Suspense fallback={null}>
        <RevealSlot />
      </Suspense>

      {/* State band: completion ring beside the headline total. */}
      <section className="grid gap-4 lg:grid-cols-2">
        <Suspense
          fallback={
            <>
              <PanelSkeleton titleWidth="w-44" bodyClassName="h-64" />
              <PanelSkeleton titleWidth="w-28" bodyClassName="h-64" />
            </>
          }
        >
          <StateBand />
        </Suspense>
      </section>

      {/* Centerpiece: what to open next (filters + pack-hourglass balance). */}
      <Suspense
        fallback={
          <section className="space-y-4">
            <Skeleton className="h-7 w-56" />
            <Skeleton className="h-9 w-96 max-w-full" />
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {[0, 1, 2].map((i) => (
                <PanelSkeleton key={i} titleWidth="w-32" bodyClassName="h-56" />
              ))}
            </div>
          </section>
        }
      >
        <NextToOpenSection />
      </Suspense>

      {/* Collection: secondary counts, then compact type/rarity/stage breakdowns. */}
      <section className="space-y-4">
        <h2 className="text-lg font-medium">Collection</h2>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <Suspense fallback={<StatTilesSkeleton className="contents" />}>
            <CollectionTiles />
          </Suspense>
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          <Suspense
            fallback={
              <>
                <PanelSkeleton titleWidth="w-20" bodyClassName="h-56" />
                <CountGridSkeleton cells={9} titleWidth="w-44" />
              </>
            }
          >
            <TypeAndRarity />
          </Suspense>
        </div>
        <Suspense fallback={<CountGridSkeleton cells={3} titleWidth="w-44" />}>
          <StageGrid />
        </Suspense>
      </section>

      {/* Recent activity: sync history (+ review-queue chip). */}
      <Suspense
        fallback={<PanelSkeleton titleWidth="w-28" bodyClassName="h-48" />}
      >
        <SyncHistorySection />
      </Suspense>
    </div>
  );
}
