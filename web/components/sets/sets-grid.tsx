"use client";

import { useState } from "react";
import Link from "next/link";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  SetScopeToggle,
  type SetScope,
} from "@/components/sets/set-scope-toggle";
import { SetLogo } from "@/components/sets/set-logo";
import { CountUp } from "@/components/ui/count-up";

export interface SetProgress {
  set_code: string;
  expansion: string;
  total: number;
  owned: number;
  baseTotal: number;
  baseOwned: number;
}

export function SetsGrid({ sets }: { sets: SetProgress[] }) {
  const [mode, setMode] = useState<SetScope>("total");

  return (
    <div className="space-y-4">
      <SetScopeToggle scope={mode} onChange={setMode} />

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
                  <CardTitle className="flex items-center justify-between gap-2 text-base">
                    <span className="flex items-center gap-2 min-w-0">
                      <SetLogo
                        setCode={s.set_code}
                        label={s.expansion}
                        className="h-7 w-10 shrink-0"
                      />
                      <span className="truncate">{s.expansion}</span>
                    </span>
                    <span className="shrink-0 text-xs font-normal text-muted-foreground">
                      {s.set_code}
                    </span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  <div className="flex items-end justify-between">
                    <span className="text-2xl font-semibold tabular-nums">
                      <CountUp value={owned} />
                      <span className="text-base text-muted-foreground">
                        /{total}
                      </span>
                    </span>
                    <span className="text-sm text-muted-foreground tabular-nums">
                      {total > 0 ? (
                        <CountUp
                          value={ratio * 100}
                          format={(n) => `${Math.round(n)}%`}
                        />
                      ) : (
                        "—"
                      )}
                    </span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-muted">
                    <div
                      className="h-full rounded-full bg-primary transition-[width] duration-500 ease-out"
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
