-- Phase 6 — auth owner (docs/hosting-roadmap.md §6).
--
-- Prereq: scripts/create_owner_user.py has created the owner auth user
-- (jackpendley9@gmail.com). This migration resolves its UUID from
-- auth.users, backfills the Phase 4 placeholder
-- a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11 onto it, adds the user_id FK that
-- 0001_init.sql deferred, and drops the temporary "anon reads seeded owner"
-- policies (the 0001 TODOs). The web app reads per-user tables server-side
-- with the service role from here on; anon sees nothing on them.

do $$
declare
  owner uuid;
  ph constant uuid := 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11';
begin
  -- STRICT: fails loudly if the seed script hasn't run.
  select id into strict owner from auth.users
    where email = 'jackpendley9@gmail.com';

  -- Defensive: if a publish already ran under the real UUID, drop the stale
  -- placeholder rows instead of colliding on the PK during the UPDATE below.
  delete from collection_summaries where user_id = ph
    and exists (select 1 from collection_summaries where user_id = owner);
  delete from pack_ev where user_id = ph
    and exists (select 1 from pack_ev where user_id = owner);
  delete from recommendations where user_id = ph
    and exists (select 1 from recommendations where user_id = owner);
  delete from sync_status where user_id = ph
    and exists (select 1 from sync_status where user_id = owner);
  delete from collections c where c.user_id = ph
    and exists (select 1 from collections c2 where c2.user_id = owner
                and c2.set_code = c.set_code
                and c2.card_number = c.card_number);
  delete from sync_history h where h.user_id = ph
    and exists (select 1 from sync_history h2 where h2.user_id = owner
                and h2.synced_at = h.synced_at);

  update collections set user_id = owner where user_id = ph;
  update collection_summaries set user_id = owner where user_id = ph;
  update pack_ev set user_id = owner where user_id = ph;
  update recommendations set user_id = owner where user_id = ph;
  update sync_status set user_id = owner where user_id = ph;
  update sync_history set user_id = owner where user_id = ph;
end $$;

-- A real auth user exists now; add the FK deferred by 0001_init.sql.
alter table collections add constraint collections_user_id_fkey
  foreign key (user_id) references auth.users (id) on delete cascade;
alter table collection_summaries add constraint collection_summaries_user_id_fkey
  foreign key (user_id) references auth.users (id) on delete cascade;
alter table pack_ev add constraint pack_ev_user_id_fkey
  foreign key (user_id) references auth.users (id) on delete cascade;
alter table recommendations add constraint recommendations_user_id_fkey
  foreign key (user_id) references auth.users (id) on delete cascade;
alter table sync_status add constraint sync_status_user_id_fkey
  foreign key (user_id) references auth.users (id) on delete cascade;
alter table sync_history add constraint sync_history_user_id_fkey
  foreign key (user_id) references auth.users (id) on delete cascade;

-- Resolves the TODO(Phase 6) markers in 0001_init.sql. The "owner reads own
-- rows" policies remain for the future login UI.
drop policy "anon reads seeded owner" on collections;
drop policy "anon reads seeded owner" on collection_summaries;
drop policy "anon reads seeded owner" on pack_ev;
drop policy "anon reads seeded owner" on recommendations;
drop policy "anon reads seeded owner" on sync_status;
drop policy "anon reads seeded owner" on sync_history;
