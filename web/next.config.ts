import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // This repo lives under ~/Desktop, which iCloud Drive syncs. iCloud moving
  // files mid-write corrupts Turbopack's build cache ("Persisting failed: Unable
  // to write SST file"). iCloud ignores any path ending in ".nosync", so build
  // into one to keep the cache off the sync daemon's radar.
  distDir: ".next.nosync",
};

export default nextConfig;
