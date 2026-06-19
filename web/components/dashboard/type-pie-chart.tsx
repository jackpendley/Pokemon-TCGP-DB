"use client";

import { Cell, Pie, PieChart } from "recharts";

import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import { typeColor } from "@/lib/domain/type-colors";

export function TypePieChart({ data }: { data: Record<string, number> }) {
  const rows = Object.entries(data)
    .map(([type, count]) => ({ type, count, fill: typeColor(type) }))
    .sort((a, b) => b.count - a.count);

  const config: ChartConfig = Object.fromEntries(
    rows.map((r) => [r.type, { label: r.type, color: r.fill }]),
  );

  return (
    <ChartContainer config={config} className="mx-auto aspect-square max-h-[280px]">
      <PieChart>
        <ChartTooltip content={<ChartTooltipContent nameKey="type" hideLabel />} />
        <Pie
          data={rows}
          dataKey="count"
          nameKey="type"
          innerRadius={55}
          strokeWidth={2}
        >
          {rows.map((r) => (
            <Cell key={r.type} fill={r.fill} />
          ))}
        </Pie>
        <ChartLegend
          content={<ChartLegendContent nameKey="type" />}
          className="flex-wrap gap-x-3 gap-y-1"
        />
      </PieChart>
    </ChartContainer>
  );
}
