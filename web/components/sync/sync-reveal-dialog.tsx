"use client";

import type { ReactNode } from "react";

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

/**
 * A sync's added cards + set progress, shown as a large dismissable popup (with the
 * Dialog's built-in appear/fade animations). Used both for the fresh sync
 * (`defaultOpen`, no trigger) and for each history row (`trigger` = the row).
 */
export function SyncRevealDialog({
  items,
  setProgress,
  count,
  title = "Added in your latest sync",
  trigger,
  triggerClassName,
  defaultOpen = false,
}: {
  items: AdditionItem[];
  setProgress: SetProgressItem[];
  count: number;
  title?: string;
  trigger?: ReactNode;
  triggerClassName?: string;
  defaultOpen?: boolean;
}) {
  return (
    <Dialog defaultOpen={defaultOpen}>
      {trigger ? (
        <DialogTrigger className={cn("text-left", triggerClassName)}>
          {trigger}
        </DialogTrigger>
      ) : null}
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-5xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {title}
            <Badge variant="secondary">{count} cards</Badge>
          </DialogTitle>
        </DialogHeader>
        <SyncReveal items={items} setProgress={setProgress} />
      </DialogContent>
    </Dialog>
  );
}
