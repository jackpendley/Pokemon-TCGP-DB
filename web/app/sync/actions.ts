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

/**
 * Fire .github/workflows/adopt-set.yml for a set Pokémon Zone is serving that the
 * pipeline hasn't registered.
 *
 * Registering a set is a code change (SET_REGISTRY + SET_ALIASES, with slugs that
 * are guesses until proven), so this stays owner-triggered rather than running off
 * detection: scripts/adopt_set.py verifies every source URL first, reverts if the
 * guard tests fail, and opens a PR instead of pushing to main.
 */
export async function adoptSet(
  setCode: string,
): Promise<{ ok: true } | { ok: false; reason: string }> {
  if (!(await canTriggerSync())) {
    return { ok: false, reason: "Sign in as the owner to adopt a set." };
  }
  if (!/^[A-Za-z0-9-]{1,10}$/.test(setCode)) {
    return { ok: false, reason: "That doesn't look like a set code." };
  }
  if (!env.GITHUB_SYNC_TOKEN || !env.GITHUB_SYNC_REPO) {
    return {
      ok: false,
      reason:
        "Adopting a set needs GITHUB_SYNC_TOKEN/GITHUB_SYNC_REPO. Locally, run: python3 scripts/adopt_set.py " +
        setCode,
    };
  }

  const res = await fetch(
    `https://api.github.com/repos/${env.GITHUB_SYNC_REPO}/dispatches`,
    {
      method: "POST",
      headers: {
        Accept: "application/vnd.github+json",
        Authorization: `Bearer ${env.GITHUB_SYNC_TOKEN}`,
        "X-GitHub-Api-Version": "2022-11-28",
      },
      body: JSON.stringify({
        event_type: "adopt-set",
        client_payload: { set_code: setCode },
      }),
    },
  );
  if (res.status !== 204) {
    return { ok: false, reason: `GitHub dispatch failed: HTTP ${res.status}` };
  }
  return { ok: true };
}
