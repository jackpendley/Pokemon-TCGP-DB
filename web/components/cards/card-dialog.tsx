"use client";

import { Plus } from "lucide-react";

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
import { displayType, powerScoreLabel } from "@/lib/domain/card";
import { MAX_COPIES_PER_NAME } from "@/lib/domain/deck";
import { titleCase } from "@/lib/domain/format";
import type { CatalogCard } from "@/types";

/**
 * The enlarged card view, in two forms.
 *
 * On a phone the card takes the whole screen and flips to reveal its details
 * (CardViewerMobile) — there isn't room to show art and metadata at once, and
 * shrinking the art to fit both wastes the one thing worth looking at. The
 * relationship tabs live in a sheet there rather than below the card.
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
  onAdd,
  canAdd,
}: {
  card: CatalogCard | null;
  onClose: () => void;
  /** When provided, the dialog shows evolution/versions tabs. */
  allCards?: CatalogCard[];
  /** Navigate the dialog to a related card (from the evolution tabs). */
  onSelect?: (c: CatalogCard) => void;
  /** Deck builder only: add a card to the deck from here. */
  onAdd?: (c: CatalogCard) => void;
  /** Whether a given card can still be added (copy limit, read-only deck). */
  canAdd?: (c: CatalogCard) => boolean;
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
                allCards={allCards}
                onSelect={onSelect}
                onAdd={onAdd}
                canAdd={canAdd}
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

              {onAdd ? (
                <AddToDeckButton card={card} onAdd={onAdd} canAdd={canAdd} />
              ) : null}

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
                    <Row label={powerScoreLabel(card)}>
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
                  onAdd={onAdd}
                  canAdd={canAdd}
                />
              ) : null}
            </div>
          ) : null}
        </DialogContent>
      )}
    </Dialog>
  );
}

function AddToDeckButton({
  card,
  onAdd,
  canAdd,
}: {
  card: CatalogCard;
  onAdd: (c: CatalogCard) => void;
  canAdd?: (c: CatalogCard) => boolean;
}) {
  const allowed = canAdd == null || canAdd(card);
  return (
    <button
      type="button"
      onClick={() => onAdd(card)}
      disabled={!allowed}
      className="inline-flex h-9 items-center gap-1.5 self-start rounded-md border px-3 text-sm font-medium transition-colors hover:bg-accent disabled:opacity-45"
    >
      <Plus className="size-4" />
      {allowed ? "Add to deck" : `Already at ${MAX_COPIES_PER_NAME} copies`}
    </button>
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
