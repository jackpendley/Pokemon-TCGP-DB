"use client";

import { useCallback, useSyncExternalStore } from "react";

/**
 * Subscribe to a CSS media query.
 *
 * Modelled as an external store because that is what a MediaQueryList is —
 * setState-in-effect for this trips react-hooks/set-state-in-effect and causes a
 * cascading render. The server snapshot is always false, so server and first
 * client render agree and the client corrects on hydration.
 *
 * Use this only for behaviour CSS cannot express (which tree to render, whether
 * to run a JS-driven animation). Plain responsive styling belongs in Tailwind
 * breakpoints.
 */
export function useMediaQuery(query: string): boolean {
  const subscribe = useCallback(
    (onChange: () => void) => {
      const mq = window.matchMedia(query);
      mq.addEventListener("change", onChange);
      return () => mq.removeEventListener("change", onChange);
    },
    [query],
  );
  const getSnapshot = useCallback(() => window.matchMedia(query).matches, [query]);
  return useSyncExternalStore(subscribe, getSnapshot, () => false);
}

/** Phone-sized viewport — below Tailwind's `sm` breakpoint. */
export const MOBILE_QUERY = "(max-width: 639px)";

/**
 * Whether this is a phone-sized viewport. Drives the card viewer's interaction
 * model (full-screen + swipe on phones, side-by-side on larger screens).
 */
export function useIsMobile(): boolean {
  return useMediaQuery(MOBILE_QUERY);
}
