import { describe, expect, it, vi } from "vitest";

import { createRemoteSyncRunner } from "@/lib/sync/remote-runner";

const CONFIG = { repo: "jackpendley/Pokemon-TCGP-DB", token: "gh_test_token" };

function fetchReturning(status: number) {
  return vi.fn(async () => ({ status }) as Response);
}

async function settled() {
  // Let the enqueue's fetch promise chain resolve.
  await new Promise((r) => setTimeout(r, 0));
}

describe("remoteSyncRunner", () => {
  it("fires repository_dispatch with the sync event", async () => {
    const fetchMock = fetchReturning(204);
    const runner = createRemoteSyncRunner(CONFIG, fetchMock);
    runner.enqueue();
    await settled();

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

  it("marks the job done when GitHub accepts the dispatch (204)", async () => {
    const runner = createRemoteSyncRunner(CONFIG, fetchReturning(204));
    const job = runner.enqueue();
    expect(job.status).toBe("running");
    await settled();

    const finished = runner.get(job.id);
    expect(finished?.status).toBe("done");
    expect(finished?.finishedAt).not.toBeNull();
    expect(finished?.message).toMatch(/GitHub Actions/);
  });

  it("marks the job errored on a non-204 response", async () => {
    const runner = createRemoteSyncRunner(CONFIG, fetchReturning(401));
    const job = runner.enqueue();
    await settled();

    const finished = runner.get(job.id);
    expect(finished?.status).toBe("error");
    expect(finished?.message).toMatch(/HTTP 401/);
  });

  it("marks the job errored when the request itself fails", async () => {
    const failingFetch = vi.fn(async () => {
      throw new Error("network down");
    });
    const runner = createRemoteSyncRunner(CONFIG, failingFetch);
    const job = runner.enqueue();
    await settled();

    expect(runner.get(job.id)?.status).toBe("error");
    expect(runner.get(job.id)?.message).toBe("network down");
  });

  it("returns null for unknown job ids", () => {
    const runner = createRemoteSyncRunner(CONFIG, fetchReturning(204));
    expect(runner.get("nope")).toBeNull();
  });
});
