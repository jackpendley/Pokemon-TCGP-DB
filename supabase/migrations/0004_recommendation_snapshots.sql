-- Phase 7 — recommendation history (docs/hosting-roadmap.md §7).
--
-- Append-only log of the owner's recommendation + pack-EV state, one row per
-- real sync (scripts/publish_to_supabase.py inserts it; pure republishes are
-- skipped). Feeds the /history drift view. captured_at defaults to the publish
-- time; rows are never updated or deleted, so EV/recommendation drift over
-- time is recoverable.

create table recommendation_snapshots (
  id bigint generated always as identity primary key,
  user_id uuid not null references auth.users (id) on delete cascade,
  captured_at timestamptz not null default now(),
  payload jsonb not null
);

-- Newest-first reads per owner (the drift view walks the series in reverse).
create index recommendation_snapshots_user_captured_idx
  on recommendation_snapshots (user_id, captured_at desc);

-- Same RLS posture as the other per-user tables (0001/0002): owner-only via
-- auth.uid(); the service-role publisher bypasses RLS. No anon policy — Phase 6
-- dropped those. The /history view reads server-side with the service role.
alter table recommendation_snapshots enable row level security;
create policy "owner reads own rows" on recommendation_snapshots
  for select to authenticated using (user_id = auth.uid());
