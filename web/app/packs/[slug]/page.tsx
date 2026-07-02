import { notFound } from "next/navigation";
import Link from "next/link";

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

export const dynamic = "force-dynamic";

export default async function PackDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const packEv = await dataSource.getPackEv();
  const pack = packEv.packs.find((p) => packSlug(p.pack_name) === slug);

  if (!pack) notFound();

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
                // alt-art ex), and top_ev_cards carries no coord — key by index.
                <TableRow key={`${c.name}-${i}`}>
                  <TableCell className="font-medium">{c.name}</TableCell>
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
                    <TableCell className="font-medium">{c.name}</TableCell>
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
