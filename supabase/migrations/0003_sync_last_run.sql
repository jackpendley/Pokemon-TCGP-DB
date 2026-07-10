-- CI live sync (docs/hosting-roadmap.md §5, revised): the publisher stamps
-- sync_status.last_run = {finished_at, outcome: ok|review|auth_expired,
-- mode: live|skip} on each CI publish, and bumps published_at explicitly.
-- The web remote sync runner polls both to report honest completion.

alter table sync_status add column last_run jsonb;
