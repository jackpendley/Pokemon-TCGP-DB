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

/**
 * Grace period before asking GitHub about the run — it takes a few seconds to
 * appear after the dispatch is accepted, and "not found" would otherwise be
 * indistinguishable from "never started".
 */
const RUN_LOOKUP_AFTER_MS = 20 * 1000;

/** Tolerance for clock skew when matching a run to this job's dispatch. */
const RUN_MATCH_SKEW_MS = 30 * 1000;

/**
 * Pokémon Zone refreshes its own snapshot of the collection from the game before
 * we read it. When that does not finish, the sync genuinely succeeds but can only
 * republish what PZ already had — so it must say so, or "sync worked, nothing
 * changed" reads as a bug in this app rather than a stall upstream.
 */
const STALE_SOURCE_MESSAGE =
  "Sync finished, but Pokémon Zone hadn't refreshed your collection from the game, " +
  "so this republished its previous snapshot. Recent pulls may be missing — open " +
  "the game, then try again in a few minutes.";

const TIMEOUT_MESSAGE =
  "Sync is taking longer than expected — check the repo's Actions tab. " +
  "The self-hosted runner may be offline, or Pokémon Zone auth may have expired.";

const GH_HEADERS = (token: string) => ({
  Accept: "application/vnd.github+json",
  Authorization: `Bearer ${token}`,
  "X-GitHub-Api-Version": "2022-11-28",
});

type RunInfo = {
  status: string;
  conclusion: string | null;
  url: string;
};

/**
 * The sync workflow run this job dispatched, or null if GitHub can't tell us.
 *
 * Every failure here is non-fatal and returns null: this is diagnostics layered
 * on top of the published_at signal, and a token without `actions:read` must
 * still get a working sync.
 */
async function fetchRun(
  config: { repo: string; token: string },
  fetchImpl: typeof fetch,
  startedAt: string,
): Promise<RunInfo | null> {
  try {
    const res = await fetchImpl(
      `https://api.github.com/repos/${config.repo}/actions/workflows/sync.yml/runs` +
        `?event=repository_dispatch&per_page=10`,
      { headers: GH_HEADERS(config.token) },
    );
    if (!res.ok) return null;
    const body = (await res.json()) as {
      workflow_runs?: {
        created_at?: string;
        status?: string;
        conclusion?: string | null;
        html_url?: string;
      }[];
    };
    const floor = Date.parse(startedAt) - RUN_MATCH_SKEW_MS;
    const match = (body.workflow_runs ?? [])
      .filter((r) => r.created_at && Date.parse(r.created_at) >= floor)
      .sort((a, b) => Date.parse(b.created_at!) - Date.parse(a.created_at!))[0];
    if (!match) return null;
    return {
      status: match.status ?? "unknown",
      conclusion: match.conclusion ?? null,
      url: match.html_url ?? "",
    };
  } catch {
    return null;
  }
}

/**
 * True when the repo has self-hosted runners and none can pick up work.
 * Returns null when GitHub can't tell us — callers must treat that as "proceed".
 */
async function selfHostedOffline(
  config: { repo: string; token: string },
  fetchImpl: typeof fetch,
): Promise<boolean | null> {
  try {
    const res = await fetchImpl(
      `https://api.github.com/repos/${config.repo}/actions/runners`,
      { headers: GH_HEADERS(config.token) },
    );
    if (!res.ok) return null;
    const body = (await res.json()) as {
      runners?: { status?: string; labels?: { name?: string }[] }[];
    };
    const selfHosted = (body.runners ?? []).filter((r) =>
      (r.labels ?? []).some((l) => l.name === "self-hosted"),
    );
    if (selfHosted.length === 0) return null;
    return selfHosted.every((r) => r.status !== "online");
  } catch {
    return null;
  }
}

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

      // A dispatch to an offline runner is accepted (204) and then queues
      // forever, which used to surface only as a blank 6-minute timeout.
      if ((await selfHostedOffline(config, fetchImpl)) === true) {
        return errorJob(
          startedAt,
          "The self-hosted runner is offline, so a sync would queue indefinitely. " +
            "Start it on the runner machine, then try again.",
        );
      }

      let res: Response;
      try {
        res = await fetchImpl(
          `https://api.github.com/repos/${config.repo}/dispatches`,
          {
            method: "POST",
            headers: GH_HEADERS(config.token),
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
          message: reauth
            ? "Pokémon Zone auth expired."
            : state.playerSynced === false
              ? STALE_SOURCE_MESSAGE
              : "Sync complete.",
        };
      }

      const elapsed = Date.now() - Date.parse(startedAt);

      // Ask GitHub what the run is actually doing. Without this, "queued behind
      // an offline runner", "crashed before publishing", and "still working"
      // all looked the same: a silent wait ending in a generic timeout.
      const run =
        elapsed > RUN_LOOKUP_AFTER_MS
          ? await fetchRun(config, fetchImpl, startedAt)
          : null;

      if (run?.status === "completed") {
        const bad = run.conclusion !== null && run.conclusion !== "success";
        if (bad) {
          return {
            id,
            status: "error",
            startedAt,
            finishedAt: new Date().toISOString(),
            message: `Sync run ${run.conclusion}${run.url ? ` — ${run.url}` : ""}`,
          };
        }
        // Succeeded without advancing published_at. Re-read once in case the
        // publish landed between the two calls, then report it as the anomaly
        // it is rather than waiting out the timeout.
        const recheck = await fetchState().catch(() => null);
        const republished = recheck?.publishedAt
          ? Date.parse(recheck.publishedAt)
          : NaN;
        if (Number.isFinite(republished) && republished > Date.parse(baseline)) {
          return {
            id,
            status: recheck?.lastRun?.outcome === "auth_expired" ? "needs_reauth" : "done",
            startedAt,
            finishedAt: recheck!.publishedAt,
            message:
              recheck?.playerSynced === false
                ? STALE_SOURCE_MESSAGE
                : "Sync complete.",
          };
        }
        return {
          id,
          status: "error",
          startedAt,
          finishedAt: new Date().toISOString(),
          message:
            "The sync run finished but published no data" +
            (run.url ? ` — ${run.url}` : "") +
            ". The runner may have failed to report its result.",
        };
      }

      if (run?.status === "queued" || run?.status === "waiting" || run?.status === "pending") {
        return {
          id,
          status: "queued",
          startedAt,
          finishedAt: null,
          message: "Waiting for the self-hosted runner to pick up the job.",
        };
      }

      if (elapsed > TIMEOUT_MS) {
        return {
          id,
          status: "error",
          startedAt,
          finishedAt: new Date().toISOString(),
          message: run?.url ? `${TIMEOUT_MESSAGE} Run: ${run.url}` : TIMEOUT_MESSAGE,
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
