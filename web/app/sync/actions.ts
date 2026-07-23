"use server";

import { isOwner } from "@/lib/auth/server";
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

/**
 * Whether the current request may trigger a sync. When an owner is configured
 * (hosted), only that signed-in user qualifies — sync is the public site's
 * write surface. In local-json dev OWNER_USER_ID is unset, so local sync is
 * unaffected.
 */
export async function canTriggerSync(): Promise<boolean> {
  if (env.OWNER_USER_ID) return isOwner();
  return true;
}

export async function enqueueSync(): Promise<EnqueueResult> {
  if (!(await canTriggerSync())) {
    return { ok: false, reason: "Sign in as the owner to sync." };
  }

  const runner = selectRunner();
  if (!runner) {
    return {
      ok: false,
      reason:
        "Sync is not configured for this deployment. Locally it runs the Python pipeline; hosted it needs GITHUB_SYNC_TOKEN/GITHUB_SYNC_REPO to trigger the sync workflow.",
    };
  }
  return { ok: true, job: await runner.enqueue() };
}

export async function getSyncJob(id: string): Promise<SyncJob | null> {
  return (await selectRunner()?.get(id)) ?? null;
}

export async function isSyncEnabled(): Promise<boolean> {
  return selectRunner() !== null;
}
