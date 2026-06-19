"use client";

import { Cell, Label, Pie, PieChart } from "recharts";

import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import { typeColor } from "@/lib/domain/type-colors";
import { formatNumber } from "@/lib/domain/format";

export function TypePieChart({ data }: { data: Record<string, number> }) {
  const rows = Object.entries(data)
    .map(([type, count]) => ({ type, count, fill: typeColor(type) }))
    .sort((a, b) => b.count - a.count);

  const total = rows.reduce((sum, r) => sum + r.count, 0);

  const config: ChartConfig = Object.fromEntries(
    rows.map((r) => [r.type, { label: r.type, color: r.fill }]),
  );

  return (
    <div className="flex flex-col items-center gap-6 sm:flex-row sm:items-center sm:justify-around">
      <ChartContainer
        config={config}
        className="aspect-square h-[300px] w-[300px] shrink-0"
      >
        <PieChart>
          <ChartTooltip content={<ChartTooltipContent nameKey="type" hideLabel />} />
          <Pie
            data={rows}
            dataKey="count"
            nameKey="type"
            innerRadius={75}
            outerRadius={130}
            strokeWidth={2}
          >
            {rows.map((r) => (
              <Cell key={r.type} fill={r.fill} />
            ))}
            <Label
              content={({ viewBox }) => {
                if (!viewBox || !("cx" in viewBox)) return null;
                return (
                  <text
                    x={viewBox.cx}
                    y={viewBox.cy}
                    textAnchor="middle"
                    dominantBaseline="middle"
                  >
                    <tspan
                      x={viewBox.cx}
                      y={viewBox.cy}
                      className="fill-foreground text-2xl font-semibold"
                    >
                      {formatNumber(total)}
                    </tspan>
                    <tspan
                      x={viewBox.cx}
                      y={(viewBox.cy ?? 0) + 22}
                      className="fill-muted-foreground text-xs"
                    >
                      Pokémon
                    </tspan>
                  </text>
                );
              }}
            />
          </Pie>
        </PieChart>
      </ChartContainer>

      <ul className="grid w-full max-w-sm gap-1.5 sm:w-auto sm:min-w-52">
        {rows.map((r) => (
          <li key={r.type} className="flex items-center gap-2.5 text-sm">
            <span
              className="size-3 shrink-0 rounded-[3px]"
              style={{ backgroundColor: r.fill }}
            />
            <span className="flex-1">{r.type}</span>
            <span className="tabular-nums font-medium">
              {formatNumber(r.count)}
            </span>
            <span className="w-11 text-right text-xs tabular-nums text-muted-foreground">
              {total > 0 ? ((r.count / total) * 100).toFixed(1) : "0.0"}%
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
