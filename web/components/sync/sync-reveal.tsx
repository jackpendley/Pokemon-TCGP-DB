"use client";

import { useEffect, useState } from "react";

import { CardImage } from "@/components/cards/card-image";
import { formatPercent } from "@/lib/domain/format";
import type { CatalogCard, SyncDeltaEntry } from "@/types";

export interface AdditionItem {
  entry: SyncDeltaEntry;
  card: CatalogCard | null;
}

export interface SetProgressItem {
  set_code: string;
  expansion: string;
  total: number;
  before: number;
  after: number;
  gained: number;
}

const STAGGER_MS = 110;
const PHASE_GAP_MS = 450;

export function SyncReveal({
  items,
  setProgress,
}: {
  items: AdditionItem[];
  setProgress: SetProgressItem[];
}) {
  const newItems = items.filter((i) => i.entry.is_new);
  const ownedItems = items.filter((i) => !i.entry.is_new);

  // Owned cards reveal only after the new cards finish.
  const ownedStartMs = newItems.length * STAGGER_MS + PHASE_GAP_MS;
  // Set-progress bars fill once every card has revealed.
  const barsStartMs =
    ownedStartMs + ownedItems.length * STAGGER_MS + PHASE_GAP_MS;

  const [barsFilled, setBarsFilled] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setBarsFilled(true), barsStartMs);
    return () => clearTimeout(t);
  }, [barsStartMs]);

  if (items.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No cards were added in the last sync.
      </p>
    );
  }

  return (
    <div className="space-y-6">
      {newItems.length > 0 ? (
        <section className="space-y-2">
          <h3 className="text-sm font-medium">New to your collection</h3>
          <Grid>
            {newItems.map((item, i) => (
              <RevealTile
                key={`${item.entry.set_code}-${item.entry.card_number}`}
                item={item}
                delayMs={i * STAGGER_MS}
                isNew
              />
            ))}
          </Grid>
        </section>
      ) : null}

      {ownedItems.length > 0 ? (
        <section className="space-y-2">
          <h3 className="text-sm font-medium text-muted-foreground">
            More copies of cards you owned
          </h3>
          <Grid>
            {ownedItems.map((item, i) => (
              <RevealTile
                key={`${item.entry.set_code}-${item.entry.card_number}`}
                item={item}
                delayMs={ownedStartMs + i * STAGGER_MS}
              />
            ))}
          </Grid>
        </section>
      ) : null}

      {setProgress.length > 0 ? (
        <section className="space-y-3">
          <h3 className="text-sm font-medium">Set progress</h3>
          <div className="space-y-3">
            {setProgress.map((s) => {
              const beforePct = s.total > 0 ? s.before / s.total : 0;
              const afterPct = s.total > 0 ? s.after / s.total : 0;
              return (
                <div key={s.set_code} className="space-y-1">
                  <div className="flex justify-between text-sm">
                    <span>
                      {s.expansion}{" "}
                      <span className="text-muted-foreground">{s.set_code}</span>
                    </span>
                    <span className="tabular-nums text-muted-foreground">
                      {s.before} → <span className="text-foreground">{s.after}</span>/
                      {s.total}{" "}
                      <span className="text-primary">(+{s.gained})</span>
                    </span>
                  </div>
                  <div className="relative h-2 overflow-hidden rounded-full bg-muted">
                    {/* The gained slice fills in on top of the prior progress. */}
                    <div
                      className="absolute inset-y-0 left-0 rounded-full bg-primary/40"
                      style={{ width: `${beforePct * 100}%` }}
                    />
                    <div
                      className="absolute inset-y-0 left-0 rounded-full bg-primary transition-[width] duration-1000 ease-out"
                      style={{
                        width: `${(barsFilled ? afterPct : beforePct) * 100}%`,
                      }}
                    />
                  </div>
                  <div className="text-right text-[10px] text-muted-foreground tabular-nums">
                    {formatPercent(afterPct)}
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      ) : null}
    </div>
  );
}

function Grid({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-3 gap-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8">
      {children}
    </div>
  );
}

function RevealTile({
  item,
  delayMs,
  isNew = false,
}: {
  item: AdditionItem;
  delayMs: number;
  isNew?: boolean;
}) {
  const { entry, card } = item;
  return (
    <div
      className="animate-card-reveal flex flex-col"
      style={{ animationDelay: `${delayMs}ms` }}
    >
      {/* NEW badge sits ABOVE the art so it never covers it. */}
      {isNew ? (
        <span className="mx-auto mb-1 rounded-full bg-primary px-2 py-0.5 text-[10px] font-bold tracking-wide text-primary-foreground">
          NEW
        </span>
      ) : null}
      <div className="relative flex aspect-[5/7] items-center justify-center overflow-hidden rounded-md border bg-muted">
        {card ? (
          <CardImage card={card} />
        ) : (
          <span className="text-sm font-semibold tabular-nums text-muted-foreground/60">
            #{entry.card_number}
          </span>
        )}
      </div>
      <div className="mt-1 truncate text-xs font-medium" title={entry.name ?? ""}>
        {entry.name ?? `#${entry.card_number}`}
      </div>
      <span className="text-[10px] text-muted-foreground tabular-nums">
        {isNew
          ? entry.set_code
          : `${entry.previous_count} → ${entry.new_count} (+${entry.added})`}
      </span>
    </div>
  );
}
