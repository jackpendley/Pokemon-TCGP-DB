# Senior-Engineer Code Review — Pokemon TCGP-DB

_Read-only architecture review. No code was changed. Findings cite `file:line` against the
tree at the time of writing; the highest-severity citations were re-verified by hand._

**Scale:** ~13,971 LOC source (`scripts/`), ~3,449 LOC tests (`tests/`), test ratio ≈ 25%.
**Entry point:** `scripts/run_recommendations.py`. **Shared core:** `scripts/_collection_io.py` (468 LOC).

---

## 1. Architecture & Data Flow

Single-user Python data pipeline. It syncs a Pokemon TCG Pocket collection from Pokemon
Zone, cross-validates card metadata against three independent sources, and computes
expected-value (EV) recommendations for which packs to open.

```
INPUTS                              PIPELINE (run_recommendations.py)         OUTPUTS
─────────────────────────────────  ────────────────────────────────────────  ───────────────────────────
collection.json (source of truth)   1. sync_collection.py        (1785 LOC)   data/sync/last_sync_raw.json
data/reference/                      2. assign_collection_coords.py (436)      data/current/
  card_reference.json (1.5MB,3233)   3. validate_collection_coords.py (472)      collection_normalized.json
  pack_sources.json   (1.5MB,3233)   4. validate_current_collection.py (224)     pack_ev.json / promo_pack_ev.json
  pz_pack_odds.json   (1.1MB)        5. normalize_current_collection.py (269)    coord_assignments_log.json
  pull_probability_model.json        6. build_pack_ev.py          (920)        review/
  reprint_links.json, overrides      7. build_promo_pack_ev.py    (292)          inferred_pack_recommendations.md
  sources/{tcgdex,serebii,           8. generate_pack_recommendation_report.py    final_hourglass_spending_plan.md
           bulbapedia}/<SET>.json       (751)                                  data/exports/*.csv
                                     9. generate_hourglass_spending_plan.py    data/pipeline.log
                                        (513)
```

**Reference-build side-chain (run on demand, not every pipeline run):**
`fetch_source_snapshots.py` → `build_card_reference.py` (reconciles 3 sources by majority
vote) → `card_reference.json`; `ingest_pz.py` → `pz_pack_odds.json` →
`build_pull_probability_model.py` (1349 LOC) → `pull_probability_model.json`;
`build_pack_sources.py` scrapes Limitless → `pack_sources.json`.

**Coordinate model:** every card is a `(set_code, card_number)` tuple. `coord_resolver.py`
resolves these offline (PZ × `card_reference`) with a live TCGdex/Limitless fallback for
brand-new cards. Stack: stdlib + `curl-cffi`/`playwright` (PZ auth/TLS), `requests`,
`beautifulsoup4`, `rapidfuzz`, `jsonschema`.

**Overall assessment:** genuinely well-architected for its purpose. Clear stage separation,
a single canonical path/registry module, deterministic input-hash caching of the EV build,
3-source cross-validation, and graceful auth-expiry degradation. The issues below are
incremental hardening, not redesign.

---

## 2. Findings (ranked by severity within each area)

### Duplication

**D1 · `REQUEST_TIMEOUT` / `REQUEST_DELAY` defined 3× with divergent values — HIGH**
- `coord_resolver.py:57-58` → `12 / 0.35`
- `validate_collection_coords.py:50-51` → `12 / 0.35`
- `fetch_source_snapshots.py:49-50` → `15 / 0.4` (**different**)
Three independent network-timing knobs, one of them silently different. A change to
rate-limit behavior must be made in three places, and the divergence can cause a URL to
succeed in one script but time out in another — hard-to-debug intermittent failure.
_Fix:_ hoist to `_collection_io.py` (which already centralizes `CACHE_MAX_AGE_DAYS`).

**D2 · Three near-identical `*_by_coord()` JSON indexers — MED**
`_collection_io.py:316-375` — `pack_sources_by_coord`, `card_reference_by_coord`,
`ext_ref_by_coord` differ only in field name (`card_number` vs `number`), an `.exists()`
guard, and envelope handling. The malformed-`int()` `try/except` is copy-pasted 3×.
_Fix:_ one `_load_by_coord(path, num_key, *, check_exists=False)` helper.

**D3 · Four `_coord` / `_coord_from_ref` tuple-extractors — MED**
`migrate_reference_rarity.py:35`, `build_reprint_links.py:49`, `sync_collection.py:1056`,
`coord_resolver.py:303`. Same `(set_code.upper().strip(), int(num))` shape with subtly
different error handling. _Fix:_ a shared `parse_coord(set_code, num) -> tuple|None`.

**D4 · JSON envelope detection re-implemented across 4+ loaders — MED**
The `raw.get("records", raw) if isinstance(raw, dict) else raw` idiom appears in
`_collection_io.py:323,346`, `coord_resolver.py`, `ingest_pz.py`, and others. _Fix:_ a
single `load_records(path)`; this would also be the natural place to add the missing
corrupt-JSON guard (R2 below).

**D5 · `SCORING_WEIGHTS` duplicated — MED**
`build_pack_ev.py:57-61` vs `build_promo_pack_ev.py:32-36`. The `new_card` (1.0) and
`copy_up_to_2` (0.4) weights are semantically shared; they will drift if the base model is
re-tuned in only one file. _Fix:_ shared base dict with a per-script override for the
promo-only `ex_missing` term.

### Structure

**S1 · Monolithic `main()` in `sync_collection.py:1239-1785` (546 lines) — HIGH**
One function handles arg parsing, five import modes (JSON / HAR / cURL-stdin / cURL-file /
headless), auth-cache management, PZ fetch, card matching/normalization, the review queue,
collection file editing, validation, and diff printing — via deeply nested `if/elif`. This
is the least testable part of the system and the highest-churn file. _Fix:_ extract
`_phase_fetch / _normalize / _match / _apply` so each import mode and the matching core can
be unit-tested in isolation.

**S2 · Oversized compute functions — HIGH**
- `compute_pack_ev_record()` `build_pack_ev.py:459-559` (8 params; EV aggregation +
  confidence weighting + cost + sorting + formatting in one body).
- `build_pack_records()` `build_pull_probability_model.py:748-921` (174 lines). Note: the
  branch *routing* is already data-driven via `SET_CODE_BRANCH_CONFIG` (`:796`) — good — but
  lines `798-852` are a 55-line `if/elif` chain that maps `branch_type` → static
  `bulbapedia_match` + notes strings. That is a pure lookup masquerading as control flow.
  _Fix:_ move it to a `BRANCH_ANNOTATIONS: dict[str, tuple[str, str]]` table.

**S3 · Set-code business logic hardcoded across 6+ files — MED**
The A4b mislabel rule (`_PZ_MISLABEL_SOURCE_SETS`/`_TARGET_SETS`, `coord_resolver.py:52-53`)
and PROMO-prefix checks recur in `build_reprint_links.py`, `sync_collection.py`,
`reconcile_coords_from_pz.py`, `validate_reprint_links.py`, `build_promo_pack_ev.py`,
`build_card_reference.py`, `generate_pack_recommendation_report.py`. A set-definition change
touches all of them. _Fix:_ centralize `A4B_*` / `PROMO_SETS` constants in `_collection_io.py`.

### Performance

**P1 · Serial network fetches with no retry/backoff — HIGH (refresh runs only)**
- `fetch_ext_ref.py:429-478` — loops ~3200 cards at a fixed `--delay` (0.5s) → ~27 min
  worst case; a failed card just gets dropped (`:144-149` swallows `HTTPError` → `None`).
- `ingest_pz.py:154-165` — per-pack odds pages, fixed 0.5s, no parallelism.
- `coord_resolver.py:127-190` — 1–2 calls per new card, `time.sleep(REQUEST_DELAY)` fixed.
These are **off the hot path** of a normal `--skip-sync` recommendation run, so day-to-day
latency is unaffected; the pain is reference refreshes (new set drops). _Fix:_ a small
`retry(max=3, backoff=2x)` helper + persist failed `(set,num)` so a re-run resumes instead
of refetching the ~3200 that already succeeded.

**P2 · `pack_sources.json` (1.5 MB) reloaded ~4× per pipeline — MED (low real gain)**
Reloaded in `sync_collection.py`, `build_pack_ev.py`, `coord_resolver.py`,
`build_pack_sources.py`. Total JSON parse cost is ~0.2 s/file and the stages are separate
processes, so the realistic win is small — flagged for completeness, not urgency.

**P3 · O(n²) A4b reprint pairing — LOW**
`sync_collection.py:1059-1089` is a nested name-match loop over collection entries (~512),
but it only fires when A4b reprints are present and `break`s early. Acceptable as-is.

### Robustness & Maintainability

**R1 · No retries anywhere on network; errors silently become `None` — MED**
`fetch_ext_ref.py:144-149` is representative: `HTTPError` is caught and discarded, so a
transient 5xx looks identical to "card genuinely absent." Covered by the P1 fix.

**R2 · No `try/except` around `json.loads()` in most loaders — MED**
A corrupt reference/collection file surfaces as a raw `JSONDecodeError` deep in a loader
with no file context. _Fix:_ wrap the shared `load_records()` (D4) with a message naming the
offending path.

**R3 · Silent `.get()` fallbacks for required reference fields — MED**
E.g. a missing `rarity` in `pack_sources.json` flows through as `None` into EV scoring
rather than failing loudly — the pipeline computes a quietly-wrong number. _Fix:_ validate
required fields once at load (the `pack_sources.schema.json` already exists; enforce it).

**R4 · Test gaps concentrated in failure modes — MED**
Suite is solid on *logic* (EV ordering, coord resolution, sync matching, new-card
additions). Largely untested: network errors/timeouts, rate-limit handling, the auth-expiry
*fallback to existing collection.json* (only the exit code is checked), malformed input, and
large-collection scaling. No network mocking means integration tests are network-dependent
(CI-flaky). _Fix:_ mock `urllib`/`requests` for the failure-path cases.

**R5 · Dead/stub + oversized test file — LOW**
`deck_target_ev` is hardcoded to 0 in `build_pack_ev.py` (deck feature deferred) — keep, but
add a one-line `# DEFERRED` marker and a test pinning it to 0 so the stub can't silently
activate. `tests/test_new_card_additions.py` (1257 LOC) should be split by feature.

---

## 3. Prioritized Remediation Roadmap

Grouped to match the "one agent per area" follow-up. Quick wins first.

| # | Area | Action | Effort | Risk |
|---|------|--------|--------|------|
| D1 | Duplication | Centralize `REQUEST_TIMEOUT`/`REQUEST_DELAY` in `_collection_io.py` | XS | Low |
| D4+R2 | Duplication/Robustness | Single `load_records(path)` with corrupt-JSON guard; adopt in loaders | S | Low |
| D2 | Duplication | Fold 3 `*_by_coord()` into one helper | S | Low |
| D3 | Duplication | Shared `parse_coord()` | S | Low |
| S3 | Structure | Centralize A4b / PROMO set constants | S | Low |
| D5/S2b | Structure | `SCORING_WEIGHTS` base dict; `BRANCH_ANNOTATIONS` lookup table | S | Low |
| R3 | Robustness | Enforce `pack_sources.schema.json` at load | S | Low–Med |
| P1+R1 | Performance/Robustness | `retry(backoff)` helper + resumable failed-card set | M | Med |
| R4 | Robustness | Failure-path tests with network mocking | M | Low |
| S1 | Structure | Split `sync_collection.main()` into phase functions | L | **Med–High** (highest-churn file; do last, behind tests) |
| S2a | Structure | Decompose `compute_pack_ev_record()` | M | Med |
| R5 | Maintainability | Mark deck stub + pin test; split `test_new_card_additions.py` | XS | Low |

**Sequencing:** the top six are mechanical, individually shippable, and de-risk everything
below them by establishing the shared helpers. Tackle the retry layer (P1) next for the only
user-visible win. Defer the `sync_collection.main()` split (S1) until the failure-path tests
(R4) exist to catch regressions — it touches the most critical and highest-churn code.
