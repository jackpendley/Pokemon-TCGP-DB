import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatNumber } from "@/lib/domain/format";

export type BarItem = { label: string; value: number };

/**
 * A card with proportional horizontal bars — used for small breakdowns (e.g. by
 * stage) where a count grid reads as sparse.
 */
export function BreakdownBars({
  title,
  items,
}: {
  title: string;
  items: BarItem[];
}) {
  const max = Math.max(...items.map((i) => i.value), 1);

  return (
    <Card className="h-full">
      <CardHeader className="pb-2">
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col justify-center gap-4">
        {items.map((it) => (
          <div key={it.label} className="space-y-1.5">
            <div className="flex justify-between text-sm">
              <span>{it.label}</span>
              <span className="tabular-nums text-muted-foreground">
                {formatNumber(it.value)}
              </span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-primary"
                style={{ width: `${(it.value / max) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
