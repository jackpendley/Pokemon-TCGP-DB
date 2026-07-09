-- Phase 4 — Supabase hosted read layer (docs/hosting-roadmap.md §4.1).
--
-- Owner UUID: single-tenant placeholder used until Phase 6 (auth) creates a
-- real auth.users row. It appears in three places that must stay in sync:
--   1. the anon SELECT policies below,
--   2. scripts/publish_to_supabase.py (OWNER_USER_ID default),
--   3. the Phase 6 migration that backfills the real auth user.
-- Value: a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11
--
-- No FK from user_id to auth.users yet — the owner has no auth user until
-- Phase 6; that migration adds the FK after backfilling.

-- ---------------------------------------------------------------------------
-- Global tables (no user_id): the card/pack catalog published from
-- data/reference/. Readable by everyone; written only by the publisher
-- (service role, which bypasses RLS).
-- ---------------------------------------------------------------------------

create table cards (
  set_code text not null,
  card_number integer not null,
  name text not null,
  rarity text,
  pokemon_type text,
  card_category text,
  trainer_subtype text,
  stage text,
  expansion text,
  is_ex boolean,
  -- Derived at publish time: is_ex AND name LIKE 'Mega %'
  -- (same rule as web/lib/domain/card.ts).
  is_mega boolean not null default false,
  evolves_from text,
  hp integer,
  pack_name text,
  -- Denormalized from data/reference/card_power_scores.json.
  power_score numeric,
  primary key (set_code, card_number)
);

create table packs (
  pack_name text primary key,
  expansion text not null,
  set_code text not null
);

create table pack_cards (
  pack_name text not null,
  set_code text not null,
  card_number integer not null,
  primary key (pack_name, set_code, card_number)
);

-- Top-cards breakdowns per pack. NOTE: top_ev_cards depends on the owner's
-- collection (owned counts / ev_contribution), so despite living in the
-- "global" section per the roadmap, this is owner-derived data today.
-- Revisit at the auth phase; the web app reads getPackEv from the per-user
-- pack_ev document, not from here.
create table pack_top_cards (
  pack_name text primary key,
  top_ev_cards jsonb not null default '[]'::jsonb,
  top_power_cards jsonb not null default '[]'::jsonb
);

-- Singleton document: data/reference/pull_probability_model.json verbatim.
create table pull_probability_model (
  id text primary key default 'current' check (id = 'current'),
  payload jsonb not null,
  generated_at text
);

-- ---------------------------------------------------------------------------
-- Per-user tables: pipeline outputs derived from a user's collection.
-- Derived artifacts (collection_summaries, pack_ev, recommendations) are
-- stored as whole JSONB documents so they round-trip byte-identically
-- through the web/types Zod contract (the Phase 4 parity gate).
-- ---------------------------------------------------------------------------

create table collections (
  user_id uuid not null,
  set_code text not null,
  card_number integer not null,
  count integer not null,
  primary key (user_id, set_code, card_number)
);

create table collection_summaries (
  user_id uuid primary key,
  payload jsonb not null,
  published_at timestamptz not null default now()
);

create table pack_ev (
  user_id uuid primary key,
  payload jsonb not null,
  published_at timestamptz not null default now()
);

create table recommendations (
  user_id uuid primary key,
  payload jsonb not null,
  published_at timestamptz not null default now()
);

-- Snapshot of data/sync/ state (player_stats / sync_review_queue /
-- last_sync_delta). Columns are nullable: absent local file => null,
-- matching the web contract where SyncStatus fields are null when absent.
create table sync_status (
  user_id uuid primary key,
  stats jsonb,
  review_queue jsonb,
  delta jsonb,
  published_at timestamptz not null default now()
);

-- One row per entry of data/sync/sync_history.json. synced_at is kept as the
-- pipeline's original string (not timestamptz) so it round-trips verbatim;
-- ISO-8601 strings order correctly as text.
create table sync_history (
  user_id uuid not null,
  synced_at text not null,
  added_count integer not null,
  added jsonb not null default '[]'::jsonb,
  primary key (user_id, synced_at)
);

-- ---------------------------------------------------------------------------
-- Row-level security.
-- Global tables: public read (anon + authenticated).
-- Per-user tables: owner-only via auth.uid(), plus a TEMPORARY anon SELECT
-- policy pinned to the seeded owner so single-tenant reads work before auth
-- ships. The web app reads with the anon key only.
-- TODO(Phase 6): drop every "anon reads seeded owner" policy when auth lands.
-- ---------------------------------------------------------------------------

alter table cards enable row level security;
alter table packs enable row level security;
alter table pack_cards enable row level security;
alter table pack_top_cards enable row level security;
alter table pull_probability_model enable row level security;

create policy "public read" on cards
  for select to anon, authenticated using (true);
create policy "public read" on packs
  for select to anon, authenticated using (true);
create policy "public read" on pack_cards
  for select to anon, authenticated using (true);
create policy "public read" on pack_top_cards
  for select to anon, authenticated using (true);
create policy "public read" on pull_probability_model
  for select to anon, authenticated using (true);

alter table collections enable row level security;
alter table collection_summaries enable row level security;
alter table pack_ev enable row level security;
alter table recommendations enable row level security;
alter table sync_status enable row level security;
alter table sync_history enable row level security;

create policy "owner reads own rows" on collections
  for select to authenticated using (user_id = auth.uid());
create policy "owner reads own rows" on collection_summaries
  for select to authenticated using (user_id = auth.uid());
create policy "owner reads own rows" on pack_ev
  for select to authenticated using (user_id = auth.uid());
create policy "owner reads own rows" on recommendations
  for select to authenticated using (user_id = auth.uid());
create policy "owner reads own rows" on sync_status
  for select to authenticated using (user_id = auth.uid());
create policy "owner reads own rows" on sync_history
  for select to authenticated using (user_id = auth.uid());

-- TODO(Phase 6): drop these six policies when login ships.
create policy "anon reads seeded owner" on collections
  for select to anon using (user_id = 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11');
create policy "anon reads seeded owner" on collection_summaries
  for select to anon using (user_id = 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11');
create policy "anon reads seeded owner" on pack_ev
  for select to anon using (user_id = 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11');
create policy "anon reads seeded owner" on recommendations
  for select to anon using (user_id = 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11');
create policy "anon reads seeded owner" on sync_status
  for select to anon using (user_id = 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11');
create policy "anon reads seeded owner" on sync_history
  for select to anon using (user_id = 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11');
