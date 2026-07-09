"use server";

import { env } from "@/lib/env";
import { localSyncRunner, type SyncRunner } from "@/lib/sync/runner";
import {
  remoteSyncConfigured,
  remoteSyncRunner,
} from "@/lib/sync/remote-runner";
import type { SyncJob } from "@/types";

export type EnqueueResult =
  | { ok: true; job: SyncJob }
  | { ok: false; reason: string };

/**
 * Remote (GitHub Actions) when configured — works in production; otherwise
 * the local spawn runner in dev (unless ENABLE_LOCAL_SYNC=false). Production
 * without a remote config degrades to read-only "last synced".
 */
function selectRunner(): SyncRunner | null {
  if (remoteSyncConfigured()) return remoteSyncRunner();
  if (process.env.NODE_ENV !== "production" && env.ENABLE_LOCAL_SYNC) {
    return localSyncRunner;
  }
  return null;
}

export async function enqueueSync(): Promise<EnqueueResult> {
  const runner = selectRunner();
  if (!runner) {
    return {
      ok: false,
      reason:
        "Sync is not configured for this deployment. Locally it runs the Python pipeline; hosted it needs GITHUB_SYNC_TOKEN/GITHUB_SYNC_REPO to trigger the sync workflow.",
    };
  }
  return { ok: true, job: runner.enqueue() };
}

export async function getSyncJob(id: string): Promise<SyncJob | null> {
  return selectRunner()?.get(id) ?? null;
}

export async function isSyncEnabled(): Promise<boolean> {
  return selectRunner() !== null;
}
