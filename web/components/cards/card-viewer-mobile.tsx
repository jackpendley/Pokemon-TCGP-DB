"use client";

import { useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import { Layers, Plus, RotateCw, X } from "lucide-react";

import { CardFlip } from "@/components/cards/card-flip";
import { EvolutionTabs } from "@/components/cards/evolution-tabs";
import { usePrefersReducedMotion } from "@/lib/hooks/use-reduced-motion";
import { cn } from "@/lib/utils";
import type { CatalogCard } from "@/types";

/** Travel before a drag counts as a swipe rather than a tap. */
const SWIPE_PX = 55;
/** Beyond this, a gesture is too slow to be a flick — treat it as a scroll attempt. */
const SWIPE_MS = 800;

/**
 * Full-screen card viewer for phones.
 *
 * The card is the whole screen: art edge to edge, no dialog chrome competing with
 * it. Gestures follow the physical metaphor — swipe sideways to turn the card
 * over, swipe down to look behind it at the cards it's related to.
 *
 * It used to step sideways through the grid you came from instead, and had no way
 * to reach the evolution line, other printings or related cards at all — the tabs
 * were desktop-only. Navigating by tapping a related card is both more useful and
 * more discoverable than blind sideways paging, so stepping is gone.
 *
 * Buttons mirror every gesture, so the viewer is fully usable without them (and
 * reachable by keyboard and screen readers).
 */
export function CardViewerMobile({
  card,
  allCards,
  onSelect,
  onAdd,
  canAdd,
}: {
  card: CatalogCard;
  /** When provided with onSelect, the related-cards panel is available. */
  allCards?: CatalogCard[];
  /** Navigate the viewer to a related card. */
  onSelect?: (c: CatalogCard) => void;
  /** Deck builder only: add a card to the deck from the panel. */
  onAdd?: (c: CatalogCard) => void;
  /** Whether a given card can still be added (copy limit, read-only deck). */
  canAdd?: (c: CatalogCard) => boolean;
}) {
  const [flipped, setFlipped] = useState(false);
  const [panelOpen, setPanelOpen] = useState(false);
  const reduced = usePrefersReducedMotion();
  const start = useRef<{ x: number; y: number; t: number } | null>(null);

  const canExplore = allCards != null && onSelect != null;

  function onPointerDown(e: ReactPointerEvent) {
    start.current = { x: e.clientX, y: e.clientY, t: Date.now() };
  }

  function onPointerUp(e: ReactPointerEvent) {
    const from = start.current;
    start.current = null;
    if (!from) return;

    const dx = e.clientX - from.x;
    const dy = e.clientY - from.y;
    if (Date.now() - from.t > SWIPE_MS) return;

    if (Math.abs(dx) > Math.abs(dy) && Math.abs(dx) > SWIPE_PX) {
      setFlipped((v) => !v);
      return;
    }
    if (Math.abs(dy) > SWIPE_PX) {
      // Down opens the panel, up closes it — the panel comes from the bottom, so
      // the gesture matches the direction the sheet actually travels.
      if (canExplore) setPanelOpen(dy > 0);
    }
    // Anything smaller is a tap, which CardFlip's own button handles.
  }

  return (
    <div className="relative flex h-full w-full flex-col justify-center gap-4 px-3 py-4">
      <div
        onPointerDown={onPointerDown}
        onPointerUp={onPointerUp}
        // Let the browser keep vertical panning; we only claim horizontal drags.
        style={{ touchAction: "pan-y" }}
        className="contents"
      >
        <CardFlip
          card={card}
          flipped={flipped}
          onToggle={() => setFlipped((v) => !v)}
          className="mx-auto max-h-full w-full max-w-[min(100%,calc((100dvh-8.5rem)*5/7))]"
        />
      </div>

      <div className="flex items-center justify-center gap-2">
        <GestureButton
          label={flipped ? "Show artwork" : "Show details"}
          onClick={() => setFlipped((v) => !v)}
        >
          <RotateCw className="size-4" />
          <span className="text-sm font-medium">
            {flipped ? "Artwork" : "Details"}
          </span>
        </GestureButton>
        {canExplore ? (
          <GestureButton label="Show related cards" onClick={() => setPanelOpen(true)}>
            <Layers className="size-4" />
            <span className="text-sm font-medium">Related</span>
          </GestureButton>
        ) : null}
      </div>

      {!reduced ? (
        <p className="text-center text-xs text-muted-foreground">
          Swipe sideways to flip{canExplore ? " · down for related cards" : ""}
        </p>
      ) : null}

      {canExplore ? (
        <div
          // Kept mounted so the sheet can animate, and so the tab state it holds
          // survives a close/open. aria-hidden + inert keep it out of reach while
          // it's off-screen.
          inert={!panelOpen}
          aria-hidden={!panelOpen}
          className={cn(
            "absolute inset-x-0 bottom-0 max-h-[75%] overflow-y-auto rounded-t-2xl border-t bg-background p-4 shadow-lg",
            !reduced && "transition-transform duration-300 ease-out",
            panelOpen ? "translate-y-0" : "translate-y-full",
          )}
          onKeyDown={(e) => {
            // Escape closes the panel rather than the whole dialog — the panel is
            // the innermost thing open, so it's what Escape should dismiss.
            if (e.key === "Escape") {
              e.stopPropagation();
              setPanelOpen(false);
            }
          }}
        >
          <div className="mb-2 flex items-center justify-between gap-2">
            <p className="truncate text-sm font-medium">{card.name}</p>
            {onAdd ? (
              <button
                type="button"
                disabled={canAdd != null && !canAdd(card)}
                onClick={() => onAdd(card)}
                className="inline-flex h-9 shrink-0 items-center gap-1.5 rounded-md border px-3 text-sm font-medium disabled:opacity-45"
              >
                <Plus className="size-4" />
                Add
              </button>
            ) : null}
            <button
              type="button"
              aria-label="Hide related cards"
              onClick={() => setPanelOpen(false)}
              className="flex size-11 items-center justify-center rounded-full text-muted-foreground"
            >
              <X className="size-5" />
            </button>
          </div>
          <EvolutionTabs
            card={card}
            allCards={allCards}
            onSelect={onSelect}
            onAdd={onAdd}
            canAdd={canAdd}
          />
        </div>
      ) : null}
    </div>
  );
}

function GestureButton({
  label,
  onClick,
  children,
}: {
  label: string;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      onClick={onClick}
      // 44px minimum so these are comfortable one-handed targets.
      className="inline-flex h-11 items-center justify-center gap-2 rounded-full border bg-background/80 px-5 transition-colors hover:bg-accent"
    >
      {children}
    </button>
  );
}
