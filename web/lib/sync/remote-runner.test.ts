import { afterEach, describe, expect, it, vi } from "vitest";

import { createRemoteSyncRunner } from "@/lib/sync/remote-runner";
import type { SyncRunState } from "@/types";

const CONFIG = { repo: "jackpendley/Pokemon-TCGP-DB", token: "gh_test_token" };

const BASELINE = "2026-07-10T00:00:00.000Z";
const ADVANCED = "2026-07-10T00:03:00.000Z";

function fetchReturning(status: number) {
  return vi.fn(async () => ({ status }) as Response);
}

function stateReturning(state: SyncRunState) {
  return vi.fn(async () => state);
}

const idle: SyncRunState = {
  publishedAt: BASELINE,
  lastRun: null,
  playerSynced: true,
};

afterEach(() => {
  vi.useRealTimers();
});

describe("remoteSyncRunner", () => {
  it("fires repository_dispatch with the sync event", async () => {
    const fetchMock = fetchReturning(204);
    const runner = createRemoteSyncRunner(CONFIG, fetchMock, stateReturning(idle));
    await runner.enqueue();

    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.github.com/repos/jackpendley/Pokemon-TCGP-DB/dispatches",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          Authorization: "Bearer gh_test_token",
        }),
        body: JSON.stringify({ event_type: "sync" }),
      }),
    );
  });

  it("returns a running job encoding the published_at baseline (204)", async () => {
    const runner = createRemoteSyncRunner(
      CONFIG,
      fetchReturning(204),
      stateReturning(idle),
    );
    const job = await runner.enqueue();
    expect(job.status).toBe("running");
    expect(job.id).toContain(BASELINE);
  });

  it("errors at enqueue on a non-204 response", async () => {
    const runner = createRemoteSyncRunner(
      CONFIG,
      fetchReturning(401),
      stateReturning(idle),
    );
    const job = await runner.enqueue();
    expect(job.status).toBe("error");
    expect(job.message).toMatch(/HTTP 401/);
  });

  it("errors at enqueue when the request itself fails", async () => {
    const failingFetch = vi.fn(async () => {
      throw new Error("network down");
    });
    const runner = createRemoteSyncRunner(
      CONFIG,
      failingFetch,
      stateReturning(idle),
    );
    const job = await runner.enqueue();
    expect(job.status).toBe("error");
    expect(job.message).toBe("network down");
  });

  it("stays running while published_at has not advanced", async () => {
    const runner = createRemoteSyncRunner(
      CONFIG,
      fetchReturning(204),
      stateReturning(idle),
    );
    const job = await runner.enqueue();
    expect((await runner.get(job.id))?.status).toBe("running");
  });

  it("reports done once a publish lands after the baseline", async () => {
    const state = stateReturning(idle);
    const runner = createRemoteSyncRunner(CONFIG, fetchReturning(204), state);
    const job = await runner.enqueue();

    state.mockResolvedValue({
      publishedAt: ADVANCED,
      lastRun: { outcome: "ok" },
      playerSynced: true,
    });
    const finished = await runner.get(job.id);
    expect(finished?.status).toBe("done");
    expect(finished?.finishedAt).toBe(ADVANCED);
  });

  it("reports needs_reauth when the run's outcome is auth_expired", async () => {
    const state = stateReturning(idle);
    const runner = createRemoteSyncRunner(CONFIG, fetchReturning(204), state);
    const job = await runner.enqueue();

    state.mockResolvedValue({
      publishedAt: ADVANCED,
      lastRun: { outcome: "auth_expired" },
      playerSynced: true,
    });
    expect((await runner.get(job.id))?.status).toBe("needs_reauth");
  });

  it("times out with a helpful error after ~6 minutes without a publish", async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(BASELINE));
    const runner = createRemoteSyncRunner(
      CONFIG,
      fetchReturning(204),
      stateReturning(idle),
    );
    const job = await runner.enqueue();

    vi.setSystemTime(new Date(Date.parse(BASELINE) + 7 * 60 * 1000));
    const timedOut = await runner.get(job.id);
    expect(timedOut?.status).toBe("error");
    expect(timedOut?.message).toMatch(/Actions tab/);
  });

  it("returns null for ids it did not mint", async () => {
    const runner = createRemoteSyncRunner(
      CONFIG,
      fetchReturning(204),
      stateReturning(idle),
    );
    expect(await runner.get("nope")).toBeNull();
  });
});

/**
 * The runner used to report only "published_at advanced" vs "6 minutes passed",
 * so an offline runner, a crashed pipeline, and a healthy slow run were
 * indistinguishable — which is exactly how the 2026-08-03 sync looked.
 */
describe("remoteSyncRunner GitHub run reporting", () => {
  const RUNNERS_URL = "/actions/runners";
  const RUNS_URL = "/actions/workflows/sync.yml/runs";

  function ok(body: unknown) {
    return { ok: true, status: 200, json: async () => body } as unknown as Response;
  }

  /** Routes GitHub calls by URL so one mock can serve dispatch + both APIs. */
  function githubFetch(opts: {
    runnerStatus?: string;
    run?: { status: string; conclusion: string | null; created_at: string };
  }) {
    return vi.fn(async (url: string | URL | Request) => {
      const u = String(url);
      if (u.includes(RUNNERS_URL)) {
        return ok({
          runners: [
            {
              status: opts.runnerStatus ?? "online",
              labels: [{ name: "self-hosted" }],
            },
          ],
        });
      }
      if (u.includes(RUNS_URL)) {
        return ok({
          workflow_runs: opts.run
            ? [{ ...opts.run, html_url: "https://github.com/run/1" }]
            : [],
        });
      }
      return { status: 204 } as Response;
    });
  }

  /** Advances past RUN_LOOKUP_AFTER_MS so get() actually consults GitHub. */
  async function jobPastLookupGrace(fetchMock: typeof fetch, state = stateReturning(idle)) {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(BASELINE));
    const runner = createRemoteSyncRunner(CONFIG, fetchMock, state);
    const job = await runner.enqueue();
    vi.setSystemTime(new Date(Date.parse(BASELINE) + 60 * 1000));
    return { runner, job };
  }

  it("refuses to dispatch when the self-hosted runner is offline", async () => {
    const runner = createRemoteSyncRunner(
      CONFIG,
      githubFetch({ runnerStatus: "offline" }),
      stateReturning(idle),
    );
    const job = await runner.enqueue();

    expect(job.status).toBe("error");
    expect(job.message).toMatch(/offline/i);
  });

  it("dispatches normally when the runner is online", async () => {
    const runner = createRemoteSyncRunner(
      CONFIG,
      githubFetch({ runnerStatus: "online" }),
      stateReturning(idle),
    );
    expect((await runner.enqueue()).status).toBe("running");
  });

  it("reports queued while the run waits for a runner", async () => {
    const { runner, job } = await jobPastLookupGrace(
      githubFetch({
        run: { status: "queued", conclusion: null, created_at: BASELINE },
      }),
    );
    const polled = await runner.get(job.id);

    expect(polled?.status).toBe("queued");
    expect(polled?.message).toMatch(/waiting for the self-hosted runner/i);
  });

  it("surfaces a failed run with its conclusion and URL", async () => {
    const { runner, job } = await jobPastLookupGrace(
      githubFetch({
        run: { status: "completed", conclusion: "failure", created_at: BASELINE },
      }),
    );
    const polled = await runner.get(job.id);

    expect(polled?.status).toBe("error");
    expect(polled?.message).toMatch(/failure/);
    expect(polled?.message).toMatch(/github\.com\/run\/1/);
  });

  it("flags a run that completed successfully but published nothing", async () => {
    const { runner, job } = await jobPastLookupGrace(
      githubFetch({
        run: { status: "completed", conclusion: "success", created_at: BASELINE },
      }),
    );
    const polled = await runner.get(job.id);

    expect(polled?.status).toBe("error");
    expect(polled?.message).toMatch(/published no data/i);
  });

  it("prefers a publish that lands during the completed-run recheck", async () => {
    const state = stateReturning(idle);
    const { runner, job } = await jobPastLookupGrace(
      githubFetch({
        run: { status: "completed", conclusion: "success", created_at: BASELINE },
      }),
      state,
    );
    state.mockResolvedValue({
      publishedAt: ADVANCED,
      lastRun: { outcome: "ok" },
      playerSynced: true,
    });
    const polled = await runner.get(job.id);

    expect(polled?.status).toBe("done");
  });

  it("says so when Pokémon Zone republished a stale snapshot", async () => {
    // The sync genuinely succeeds; PZ just never refreshed from the game. Without
    // this the dialog reports plain success and the unchanged collection looks
    // like a bug here rather than a stall upstream.
    const state = stateReturning(idle);
    const runner = createRemoteSyncRunner(CONFIG, fetchReturning(204), state);
    const job = await runner.enqueue();

    state.mockResolvedValue({
      publishedAt: ADVANCED,
      lastRun: { outcome: "ok" },
      playerSynced: false,
    });
    const polled = await runner.get(job.id);

    expect(polled?.status).toBe("done");
    expect(polled?.message).toMatch(/hadn't refreshed your collection/i);
  });

  it("stays running while the run is in progress", async () => {
    const { runner, job } = await jobPastLookupGrace(
      githubFetch({
        run: { status: "in_progress", conclusion: null, created_at: BASELINE },
      }),
    );
    expect((await runner.get(job.id))?.status).toBe("running");
  });

  it("ignores runs created before this job was dispatched", async () => {
    const { runner, job } = await jobPastLookupGrace(
      githubFetch({
        run: {
          status: "completed",
          conclusion: "failure",
          created_at: "2026-07-09T00:00:00.000Z",
        },
      }),
    );
    // The stale failure must not be attributed to this dispatch.
    expect((await runner.get(job.id))?.status).toBe("running");
  });
});
