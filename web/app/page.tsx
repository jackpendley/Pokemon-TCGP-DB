import Link from "next/link";

import { BreakdownBars, type BarItem } from "@/components/dashboard/breakdown-bars";
import { CompletionCard } from "@/components/dashboard/completion-card";
import { CountGrid, type CountItem } from "@/components/dashboard/count-grid";
import { RaritySymbol } from "@/components/dashboard/rarity-symbol";
import { StatCard } from "@/components/dashboard/stat-card";
import { TypePieChart } from "@/components/dashboard/type-pie-chart";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { dataSource } from "@/lib/data";
import { isMegaEx } from "@/lib/domain/card";
import { formatEv, formatNumber, titleCase } from "@/lib/domain/format";
import { compareRarity, isBaseRarity } from "@/lib/domain/rarity";

export const dynamic = "force-dynamic";

const STAGE_ORDER = ["Basic", "Stage 1", "Stage 2", "Stage 3"];

export default async function DashboardPage() {
  const [summary, recs, catalog] = await Promise.all([
    dataSource.getCollectionSummary(),
    dataSource.getRecommendations(),
    dataSource.getCatalog(),
  ]);

  const topPack = recs.top_packs_unified[0];

  // Completion — derived web-side from the catalog (owned counts merged in).
  const totalOwned = catalog.filter((c) => c.owned > 0).length;
  const baseCards = catalog.filter((c) => isBaseRarity(c.rarity));
  const baseOwned = baseCards.filter((c) => c.owned > 0).length;

  // Mega ex (subset of ex) — own quantity + unique, mirroring the ex card.
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

  const stageItems: BarItem[] = Object.entries(summary.by_stage)
    .sort(([a], [b]) => {
      const ia = STAGE_ORDER.indexOf(a);
      const ib = STAGE_ORDER.indexOf(b);
      if (ia === -1 && ib === -1) return a.localeCompare(b);
      return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib);
    })
    // card_reference stages have no space ("Stage1"); the summary labels do.
    .map(([label, value]) => ({
      label,
      value,
      href: `/cards?stage=${encodeURIComponent(label.replace(/\s+/g, ""))}`,
    }));

  return (
    <div className="space-y-8">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        <p className="text-sm text-muted-foreground">
          Collection snapshot · updated {summary.meta.last_updated}
        </p>
      </header>

      {/* Overview: completion ring beside the headline collection counts. */}
      <section className="grid gap-4 lg:grid-cols-3">
        <CompletionCard
          total={{ owned: totalOwned, total: catalog.length }}
          base={{ owned: baseOwned, total: baseCards.length }}
        />
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:col-span-2">
          <StatCard
            title="Total cards"
            value={formatNumber(summary.total_quantity)}
            hint={`${formatNumber(summary.unique_entries)} unique entries`}
          />
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
      </section>

      {topPack ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between gap-2 text-base">
              <span>Top recommended pack</span>
              <Badge variant="secondary">
                {titleCase(topPack.slot_rates_confidence)}
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <div className="text-xl font-semibold">{topPack.pack_name}</div>
              <div className="text-sm text-muted-foreground">
                {topPack.expansion} · {topPack.missing_in_pool} missing of{" "}
                {topPack.cards_in_pool}
              </div>
            </div>
            <div className="text-right">
              <div className="text-2xl font-semibold tabular-nums">
                {formatEv(topPack.unified_score)}
              </div>
              <div className="text-xs text-muted-foreground">unified score</div>
            </div>
            <Link
              href="/packs"
              className="text-sm font-medium text-primary hover:underline"
            >
              View all packs →
            </Link>
          </CardContent>
        </Card>
      ) : null}

      {/* Collection breakdown: the two Pokémon views together, rarity below. */}
      <section className="space-y-4">
        <div className="grid gap-4 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <CardHeader className="pb-2">
              <CardTitle className="text-base">By type</CardTitle>
            </CardHeader>
            <CardContent>
              <TypePieChart data={summary.by_pokemon_type} />
            </CardContent>
          </Card>
          <BreakdownBars title="By stage" items={stageItems} />
        </div>
        <CountGrid title="By rarity · collected" items={rarityItems} />
      </section>
    </div>
  );
}
