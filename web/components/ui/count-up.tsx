"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Tweens a number to `value` whenever it changes (used for the set-progress
 * toggle). Honors prefers-reduced-motion by snapping instantly.
 */
export function CountUp({
  value,
  durationMs = 500,
  format = (n) => String(Math.round(n)),
}: {
  value: number;
  durationMs?: number;
  format?: (n: number) => string;
}) {
  const [display, setDisplay] = useState(value);
  const fromRef = useRef(value);

  useEffect(() => {
    const reduce =
      typeof window !== "undefined" &&
      window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    const from = fromRef.current;
    if (reduce || from === value) {
      setDisplay(value);
      fromRef.current = value;
      return;
    }
    let raf = 0;
    let start: number | null = null;
    const step = (t: number) => {
      start ??= t;
      const p = Math.min(1, (t - start) / durationMs);
      const eased = 1 - Math.pow(1 - p, 3);
      const current = from + (value - from) * eased;
      setDisplay(current);
      fromRef.current = current;
      if (p < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [value, durationMs]);

  return <>{format(display)}</>;
}
