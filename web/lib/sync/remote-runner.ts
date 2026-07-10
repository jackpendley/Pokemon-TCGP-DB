import { env } from "@/lib/env";
import { fetchSyncRunState } from "@/lib/data/supabase";
import type { SyncJob, SyncRunState } from "@/types";
import type { SyncRunner } from "@/lib/sync/runner";

/**
 * SyncRunner for hosted deployments: fires a GitHub `repository_dispatch`
 * that runs .github/workflows/sync.yml (live Pokémon Zone sync + publish),
 * then reports completion by polling Supabase — the job goes terminal only
 * once the workflow's publish lands, not when GitHub accepts the dispatch.
 *
 * Stateless by design: the job id encodes the pre-dispatch
 * sync_status.published_at baseline and the start time, so get() works on
 * any serverless instance with no in-memory job store.
 */

/** repository_dispatch event type; must match sync.yml's `types`. */
const DISPATCH_EVENT = "sync";

/** Job id shape: remote|<baseline published_at ISO>|<startedAt ISO>. */
const ID_PREFIX = "remote";
const ID_SEP = "|";

/** A live sync run takes ~2–4 min; past this, tell the user to go look. */
const TIMEOUT_MS = 6 * 60 * 1000;

const TIMEOUT_MESSAGE =
  "Sync is taking longer than expected — check the repo's Actions tab. " +
  "The self-hosted runner may be offline, or Pokémon Zone auth may have expired.";

export function remoteSyncConfigured(): boolean {
  return Boolean(env.GITHUB_SYNC_TOKEN && env.GITHUB_SYNC_REPO);
}

export function createRemoteSyncRunner(
  config: { repo: string; token: string },
  fetchImpl: typeof fetch = fetch,
  fetchState: () => Promise<SyncRunState> = fetchSyncRunState,
): SyncRunner {
  function errorJob(startedAt: string, message: string): SyncJob {
    return {
      id: `${ID_PREFIX}${ID_SEP}${ID_SEP}${startedAt}`,
      status: "error",
      startedAt,
      finishedAt: new Date().toISOString(),
      message,
    };
  }

  return {
    async enqueue() {
      const startedAt = new Date().toISOString();

      let baseline: string;
      try {
        // Fall back to the start time so a pre-existing publish can never be
        // mistaken for this run's completion.
        baseline = (await fetchState()).publishedAt ?? startedAt;
      } catch (err: unknown) {
        return errorJob(
          startedAt,
          `Could not read sync state: ${err instanceof Error ? err.message : String(err)}`,
        );
      }

      let res: Response;
      try {
        res = await fetchImpl(
          `https://api.github.com/repos/${config.repo}/dispatches`,
          {
            method: "POST",
            headers: {
              Accept: "application/vnd.github+json",
              Authorization: `Bearer ${config.token}`,
              "X-GitHub-Api-Version": "2022-11-28",
            },
            body: JSON.stringify({ event_type: DISPATCH_EVENT }),
          },
        );
      } catch (err: unknown) {
        return errorJob(
          startedAt,
          err instanceof Error ? err.message : String(err),
        );
      }
      if (res.status !== 204) {
        return errorJob(startedAt, `GitHub dispatch failed: HTTP ${res.status}`);
      }

      return {
        id: [ID_PREFIX, baseline, startedAt].join(ID_SEP),
        status: "running",
        startedAt,
        finishedAt: null,
        message: null,
      };
    },

    async get(id) {
      const [prefix, baseline, startedAt] = id.split(ID_SEP);
      if (prefix !== ID_PREFIX || !baseline || !startedAt) return null;

      const state = await fetchState();
      const published = state.publishedAt ? Date.parse(state.publishedAt) : NaN;

      if (Number.isFinite(published) && published > Date.parse(baseline)) {
        const reauth = state.lastRun?.outcome === "auth_expired";
        return {
          id,
          status: reauth ? "needs_reauth" : "done",
          startedAt,
          finishedAt: state.publishedAt,
          message: reauth ? "Pokémon Zone auth expired." : "Sync complete.",
        };
      }

      if (Date.now() - Date.parse(startedAt) > TIMEOUT_MS) {
        return {
          id,
          status: "error",
          startedAt,
          finishedAt: new Date().toISOString(),
          message: TIMEOUT_MESSAGE,
        };
      }

      return { id, status: "running", startedAt, finishedAt: null, message: null };
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
