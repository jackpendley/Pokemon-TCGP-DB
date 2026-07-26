"use client";

import { useSyncExternalStore } from "react";

const QUERY = "(prefers-reduced-motion: reduce)";

function subscribe(onChange: () => void): () => void {
  const mq = window.matchMedia(QUERY);
  mq.addEventListener("change", onChange);
  return () => mq.removeEventListener("change", onChange);
}

const getSnapshot = () => window.matchMedia(QUERY).matches;

/** Server render assumes motion is fine; the client corrects on hydration. */
const getServerSnapshot = () => false;

/**
 * Whether the viewer has asked for reduced motion.
 *
 * Needed because the reveal's auto-scroll is driven from JS, so the
 * `prefers-reduced-motion` guard in globals.css can't cover it. Modelled as an
 * external store subscription, which is what a media query is.
 */
export function usePrefersReducedMotion(): boolean {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}
