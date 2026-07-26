"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { RefreshCw } from "lucide-react";

import { enqueueSync, getSyncJob } from "@/app/sync/actions";
import {
  SyncProgressDialog,
  type SyncPhase,
} from "@/components/sync/sync-progress-dialog";
import { Button } from "@/components/ui/button";
import type { SyncJobStatus } from "@/types";

const TERMINAL: SyncJobStatus[] = ["done", "error", "needs_reauth"];
const POLL_MS = 2500;
/** Beat to let "Sync complete" register before the reveal popup takes over. */
const HANDOFF_MS = 1200;

const REAUTH_MESSAGE =
  "Pokémon Zone auth expired — run scripts/sync_collection.py --curl-import and update the PZ_AUTH_JSON secret.";

/**
 * Triggers a sync and reports it in the foreground.
 *
 * Progress lives in a dialog rather than a toast: a sync takes minutes, and a
 * corner notification was easy to miss and impossible to check back on. On
 * success the dialog closes itself and the refreshed page opens the reveal
 * popup; failures stay on screen with their message.
 */
export function SyncButton({ enabled }: { enabled: boolean }) {
  const router = useRouter();
  const [jobId, setJobId] = useState<string | null>(null);
  const [phase, setPhase] = useState<SyncPhase>("queued");
  const [message, setMessage] = useState<string | null>(null);
  const [startedAtMs, setStartedAtMs] = useState<number | null>(null);
  const [open, setOpen] = useState(false);

  const running = jobId !== null;

  async function onClick() {
    setPhase("queued");
    setMessage(null);
    setStartedAtMs(Date.now());
    setOpen(true);

    const res = await enqueueSync();
    if (!res.ok) {
      setPhase("error");
      setMessage(res.reason);
      return;
    }
    // The remote runner can fail at enqueue time (dispatch rejected) — the job
    // arrives already terminal, so don't start polling.
    if (TERMINAL.includes(res.job.status)) {
      setPhase(res.job.status === "done" ? "done" : "error");
      setMessage(res.job.message ?? "Sync failed");
      return;
    }
    setPhase(res.job.status);
    setJobId(res.job.id);
  }

  useEffect(() => {
    if (!jobId) return;
    const timer = setInterval(async () => {
      const job = await getSyncJob(jobId);
      if (!job) return;
      setPhase(job.status);
      if (!TERMINAL.includes(job.status)) return;

      setJobId(null); // stops this effect's interval via cleanup
      // Always refresh on a terminal outcome: even a partial or errored run may
      // have written new collection + delta data before stopping, and the page
      // is the source of truth for what actually landed.
      router.refresh();

      if (job.status === "needs_reauth") {
        setPhase("error");
        setMessage(REAUTH_MESSAGE);
      } else if (job.status === "error") {
        setMessage(job.message ?? "Sync failed");
      }
    }, POLL_MS);
    return () => clearInterval(timer);
  }, [jobId, router]);

  // Hand off to the reveal popup, which the refreshed dashboard renders.
  useEffect(() => {
    if (phase !== "done") return;
    const t = setTimeout(() => setOpen(false), HANDOFF_MS);
    return () => clearTimeout(t);
  }, [phase]);

  return (
    <>
      <Button onClick={onClick} disabled={!enabled || running}>
        <RefreshCw className={running ? "animate-spin" : ""} />
        {running ? "Syncing…" : "Sync now"}
      </Button>
      <SyncProgressDialog
        open={open}
        phase={phase}
        message={message}
        startedAtMs={startedAtMs}
        // Only dismissable once it has stopped running, so a click-away can't
        // hide an in-flight sync.
        onOpenChange={(next) => {
          if (!next && running) return;
          setOpen(next);
        }}
      />
    </>
  );
}
