-- Trainer power scores (Phase 6).
--
-- cards.power_score used to hold one model's output: HP + attack + ability,
-- Pokémon only, null for all 287 Trainers. Trainers are now scored too, but
-- from their rule text by a different model, so a score is only meaningful
-- alongside the model that produced it. Consumers must not rank a "trainer"
-- score against a "pokemon" one.
--
-- Existing rows were all Pokémon scores, so they backfill to 'pokemon'.
alter table public.cards
  add column if not exists power_score_kind text
    check (power_score_kind in ('pokemon', 'trainer'));

update public.cards
   set power_score_kind = 'pokemon'
 where power_score is not null
   and power_score_kind is null;

comment on column public.cards.power_score_kind is
  'Which model produced power_score: pokemon (HP+attack) or trainer (rule text).';
