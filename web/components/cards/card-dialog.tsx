"use client";

import { CardImage } from "@/components/cards/card-image";
import { CardViewerMobile } from "@/components/cards/card-viewer-mobile";
import { EvolutionTabs } from "@/components/cards/evolution-tabs";
import { TypeBadge } from "@/components/cards/type-badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useIsMobile } from "@/lib/hooks/use-media-query";
import { displayType } from "@/lib/domain/card";
import { titleCase } from "@/lib/domain/format";
import type { CatalogCard } from "@/types";

/**
 * The enlarged card view, in two forms.
 *
 * On a phone the card takes the whole screen and flips to reveal its details
 * (CardViewerMobile) — there isn't room to show art and metadata at once, and
 * shrinking the art to fit both wastes the one thing worth looking at.
 *
 * On larger screens both fit side by side, so nothing is hidden behind an
 * interaction and the evolution tabs stay in view. Previously this was a fixed
 * 320px column with a two-column metadata list at every breakpoint, which was
 * near edge-to-edge on a phone and cramped at both ends.
 */
export function CardDialog({
  card,
  onClose,
  allCards,
  onSelect,
  siblings,
}: {
  card: CatalogCard | null;
  onClose: () => void;
  /** When provided, the dialog shows evolution/versions tabs. */
  allCards?: CatalogCard[];
  /** Navigate the dialog to a related card (from the evolution tabs). */
  onSelect?: (c: CatalogCard) => void;
  /** Cards a horizontal swipe steps through on mobile — usually the grid behind. */
  siblings?: CatalogCard[];
}) {
  const isMobile = useIsMobile();

  return (
    <Dialog open={card !== null} onOpenChange={(open) => !open && onClose()}>
      {isMobile ? (
        // Full-bleed: no rounding, no padding, no max width — the card is the screen.
        <DialogContent className="inset-0 top-0 left-0 h-dvh w-screen max-w-none translate-x-0 translate-y-0 rounded-none p-0">
          {card ? (
            <>
              <DialogHeader className="sr-only">
                <DialogTitle>{card.name}</DialogTitle>
              </DialogHeader>
              <CardViewerMobile
                card={card}
                siblings={siblings}
                onNavigate={onSelect}
              />
            </>
          ) : null}
        </DialogContent>
      ) : (
        <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-2xl">
          {card ? (
            <div className="space-y-4">
              <DialogHeader>
                <DialogTitle>{card.name}</DialogTitle>
              </DialogHeader>

              <div className="grid gap-5 sm:grid-cols-[minmax(0,17rem)_1fr]">
                <div className="overflow-hidden rounded-lg border">
                  <div className="aspect-[5/7]">
                    {/* key remounts on card change so the error state resets */}
                    <CardImage
                      key={`${card.set_code}-${card.card_number}`}
                      card={card}
                      size="lg"
                    />
                  </div>
                </div>

                <dl className="flex flex-col gap-3 text-sm">
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
              </div>

              {allCards && onSelect ? (
                <EvolutionTabs
                  card={card}
                  allCards={allCards}
                  onSelect={onSelect}
                />
              ) : null}
            </div>
          ) : null}
        </DialogContent>
      )}
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
