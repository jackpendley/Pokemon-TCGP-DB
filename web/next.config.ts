import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Cache Components (Next 16): pages render a prerendered static shell; data is
  // cached via `use cache` + cacheTag (lib/data/cached.ts) and streamed through
  // <Suspense>, with per-request/dynamic bits (auth, searchParams) as dynamic
  // holes. Replaces the old blanket force-dynamic. See docs/hosting-roadmap.md P5.
  cacheComponents: true,
  // This repo lives under ~/Desktop, which iCloud Drive syncs. iCloud moving
  // files mid-write corrupts Turbopack's build cache ("Persisting failed: Unable
  // to write SST file"). iCloud ignores any path ending in ".nosync", so build
  // into one to keep the cache off the sync daemon's radar.
  // On Vercel there's no iCloud, and the platform requires the default ".next".
  ...(process.env.VERCEL ? {} : { distDir: ".next.nosync" }),
};

export default nextConfig;
