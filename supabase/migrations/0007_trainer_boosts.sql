-- Trainer boost relationships.
--
-- A Trainer whose rule text only works with certain Pokémon ("your Ninetales,
-- Rapidash, or Magmar", "your {W} Pokémon") already scored *lower* for it — the
-- narrowness discount in scripts/trainer_power.py. The same restriction is also
-- what makes the card findable: it is exactly the card that one deck wants. This
-- column persists the relationship so the deck builder can recommend it and the
-- card page can show it.
--
-- Shape: {"names": ["Ninetales", ...], "types": ["Water", ...]} — names join on
-- cards.name, types on cards.pokemon_type. Both lists empty (the common case,
-- e.g. Giovanni, Poké Ball) means the card works in any deck; that is represented
-- by emptiness rather than a flag. Null means the card was never scored.
--
-- jsonb rather than two text[] columns because the two lists are one fact and are
-- always read together. No index: the whole catalog is loaded and filtered in the
-- app, never queried by boost.
alter table public.cards
  add column if not exists boosts jsonb;

comment on column public.cards.boosts is
  'Trainer-only. {"names":[],"types":[]} of Pokémon this card is restricted to '
  'helping; both empty means it works in any deck. Derived from rule text by '
  'scripts/trainer_power.py trainer_boosts().';
