"use client";

import { useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import { ChevronLeft, ChevronRight, RotateCw } from "lucide-react";

import { CardFlip } from "@/components/cards/card-flip";
import { usePrefersReducedMotion } from "@/lib/hooks/use-reduced-motion";
import type { CatalogCard } from "@/types";

/** Travel before a drag counts as a swipe rather than a tap. */
const SWIPE_PX = 55;
/** Beyond this, a gesture is too slow to be a flick — treat it as a scroll attempt. */
const SWIPE_MS = 800;

/**
 * Full-screen card viewer for phones.
 *
 * The card is the whole screen: art edge to edge, no dialog chrome competing
 * with it. Gestures follow the physical metaphor — swipe up or down (or tap) to
 * turn the card over, swipe sideways to move through the cards you were just
 * looking at.
 *
 * Buttons mirror every gesture, so the viewer is fully usable without them
 * (and reachable by keyboard and screen readers).
 */
export function CardViewerMobile({
  card,
  siblings,
  onNavigate,
}: {
  card: CatalogCard;
  /** Cards to step through with a horizontal swipe — usually the grid behind. */
  siblings?: CatalogCard[];
  onNavigate?: (card: CatalogCard) => void;
}) {
  const [flipped, setFlipped] = useState(false);
  const reduced = usePrefersReducedMotion();
  const start = useRef<{ x: number; y: number; t: number } | null>(null);

  const index =
    siblings?.findIndex(
      (c) => c.set_code === card.set_code && c.card_number === card.card_number,
    ) ?? -1;
  const canStep = onNavigate != null && index >= 0 && (siblings?.length ?? 0) > 1;

  function step(delta: number) {
    if (!canStep || !siblings) return;
    const next = siblings[index + delta];
    if (!next) return;
    // Always land on the artwork; keeping the back showing across a change
    // would present the new card already turned over.
    setFlipped(false);
    onNavigate(next);
  }

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
      step(dx < 0 ? 1 : -1); // swipe left → next
      return;
    }
    if (Math.abs(dy) > SWIPE_PX) {
      setFlipped((v) => !v);
    }
    // Anything smaller is a tap, which CardFlip's own button handles.
  }

  const hasPrev = canStep && index > 0;
  const hasNext = canStep && siblings != null && index < siblings.length - 1;

  return (
    <div
      className="flex h-full w-full flex-col justify-center gap-4 px-3 py-4"
      onPointerDown={onPointerDown}
      onPointerUp={onPointerUp}
      // Let the browser keep vertical panning; we only claim horizontal drags.
      style={{ touchAction: "pan-y" }}
    >
      <CardFlip
        card={card}
        flipped={flipped}
        onToggle={() => setFlipped((v) => !v)}
        className="mx-auto max-h-full w-full max-w-[min(100%,calc((100dvh-8.5rem)*5/7))]"
      />

      <div className="flex items-center justify-center gap-2">
        <GestureButton
          label="Previous card"
          onClick={() => step(-1)}
          disabled={!hasPrev}
        >
          <ChevronLeft className="size-5" />
        </GestureButton>
        <GestureButton
          label={flipped ? "Show artwork" : "Show details"}
          onClick={() => setFlipped((v) => !v)}
          wide
        >
          <RotateCw className="size-4" />
          <span className="text-sm font-medium">
            {flipped ? "Artwork" : "Details"}
          </span>
        </GestureButton>
        <GestureButton
          label="Next card"
          onClick={() => step(1)}
          disabled={!hasNext}
        >
          <ChevronRight className="size-5" />
        </GestureButton>
      </div>

      {!reduced ? (
        <p className="text-center text-xs text-muted-foreground">
          Swipe up or down to flip{canStep ? " · sideways to browse" : ""}
        </p>
      ) : null}
    </div>
  );
}

function GestureButton({
  label,
  onClick,
  disabled,
  wide,
  children,
}: {
  label: string;
  onClick: () => void;
  disabled?: boolean;
  wide?: boolean;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      onClick={onClick}
      disabled={disabled}
      // 44px minimum so these are comfortable one-handed targets.
      className={[
        "inline-flex h-11 items-center justify-center gap-2 rounded-full border bg-background/80 transition-colors",
        wide ? "px-5" : "w-11",
        disabled ? "opacity-35" : "hover:bg-accent",
      ].join(" ")}
    >
      {children}
    </button>
  );
}
