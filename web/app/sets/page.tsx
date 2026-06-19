import Link from "next/link";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { dataSource } from "@/lib/data";
import { formatPercent } from "@/lib/domain/format";

export const dynamic = "force-dynamic";
export const metadata = { title: "Sets · TCGP Optimizer" };

interface SetProgress {
  set_code: string;
  expansion: string;
  total: number;
  owned: number;
}

export default async function SetsPage() {
  const catalog = await dataSource.getCatalog();

  // Preserve first-seen order (≈ release order) while aggregating per set.
  const bySet = new Map<string, SetProgress>();
  for (const c of catalog) {
    let s = bySet.get(c.set_code);
    if (!s) {
      s = { set_code: c.set_code, expansion: c.expansion, total: 0, owned: 0 };
      bySet.set(c.set_code, s);
    }
    s.total += 1;
    if (c.owned > 0) s.owned += 1;
  }
  const sets = [...bySet.values()];

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">Set Completion</h1>
        <p className="text-sm text-muted-foreground">
          Unique cards owned per set ({sets.length} sets)
        </p>
      </header>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {sets.map((s) => {
          const ratio = s.total > 0 ? s.owned / s.total : 0;
          return (
            <Link
              key={s.set_code}
              href={`/sets/${encodeURIComponent(s.set_code)}`}
              className="block"
            >
              <Card className="h-full transition-colors hover:border-primary/50">
                <CardHeader className="pb-2">
                  <CardTitle className="flex items-center justify-between text-base">
                    <span>{s.expansion}</span>
                    <span className="text-xs font-normal text-muted-foreground">
                      {s.set_code}
                    </span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  <div className="flex items-end justify-between">
                    <span className="text-2xl font-semibold tabular-nums">
                      {s.owned}
                      <span className="text-base text-muted-foreground">
                        /{s.total}
                      </span>
                    </span>
                    <span className="text-sm text-muted-foreground tabular-nums">
                      {formatPercent(ratio)}
                    </span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-muted">
                    <div
                      className="h-full rounded-full bg-primary"
                      style={{ width: `${ratio * 100}%` }}
                    />
                  </div>
                </CardContent>
              </Card>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
