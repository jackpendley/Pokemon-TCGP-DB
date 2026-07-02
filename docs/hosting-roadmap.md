# Roadmap — Phases 4–7 (Hosting, Auth, Postgres Features)

**Status:** Phases 0–3 shipped (contract lock, design system, dashboard/browsing,
card power model + top pull targets, sync-on-dashboard). This document covers the
remaining infrastructure track: lifting the local-JSON app to a hosted Supabase +
Vercel stack, then unlocking Postgres-native features.

**Audience:** "Me now, multi-user later." Model the data for multi-user (carry
`user_id`, enable RLS, seed a single owner) but do **not** build login UX yet.

**Hard constraints (unchanged from the original plan):**
- The Python pipeline stays the source of truth. EV/recommendation logic is
  **never** edited for hosting. The Phase 0 golden snapshot must stay green
  through every phase.
- Hosting is **additive**, not a rewrite: the `DataSource` seam
  (`web/lib/data/source.ts`, `index.ts`) and the `SyncRunner` seam
  (`web/lib/sync/runner.ts`) already exist. New impls slot in behind them.
- The `web/types/` Zod schemas are the validated contract. Reuse them as the
  column contract for the publisher — do not invent a second schema.

---

## Phase 4 — Supabase hosted read layer (the keystone)

Now that every new field exists (`power_score`, `top_power_cards`, rarity,
sync history), the schema captures them **once** instead of being migrated twice.

### 4.1 Schema — `supabase/migrations/0001_init.sql`
- **Global (no `user_id`):** `cards` (incl. `power_score`, `rarity`,
  `pokemon_type`, `stage`, `is_ex`, mega flag), `packs`, `pack_cards`,
  `pack_top_cards` (both `top_ev_cards` and `top_power_cards`),
  `pull_probability_model`.
- **Per-user (carry `user_id`, RLS on, seed one owner):** `collections`,
  `collection_summaries`, `pack_ev`, `recommendations`,
  `sync_status`, `sync_history`.
- Every per-user table gets an RLS policy `user_id = auth.uid()`; seed the
  current owner's UUID so single-tenant reads work before auth ships.

### 4.2 Publisher — `scripts/publish_to_supabase.py`
- Upserts the existing `data/current/` + `data/reference/` artifacts into
  Postgres. Idempotent, keyed on natural PKs (`set_code`+`card_number`,
  `pack_name`). Uses the **service-role key**, server-side only.
- **Pipeline logic untouched** — this reads the JSON the pipeline already emits.
- Add a test with a mocked client asserting upsert payloads match the artifact
  shapes (reuse `web/types/__fixtures__/` shapes as the contract).

### 4.3 Web read impl — `web/lib/data/supabase.ts`
- Implement the full `DataSource` interface against Supabase.
- Wire the existing `supabase` branch in `web/lib/data/index.ts` (today it
  throws "not implemented").
- Add `SUPABASE_URL` / `SUPABASE_ANON_KEY` / `SUPABASE_SERVICE_ROLE_KEY` to
  `web/lib/env.ts` (Zod, server-only; service-role never in the client bundle).

### 4.4 Parity gate
- Extend the Phase 0 `DataSource` parity test so `supabaseSource` returns the
  **same shape** as `localJsonSource` on identical seed data.

**Checkpoint:** `DATA_SOURCE=supabase npm run dev` renders **identically** to
local-json on every page. CI stays artifact-free (Supabase steps gated/mocked).
Phase 0 golden snapshot unchanged.

---

## Phase 5 — Deploy to Vercel + hosted sync

Python can't run on Vercel, so sync moves to CI.

### 5.1 Vercel project
- Env: Supabase keys, `DATA_SOURCE=supabase`. Confirm the service-role key is
  set as a server-only Vercel env var, never `NEXT_PUBLIC_`.

### 5.2 Hosted sync — `.github/workflows/sync.yml`
- Runs the pipeline (`run_recommendations.py`) + `build_card_power_score.py` +
  `publish_to_supabase.py` on a schedule and/or `repository_dispatch`.
- Add `web/lib/sync/remote-runner.ts` — a `SyncRunner` that fires
  `repository_dispatch` instead of spawning `python3`; selected by env.
- Local dev keeps the spawn runner. Prod without CI configured degrades to
  read-only "last synced" (the existing `ENABLE_LOCAL_SYNC` flag already
  force-disables spawning in prod).

**Checkpoint:** app live on Vercel reading Supabase; a manual Action run
refreshes data without a redeploy.

---

## Phase 6 — Auth scaffolding (modeled, not user-facing)

- Supabase Auth server client (`web/lib/supabase/server.ts`) + middleware.
- Seed the single owner; backfill `user_id` on existing rows; verify RLS.
- **No login UI** surfaced — single-tenant stays the default. Flipping to
  multi-user later is "enable the UI + per-user sync," not a migration.

**Checkpoint:** RLS verified (owner sees data, anon sees nothing);
single-user behavior unchanged.

---

## Phase 7 — Postgres-enabled features

Now trivial with timestamps in Postgres.

- **Recommendation history:** append-only `recommendation_snapshots` written by
  the publisher each sync; a `/history` view of EV/recommendation drift.
- **Admin/dev tools `/admin`:** sync status, last publish time, data-integrity
  counts, manual re-publish trigger.

**Checkpoint:** each ships as its own PR, green CI, verified on Vercel.

---

## Sequencing notes
- Phases are independently shippable. If deploying sooner matters more than the
  Postgres features, P4→P5 can land before revisiting P7.
- Doing the power-score + top-pull data work first (already done) means the
  Supabase schema is designed **once**.

## Risks & mitigations
| Risk | Mitigation |
|------|-----------|
| EV correctness drift | Phase 0 golden test green every phase; pipeline never edited; P4 parity gate |
| Service-role key leakage | Server-only env, Zod-validated, Vercel/GitHub secrets, never in client bundle |
| CI needing live Supabase | Gate/mock Supabase steps; web CI stays artifact-free |
| Schema churn | All new fields already exist before P4; schema designed once |
| Scope creep | One PR per increment, green CI before each merge |

## End-to-end verification (post-Phase 5)
1. `python3 scripts/run_recommendations.py --skip-sync && python3 scripts/build_card_power_score.py && python3 scripts/publish_to_supabase.py` → data in Supabase.
2. `cd web && DATA_SOURCE=supabase npm run dev` → every page renders identically to local-json.
3. `npm run build` green; Vercel preview renders live data; a GitHub Action refresh reflects on the deployed dashboard without a redeploy.
