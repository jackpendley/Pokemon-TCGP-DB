import Link from "next/link";

import { EnlargeableCard } from "@/components/cards/enlargeable-card";
import { SetLogo } from "@/components/sets/set-logo";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { formatEv, packSlug, titleCase } from "@/lib/domain/format";
import type { CatalogCard, PackRecord } from "@/types";

/**
 * One "what to open next" recommendation: a pack's unified score + 10× new-card
 * EV, with its strongest unowned pull targets as enlargeable thumbnails. The card
 * itself isn't a link (thumbnails are interactive) — the pack name + CTA link out.
 */
export function NextPackCard({
  pack,
  targets,
  rank,
}: {
  pack: PackRecord;
  targets: CatalogCard[];
  rank: number;
}) {
  const href = `/packs/${packSlug(pack.pack_name)}`;
  return (
    <Card className="h-full">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="tabular-nums">
              #{rank}
            </Badge>
            <SetLogo
              setCode={pack.set_code}
              label={pack.expansion}
              className="h-6 w-14"
            />
          </div>
          <Badge variant="secondary">
            {titleCase(pack.slot_rates_confidence)}
          </Badge>
        </div>
        <div className="mt-2">
          <Link
            href={href}
            className="font-semibold leading-tight hover:text-primary hover:underline"
          >
            {pack.pack_name}
          </Link>
          <div className="text-xs text-muted-foreground">
            {pack.expansion} · {pack.missing_in_pool} missing of{" "}
            {pack.cards_in_pool}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-end justify-between">
          <div>
            <div className="text-2xl font-semibold tabular-nums text-primary">
              {formatEv(pack.unified_score)}
            </div>
            <div className="text-[11px] text-muted-foreground">
              unified score
            </div>
          </div>
          <div className="text-right">
            <div className="text-lg font-semibold tabular-nums">
              {formatEv(pack.new_card_ev_10x)}
            </div>
            <div className="text-[11px] text-muted-foreground">
              new-card EV (10×)
            </div>
          </div>
        </div>
        {targets.length > 0 ? (
          <div>
            <div className="mb-1 text-[11px] font-medium text-muted-foreground">
              Top pull targets
            </div>
            <div className="flex gap-1.5">
              {targets.slice(0, 4).map((c) => (
                <EnlargeableCard
                  key={`${c.set_code}-${c.card_number}`}
                  card={c}
                  className="w-12"
                />
              ))}
            </div>
          </div>
        ) : null}
        <Link
          href={href}
          className="inline-block text-sm font-medium text-primary hover:underline"
        >
          View pack →
        </Link>
      </CardContent>
    </Card>
  );
}
