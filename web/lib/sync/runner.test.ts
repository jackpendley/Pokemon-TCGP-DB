import { describe, expect, it } from "vitest";

import { mapExitCode } from "@/lib/sync/runner";

describe("mapExitCode", () => {
  it("treats 0 and 2 as done", () => {
    expect(mapExitCode(0)).toBe("done");
    expect(mapExitCode(2)).toBe("done");
  });

  it("treats 3 as needs_reauth", () => {
    expect(mapExitCode(3)).toBe("needs_reauth");
  });

  it("treats other / null codes as error", () => {
    expect(mapExitCode(1)).toBe("error");
    expect(mapExitCode(null)).toBe("error");
  });
});
