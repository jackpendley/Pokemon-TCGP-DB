# Repo Cleanup Audit

Generated: 2026-05-12  
Purpose: Identify stale, duplicate, or unsafe-to-track files. Maintain a lean, organized repo.

---

## Scan Results Summary

| Category | Count | Action |
|---|---|---|
| Clearly safe deletes (tracked DRAFT/superseded) | 6 | **Deleted** |
| Untracked local files already gitignored | ~260+ | No action — .gitignore working correctly |
| Historical pipeline reports (referenced by scripts/docs) | 12 | Keep — provenance |
| Historical pipeline reports (unreferenced) | 3 | Document only — borderline |
| TEMPLATE placeholder files (pipeline complete) | 23 | Keep — no harm, minor historical value |
| .gitignore additions needed | 0 | .gitignore is comprehensive |

---

## .gitignore Status

`.gitignore` is comprehensive and working correctly. All expected local-only files are excluded:

| Pattern | Coverage |
|---|---|
| `__pycache__/` | Python bytecode cache (scripts/__pycache__ is not tracked) |
| `*.pyc` | Python bytecode files |
| `.DS_Store` | macOS metadata (root + data/ are not tracked) |
| `.venv/`, `venv/`, `env/` | Python virtual environments |
| `.env` | Local secrets |
| `*.zip`, `Archive.zip` | Archives |
| `screenshots/` | Active collection screenshots (not tracked, local only) |
| `crops/` | Cropped card images from historical OCR pipeline (~243 PNGs, not tracked) |
| `*.log` | Log files |
| `.claude/` | Claude Code local settings (not tracked) |
| `review/contact_sheets/` | Contact sheet images from historical pipeline (not tracked) |
| `ocr_temp/` | OCR scratch directory |
| `data/reference/*.raw.json` | Raw reference downloads |
| `data/reference/images/` | Downloaded card images |
| `data/reference/external/html_cache/` | Scraped HTML cache |
| `data/reference/external/scrape_log.txt` | Scrape process log |

**No .gitignore additions required.**

---

## Files Deleted

These tracked files were superseded by confirmed/final versions with identical content. Deleting them removes noise without any provenance loss.

| File | Reason |
|---|---|
| `batches/cards_batch_015_DRAFT.json` | Superseded by `batches/cards_batch_015.json` (same 9 cards, pipeline complete) |
| `batches/cards_batch_016_DRAFT.json` | Superseded by `batches/cards_batch_016.json` (same 9 cards, pipeline complete) |
| `batches/cards_batch_017_DRAFT.json` | Superseded by `batches/cards_batch_017.json` (same 9 cards, pipeline complete) |
| `review/confirmed/IMG_1538_confirmed_DRAFT.csv` | Superseded by `IMG_1538_confirmed.csv` (draft had auto-candidates, final has user-confirmed data) |
| `review/confirmed/IMG_1539_confirmed_DRAFT.csv` | Superseded by `IMG_1539_confirmed.csv` |
| `review/confirmed/IMG_1540_confirmed_DRAFT.csv` | Superseded by `IMG_1540_confirmed.csv` |

---

## Files Intentionally Kept

### Source-of-truth files

| File | Reason |
|---|---|
| `collection.json` | Active collection source of truth (380 cards) |
| `cards.json` | Historical 329-card baseline (provenance) |
| `data/reference/pack_sources.json` | Pack source DB (3110 records) |
| `data/reference/pull_probability_model.json` | Pull probability model (v0.3.0) |
| `cards.schema.json`, `data/reference/pack_sources.schema.json`, `data/reference/pull_probability_model.schema.json` | Schemas |

### Root-level files referenced by active pipeline scripts or docs

| File | Referenced by |
|---|---|
| `ambiguous_cards.md` | `scripts/validate_cards.py` (AMBIGUOUS_MD constant), README.md |
| `cards.csv` | README.md (documented output of export_cards_csv.py) |
| `crop_calibration_report.md` | `scripts/crop_all_screenshots.py`, `scripts/crop_3x3_cards.py` |
| `crop_override_report.md` | Historical pipeline output for crop_all_screenshots.py |
| `crop_override_workflow.md` | `scripts/crop_all_screenshots.py`, `scripts/evaluate_crop_quality.py`, README.md |
| `detection_validation_report.md` | `scripts/evaluate_detection_against_confirmed.py`, README.md |
| `field_detection_report.md` | `scripts/evaluate_field_detection.py`, README.md |
| `merge_report.md` | `scripts/merge_batches.py` (MERGE_REPORT constant) |
| `reference_coverage_report.md` | `scripts/evaluate_reference_coverage.py` (OUT_MD constant) |
| `screenshots_inventory.json` | `scripts/crop_all_screenshots.py` (INVENTORY_FILE constant) |
| `screenshots_manifest.md` | README.md |

### Root-level historical docs (unreferenced, provenance value)

These are not referenced by any active script or doc file, but they document the historical pipeline state and have minor provenance value. Keeping them avoids loss of context.

| File | Description |
|---|---|
| `extraction_checklist.md` | Step-by-step guide used during the original screenshot extraction (434 lines, 2026-05-10) |
| `external_reference_integration_report.md` | Status report from the Limitless reference scraping phase (99 lines, 2026-05-10) |
| `pipeline_detection_report.md` | OCR detection performance report after crop override tuning (140 lines, 2026-05-10) |

**Future cleanup candidate:** If the 329-card historical pipeline is formally archived or deprecated, these three files can be removed in a future cleanup pass.

### TEMPLATE placeholder files (review/confirmed/)

23 TEMPLATE CSV files remain tracked (`IMG_1525_confirmed_TEMPLATE.csv` through `IMG_1547_confirmed_TEMPLATE.csv`). These contain OCR-generated row suggestions used to scaffold the manual confirmation step. The confirmed CSVs supersede them functionally. They are kept because:
- They are referenced by `scripts/create_screenshot_review_package.py` (which creates TEMPLATE files for new screenshot review packages)
- They show pre-human-review OCR confidence state for each screenshot — minor provenance value
- 23 files × ~10 lines each — low noise cost

**Future cleanup candidate:** Can be deleted in a future archival pass once the historical pipeline is formally completed or the batch files alone are confirmed sufficient for provenance.

### Active generated outputs

All files under `data/current/`, `data/exports/`, and `review/` that are generated by current active scripts are kept. These include:
- `data/current/collection_normalized.json`, `pack_ev.json`, `final_hourglass_spending_plan.json`, etc.
- `data/exports/*.csv` and `*.json`
- `review/*.md` reports

### Historical pipeline generated outputs

| File/Directory | Description |
|---|---|
| `batches/cards_batch_001.json` — `cards_batch_024.json` | 24 confirmed batch files for 329-card ingestion |
| `batches/cards_batch_TEMPLATE.json` | Batch format template (referenced by `create_draft_batch_from_template.py`) |
| `review/confirmed/IMG_*_confirmed.csv` | Manual confirmation records for all 24 screenshots |
| `data/extraction/*.json` | OCR pipeline outputs: crop manifest, quality report, detection report, field report, match candidates, OCR results |
| `data/reference/external/*.json`, `*.txt` | External reference data from Limitless scrape |
| `data/reference/card_names.txt`, `confirmed_card_names.txt`, `manual_card_names_seed.txt` | Reference card name lists |
| `data/reference/confirmed_lexicon.json`, `card_reference.json` | Reference lookup databases |

---

## Not Tracked (local only, correctly gitignored)

| Path | Contents | Notes |
|---|---|---|
| `.DS_Store`, `data/.DS_Store` | macOS metadata | Gitignored, not tracked |
| `scripts/__pycache__/` | Python .pyc bytecode (26 files) | Gitignored, not tracked |
| `crops/` | ~243 PNG crop images (IMG_1524–IMG_1547) | Gitignored. Generated from historical screenshots by `crop_all_screenshots.py`. Not tracked — originals (IMG_1524–IMG_1547) are no longer in repo. |
| `review/contact_sheets/` | 25 contact sheet PNGs | Gitignored — pipeline visualization outputs |
| `.claude/` | Claude Code settings + scheduled_tasks.lock | Gitignored — local tool state |

---

## Directory Organization Assessment

| Directory | Assessment |
|---|---|
| `batches/` | Clean — 24 confirmed batches + 1 template. DRAFT files removed by this audit. |
| `config/` | Clean — `crop_config.json` only. |
| `data/current/` | Clean — all generated outputs from active scripts. |
| `data/exports/` | Clean — all generated CSV/JSON exports. |
| `data/extraction/` | Clean — historical OCR pipeline outputs, all referenced. |
| `data/reference/` | Clean — reference DBs, schemas, pull model. |
| `docs/` | Clean — 5 docs, all current. |
| `review/` | Mostly clean — 3 unreferenced root reports kept for provenance. |
| `review/confirmed/` | Mostly clean — TEMPLATE files remain (pipeline complete). |
| `review/screenshot_reviews/` | Clean — 19 per-screenshot review notes from historical ingestion. |
| `scripts/` | Clean — 47 scripts, all serve defined purposes. |

---

## Recommended Next Cleanup

Low priority, future pass only:

1. If the historical 329-card pipeline is formally archived: delete `extraction_checklist.md`, `external_reference_integration_report.md`, `pipeline_detection_report.md`.
2. If historical ingestion is complete and batch files alone are confirmed sufficient: delete `review/confirmed/*_TEMPLATE.csv` (23 files).
3. If `crops/` originals (IMG_1524–IMG_1547 source screenshots) are no longer needed: the `crops/` directory can be deleted locally (it's already gitignored and won't be committed).

---

## Cleanup Performed

- **6 files deleted** — superseded DRAFT files only
- **.gitignore** — no changes (already comprehensive)
- **No source-of-truth files modified**
- **No active generated outputs removed**
- **collection.json unchanged, cards.json unchanged**

---

## Standing Workflow (added 2026-05-12)

The repo cleanup and organization review is now a **permanent required phase** for every major development prompt. The full workflow, preservation rules, decision criteria, and documentation requirements are documented in:

**`CLAUDE.md` — Section 19: Repo Hygiene / Cleanup Review**

This audit file (`review/repo_cleanup_audit.md`) records per-pass results. Section 19 of CLAUDE.md is the standing policy.

---

## Pass: 2026-05-13 (pending pack checklist phase)

**Scan findings:**
- `.DS_Store` (root + `data/`) — gitignored, not tracked. No action.
- `scripts/__pycache__/` — gitignored, not tracked. No action.
- `data/current/resolved_pack_sources.json` — timestamp-only modification from validation run. Not staged.
- `data/current/screenshot_inventory.json` — timestamp-only modification from inventory run. Not staged.

**No deletions performed.**

**New files added this phase:**
- `review/pending_pack_in_app_verification_checklist.md` — user-facing in-app verification guide for 3 pending packs
- `data/current/pending_pack_in_app_verification_checklist.json` — machine-readable version with fill-in verification_record fields

**Repo state:** Clean. No new gitignore additions needed.

---

## Pass: 2026-05-14 (A4 in-app verification phase)

**Scan findings:**
- `.DS_Store` (root + `data/`) — gitignored, not tracked. No action.
- `scripts/__pycache__/` — gitignored, not tracked. No action.
- `data/current/resolved_pack_sources.json` — timestamp-only modification. Not staged.
- `data/current/screenshot_inventory.json` — timestamp-only modification. Not staged.
- `Offering Rates screenshots/` (untracked) — 31 user-captured PTCGP app screenshots (IMG_1692–IMG_1722 + IMG_1723). **Staged per user instruction.** Gitignore does not cover this folder (screenshots/ covers `screenshots/` only); these files are intentionally tracked as verification evidence.

**No deletions performed.**

**Files modified this phase:**
- `scripts/build_pull_probability_model.py` — v0.6.0: A4 user_in_app_verified routing, A4_WISDOM_SLOT_RATES, _A4_SLOT_6 constants
- `data/reference/pull_probability_model.schema.json` — slot_6 extended with one_star and three_diamond properties
- `data/reference/pull_probability_model.json` — rebuilt at v0.6.0 (A4 three-branch, slot_6 confirmed)
- `data/current/in_app_rate_verification.json` — A4 (Ho-Oh, Lugia) verification records added
- `review/in_app_rate_verification.md` — A4 section added
- `review/pending_pack_in_app_verification_checklist.md` — Ho-Oh/Lugia marked verified; A4b marked pending/unavailable
- `data/current/pack_ev.json`, `data/exports/pack_ev.csv`, `review/pack_ev.md` — EV rebuilt
- `data/current/inferred_pack_recommendations.json`, `data/exports/inferred_pack_recommendations.csv`, `review/inferred_pack_recommendations.md` — recommendations rebuilt (Lugia now top 5)
- `data/current/final_hourglass_spending_plan.json`, `review/final_hourglass_spending_plan.md`, `data/exports/final_hourglass_spending_plan.csv` — spending plan rebuilt
- `CLAUDE.md` — model version updated, completed phase added
- `docs/recommendation_readiness.md` — model v0.6.0 stats and blockers updated

**Repo state:** Clean. No new gitignore additions needed.

---

## Pass: 2026-05-15 (ambiguous pack-source resolution phase)

**Scan findings:**
- `.DS_Store` (root + `data/`) — gitignored, not tracked. No action.
- `scripts/__pycache__/` — gitignored, not tracked. No action.
- `data/current/screenshot_inventory.json` — timestamp-only modification from validation run. Not staged.

**No deletions performed.**

**New files added this phase:**
- `data/current/current_collection_pack_confirmations.json` — 38 user-confirmed pack-source resolutions (Limitless HP/attack analysis, 2026-05-15)

**Files modified this phase:**
- `data/exports/current_pack_source_review.csv` — 38 confirmed rows filled (confirmed_set_code, confirmed_card_number, confirmed_yes_no=yes)
- `scripts/resolve_ambiguous_pack_sources.py` — PASS 0 added (user_confirmation ingestion from current_collection_pack_confirmations.json); version 1.0.0 → 1.1.0
- `scripts/build_pack_ev.py` — coverage counts updated (35 → 46 newly resolved, 32 → 21 excluded)
- `data/current/resolved_pack_sources.json` — rebuilt at 46/59 resolved (was 35/59)
- `review/resolved_pack_sources.md` — rebuilt with PASS 0 section
- `data/current/pack_ev.json`, `data/exports/pack_ev.csv`, `review/pack_ev.md` — EV rebuilt (coverage 192/224 → 203/224)
- `data/current/inferred_pack_recommendations.json`, `data/exports/inferred_pack_recommendations.csv`, `review/inferred_pack_recommendations.md` — recommendations rebuilt (unchanged rankings)
- `CLAUDE.md` — coverage table updated, completed phase added, blockers updated

**Repo state:** Clean. No new gitignore additions needed.

---

## Pass: 2026-05-15 (final 13 ambiguous entry investigation)

**Scan findings:**
- `.DS_Store` (root + `data/`) — gitignored, not tracked. No action.
- `scripts/__pycache__/` — gitignored, not tracked. No action.

**No deletions performed. No files modified.**

**Findings:**

Group 3 (B-series HP ties — 4 entries: blaziken, frillish, skrelp, porygon2):
- All have distinct rarities (B1/B1a = common; B3 = one_star) but count=1 for all four.
- rarity_count rule requires count ≥ 2; cannot resolve.
- Unresolvable without screenshot evidence of the card art.

Groups 1+2 (A-series trainers + Pokémon — 9 entries):
- A4b exclusion cannot be applied: user confirmed they sometimes receive A4b packs as rewards.
- Confirmed: `professor_s_research` is auto-accepted to A4b (Deluxe Pack: ex), proving A4b cards ARE in the collection.
- Therefore giovanni, sabrina, leaf, cyrus, lillie, giant_cape, moltres_ex, marowak_ex, farfetch_d remain ambiguous.
- Circumstantial evidence: 0 confirmed A3b (Eevee Grove) and 0 confirmed A3/Lunala cards in collection, suggesting moltres_ex likely A1/Charizard and marowak_ex likely A1/Mewtwo — but cannot apply without explicit confirmation.

**Resolution path for future:**
- For trainers/giant_cape: check in-game if the card art shown is standard (two_diamond) or full art (double_star). Standard → older set two_diamond version confirmed.
- For blaziken/frillish/skrelp/porygon2: screenshot evidence needed (or in-game set display).
- For moltres_ex/marowak_ex: check in-game card detail screen — it may show the set/card number.

**Final coverage: 203/224 EV-ready (91%). 13 entries remain unresolved.**

**Repo state:** Clean. No new gitignore additions needed.

---

## Pass: 2026-05-15 (external research + PASS 2B + in-game verification prep)

**Scan findings:**
- `.DS_Store` (root + `data/`) — gitignored, not tracked. No action.
- `scripts/__pycache__/` — gitignored, not tracked. No action.

**No deletions performed.**

**Findings from external research (Limitless + Game8 + web, 2026-05-15):**

1. **B-series shinies (blaziken, frillish, skrelp):** B3 versions (B3/208, B3/209, B3/218) are all one_star SHINY cards. Limitless confirms IDENTICAL HP and attacks to their B1 counterparts. Cannot resolve by stats; require in-game shiny visual check.

2. **farfetch_d A4a/56 ELIMINATED:** Limitless confirms A4a/56 = HP 70, Leek Slam 60. Collection has HP=60, Leek Slap 40. HP and attack mismatch → definitively excluded. Added to KNOWN_INVALID_CANDIDATES pre-pass in resolve script.

3. **farfetch_d A1/198:** Confirmed "Any Pack" card (available in all three A1 Genetic Apex packs). Explains null pack_name in pack_sources.

4. **Starter pack research:** PTCGP tutorial gives players one choice from three Genetic Apex packs (Charizard/Pikachu/Mewtwo). Specific cards: Exeggutor EX (Charizard), Arcanine EX (Pikachu), Marowak EX (Mewtwo). Trainer cards (giovanni, sabrina, leaf, cyrus, lillie, giant_cape) are NOT starter pack rewards — pulled from regular packs.

5. **moltres_ex and marowak_ex:** A4b versions (A4b/67, A4b/196) confirmed to have identical HP and attacks to A1 versions. Cannot resolve by stats; require in-game card number check.

**Files modified this phase:**
- `scripts/resolve_ambiguous_pack_sources.py` — PASS 2B added (evo_chain re-run post-PASS 3); KNOWN_INVALID_CANDIDATES pre-pass added (farfetch_d A4a/56 elimination); version 1.1.0 → 1.2.0
- `data/current/resolved_pack_sources.json` — rebuilt: porygon2 resolved by PASS 2B; farfetch_d A4a candidate eliminated. Total: 47 resolved, 12 unresolved.
- `review/resolved_pack_sources.md` — rebuilt with PASS 2B section
- `data/current/pack_ev.json`, `data/exports/pack_ev.csv`, `review/pack_ev.md` — EV rebuilt (204/224)
- `data/current/inferred_pack_recommendations.json`, `data/exports/inferred_pack_recommendations.csv`, `review/inferred_pack_recommendations.md` — recommendations rebuilt
- `data/current/final_hourglass_spending_plan.json`, `review/final_hourglass_spending_plan.md`, `data/exports/final_hourglass_spending_plan.csv` — spending plan rebuilt
- `CLAUDE.md` — coverage updated (204/224), 12 unresolved, blockers updated

**Coverage: 204/224 EV-ready (91%). 12 entries require in-game verification.**

Remaining 12 breakdown:
- 3 B-series shiny ties: blaziken (B1 vs B3 shiny), frillish (B1 vs B3 shiny), skrelp (B1 vs B3 shiny)
- 3 A-series Pokémon: moltres_ex (A1/47 vs A4b/67), marowak_ex (A1/153 vs A4b/196), farfetch_d (A1/198 vs A3b/102 vs A4b/280-281-359)
- 6 trainer cards: giovanni (A1 vs A4b), sabrina (A1 vs A4b), leaf (A1a vs A4b), cyrus (A2 vs A4b), lillie (A3 vs A4b), giant_cape (A2 vs A4b)

All 12 require checking cards in-game: shininess, card number, or pack icon.

**Repo state:** Clean. No new gitignore additions needed.
