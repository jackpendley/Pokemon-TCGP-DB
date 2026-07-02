import type {
  CatalogCard,
  CollectionSummary,
  PackEv,
  Recommendations,
  SyncStatus,
} from "@/types";

/**
 * The only abstraction the rest of the app depends on for reads. Today the sole
 * implementation is LocalJsonSource (reads the pipeline's JSON artifacts); a
 * SupabaseSource can be added later without touching UI or domain code.
 */
export interface DataSource {
  getCollectionSummary(): Promise<CollectionSummary>;
  getPackEv(): Promise<PackEv>;
  getRecommendations(): Promise<Recommendations>;
  /** Full card catalog merged with owned counts (Cards + Sets pages). */
  getCatalog(): Promise<CatalogCard[]>;
  /** Sync state (balances + review queue); fields are null when absent. */
  getSyncStatus(): Promise<SyncStatus>;
}
