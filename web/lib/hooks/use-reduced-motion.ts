"use client";

import { useMediaQuery } from "@/lib/hooks/use-media-query";

/**
 * Whether the viewer has asked for reduced motion.
 *
 * Needed because some of our motion is driven from JS (the reveal auto-scroll,
 * the card flip's swipe handling), so the `prefers-reduced-motion` guard in
 * globals.css can't cover it on its own.
 */
export function usePrefersReducedMotion(): boolean {
  return useMediaQuery("(prefers-reduced-motion: reduce)");
}
