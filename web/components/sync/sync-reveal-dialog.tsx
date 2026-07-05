"use client";

import { useState } from "react";

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
} from "@/components/ui/dialog";

/**
 * The just-synced reveal, shown as a dismissable popup right after a sync. Same
 * content/animation as before, but overlaid so dismissing returns the dashboard to
 * normal (with refreshed numbers) — the sync itself stays listed in Sync history.
 */
export function SyncRevealDialog({
  items,
  setProgress,
  count,
}: {
  items: AdditionItem[];
  setProgress: SetProgressItem[];
  count: number;
}) {
  const [open, setOpen] = useState(true);
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            Added in your latest sync
            <Badge variant="secondary">{count} cards</Badge>
          </DialogTitle>
        </DialogHeader>
        <SyncReveal items={items} setProgress={setProgress} />
      </DialogContent>
    </Dialog>
  );
}
