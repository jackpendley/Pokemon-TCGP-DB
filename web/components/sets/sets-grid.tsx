"use client";

import { useState } from "react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatPercent } from "@/lib/domain/format";

export interface SetProgress {
  set_code: string;
  expansion: string;
  total: number;
  owned: number;
  baseTotal: number;
  baseOwned: number;
}

type Mode = "total" | "base";

export function SetsGrid({ sets }: { sets: SetProgress[] }) {
  const [mode, setMode] = useState<Mode>("total");

  return (
    <div className="space-y-4">
      <div className="inline-flex rounded-md border p-0.5">
        {(["total", "base"] as Mode[]).map((m) => (
          <Button
            key={m}
            type="button"
            size="sm"
            variant={mode === m ? "secondary" : "ghost"}
            className="h-7 capitalize"
            onClick={() => setMode(m)}
          >
            {m === "total" ? "Full set" : "Base set"}
          </Button>
        ))}
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {sets.map((s) => {
          const owned = mode === "base" ? s.baseOwned : s.owned;
          const total = mode === "base" ? s.baseTotal : s.total;
          const ratio = total > 0 ? owned / total : 0;
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
                      {owned}
                      <span className="text-base text-muted-foreground">
                        /{total}
                      </span>
                    </span>
                    <span className="text-sm text-muted-foreground tabular-nums">
                      {total > 0 ? formatPercent(ratio) : "—"}
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
