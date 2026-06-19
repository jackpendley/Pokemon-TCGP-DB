"use server";

import { env } from "@/lib/env";
import { localSyncRunner } from "@/lib/sync/runner";
import type { SyncJob } from "@/types";

export type EnqueueResult =
  | { ok: true; job: SyncJob }
  | { ok: false; reason: string };

/** True only in local dev with the explicit opt-in flag. Never in production. */
function syncEnabled(): boolean {
  return env.ENABLE_LOCAL_SYNC && process.env.NODE_ENV !== "production";
}

export async function enqueueSync(): Promise<EnqueueResult> {
  if (!syncEnabled()) {
    return {
      ok: false,
      reason:
        "Sync is disabled here. Enable it locally with ENABLE_LOCAL_SYNC=true, or run `python3 scripts/run_recommendations.py` in the repo.",
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
