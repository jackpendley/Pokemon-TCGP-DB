import { Suspense } from "react";
import { notFound } from "next/navigation";
import Link from "next/link";

import { EnlargeableCard } from "@/components/cards/enlargeable-card";
import { StatCard } from "@/components/dashboard/stat-card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { StatTilesSkeleton, TableSkeleton } from "@/components/ui/skeletons";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { getCachedCatalog, getCachedPackEv } from "@/lib/data/cached";
import {
  formatEv,
  formatPercent,
  packSlug,
  titleCase,
} from "@/lib/domain/format";
import type { CatalogCard } from "@/types";

/** A pack-table row (top EV or top power) carries a coord + name; may be null. */
type CardRow = {
  set_code: string | null;
  card_number: number | null;
  name: string;
  rarity: string | null;
  owned?: number;
  power_score?: number;
};

/** Enlargeable thumbnail + name, shared by both pack card tables. */
function CardCell({ card }: { card: CatalogCard }) {
  return (
    <div className="flex items-center gap-3">
      <EnlargeableCard card={card} className="w-14" />
      <span className="font-medium">{card.name}</span>
    </div>
  );
}

async function PackDetailContent({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const [packEv, catalog] = await Promise.all([
    getCachedPackEv(),
    getCachedCatalog(),
  ]);
  const pack = packEv.packs.find((p) => packSlug(p.pack_name) === slug);

  if (!pack) notFound();

  // Resolve a table row to a full CatalogCard (for the enlarged dialog), falling
  // back to a minimal card when the coord isn't in the catalog.
  const byCoord = new Map(
    catalog.map((c) => [`${c.set_code}:${c.card_number}`, c]),
  );
  const resolve = (row: CardRow): CatalogCard =>
    byCoord.get(`${row.set_code}:${row.card_number}`) ?? {
      set_code: row.set_code ?? "",
      card_number: row.card_number ?? 0,
      name: row.name,
      rarity: row.rarity,
      pokemon_type: null,
      card_category: null,
      trainer_subtype: null,
      stage: null,
      expansion: pack.expansion,
      is_ex: false,
      owned: row.owned ?? 0,
      power_score: row.power_score ?? null,
      // Pack tables list Pokémon pull targets; unknown when there's no score.
      power_score_kind: row.power_score != null ? "pokemon" : null,
      boosts: null,
      evolves_from: null,
    };

  return (
    <>
      <div>
        <h1 className="flex items-center gap-3 text-2xl font-semibold tracking-tight">
          {pack.pack_name}
          <Badge variant={pack.confidence_weight >= 1 ? "secondary" : "outline"}>
            {titleCase(pack.slot_rates_confidence)}
          </Badge>
        </h1>
        <p className="text-sm text-muted-foreground">{pack.expansion}</p>
      </div>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard title="Unified score" value={formatEv(pack.unified_score)} />
        <StatCard
          title="New-card EV (10x)"
          value={formatEv(pack.new_card_ev_10x)}
        />
        <StatCard
          title="Missing in pool"
          value={`${pack.missing_in_pool} / ${pack.cards_in_pool}`}
        />
        <StatCard
          title="Cost per unique (10x)"
          value={formatEv(pack.cost_per_unique_card_10x)}
        />
      </section>

      <div>
        <h2 className="mb-3 text-lg font-medium">Top EV cards</h2>
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Card</TableHead>
                <TableHead>Rarity</TableHead>
                <TableHead className="text-right">Owned</TableHead>
                <TableHead className="text-right">Pull prob</TableHead>
                <TableHead className="text-right">EV contribution</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {pack.top_ev_cards.map((c, i) => (
                // Same card name can appear as multiple printings (e.g. base +
                // alt-art ex), so key by index rather than coord.
                <TableRow key={`${c.name}-${i}`}>
                  <TableCell>
                    <CardCell card={resolve(c)} />
                  </TableCell>
                  <TableCell>{titleCase(c.rarity)}</TableCell>
                  <TableCell className="text-right tabular-nums">
                    {c.owned}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {formatPercent(c.pull_prob, 2)}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {formatEv(c.ev_contribution, 3)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
        {pack.notes ? (
          <p className="mt-3 text-xs text-muted-foreground">{pack.notes}</p>
        ) : null}
      </div>

      {pack.top_power_cards.length > 0 ? (
        <div>
          <h2 className="mb-1 text-lg font-medium">Top pull targets by power</h2>
          <p className="mb-3 text-sm text-muted-foreground">
            The strongest cards you don&apos;t own yet in this pack, with the
            chance of pulling each from a single pack.
          </p>
          <div className="rounded-lg border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Card</TableHead>
                  <TableHead>Set</TableHead>
                  <TableHead>Rarity</TableHead>
                  <TableHead className="text-right">Power</TableHead>
                  <TableHead className="text-right">Pull prob (1 pack)</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {pack.top_power_cards.map((c, i) => (
                  <TableRow key={`${c.set_code}-${c.card_number}-${i}`}>
                    <TableCell>
                      <CardCell card={resolve({ ...c, owned: 0 })} />
                    </TableCell>
                    <TableCell className="tabular-nums text-muted-foreground">
                      {c.set_code}:{c.card_number}
                    </TableCell>
                    <TableCell>{titleCase(c.rarity)}</TableCell>
                    <TableCell className="text-right font-semibold tabular-nums text-primary">
                      {c.power_score.toFixed(1)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatPercent(c.pull_prob, 2)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>
      ) : null}
    </>
  );
}

/** Matches PackDetailContent's layout: title block, stat row, two card tables. */
function PackDetailSkeleton() {
  return (
    <>
      <div>
        <Skeleton className="h-8 w-72 max-w-full" />
        <Skeleton className="mt-2 h-4 w-40" />
      </div>
      <StatTilesSkeleton count={4} className="sm:grid-cols-2 lg:grid-cols-4" />
      {[0, 1].map((i) => (
        <div key={i}>
          <Skeleton className="mb-3 h-6 w-40" />
          <TableSkeleton rows={6} columns={5} />
        </div>
      ))}
    </>
  );
}

export default function PackDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  // The back-link is static shell, so PPR paints it before the pack resolves.
  return (
    <div className="space-y-6">
      <Link
        href="/packs"
        className="text-sm text-muted-foreground hover:underline"
      >
        ← Pack Recommendations
      </Link>
      <Suspense fallback={<PackDetailSkeleton />}>
        <PackDetailContent params={params} />
      </Suspense>
    </div>
  );
}
