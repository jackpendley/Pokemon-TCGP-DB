import Link from "next/link";

import { StatCard } from "@/components/dashboard/stat-card";
import { TypePieChart } from "@/components/dashboard/type-pie-chart";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { dataSource } from "@/lib/data";
import { formatEv, formatNumber, titleCase } from "@/lib/domain/format";

export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  const [summary, recs] = await Promise.all([
    dataSource.getCollectionSummary(),
    dataSource.getRecommendations(),
  ]);

  const completeLines = summary.evolution_groups.filter((g) => g.complete).length;
  const topPack = recs.top_packs_unified[0];

  return (
    <div className="space-y-8">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        <p className="text-sm text-muted-foreground">
          Collection snapshot · updated {summary.meta.last_updated}
        </p>
      </header>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
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
          title="Evolution lines complete"
          value={`${completeLines} / ${summary.evolution_groups.length}`}
          hint="fully owned by name"
          info="Of the evolution lines you've started collecting, how many you own every stage of (counted by card name, one copy each)."
        />
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

      <section className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">By type</CardTitle>
          </CardHeader>
          <CardContent>
            <TypePieChart data={summary.by_pokemon_type} />
          </CardContent>
        </Card>
        <BreakdownCard title="By stage" data={summary.by_stage} />
      </section>
    </div>
  );
}

function BreakdownCard({
  title,
  data,
}: {
  title: string;
  data: Record<string, number>;
}) {
  const rows = Object.entries(data).sort((a, b) => b[1] - a[1]);
  const max = Math.max(...rows.map(([, v]) => v), 1);

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {rows.map(([label, value]) => (
          <div key={label} className="space-y-1">
            <div className="flex justify-between text-sm">
              <span>{label}</span>
              <span className="tabular-nums text-muted-foreground">
                {formatNumber(value)}
              </span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-primary"
                style={{ width: `${(value / max) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
