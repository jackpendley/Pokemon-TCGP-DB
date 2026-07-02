import Link from "next/link";

import { CardImage } from "@/components/cards/card-image";
import { SetLogo } from "@/components/sets/set-logo";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { formatEv, packSlug, titleCase } from "@/lib/domain/format";
import type { PackRecord, TopPowerCard } from "@/types";

/**
 * One "what to open next" recommendation: a pack's unified score + 10× new-card
 * EV, with its strongest unowned pull targets as thumbnails. Links to the pack
 * detail page. `powerCards` may be empty (falls back to just the scores).
 */
export function NextPackCard({
  pack,
  powerCards,
  rank,
}: {
  pack: PackRecord;
  powerCards: TopPowerCard[];
  rank: number;
}) {
  return (
    <Link href={`/packs/${packSlug(pack.pack_name)}`} className="group block">
      <Card className="h-full transition-colors hover:border-primary/50">
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
            <div className="font-semibold leading-tight group-hover:text-primary">
              {pack.pack_name}
            </div>
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
          {powerCards.length > 0 ? (
            <div>
              <div className="mb-1 text-[11px] font-medium text-muted-foreground">
                Top pull targets
              </div>
              <div className="flex gap-1.5">
                {powerCards.slice(0, 4).map((c, i) => (
                  <div
                    key={`${c.set_code}-${c.card_number}-${i}`}
                    className="aspect-[5/7] w-10 shrink-0 overflow-hidden rounded border"
                    title={`${c.name} · power ${c.power_score.toFixed(0)}`}
                  >
                    <CardImage card={{ ...c, owned: 0 }} />
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </CardContent>
      </Card>
    </Link>
  );
}
