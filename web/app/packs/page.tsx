import Link from "next/link";

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
import { formatEv, packSlug, titleCase } from "@/lib/domain/format";

export const dynamic = "force-dynamic";
export const metadata = { title: "Pack Recommendations · TCGP Optimizer" };

export default async function PacksPage() {
  const recs = await dataSource.getRecommendations();

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">
          Pack Recommendations
        </h1>
        <p className="text-sm text-muted-foreground">{recs.disclaimer}</p>
      </header>

      <div className="rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-10">#</TableHead>
              <TableHead>Pack</TableHead>
              <TableHead className="text-right">Unified</TableHead>
              <TableHead className="text-right">New-card EV (10x)</TableHead>
              <TableHead className="text-right">Missing</TableHead>
              <TableHead className="text-right">Cost / unique</TableHead>
              <TableHead>Confidence</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {recs.top_packs_unified.map((p, i) => (
              <TableRow key={`${p.set_code}-${p.pack_name}`}>
                <TableCell className="text-muted-foreground tabular-nums">
                  {i + 1}
                </TableCell>
                <TableCell>
                  <Link
                    href={`/packs/${packSlug(p.pack_name)}`}
                    className="font-medium hover:underline"
                  >
                    {p.pack_name}
                  </Link>
                  <div className="text-xs text-muted-foreground">
                    {p.expansion}
                  </div>
                </TableCell>
                <TableCell className="text-right font-medium tabular-nums">
                  {formatEv(p.unified_score)}
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {formatEv(p.new_card_ev_10x)}
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {p.missing_in_pool}/{p.cards_in_pool}
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {formatEv(p.cost_per_unique_card_10x)}
                </TableCell>
                <TableCell>
                  <Badge
                    variant={p.confidence_weight >= 1 ? "secondary" : "outline"}
                  >
                    {titleCase(p.slot_rates_confidence)}
                  </Badge>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
