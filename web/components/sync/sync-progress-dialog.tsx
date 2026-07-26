"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, RefreshCw } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";
import type { SyncJobStatus } from "@/types";

/** What the dialog is reporting. `error` carries a message; the rest are job states. */
export type SyncPhase = SyncJobStatus | "error";

const STATUS_COPY: Record<string, { title: string; detail: string }> = {
  queued: {
    title: "Sync queued",
    detail: "Waiting for the runner to pick up the job…",
  },
  running: {
    title: "Syncing your collection",
    detail:
      "Reading your Pokémon Zone collection and rebuilding pack recommendations. This usually takes a couple of minutes.",
  },
  done: {
    title: "Sync complete",
    detail: "Bringing in what changed…",
  },
};

function elapsedLabel(ms: number): string {
  const s = Math.floor(ms / 1000);
  return s < 60 ? `${s}s` : `${Math.floor(s / 60)}m ${String(s % 60).padStart(2, "0")}s`;
}

/**
 * Foreground progress for a sync run.
 *
 * A sync takes minutes, and previously the only feedback was a button spinner
 * and a corner toast — easy to miss and impossible to check back on. The job
 * contract (types/sync.ts) has no percentage, so this reports the honest
 * things: the lifecycle state, elapsed time, and any message. On success it
 * closes itself and hands off to the reveal popup.
 */
export function SyncProgressDialog({
  open,
  phase,
  message,
  startedAtMs,
  onOpenChange,
}: {
  open: boolean;
  phase: SyncPhase;
  message: string | null;
  startedAtMs: number | null;
  onOpenChange: (open: boolean) => void;
}) {
  const failed = phase === "error" || phase === "needs_reauth";
  const succeeded = phase === "done";
  const copy = STATUS_COPY[phase] ?? STATUS_COPY.running;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="sm:max-w-md"
        showCloseButton={failed}
        // Don't yank focus mid-task; the dialog is a status report, not a prompt.
        initialFocus={false}
      >
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {failed ? (
              <AlertTriangle className="size-4 shrink-0 text-destructive" />
            ) : succeeded ? (
              <CheckCircle2 className="size-4 shrink-0 text-primary" />
            ) : (
              <RefreshCw className="size-4 shrink-0 animate-spin text-primary" />
            )}
            {failed ? "Sync failed" : copy.title}
          </DialogTitle>
          <DialogDescription>
            {failed ? (message ?? "The sync did not finish.") : copy.detail}
          </DialogDescription>
        </DialogHeader>

        {!failed ? (
          <div className="space-y-2">
            <IndeterminateBar done={succeeded} />
            <Elapsed startedAtMs={startedAtMs} running={!succeeded} />
          </div>
        ) : null}

        {failed ? <DialogFooter showCloseButton /> : null}
      </DialogContent>
    </Dialog>
  );
}

/**
 * Indeterminate because the job reports no progress fraction — a fake
 * percentage would be worse than none. Fills solid on success.
 */
function IndeterminateBar({ done }: { done: boolean }) {
  return (
    <div className="relative h-1.5 overflow-hidden rounded-full bg-muted">
      <div
        className={cn(
          "absolute inset-y-0 rounded-full bg-primary",
          done ? "left-0 w-full transition-[width] duration-500" : "animate-sync-sweep",
        )}
      />
    </div>
  );
}

function Elapsed({
  startedAtMs,
  running,
}: {
  startedAtMs: number | null;
  running: boolean;
}) {
  const [now, setNow] = useState(startedAtMs ?? 0);

  useEffect(() => {
    if (!running || startedAtMs == null) return;
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, [running, startedAtMs]);

  if (startedAtMs == null) return null;
  return (
    <p className="text-right text-xs text-muted-foreground tabular-nums">
      {elapsedLabel(Math.max(0, now - startedAtMs))}
    </p>
  );
}
