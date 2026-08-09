-- Printing groups: coords that are the same physical card.
--
-- The 2026-07-29 game update changed card-dex registration. Obtaining a card that
-- appears in several booster packs now registers it under *every* one of those
-- expansions, retroactively — "if you obtain Mewtwo ex from Genetic Apex, it will
-- be registered in your card dex under both Genetic Apex and Deluxe Pack: ex."
--
-- Ownership stays keyed per coord in public.collections, exactly as Pokémon Zone
-- reports it: you own three cards, not six, and total_quantity must keep saying so.
-- What changes is which dex slots that ownership *credits*. This column names the
-- group, so a read can credit every coord sharing it without a join table.
--
-- Null (the overwhelming majority) means the card has a single printing and is its
-- own group. Derived by scripts/build_printing_groups.py from Pokémon Zone's
-- expansionIds, falling back to data/reference/reprint_links.json.
alter table public.cards
  add column if not exists printing_group text;

-- The catalog read filters/groups by this, and it is null for most rows, so a
-- partial index keeps it small.
create index if not exists cards_printing_group_idx
  on public.cards (printing_group)
  where printing_group is not null;

comment on column public.cards.printing_group is
  'Group id shared by every coord that is the same physical card (post-2026-07-29 '
  'multi-expansion dex registration). Null means a single-printing card. Ownership '
  'of any coord in a group credits the whole group. Written by '
  'scripts/build_printing_groups.py via scripts/publish_to_supabase.py.';
