"use client";

import { CardImage } from "@/components/cards/card-image";
import { EvolutionTabs } from "@/components/cards/evolution-tabs";
import { TypeBadge } from "@/components/cards/type-badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { displayType } from "@/lib/domain/card";
import { titleCase } from "@/lib/domain/format";
import type { CatalogCard } from "@/types";

export function CardDialog({
  card,
  onClose,
  allCards,
  onSelect,
}: {
  card: CatalogCard | null;
  onClose: () => void;
  /** When provided, the dialog shows evolution/versions tabs. */
  allCards?: CatalogCard[];
  /** Navigate the dialog to a related card (from the evolution tabs). */
  onSelect?: (c: CatalogCard) => void;
}) {
  return (
    <Dialog open={card !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-lg">
        {card ? (
          <div className="space-y-4">
            <div className="mx-auto w-56 overflow-hidden rounded-lg border">
              <div className="aspect-[5/7]">
                {/* key remounts on card change so the error state resets */}
                <CardImage
                  key={`${card.set_code}-${card.card_number}`}
                  card={card}
                  size="lg"
                />
              </div>
            </div>

            <DialogHeader>
              <DialogTitle className="text-center">{card.name}</DialogTitle>
            </DialogHeader>

            <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
              <Row label="Set">
                {card.expansion} · {card.set_code}
              </Row>
              <Row label="Number">#{card.card_number}</Row>
              <Row label="Rarity">{titleCase(card.rarity)}</Row>
              <Row label="Type">
                <TypeBadge type={displayType(card)} />
              </Row>
              <Row label="Owned">
                {card.owned > 0 ? `×${card.owned}` : "Not owned"}
              </Row>
              {card.power_score != null ? (
                <Row label="Power score">
                  <span className="font-semibold tabular-nums text-primary">
                    {card.power_score.toFixed(1)}
                  </span>
                  <span className="text-xs text-muted-foreground"> / 100</span>
                </Row>
              ) : null}
            </dl>

            {allCards && onSelect ? (
              <EvolutionTabs card={card} allCards={allCards} onSelect={onSelect} />
            ) : null}
          </div>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}

function Row({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="font-medium">{children}</dd>
    </div>
  );
}
