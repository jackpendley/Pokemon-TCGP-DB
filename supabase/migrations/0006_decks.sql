-- Deck builder (Phase 7).
--
-- Unlike every other table here, decks are authored in the app rather than
-- published by the pipeline, so this is the first table the web layer writes to
-- at request time. Cards are stored as a JSONB list of {set_code, card_number,
-- count} coordinates rather than FKs to public.cards: a deck should survive a
-- card-reference rebuild, and the catalog join happens in the app anyway.

create table if not exists public.decks (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  name text not null,
  -- [{ "set_code": "A1", "card_number": 1, "count": 2 }, ...]
  cards jsonb not null default '[]'::jsonb,
  -- Energy Zone selection; 1-3 entries enforced by the app's rules engine
  -- (web/lib/domain/deck.ts), which owns every deck-legality rule.
  energy_types text[] not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists decks_user_id_updated_at_idx
  on public.decks (user_id, updated_at desc);

alter table public.decks enable row level security;

-- Public read, owner-only write — the same shape as the rest of the app. Writes
-- go through server actions using the cookie-bound (anon-key) client, so these
-- policies are what actually enforce ownership; the service-role read path
-- bypasses RLS as it does elsewhere.
drop policy if exists "decks are publicly readable" on public.decks;
create policy "decks are publicly readable"
  on public.decks for select
  using (true);

drop policy if exists "owner inserts own decks" on public.decks;
create policy "owner inserts own decks"
  on public.decks for insert
  with check (auth.uid() = user_id);

drop policy if exists "owner updates own decks" on public.decks;
create policy "owner updates own decks"
  on public.decks for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

drop policy if exists "owner deletes own decks" on public.decks;
create policy "owner deletes own decks"
  on public.decks for delete
  using (auth.uid() = user_id);

comment on table public.decks is
  'User-authored decks. Written by the app at request time, unlike the pipeline-published tables.';
