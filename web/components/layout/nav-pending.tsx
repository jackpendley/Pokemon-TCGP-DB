"use client";

import { useLinkStatus } from "next/link";
import { Loader2 } from "lucide-react";

import { cn } from "@/lib/utils";

/**
 * Inline pending hint for a sidebar link. Must render inside a <Link>.
 *
 * Always occupies its slot and only toggles opacity, so it can never shift the
 * nav layout (see the Next docs' warning about inline indicators). Once a route
 * has been prefetched the pending phase is skipped entirely — this exists for
 * the slow-connection case where the click would otherwise feel unresponsive.
 */
export function NavPending() {
  const { pending } = useLinkStatus();
  return (
    <Loader2
      aria-hidden
      className={cn(
        "ml-auto size-3.5 shrink-0 transition-opacity",
        pending ? "animate-spin opacity-70" : "opacity-0",
      )}
    />
  );
}
