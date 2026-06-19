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
    setRunning(true);
    toast.info("Sync started…");

    const { id } = res.job;
    const poll = setInterval(async () => {
      const job = await getSyncJob(id);
      if (!job || !TERMINAL.includes(job.status)) return;
      clearInterval(poll);
      setRunning(false);
      if (job.status === "done") {
        toast.success("Sync complete");
        router.refresh();
      } else if (job.status === "needs_reauth") {
        toast.error("Re-authentication needed to sync");
      } else {
        toast.error(job.message ?? "Sync failed");
      }
    }, 1500);
  }

  return (
    <Button onClick={onClick} disabled={!enabled || running}>
      <RefreshCw className={running ? "animate-spin" : ""} />
      {running ? "Syncing…" : "Sync now"}
    </Button>
  );
}
