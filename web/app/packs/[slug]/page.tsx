import { notFound } from "next/navigation";
import Link from "next/link";

import { EnlargeableCard } from "@/components/cards/enlargeable-card";
import { StatCard } from "@/components/dashboard/stat-card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { dataSource } from "@/lib/data";
import {
  formatEv,
  formatPercent,
  packSlug,
  titleCase,
} from "@/lib/domain/format";
import type { CatalogCard } from "@/types";

export const dynamic = "force-dynamic";

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

export default async function PackDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const [packEv, catalog] = await Promise.all([
    dataSource.getPackEv(),
    dataSource.getCatalog(),
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
    };

  return (
    <div className="space-y-6">
      <div>
        <Link
          href="/packs"
          className="text-sm text-muted-foreground hover:underline"
        >
          ← Pack Recommendations
        </Link>
        <h1 className="mt-2 flex items-center gap-3 text-2xl font-semibold tracking-tight">
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
    </div>
  );
}
