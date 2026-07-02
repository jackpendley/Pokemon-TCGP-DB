# Adding a newly-released set (runbook + retrospective)

Written while integrating the **2026-06-29** release:
- **B3b — "Everyday Wonders"** (106 cards, single pack `everyday-wonders`)
- **Promo Pack B Series Vol. 10** (PROMO-B/72–76, 5 new cards)

This is both the step-by-step runbook and a record of the gaps hit, so the next
release goes faster.

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
   - `python3 scripts/build_pull_probability_model.py`  ← **required for EV** (gap #6)
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
| 2 | `fetch_ext_ref.py` **403s on every card** of a new set — it hits pokemon-zone.com card pages with plain `urllib` and gets Cloudflare-blocked (unlike the sync client, which uses curl-cffi impersonation). So the Limitless/PZ external reference (`card_category`, `pokemon_type`) never populates for new sets. | High — removes a whole classification source right when it's needed | **Not fixed** — worked around via snapshot + overrides. Recommend routing `fetch_ext_ref` through `pokemon_zone_client` (impersonation) or a HAR fallback. |
| 3 | Bulbapedia snapshot parser drops the **type of Mega ex cards**: rows carry `{{TCGP Icon\|Mega ex}}`, whose inner `\|` breaks the `[^\|]*` type-column match in `fetch_source_snapshots.py` (`_BP_ROW` regex only allows `{{TCGP Icon\|ex}}`). | Med — every Mega ex in a tcgdex-uncovered set lands typeless | **Worked around** via `card_type_overrides.json` (the established pattern; see the pre-existing B3a Mega Altaria ex entry). Root fix: make the regex tolerate any `{{TCGP Icon\|...}}` marker + add a test. |
| 4 | Bulbapedia emits the **accented** `"Pokémon Tool"`, but `TRAINER_SUBTYPE_TOKENS` only had the un-accented `"Pokemon Tool"`, so tool cards (Small Balloon, Elegant Cape) were left unclassified when Bulbapedia is the only source. | Med | **Fixed** — added the accented variant to the token set. |
| 5 | `ingest_pz` adds pack-odds/records for a new promo volume, but the **source snapshot isn't auto-refreshed** (30-day TTL), so the new promo cards get `pokemon_type=None` from a stale cache. Had to `--force` the PROMO-B snapshot manually. | Med | **Documented** (runbook step 3). Consider having ingest force-refresh snapshots for any set whose card count grew. |
| 6 | EV/recommendations only score packs present in `pull_probability_model.json`, and **`run_recommendations.py` does not rebuild that model** — you must run `build_pull_probability_model.py` separately or the new pack silently never appears in EV. | High — new pack invisible in the product | **Documented** (runbook step 3). Consider having `ingest_pz --rebuild-refs` also rebuild the pull model, or having EV warn on a pz-odds pack with no model entry. |
| 7 | Discovery is not wired into the normal sync: `run_recommendations.py` runs `--no-fetch` and routes unknown cards to `sync_review_queue.json`. Nothing tells you "a new set exists — run ingest." | Low/Med | Recommend: sync detects an unregistered `set_code` and prints a loud "new set detected" hint. |
| 8 | Adding a set is a **manual dual-edit** (`SET_REGISTRY` + `SET_ALIASES`), kept consistent only by an import-time assertion + one test. Source slugs are hand-guessed. | Low (assertion catches drift) | Consider a `scripts/add_set.py` scaffold that writes both entries and curls each source URL. |
| 9 | **tcgdex lag**: B3b has no `hp`/`stage` (tcgdex is the authority) and Limitless hasn't uploaded B3b **large** card art yet (`_EN.png` 403; small `_SM.webp` works). UI degrades to placeholders for detail images. | Low — transient, self-heals when upstreams catch up | Recommend a periodic "tcgdex/limitless backfill" that re-fetches `tcgdex: None` sets and flips `TCGDEX_COVERED`. |

## What worked well
- The `SET_ALIASES`/`SET_REGISTRY` import assertion + `test_set_registry_consistency.py` made registration foolproof.
- The web layer is genuinely data-derived: new set, cards, packs, rarities, and the by-type/by-rarity/by-stage grids all appeared with zero frontend code changes.
- PZ per-card odds gave B3b **full-confidence** EV immediately (no in-app-verification wait), and the zod read-boundary contract meant a bad shape would have failed loudly rather than silently.
- `card_reference` confidence held up: B3b names are `confirmed` (Serebii + Bulbapedia agree) despite tcgdex being absent.
