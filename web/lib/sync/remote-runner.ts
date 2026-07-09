import { randomUUID } from "node:crypto";

import { env } from "@/lib/env";
import type { SyncJob, SyncJobStatus } from "@/types";
import type { SyncRunner } from "@/lib/sync/runner";

/**
 * SyncRunner for hosted deployments (Phase 5): instead of spawning the local
 * Python pipeline, fire a GitHub `repository_dispatch` that runs
 * .github/workflows/sync.yml (rebuild + publish to Supabase). Dispatch is
 * fire-and-forget — the job reports "done" once GitHub accepts it (HTTP 204);
 * the refreshed data appears in Supabase when the Action finishes.
 */

/** repository_dispatch event type; must match sync.yml's `types`. */
const DISPATCH_EVENT = "sync";

export function remoteSyncConfigured(): boolean {
  return Boolean(env.GITHUB_SYNC_TOKEN && env.GITHUB_SYNC_REPO);
}

export function createRemoteSyncRunner(
  config: { repo: string; token: string },
  fetchImpl: typeof fetch = fetch,
): SyncRunner {
  const jobs = new Map<string, SyncJob>();

  function finish(job: SyncJob, status: SyncJobStatus, message: string | null) {
    job.status = status;
    job.finishedAt = new Date().toISOString();
    job.message = message;
  }

  return {
    enqueue() {
      const job: SyncJob = {
        id: randomUUID(),
        status: "running",
        startedAt: new Date().toISOString(),
        finishedAt: null,
        message: null,
      };
      jobs.set(job.id, job);

      fetchImpl(`https://api.github.com/repos/${config.repo}/dispatches`, {
        method: "POST",
        headers: {
          Accept: "application/vnd.github+json",
          Authorization: `Bearer ${config.token}`,
          "X-GitHub-Api-Version": "2022-11-28",
        },
        body: JSON.stringify({ event_type: DISPATCH_EVENT }),
      })
        .then((res) => {
          if (res.status === 204) {
            finish(
              job,
              "done",
              "Sync dispatched to GitHub Actions — data refreshes in a few minutes.",
            );
          } else {
            finish(job, "error", `GitHub dispatch failed: HTTP ${res.status}`);
          }
        })
        .catch((err: unknown) => {
          finish(job, "error", err instanceof Error ? err.message : String(err));
        });

      return job;
    },
    get(id) {
      return jobs.get(id) ?? null;
    },
  };
}

let defaultRunner: SyncRunner | null = null;

/** Runner from validated env; call only when remoteSyncConfigured(). */
export function remoteSyncRunner(): SyncRunner {
  if (!env.GITHUB_SYNC_TOKEN || !env.GITHUB_SYNC_REPO) {
    throw new Error("GITHUB_SYNC_TOKEN and GITHUB_SYNC_REPO are required.");
  }
  defaultRunner ??= createRemoteSyncRunner({
    repo: env.GITHUB_SYNC_REPO,
    token: env.GITHUB_SYNC_TOKEN,
  });
  return defaultRunner;
}
