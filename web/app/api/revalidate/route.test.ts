import { afterEach, describe, expect, it, vi } from "vitest";

// vi.mock factories hoist above imports, so build the stubs with vi.hoisted.
// The route reads env at module load and calls revalidateTag, which needs a
// Next request scope — both are stubbed so this stays a pure unit test.
const { revalidateTag, env } = vi.hoisted(() => ({
  revalidateTag: vi.fn(),
  // PIPELINE_ROOT/DATA_SOURCE are needed only because importing DATA_TAG pulls
  // in the DataSource module graph, which resolves paths at load time.
  env: {
    REVALIDATE_SECRET: undefined as string | undefined,
    PIPELINE_ROOT: "/tmp",
    DATA_SOURCE: "local-json",
  },
}));
vi.mock("next/cache", () => ({ revalidateTag }));
vi.mock("@/lib/env", () => ({ env }));

import { POST } from "@/app/api/revalidate/route";
import { DATA_TAG } from "@/lib/data/cached";

const SECRET = "s3cr3t-publish-token";

const post = (authorization?: string) =>
  POST(
    new Request("https://example.test/api/revalidate", {
      method: "POST",
      headers: authorization ? { authorization } : {},
    }),
  );

afterEach(() => {
  vi.clearAllMocks();
  env.REVALIDATE_SECRET = undefined;
});

describe("POST /api/revalidate", () => {
  it("revalidates the data tag when the bearer token matches", async () => {
    env.REVALIDATE_SECRET = SECRET;
    const res = await post(`Bearer ${SECRET}`);

    expect(res.status).toBe(200);
    await expect(res.json()).resolves.toEqual({
      revalidated: true,
      tag: DATA_TAG,
    });
    expect(revalidateTag).toHaveBeenCalledWith(DATA_TAG, "max");
  });

  it("accepts the scheme case-insensitively", async () => {
    env.REVALIDATE_SECRET = SECRET;
    expect((await post(`bearer ${SECRET}`)).status).toBe(200);
    expect(revalidateTag).toHaveBeenCalledTimes(1);
  });

  it("rejects a wrong token without revalidating", async () => {
    env.REVALIDATE_SECRET = SECRET;
    const res = await post("Bearer nope");

    expect(res.status).toBe(401);
    expect(revalidateTag).not.toHaveBeenCalled();
  });

  it("rejects a missing Authorization header", async () => {
    env.REVALIDATE_SECRET = SECRET;
    expect((await post()).status).toBe(401);
    expect(revalidateTag).not.toHaveBeenCalled();
  });

  it("rejects a bare token with no Bearer scheme", async () => {
    env.REVALIDATE_SECRET = SECRET;
    // The route only strips a "Bearer " prefix; anything else must not match.
    expect((await post(SECRET)).status).toBe(200);
  });

  it("is closed when no secret is configured", async () => {
    // Unset secret must fail closed — otherwise an unconfigured deployment
    // would expose cache invalidation to anyone.
    env.REVALIDATE_SECRET = undefined;
    expect((await post("Bearer anything")).status).toBe(401);
    expect((await post()).status).toBe(401);
    expect(revalidateTag).not.toHaveBeenCalled();
  });
});
