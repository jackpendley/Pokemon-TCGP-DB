/**
 * Timing for the post-sync reveal.
 *
 * Lives here because three components have to agree on it: RevealGrid staggers
 * the tiles, SyncReveal starts the set-progress bars once the tiles are done,
 * and the auto-scroll follows the same schedule. These constants were previously
 * duplicated across two of those files, which made the schedules drift.
 */

/** Pause between phases (new cards → extra copies → set progress). */
export const PHASE_GAP_MS = 350;

/** Delay per tile for a small sync. */
const BASE_STAGGER_MS = 90;

/** Floor, so a very large sync still reads as a sequence rather than a flash. */
const MIN_STAGGER_MS = 22;

/**
 * Budget for revealing all tiles. At the base stagger a 60-card sync spent ~5.4s
 * before the progress bars even started moving; compressing the per-tile delay
 * past this point keeps a big sync watchable.
 */
const REVEAL_BUDGET_MS = 4000;

/** Per-tile stagger, compressed as the card count grows. */
export function staggerMs(totalCards: number): number {
  if (totalCards <= 1) return BASE_STAGGER_MS;
  return Math.max(
    MIN_STAGGER_MS,
    Math.min(BASE_STAGGER_MS, REVEAL_BUDGET_MS / totalCards),
  );
}

/** When the "extra copies" phase begins, given how many cards are new. */
export function ownedStartMs(totalCards: number, newCount: number): number {
  return newCount * staggerMs(totalCards) + PHASE_GAP_MS;
}

/** When the set-progress bars begin filling — after every tile has revealed. */
export function barsStartMs(totalCards: number): number {
  return totalCards * staggerMs(totalCards) + 2 * PHASE_GAP_MS;
}

/** How long the set-progress bars take to fill (matches their CSS transition). */
export const BARS_FILL_MS = 1000;
