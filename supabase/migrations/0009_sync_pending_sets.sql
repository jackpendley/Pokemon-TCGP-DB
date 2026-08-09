-- Sets Pokémon Zone is serving that SET_REGISTRY does not know.
--
-- Nothing used to notice a released expansion: the pipeline syncs offline
-- (--no-fetch), so a new set's cards became unexplained "new cards" in the review
-- queue with no signal that a whole set was missing. That is why Ruler of the
-- Skies (B4) stayed invisible for a week after release.
--
-- scripts/sync_collection.py detect_unregistered_sets() writes the codes it saw,
-- publish_to_supabase stamps them here, and the dashboard renders a "new set
-- detected" banner with a one-click adopt.
--
-- Shape: [{"set_code": "B4", "card_count": 233, "copies": 240}, ...]
-- Empty array (the normal case) means every set PZ serves is registered; the
-- publisher always writes it so the banner clears itself once a set is adopted.
--
-- jsonb rather than a table: it is a per-sync snapshot read as a whole and never
-- queried by set, exactly like sync_status.last_run and .delta.
alter table public.sync_status
  add column if not exists pending_sets jsonb;

comment on column public.sync_status.pending_sets is
  'Set codes Pokémon Zone serves that SET_REGISTRY lacks, as '
  '[{set_code, card_count, copies}]. Empty array = nothing pending. Drives the '
  'dashboard new-set banner and scripts/adopt_set.py.';
