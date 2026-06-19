"use server";

import { env } from "@/lib/env";
import { localSyncRunner } from "@/lib/sync/runner";
import type { SyncJob } from "@/types";

export type EnqueueResult =
  | { ok: true; job: SyncJob }
  | { ok: false; reason: string };

/** Enabled in local dev (unless ENABLE_LOCAL_SYNC=false); never in production. */
function syncEnabled(): boolean {
  return process.env.NODE_ENV !== "production" && env.ENABLE_LOCAL_SYNC;
}

export async function enqueueSync(): Promise<EnqueueResult> {
  if (!syncEnabled()) {
    return {
      ok: false,
      reason:
        "Sync runs the local Python pipeline and is available only in local dev. In production this is handled by the cloud sync worker.",
    };
  }
  return { ok: true, job: localSyncRunner.enqueue() };
}

export async function getSyncJob(id: string): Promise<SyncJob | null> {
  return localSyncRunner.get(id);
}

export async function isSyncEnabled(): Promise<boolean> {
  return syncEnabled();
}
