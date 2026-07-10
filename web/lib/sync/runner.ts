import { randomUUID } from "node:crypto";
import { spawn } from "node:child_process";

import { env } from "@/lib/env";
import type { SyncJob, SyncJobStatus } from "@/types";

/**
 * Maps a `run_recommendations.py` exit code to a job status. Pure + exported so
 * the state machine is unit-tested without spawning a process. Exit codes
 * (documented in scripts/run_recommendations.py):
 *   0 success · 2 completed with review-queue items · 3 completed but PZ auth
 *   expired, collection NOT refreshed → needs_reauth · anything else = error.
 */
export function mapExitCode(code: number | null): SyncJobStatus {
  switch (code) {
    case 0:
    case 2:
      return "done";
    case 3:
      return "needs_reauth";
    default:
      return "error";
  }
}

/**
 * Runs a collection sync + pipeline rebuild. The local implementation shells out
 * to the Python pipeline; a remote container worker can implement this same
 * interface in the cloud phase without any UI change.
 */
export interface SyncRunner {
  enqueue(): SyncJob | Promise<SyncJob>;
  get(id: string): SyncJob | null | Promise<SyncJob | null>;
}

const jobs = new Map<string, SyncJob>();

function newJob(): SyncJob {
  return {
    id: randomUUID(),
    status: "queued",
    startedAt: new Date().toISOString(),
    finishedAt: null,
    message: null,
  };
}

export const localSyncRunner: SyncRunner = {
  enqueue() {
    const job = newJob();
    jobs.set(job.id, job);

    const child = spawn(
      "python3",
      ["scripts/run_recommendations.py"],
      { cwd: env.PIPELINE_ROOT },
    );
    job.status = "running";

    let stderr = "";
    child.stderr.on("data", (d) => {
      stderr += String(d);
    });
    child.on("error", (err) => {
      finish(job, "error", err.message);
    });
    child.on("close", (code) => {
      const status = mapExitCode(code);
      finish(job, status, status === "done" ? null : stderr.slice(-500) || null);
    });

    return job;
  },
  get(id) {
    return jobs.get(id) ?? null;
  },
};

function finish(job: SyncJob, status: SyncJobStatus, message: string | null) {
  job.status = status;
  job.finishedAt = new Date().toISOString();
  job.message = message;
}
