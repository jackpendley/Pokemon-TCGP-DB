"use client";

import { useEffect, useState, type ReactNode } from "react";

import {
  SyncReveal,
  type AdditionItem,
  type SetProgressItem,
} from "@/components/sync/sync-reveal";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";

/** Last dismissed fresh-sync reveal (a stats.fetched_at value). */
const DISMISSED_KEY = "sync-reveal-dismissed";

/**
 * A sync's added cards + set progress, shown as a large dismissable popup (with the
 * Dialog's built-in appear/fade animations). Two modes:
 * - fresh sync (`revealId` = the sync's fetched_at): auto-opens once per sync;
 *   dismissal is remembered in localStorage so navigating back to the
 *   dashboard doesn't relaunch it.
 * - history row (`trigger` = the row): plain uncontrolled dialog.
 */
export function SyncRevealDialog({
  items,
  setProgress,
  count,
  title = "Added in your latest sync",
  trigger,
  triggerClassName,
  revealId,
}: {
  items: AdditionItem[];
  setProgress: SetProgressItem[];
  count: number;
  title?: string;
  trigger?: ReactNode;
  triggerClassName?: string;
  revealId?: string;
}) {
  const [open, setOpen] = useState(false);

  // Open after mount (localStorage is client-only) unless this sync's reveal
  // was already dismissed. Deferred a frame so the dialog mounts closed and
  // animates in.
  useEffect(() => {
    if (!revealId || localStorage.getItem(DISMISSED_KEY) === revealId) return;
    const id = requestAnimationFrame(() => setOpen(true));
    return () => cancelAnimationFrame(id);
  }, [revealId]);

  function onOpenChange(next: boolean) {
    setOpen(next);
    if (!next && revealId) localStorage.setItem(DISMISSED_KEY, revealId);
  }

  return (
    <Dialog {...(revealId ? { open, onOpenChange } : {})}>
      {trigger ? (
        <DialogTrigger className={cn("text-left", triggerClassName)}>
          {trigger}
        </DialogTrigger>
      ) : null}
      {/* The popup itself no longer scrolls — only the body does — so the title
          and the absolutely-positioned close button stay put. Previously the
          whole dialog scrolled and both disappeared off the top. */}
      <DialogContent
        className="flex max-h-[90vh] flex-col overflow-hidden sm:max-w-5xl"
        // Auto-opened: leave focus alone so the first card / close button
        // doesn't render with a focus ring the user never asked for.
        initialFocus={revealId ? false : undefined}
      >
        <DialogHeader className="shrink-0 pr-10">
          <DialogTitle className="flex items-center gap-2">
            {title}
            <Badge variant="secondary">{count} cards</Badge>
          </DialogTitle>
        </DialogHeader>
        {/* Negative margins let the scrollbar sit at the popup edge while the
            content keeps the dialog's own padding. */}
        <div className="-mx-4 min-h-0 flex-1 overflow-y-auto px-4 pb-1">
          <SyncReveal items={items} setProgress={setProgress} />
        </div>
      </DialogContent>
    </Dialog>
  );
}
