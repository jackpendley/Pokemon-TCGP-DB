# Adding a newly-released set (runbook + retrospective)

Written while integrating the **2026-06-29** release:
- **B3b — "Everyday Wonders"** (106 cards, single pack `everyday-wonders`)
- **Promo Pack B Series Vol. 10** (PROMO-B/72–76, 5 new cards)

This is both the step-by-step runbook and a record of the gaps hit, so the next
release goes faster.

## The short version (since 2026-08-05)

`python3 scripts/adopt_set.py <SET>` does steps 1–5 below, or click **Adopt** on
the dashboard banner (which fires `.github/workflows/adopt-set.yml` on the
self-hosted runner and opens a PR). It verifies every source URL *before*
touching the registry and reverts the registration if
`test_set_registry_consistency` / `test_card_type_completeness` fail afterwards,
so a failed run leaves the tree clean.

It still can't invent a Mega ex's type — if the classification gate fails, add the
`data/reference/card_type_overrides.json` entry (gap #3) and re-run. The manual
runbook below remains the reference for what it automates.

## Runbook

1. **Discover** what dropped:
   `python3 scripts/ingest_pz.py` (live dry-run). Reports new packs/cards with
   set code, expansion name, and pack slug. Cross-check names against
   Serebii/Bulbapedia. (Auth: reuses `data/sync/.auth.json`; if 403/expired, run
   `python3 scripts/sync_collection.py --curl-import` first.)

2. **Register the set** (only for a genuinely new set code — a new promo *volume*
   in an existing PROMO set needs no registration):
   - `scripts/_collection_io.py` → add to `SET_REGISTRY` (`pack_type`,
     `limitless_slug`). Use the **lowercase-suffix** canonical casing (`B3b`, not
     `B3B`); PZ's `B3B` resolves to it via `_SET_CANONICAL`.
   - `scripts/fetch_source_snapshots.py` → add to `SET_ALIASES`
     (`tcgdex`/`serebii`/`bulbapedia`/`limitless`). **tcgdex is almost always
     `None`** for a brand-new set (it lags weeks). Verify each URL returns 200:
     `curl -sI "https://www.serebii.net/tcgpocket/<slug>/"` etc.
   - Guard: `python3 -m pytest tests/test_set_registry_consistency.py`.

3. **Fetch sources + rebuild reference**:
   - `python3 scripts/fetch_source_snapshots.py --set <NEW>`
   - **Also `--force` any existing set that gained cards** (e.g. a promo volume):
     `python3 scripts/fetch_source_snapshots.py --set PROMO-B --force`
     (the snapshot TTL will otherwise serve a stale, pre-release cache — see gap #5).
   - `python3 scripts/ingest_pz.py --apply --write-pack-sources --rebuild-refs`
     (`--rebuild-refs` rebuilds both `card_reference.json` and
     `pull_probability_model.json`, so the new pack is scored in EV — see gap #6)
   - `python3 scripts/build_reprint_links.py`

4. **Classify stragglers.** Rebuild and check:
   `python3 scripts/build_card_reference.py` then
   `python3 -m pytest tests/test_card_type_completeness.py`.
   New Mega ex and Trainer tools often land typeless (gaps #3, #4). Fix Mega ex
   via `data/reference/card_type_overrides.json` (type read from the Bulbapedia
   expansion page `{{TCG Icon|...}}`).

5. **Sync + rank**: `python3 scripts/run_recommendations.py`
   (or `--skip-sync` if PZ was synced <24h ago). Verify no `COUNT MISMATCH`.

6. **Web**: usually nothing — the UI is data-derived. Only touch
   `web/lib/domain/card-image.ts` (`TCGDEX_COVERED`, add the set **only once
   tcgdex hosts it**), `web/lib/domain/rarity.ts` (a brand-new rarity token), or
   the series quick-actions in `cards-browser.tsx` (a new series *letter*).

7. **Validate**: `python3 -m pytest tests/ -q`; the three `validate_*.py`
   scripts; `cd web && npm run lint && npm run typecheck && npm run test && npm run build`.

## Gaps found (and what was done)

| # | Gap | Severity | Status |
|---|-----|----------|--------|
| 1 | `ingest_pz.py --write-pack-sources` wrote the set **code** (`B3b`) into the `expansion` field instead of the readable name. Latent since B3b is the first set ingested purely through the odds path (older sets came via limitless/pz_catalog). | Med — wrong display name everywhere `expansion` is shown | **Fixed** — parse the readable expansion name from the page title; promos still keep the code to match existing records. |
| 2 | `fetch_ext_ref.py` **403s on every card** of a new set — it followed the stored `source_url`, which for PZ-ingested records points at pokemon-zone.com (a different site than its Limitless parser expects, and one that Cloudflare-blocks plain `urllib`). So the external reference (`card_category`, etc.) never populated for new sets. | High — removes a whole classification source right when it's needed | **Fixed** (#62): build the fetch URL from `(set_code, number)` against Limitless (promos → `P-A`/`P-B`), which serves 200 with a normal UA. |
| 3 | Bulbapedia snapshot parser drops the **type of Mega ex cards**: rows carry `{{TCGP Icon\|Mega ex}}`, whose inner `\|` breaks the `[^\|]*` type-column match in `fetch_source_snapshots.py` (`_BP_ROW` regex only allows `{{TCGP Icon\|ex}}`). | Med — every Mega ex in a tcgdex-uncovered set lands typeless | **Worked around** via `card_type_overrides.json` (the established pattern; see the pre-existing B3a Mega Altaria ex entry). Root fix: make the regex tolerate any `{{TCGP Icon\|...}}` marker + add a test. |
| 4 | Bulbapedia emits the **accented** `"Pokémon Tool"`, but `TRAINER_SUBTYPE_TOKENS` only had the un-accented `"Pokemon Tool"`, so tool cards (Small Balloon, Elegant Cape) were left unclassified when Bulbapedia is the only source. | Med | **Fixed** — added the accented variant to the token set. |
| 5 | `ingest_pz` adds pack-odds/records for a new promo volume, but the **source snapshot isn't auto-refreshed** (30-day TTL), so the new promo cards get `pokemon_type=None` from a stale cache. Had to `--force` the PROMO-B snapshot manually. | Med | **Documented** (runbook step 3). Consider having ingest force-refresh snapshots for any set whose card count grew. |
| 6 | EV/recommendations only score packs present in `pull_probability_model.json`, and that model wasn't rebuilt on ingest — so a new pack silently never appeared in EV. | High — new pack invisible in the product | **Fixed** (#62): `ingest_pz --rebuild-refs` now also rebuilds the pull model, and `build_pack_ev` warns when a PZ-odds pack has no model entry. |
| 7 | Discovery is not wired into the normal sync: `run_recommendations.py` runs `--no-fetch` and routes unknown cards to `sync_review_queue.json`. Nothing tells you "a new set exists — run ingest." | Low/Med | **Fixed** (2026-08-05) — `sync_collection.detect_unregistered_sets` writes `data/sync/new_sets_detected.json`, published as `sync_status.pending_sets` and shown as a dashboard banner with an Adopt button. Cost us the whole B4 release: the 2026-08-03 sync completed with zero net change and no hint that Ruler of the Skies existed. |
| 8 | Adding a set is a **manual dual-edit** (`SET_REGISTRY` + `SET_ALIASES`), kept consistent only by an import-time assertion + one test. Source slugs are hand-guessed. | Low (assertion catches drift) | **Fixed** (2026-08-05) — `scripts/adopt_set.py` writes both entries, but only after resolving the Serebii slug by trying candidate shapes against the live page and reading the expansion name off Limitless. Guard tests gate the result; failure rolls the registration back. |
| 9 | **tcgdex lag**: B3b has no `hp`/`stage` (tcgdex is the authority) and Limitless hasn't uploaded B3b **large** card art yet (`_EN.png` 403; small `_SM.webp` works). UI degrades to placeholders for detail images. | Low — transient, self-heals when upstreams catch up | Recommend a periodic "tcgdex/limitless backfill" that re-fetches `tcgdex: None` sets and flips `TCGDEX_COVERED`. |

## What worked well
- The `SET_ALIASES`/`SET_REGISTRY` import assertion + `test_set_registry_consistency.py` made registration foolproof.
- The web layer is genuinely data-derived: new set, cards, packs, rarities, and the by-type/by-rarity/by-stage grids all appeared with zero frontend code changes.
- PZ per-card odds gave B3b **full-confidence** EV immediately (no in-app-verification wait), and the zod read-boundary contract meant a bad shape would have failed loudly rather than silently.
- `card_reference` confidence held up: B3b names are `confirmed` (Serebii + Bulbapedia agree) despite tcgdex being absent.

## B4 — Ruler of the Skies (2026-07-29)

Integrated 2026-08-05. 233 cards, single pack, `ruleroftheskies` on Serebii,
tcgdex absent as usual. Notes specific to this release:

- **Pokémon Zone lagged the release by ~6 days.** The 2026-08-03 sync fetched 864
  cards with zero B4 among them because PZ's own catalog had not ingested the set;
  it appeared on 2026-08-04. Nothing in the pipeline could have surfaced B4 before
  PZ carried it — worth checking `pokemon-zone.com` before assuming a bug.
- **`fetch_ext_ref.py --set B4` is required**, not optional. HP and stage come from
  ext_ref for tcgdex-uncovered sets (`build_card_reference.py` `hp_final` /
  `stage_final`), *not* from `fetch_combat_stats.py`, whose cache only feeds
  `evolves_from`. Skipping it leaves 202 Pokémon with null HP and stage.
- **Gap #3 recurred**: 16 B4 Mega ex printings landed typeless. Types were read
  off the Limitless card page title (`<p class="card-text-title">` → `Name - Type -
  HP`) and pinned in `card_type_overrides.json`.
- **PROMO-B grew to 86 cards** in the same release (72→86). Its snapshot needed
  `--force` (gap #5) and two more Mega ex type overrides.
