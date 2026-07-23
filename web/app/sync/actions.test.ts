import { afterEach, describe, expect, it, vi } from "vitest";

// vi.mock factories are hoisted above imports, so build the stubs with
// vi.hoisted. The gate calls isOwner() (stubbed, so no Supabase/cookies) and
// reads env at module load. No runner is configured (tokens undefined) — fine,
// since the gate returns before runner selection in the blocking case.
const { isOwner, env } = vi.hoisted(() => ({
  isOwner: vi.fn(),
  env: {
    OWNER_USER_ID: undefined as string | undefined,
    GITHUB_SYNC_TOKEN: undefined,
    GITHUB_SYNC_REPO: undefined,
    ENABLE_LOCAL_SYNC: false,
    PIPELINE_ROOT: "/tmp",
  },
}));
vi.mock("@/lib/auth/server", () => ({ isOwner: () => isOwner() }));
vi.mock("@/lib/env", () => ({ env }));

import { canTriggerSync, enqueueSync } from "@/app/sync/actions";

const OWNER = "49aa8ac8-41ff-4ec1-9a11-2a7e4c171464";

afterEach(() => {
  vi.clearAllMocks();
  env.OWNER_USER_ID = undefined;
});

describe("sync owner gate", () => {
  it("blocks an anonymous request when an owner is configured", async () => {
    env.OWNER_USER_ID = OWNER;
    isOwner.mockResolvedValue(false);
    const res = await enqueueSync();
    expect(res).toEqual({
      ok: false,
      reason: "Sign in as the owner to sync.",
    });
  });

  it("canTriggerSync is true for the signed-in owner", async () => {
    env.OWNER_USER_ID = OWNER;
    isOwner.mockResolvedValue(true);
    expect(await canTriggerSync()).toBe(true);
  });

  it("canTriggerSync is false for a non-owner", async () => {
    env.OWNER_USER_ID = OWNER;
    isOwner.mockResolvedValue(false);
    expect(await canTriggerSync()).toBe(false);
  });

  it("canTriggerSync is true (no auth) in local-json mode", async () => {
    env.OWNER_USER_ID = undefined;
    expect(await canTriggerSync()).toBe(true);
    expect(isOwner).not.toHaveBeenCalled();
  });
});
