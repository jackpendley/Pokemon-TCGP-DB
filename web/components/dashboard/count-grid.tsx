import type { ReactNode } from "react";
import Link from "next/link";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { formatNumber } from "@/lib/domain/format";

export type CountItem = {
  key: string;
  label: string;
  value: number;
  /** Optional denominator — when present, rendered as "value / total". */
  total?: number;
  icon?: ReactNode;
  /** When set, the cell becomes a link (e.g. to the filtered Cards page). */
  href?: string;
};

/**
 * A card holding a responsive grid of labelled count cells. Cells with an href
 * are clickable (e.g. a rarity opens that rarity on the Cards page).
 */
export function CountGrid({
  title,
  items,
}: {
  title: string;
  items: CountItem[];
}) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {items.map((item) => {
            const inner = (
              <>
                <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  {item.icon}
                  <span className="truncate">{item.label}</span>
                </div>
                <div className="text-lg font-semibold tabular-nums">
                  {formatNumber(item.value)}
                  {item.total != null ? (
                    <span className="ml-1 text-xs font-normal text-muted-foreground">
                      / {formatNumber(item.total)}
                    </span>
                  ) : null}
                </div>
              </>
            );
            const cls = "flex flex-col gap-1 rounded-lg bg-muted/40 px-3 py-2.5";
            return item.href ? (
              <Link
                key={item.key}
                href={item.href}
                className={cn(cls, "transition-colors hover:bg-muted")}
              >
                {inner}
              </Link>
            ) : (
              <div key={item.key} className={cls}>
                {inner}
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
