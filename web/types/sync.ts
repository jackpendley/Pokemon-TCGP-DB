import { z } from "zod";

/** data/sync/player_stats.json — currency balances + last fetch time. */
export const playerStatsSchema = z
  .object({
    fetched_at: z.string(),
    pack_hourglasses: z.number(),
    wonder_hourglasses: z.number(),
    shop_tickets: z.number(),
  })
  .loose();
export type PlayerStats = z.infer<typeof playerStatsSchema>;

/** data/sync/sync_review_queue.json — items needing manual attention. */
export const reviewQueueSchema = z
  .object({
    generated_at: z.string(),
    resolved: z.boolean(),
    new_cards: z.array(z.unknown()),
    ambiguous_matches: z.array(z.unknown()),
    missing_from_pz: z.array(z.unknown()),
  })
  .loose();
export type ReviewQueue = z.infer<typeof reviewQueueSchema>;

/** data/sync/last_sync_delta.json — cards added by the most recent sync. */
export const syncDeltaEntrySchema = z.object({
  name: z.string().nullable(),
  set_code: z.string().nullable(),
  card_number: z.number().nullable(),
  previous_count: z.number(),
  new_count: z.number(),
  added: z.number(),
  is_new: z.boolean(),
});
export type SyncDeltaEntry = z.infer<typeof syncDeltaEntrySchema>;

export const syncDeltaSchema = z.object({
  generated_at: z.string(),
  added_count: z.number(),
  added: z.array(syncDeltaEntrySchema),
});
export type SyncDelta = z.infer<typeof syncDeltaSchema>;

/** data/sync/sync_history.json — running log of past sync additions (newest last). */
export const syncHistoryEntrySchema = z.object({
  synced_at: z.string(),
  added_count: z.number(),
  added: z.array(syncDeltaEntrySchema),
});
export type SyncHistoryEntry = z.infer<typeof syncHistoryEntrySchema>;

export const syncHistoryFileSchema = z.object({
  entries: z.array(syncHistoryEntrySchema),
});

export interface SyncStatus {
  stats: PlayerStats | null;
  reviewQueue: ReviewQueue | null;
  delta: SyncDelta | null;
  history: SyncHistoryEntry[];
}

/**
 * Sync job lifecycle. Designed for the cloud end-state (Phase 7) so the UI
 * contract is identical whether the executor is the local pipeline or a remote
 * container worker. `needs_reauth` is surfaced when credentials lapse.
 */
export type SyncJobStatus =
  | "queued"
  | "running"
  | "done"
  | "error"
  | "needs_reauth";

export interface SyncJob {
  id: string;
  status: SyncJobStatus;
  startedAt: string;
  finishedAt: string | null;
  message: string | null;
}
