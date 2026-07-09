import { mkdtempSync, mkdirSync, readFileSync, writeFileSync, utimesSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";

import { beforeEach, describe, expect, it, vi } from "vitest";

/**
 * Locks the mtime-keyed artifact cache: unchanged files must be served from
 * the parsed+validated memo (same object identity), and a rewritten file must
 * re-parse. Uses a temp PIPELINE_ROOT with the committed fixture as data.
 */

const FIXTURE = path.join(
  __dirname,
  "..",
  "..",
  "types",
  "__fixtures__",
  "collection_summary.json",
);

function makePipelineRoot(): string {
  const root = mkdtempSync(path.join(tmpdir(), "tcgp-cache-test-"));
  mkdirSync(path.join(root, "data", "current"), { recursive: true });
  writeFileSync(
    path.join(root, "data", "current", "collection_summary.json"),
    readFileSync(FIXTURE),
  );
  return root;
}

beforeEach(() => {
  vi.resetModules();
  vi.unstubAllEnvs();
});

describe("artifact cache", () => {
  it("returns the memoized object while the file is unchanged", async () => {
    vi.stubEnv("PIPELINE_ROOT", makePipelineRoot());
    const { localJsonSource } = await import("@/lib/data/local-json");
    const first = await localJsonSource.getCollectionSummary();
    const second = await localJsonSource.getCollectionSummary();
    expect(second).toBe(first);
  });

  it("re-parses when the file's mtime changes", async () => {
    const root = makePipelineRoot();
    vi.stubEnv("PIPELINE_ROOT", root);
    const { localJsonSource } = await import("@/lib/data/local-json");
    const first = await localJsonSource.getCollectionSummary();

    const file = path.join(root, "data", "current", "collection_summary.json");
    const edited = { ...JSON.parse(readFileSync(file, "utf-8")), total_quantity: 9999 };
    writeFileSync(file, JSON.stringify(edited));
    // Force an mtime step in case the rewrite lands within timestamp granularity.
    const future = new Date(Date.now() + 5000);
    utimesSync(file, future, future);

    const second = await localJsonSource.getCollectionSummary();
    expect(second).not.toBe(first);
    expect(second.total_quantity).toBe(9999);
  });

  it("readOptional returns null for missing files but throws on invalid ones", async () => {
    const root = makePipelineRoot();
    vi.stubEnv("PIPELINE_ROOT", root);
    const { localJsonSource } = await import("@/lib/data/local-json");

    // No sync artifacts exist in the temp root → all-null status, no throw.
    const status = await localJsonSource.getSyncStatus();
    expect(status.stats).toBeNull();
    expect(status.history).toEqual([]);

    // An invalid present file must still fail loudly, not be treated as absent.
    const syncDir = path.join(root, "data", "sync");
    mkdirSync(syncDir, { recursive: true });
    writeFileSync(path.join(syncDir, "player_stats.json"), JSON.stringify({ bogus: true }));
    await expect(localJsonSource.getSyncStatus()).rejects.toThrow(/schema validation/);
  });
});
