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

const idle: SyncRunState = { publishedAt: BASELINE, lastRun: null };

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
