import "server-only";

import { cacheLife, cacheTag } from "next/cache";

import { dataSource } from "@/lib/data";
import {
  fetchRecommendationHistory,
  type RecommendationHistoryEntry,
} from "@/lib/data/supabase";
import { env } from "@/lib/env";
import type {
  CatalogCard,
  CollectionSummary,
  PackEv,
  Recommendations,
  SyncStatus,
} from "@/types";

/**
 * Cached (`use cache`) wrappers over the DataSource reads. All app data changes
 * only on a sync/publish, so each is cached with `cacheLife('max')` and the one
 * DATA_TAG — a publish invalidates the whole set via revalidateTag(DATA_TAG)
 * (app/api/revalidate). This turns the per-request Supabase round-trips (the
 * measured TTFB cost) into cache hits. Page content is rendered inside
 * <Suspense> as a dynamic hole (dashboard reads cookies; the others call
 * `connection()`), so the local-json CI build never prerenders these — it would
 * fail on the gitignored artifacts.
 */
export const DATA_TAG = "app-data";

export async function getCachedCatalog(): Promise<CatalogCard[]> {
  "use cache";
  cacheTag(DATA_TAG);
  cacheLife("max");
  return dataSource.getCatalog();
}

export async function getCachedPackEv(): Promise<PackEv> {
  "use cache";
  cacheTag(DATA_TAG);
  cacheLife("max");
  return dataSource.getPackEv();
}

export async function getCachedRecommendations(): Promise<Recommendations> {
  "use cache";
  cacheTag(DATA_TAG);
  cacheLife("max");
  return dataSource.getRecommendations();
}

export async function getCachedCollectionSummary(): Promise<CollectionSummary> {
  "use cache";
  cacheTag(DATA_TAG);
  cacheLife("max");
  return dataSource.getCollectionSummary();
}

export async function getCachedSyncStatus(): Promise<SyncStatus> {
  "use cache";
  cacheTag(DATA_TAG);
  cacheLife("max");
  return dataSource.getSyncStatus();
}

export async function getCachedRecommendationHistory(): Promise<
  RecommendationHistoryEntry[]
> {
  "use cache";
  cacheTag(DATA_TAG);
  cacheLife("max");
  return env.DATA_SOURCE === "supabase" ? fetchRecommendationHistory() : [];
}
