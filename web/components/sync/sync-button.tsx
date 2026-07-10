"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { RefreshCw } from "lucide-react";
import { toast } from "sonner";

import { enqueueSync, getSyncJob } from "@/app/sync/actions";
import { Button } from "@/components/ui/button";
import type { SyncJobStatus } from "@/types";

const TERMINAL: SyncJobStatus[] = ["done", "error", "needs_reauth"];

export function SyncButton({ enabled }: { enabled: boolean }) {
  const router = useRouter();
  const [running, setRunning] = useState(false);

  async function onClick() {
    const res = await enqueueSync();
    if (!res.ok) {
      toast.error(res.reason);
      return;
    }
    // The remote runner can fail at enqueue time (dispatch rejected) — the
    // job arrives already terminal, so don't start polling.
    if (TERMINAL.includes(res.job.status)) {
      toast.error(res.job.message ?? "Sync failed");
      return;
    }
    setRunning(true);
    toast.info("Sync started…");

    const { id } = res.job;
    const poll = setInterval(async () => {
      const job = await getSyncJob(id);
      if (!job || !TERMINAL.includes(job.status)) return;
      clearInterval(poll);
      setRunning(false);
      // Always refresh on a terminal outcome: even a partial/errored run may have
      // written new collection + delta data before stopping, and the page is the
      // source of truth for what actually landed.
      router.refresh();
      if (job.status === "done") {
        toast.success("Sync complete");
      } else if (job.status === "needs_reauth") {
        toast.error(
          "Pokémon Zone auth expired — run scripts/sync_collection.py --curl-import and update the PZ_AUTH_JSON secret.",
        );
      } else {
        toast.error(job.message ?? "Sync failed");
      }
    }, 4000);
  }

  return (
    <Button onClick={onClick} disabled={!enabled || running}>
      <RefreshCw className={running ? "animate-spin" : ""} />
      {running ? "Syncing…" : "Sync now"}
    </Button>
  );
}
