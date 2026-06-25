import Link from "next/link";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { formatNumber, formatPercent } from "@/lib/domain/format";

export type BarItem = { label: string; value: number; href?: string };

/**
 * Proportional horizontal bars with count + share, mirroring the By-type legend
 * so the two Pokémon breakdowns read as siblings. Bars fill the card height;
 * rows with an href are clickable (e.g. a stage opens that stage on Cards).
 */
export function BreakdownBars({
  title,
  items,
}: {
  title: string;
  items: BarItem[];
}) {
  const total = items.reduce((n, i) => n + i.value, 0) || 1;
  const max = Math.max(...items.map((i) => i.value), 1);

  return (
    <Card className="h-full">
      <CardHeader className="pb-2">
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent className="flex h-full flex-col justify-center gap-5">
        {items.map((it) => {
          const inner = (
            <>
              <div className="flex items-baseline justify-between gap-2 text-sm">
                <span className="font-medium">{it.label}</span>
                <span className="tabular-nums text-muted-foreground">
                  {formatNumber(it.value)}
                  <span className="ml-1.5 text-xs">
                    {formatPercent(it.value / total)}
                  </span>
                </span>
              </div>
              <div className="mt-2 h-2 overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full bg-primary transition-[width] duration-500"
                  style={{ width: `${(it.value / max) * 100}%` }}
                />
              </div>
            </>
          );
          return it.href ? (
            <Link
              key={it.label}
              href={it.href}
              className={cn(
                "-mx-2 rounded-md px-2 py-1 transition-colors hover:bg-muted/50",
              )}
            >
              {inner}
            </Link>
          ) : (
            <div key={it.label}>{inner}</div>
          );
        })}
      </CardContent>
    </Card>
  );
}
