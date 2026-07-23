"use client";

import { useMemo } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  LineChart,
  XAxis,
  YAxis,
} from "recharts";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import { formatEv, formatNumber } from "@/lib/domain/format";

/** Matches RecommendationHistoryEntry (kept local to avoid a server-only import). */
export interface HistoryEntry {
  capturedAt: string;
  collectionTotal: number;
  packs: {
    packName: string;
    unifiedScore: number;
    totalEv: number;
    purchasable: boolean;
    blocked: boolean;
  }[];
}

// Design-system categorical theme (app --chart-1..5), consumed in fixed order.
const SERIES_COLORS = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-4)",
  "var(--chart-5)",
];
const MAX_PACKS = SERIES_COLORS.length;

const fmtDate = (iso: string) =>
  new Date(iso).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });

export function HistoryView({ entries }: { entries: HistoryEntry[] }) {
  // Top packs by their latest unified_score (purchasable, unblocked), in a
  // fixed order so a series keeps its colour across the whole time range.
  const series = useMemo(() => {
    const latest = entries.at(-1);
    if (!latest) return [];
    return [...latest.packs]
      .filter((p) => p.purchasable && !p.blocked)
      .sort((a, b) => b.unifiedScore - a.unifiedScore)
      .slice(0, MAX_PACKS)
      .map((p, i) => ({
        id: `p${i}`,
        name: p.packName,
        color: SERIES_COLORS[i],
      }));
  }, [entries]);

  const growthData = useMemo(
    () =>
      entries.map((e) => ({ t: e.capturedAt, total: e.collectionTotal })),
    [entries],
  );

  const driftData = useMemo(
    () =>
      entries.map((e) => {
        const row: Record<string, number | string | null> = { t: e.capturedAt };
        for (const s of series) {
          row[s.id] = e.packs.find((p) => p.packName === s.name)?.unifiedScore ?? null;
        }
        return row;
      }),
    [entries, series],
  );

  const growthConfig: ChartConfig = {
    total: { label: "Cards collected", color: "var(--chart-2)" },
  };
  const driftConfig: ChartConfig = Object.fromEntries(
    series.map((s) => [s.id, { label: s.name, color: s.color }]),
  );

  if (entries.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-sm text-muted-foreground">
          No history yet. A snapshot is recorded after each sync — check back
          once you&apos;ve synced your collection.
        </CardContent>
      </Card>
    );
  }

  const sparse = entries.length < 2;

  return (
    <div className="space-y-6">
      {sparse ? (
        <p className="text-sm text-muted-foreground">
          Only one snapshot so far — trends fill in as more syncs are recorded.
        </p>
      ) : null}

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Collection growth</CardTitle>
          <CardDescription>
            Unique cards tracked at each sync over time.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ChartContainer config={growthConfig} className="h-[240px] w-full">
            <AreaChart data={growthData} margin={{ left: 8, right: 12, top: 8 }}>
              <CartesianGrid vertical={false} strokeDasharray="3 3" />
              <XAxis
                dataKey="t"
                tickLine={false}
                axisLine={false}
                tickMargin={8}
                tickFormatter={fmtDate}
              />
              <YAxis
                width={40}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v: number) => formatNumber(v)}
              />
              <ChartTooltip
                content={
                  <ChartTooltipContent
                    labelFormatter={(_, p) => fmtDate(String(p?.[0]?.payload?.t))}
                  />
                }
              />
              <Area
                dataKey="total"
                type="monotone"
                stroke="var(--color-total)"
                fill="var(--color-total)"
                fillOpacity={0.15}
                strokeWidth={2}
                dot={{ r: 3 }}
              />
            </AreaChart>
          </ChartContainer>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Pack EV drift</CardTitle>
          <CardDescription>
            Unified score of your top packs at each sync — how the ranking
            shifts as you collect and new sets land.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {series.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">
              No purchasable packs to chart yet.
            </p>
          ) : (
            <ChartContainer config={driftConfig} className="h-[300px] w-full">
              <LineChart data={driftData} margin={{ left: 8, right: 12, top: 8 }}>
                <CartesianGrid vertical={false} strokeDasharray="3 3" />
                <XAxis
                  dataKey="t"
                  tickLine={false}
                  axisLine={false}
                  tickMargin={8}
                  tickFormatter={fmtDate}
                />
                <YAxis
                  width={44}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(v: number) => formatEv(v, 1)}
                />
                <ChartTooltip
                  content={
                    <ChartTooltipContent
                      labelFormatter={(_, p) =>
                        fmtDate(String(p?.[0]?.payload?.t))
                      }
                    />
                  }
                />
                <ChartLegend content={<ChartLegendContent />} />
                {series.map((s) => (
                  <Line
                    key={s.id}
                    dataKey={s.id}
                    type="monotone"
                    stroke={`var(--color-${s.id})`}
                    strokeWidth={2}
                    dot={{ r: 3 }}
                    connectNulls
                  />
                ))}
              </LineChart>
            </ChartContainer>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
