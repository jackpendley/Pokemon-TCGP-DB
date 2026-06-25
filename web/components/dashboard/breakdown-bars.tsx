import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatNumber, formatPercent } from "@/lib/domain/format";

export type BarItem = { label: string; value: number };

/**
 * Proportional horizontal bars with count + share, mirroring the By-type legend
 * so the two Pokémon breakdowns read as siblings. Bars fill the card height.
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
        {items.map((it) => (
          <div key={it.label} className="space-y-2">
            <div className="flex items-baseline justify-between gap-2 text-sm">
              <span className="font-medium">{it.label}</span>
              <span className="tabular-nums text-muted-foreground">
                {formatNumber(it.value)}
                <span className="ml-1.5 text-xs">
                  {formatPercent(it.value / total)}
                </span>
              </span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-primary transition-[width] duration-500"
                style={{ width: `${(it.value / max) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
