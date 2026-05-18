# Claude Code Project Instructions

## 1. Project Overview

Pokemon-TCGP-DB tracks the user's Pokémon TCG Pocket collection.

The active goal is to support accurate deck-building and pack-opening decisions.

- **Active collection baseline:** `collection.json` — 380 cards, 224 unique entries, manually authored, validated.

Everything added to this project must serve the collection tracking and recommendation goal.

## 2. Source of Truth

- `collection.json` is the **active source of truth** for all new recommendation work.
- `data/current/collection_normalized.json` is the generated machine-readable normalized version.
- `screenshots/` is the **visual evidence source** for training, alignment, and confidence validation.
- For current work, `collection.json` + `screenshots/` together are sufficient to train and validate automated matching and confidence scoring.

## 3. Current Validated State

| Item | Status |
|---|---|
| `collection.json` total | **380 validated ✅** |
| `collection.json` unique entries | 224 |
| `pack_sources.json` records | **3110 validated ✅** |
| Screenshots | 26 cropped grid images, `IMG_1556–IMG_1581` |
| Screenshot slots | 232 (25 × 9 standard + 1 × 7 final) |
| Structural reconciliation | **PASS** — 232 slots ≥ 224 unique entries |
| Pack-source coverage | **207/224 entries resolved (92%)** |

Screenshots are local user-provided evidence under `screenshots/`. They are gitignored. Do not delete them.

## 4. Important Scripts

### Collection sync from Pokemon Zone (primary update path)

**First-time setup (Cloudflare-safe — recommended):**
```bash
python3 scripts/sync_collection.py --curl-import
# Opens instructions; paste a cURL from browser DevTools once.
# Auth is saved to data/sync/.auth.json (gitignored). Expires in hours–days.
```

**When auth expires, re-run the same command.**

**Subsequent syncs (headless, no browser needed):**
```bash
python3 scripts/sync_collection.py           # headless sync using stored auth
python3 scripts/sync_collection.py --dry-run # preview changes, no writes
```

**One-shot HAR import (no persistent auth):**
```bash
# 1. Open pokemon-zone.com/collection-tracker/ in your browser
# 2. DevTools → Network → Export as HAR
# 3. Run:
python3 scripts/sync_collection.py --har-import www.pokemon-zone.com.har
```

**Fallback (may hit Cloudflare CAPTCHA):**
```bash
python3 scripts/sync_collection.py --login   # headed Playwright browser login
python3 scripts/sync_collection.py --discover # inspect all Playwright-captured responses
```

### Full recommendation pipeline (sync + EV + reports)

```bash
python3 scripts/run_recommendations.py             # sync → validate → EV → all reports
python3 scripts/run_recommendations.py --skip-sync # skip sync, use current collection.json
python3 scripts/run_recommendations.py --login     # re-auth via Playwright before sync
```

### Active collection (manual validation)

```bash
python3 scripts/validate_current_collection.py --expected-total 380
python3 scripts/normalize_current_collection.py
python3 scripts/inventory_screenshots.py
python3 scripts/reconcile_current_collection_sources.py
```

### Pack-source readiness

```bash
python3 scripts/current_collection_pack_coverage.py
python3 scripts/create_current_pack_review.py   # report generator — not a mandatory manual step
python3 scripts/apply_current_pack_confirmations.py --dry-run   # only when user has filled CSV
python3 scripts/apply_current_pack_confirmations.py --apply
```

### Automated confidence scoring (built)

```bash
python3 scripts/build_screenshot_collection_alignment.py
python3 scripts/score_pack_source_confidence.py
python3 scripts/resolve_ambiguous_pack_sources.py
```

### Deck validation

```bash
python3 scripts/validate_deck_recommendations.py
```

### EV pipeline (individual steps)

```bash
python3 scripts/resolve_ambiguous_pack_sources.py
python3 scripts/build_pack_ev.py
python3 scripts/generate_pack_recommendation_report.py
python3 scripts/generate_hourglass_spending_plan.py
```

## 5. Generated Outputs

| File | Description |
|---|---|
| `data/current/collection_normalized.json` | Clean JSON, no comments, generated fields |
| `data/current/collection_summary.json` | Aggregated statistics |
| `review/current_collection_summary.md` | Human-readable collection summary |
| `data/current/screenshot_inventory.json` | Screenshot file list and slot counts |
| `data/current/screenshot_manifest.json` | Slot-level manifest |
| `review/screenshot_inventory.md` | Screenshot inventory table |
| `review/screenshot_manifest.md` | Per-slot manifest |
| `data/current/current_collection_reconciliation.json` | Structural reconciliation result |
| `review/current_collection_reconciliation.md` | Reconciliation report |
| `data/current/current_collection_pack_coverage.json` | Pack-source match results per entry |
| `data/exports/current_collection_pack_coverage.csv` | CSV version of coverage |
| `review/current_collection_pack_coverage.md` | Human-readable coverage report |
| `data/exports/current_pack_source_review.csv` | Fallback: manual confirmation for below-threshold entries |
| `data/exports/current_pack_source_review.json` | Machine-readable review data |
| `review/current_pack_source_review.md` | Per-card candidate tables (fallback/debugging reference) |
| `data/current/current_collection_pack_confirmations.json` | Applied confirmations (written by apply script) |
| `data/exports/deck_recommendation_validation.json` | Machine-readable deck validation |
| `review/deck_recommendation_validation.md` | Deck-by-deck validation report |

Additional active outputs (EV pipeline):

| File | Description |
|---|---|
| `data/current/screenshot_collection_alignment.json` | Screenshot slot → collection entry mapping |
| `data/current/pack_source_confidence_scores.json` | Per-entry confidence scores from automated matching |
| `data/current/resolved_pack_sources.json` | Final resolved pack sources (50 resolved, 9 unresolvable) |
| `data/current/pack_ev.json` | EV scores for all 24 packs |
| `data/current/pack_ev_readiness.json` | EV readiness status per pack |
| `data/current/inferred_pack_recommendations.json` | 5-metric pack ranking |
| `data/current/final_hourglass_spending_plan.json` | Conservative/moderate/aggressive scenarios |
| `data/current/in_app_rate_verification.json` | In-app verified pull rate records |
| `data/current/pull_rate_cross_check.json` | Cross-check verification results |
| `data/current/pending_pack_in_app_verification_checklist.json` | Packs awaiting in-app verification |

## 6. Current Pack-Source Coverage

**Important model alignment note:** PTCGP tracks cards by name + count, not by which pack they were pulled from. Same-rarity reprints of a card are grouped together in the game's UI and treated as interchangeable. Our EV model mirrors this exactly — `build_pack_ev.py` matches owned cards by normalized name only (`collection.get(nn, 0)`), so all 224 entries are EV-correct regardless of pack source resolution status. Pack-source resolution is **provenance metadata only**, not required for EV accuracy or deck recommendations.

| Metric | Value |
|---|---|
| Base entries with known source | **157/224 (70%)** — exact_match + unanimous_pack |
| Entries with resolved source | **207/224 (92%)** — +50 via resolve_ambiguous_pack_sources.py |
| Exact match | 108 entries |
| Unanimous pack | 49 entries |
| Newly resolved (resolve script) | 50 entries (41 user-confirmed + 9 automated) |
| Source-ambiguous (provenance gap only) | 9 entries — original set vs A4b reprint at identical rarity; PTCGP UI cannot distinguish |
| No match (Zygarde forms) | 3 entries — not in Limitless DB |
| Known trainer gap | 5 entries (Potion, X Speed, Red Card, Hand Scope, Pokédex) |

The 59 original ambiguous entries are now resolved as follows:
- 38 resolved via user confirmations (Limitless HP/attack analysis, 2026-05-15) stored in `data/current/current_collection_pack_confirmations.json`
- 8 resolved by automated passes (rarity_count inference, PASS 3)
- 1 resolved by PASS 2B (evo_chain re-run post-PASS 3): porygon2 → B1a/57 via porygon anchor
- 3 resolved by user in-game shiny check: blaziken→B3/208, frillish→B1/68, skrelp→B3/218
- Multiple candidates eliminated by pre-pass: A4a farfetch_d (HP mismatch); double_star/triple_star variants (rarity confirmed from in-game screenshots)
- 9 remaining are a provenance gap only — not an EV accuracy issue

Manual CSV review (`data/exports/current_pack_source_review.csv`) is a **fallback tool only**, used when:
- Automated confidence scores fall below threshold for a specific entry
- Conflicting high-confidence candidates cannot be resolved automatically
- The user explicitly requests manual confirmation

## 7. Confidence Threshold Policy

Automated matching is allowed when confidence is high enough and evidence is traceable.

Suggested thresholds:

| Tier | Confidence | Action |
|---|---|---|
| Auto-accept | ≥ 0.95 | Apply without manual review |
| Secondary evidence needed | 0.80 – 0.949 | Require corroborating signal (e.g. screenshot position, HP, type) |
| Below threshold — unresolved | < 0.80 | Flag for manual review or leave as unresolved |

Manual review is only required for:
- Entries with no candidate reaching the auto-accept threshold
- Conflicting high-confidence candidates that cannot be disambiguated
- Cards where `collection.json` and screenshot evidence disagree
- Cards with no reliable `pack_sources` candidate (e.g. Zygarde forms)

**Do not ask the user to manually confirm every ambiguous row by default.**

## 8. Current Automation Direction

Build tooling to align screenshot grid slots with `collection.json` entries.

- Use `collection.json` quantities as labels.
- Use screenshot position/order, card names, type/category metadata, HP/attack/ability, and `pack_sources` candidates as evidence.
- No OCR-heavy pipeline unless needed; prefer deterministic parsing from `collection.json` and the structural screenshot manifest first.
- If using vision/OCR later, treat it as validation evidence — not the canonical source.
- Generate confidence reports before applying any changes.
- Do not mutate `collection.json`; write generated mappings under `data/current/`.

Scripts built (do not rebuild):
- `scripts/build_screenshot_collection_alignment.py` — align screenshot slots to collection entries (DONE)
- `scripts/validate_screenshot_collection_alignment.py` — validate alignment output (DONE)
- `scripts/score_pack_source_confidence.py` — score each entry's best pack candidate (DONE)
- `scripts/build_pull_probability_model.py` — build pull probability model scaffold from pack_sources.json (DONE)
- `scripts/validate_pull_probability_model.py` — validate pull probability model output (DONE)

## 9. Current Recommendation Status

- Deck recommendations are currently **manual/prototype** via `deck-recommendations.jsx`.
- `validate_deck_recommendations.py` found **4 buildable decks** and **4 chase decks** (each 1 ex card short).
- Buildable: Mega Charizard Y ex, Victini + Darmanitan, Crobat Darkness Pivot, Staraptor Blitz.
- Chase (need 1 more ex each): Mega Venusaur ex, Incineroar ex, Zygarde ex, Magnezone ex.
- **Do not make final automated pack-opening recommendations yet.**

Current blockers before automated pack recommendations:
- Branch percentages: A4 (Ho-Oh/Lugia) user_in_app_verified + Pulsing Aura (B3) user_in_app_verified_plus_bulbapedia + 12 packs bulbapedia_branch_verified; rarity distributions remain third_party_verified. Model v0.6.0, source_status=third_party_verified_with_in_app_anchor
- 1 pack pending_verification (A4b Deluxe Pack: ex) — pack unavailable in app, 4 cards/pack, Offering Rates inaccessible
- 9 ambiguous pack-source entries still unresolved — EV-ready 207/224 (92%). PTCGP's card detail screen shows ALL same-rarity printings of a card together; it does not record which set a specific copy was pulled from. Remaining 9 are all original-set vs A4b (Deluxe Pack: ex) at identical rarity: moltres_ex (A1/A4b four_diamond), marowak_ex (A1/A4b four_diamond), farfetch_d (A1/A4b one_diamond), giovanni (A1/A4b two_diamond), sabrina (A1/A4b two_diamond), leaf (A1a/A4b two_diamond), cyrus (A2/A4b two_diamond), lillie (A3/A4b two_diamond), giant_cape (A2/A4b two_diamond). Functionally unresolvable by in-game means without pack opening history.
- Deck scoring model not built
- Optional meta/tier data not integrated

Manual CSV confirmation is **not** required before these phases can proceed.

## 10. Standard Validation Checklist

Run this before and after any meaningful change:

```bash
python3 scripts/validate_current_collection.py --expected-total 380
python3 scripts/normalize_current_collection.py
python3 scripts/current_collection_pack_coverage.py
python3 scripts/create_current_pack_review.py        # generates report — not a required manual step
python3 scripts/apply_current_pack_confirmations.py --dry-run   # only if CSV has been filled
python3 scripts/validate_deck_recommendations.py
python3 scripts/validate_pack_sources.py
python3 scripts/inventory_screenshots.py
python3 scripts/reconcile_current_collection_sources.py
```

## 11. Next Recommended Phase

Continue in-app verification for remaining packs to upgrade all packs from third_party_verified → verified confidence.

Completed phases (do not rebuild):
- Screenshot-to-collection alignment (`scripts/build_screenshot_collection_alignment.py`) — 224/224 entries, PASS
- Pack-source confidence scoring (`scripts/score_pack_source_confidence.py`) — 108 auto-accept, 49 secondary, 59 low, 8 unresolved, avg 0.8204, PASS
- Pull probability model scaffold + inferred rates (`scripts/build_pull_probability_model.py`) — 24 packs, slot_rates=inferred, PASS
- External pull rate lookup (`review/pull_probability_external_lookup.md`) — inferred rates from Game8 + corroborating sources, documented
- Pack EV calculator (`scripts/build_pack_ev.py`) — 24 packs ranked, 0 blocked, top pack: Paldean Wonders (ev=4.94, adj=4.20), PASS
- Inferred pack recommendation report (`scripts/generate_pack_recommendation_report.py`) — 5-metric ranking, chase-deck guide, 3 planning scenarios, PASS
- Pull rate cross-check (`review/pull_rate_cross_check.md`) — confirmed by ONE Esports (full match) + 3 other sources, confidence upgraded to third_party_verified, model_version=0.3.0, PASS
- Hourglass spending plan (`scripts/generate_hourglass_spending_plan.py`) — conservative/moderate/aggressive, 10-pack batches, stopping points, rerun checklist, PASS
- **Pulsing Aura (B3) in-app verification** — user verified three-branch model in-app 2026-05-13 (screenshots in ChatGPT, not in repo). Corrected rare pack rates (47.058/45.098/3.921/3.921). Schema updated, model rebuilt at v0.4.0, confidence=in_app_verified_partial. See `review/in_app_rate_verification.md`.
- **Bulbapedia branch-verified pack rates (v0.5.0)** — per-pack Bulbapedia offering rate pages confirm branch structure for 12 packs (bulbapedia_branch_verified) + Secluded Springs (A4a) unique three-branch + Mega Shine (B2b) four-branch. Pulsing Aura upgraded to user_in_app_verified_plus_bulbapedia. A-series packs confirmed two-branch; stale_model_warnings removed. Schema extended for four_branch and themed_rare. model_version=0.5.0, source_status=third_party_verified_with_in_app_anchor. PASS.
- **A4 (Wisdom of Sea and Sky) in-app verification (v0.6.0)** — Ho-Oh verified from in-repo screenshots (`Offering Rates screenshots/`, IMG_1692–IMG_1722, 2026-05-14). Three-branch model confirmed: regular=91.620%, rare=0.050%, regular+1=8.330% (matches A4a). Slot_6 confirmed: one_star=12.900%, three_diamond=87.100% (standard rarity, NOT shiny). Schema extended for slot_6 standard rarities. Lugia inferred from shared expansion. A4b (Deluxe Pack: ex) remains pending (pack unavailable, 4 cards/pack). model_version=0.6.0. EV pipeline rebuilt; Lugia now in top 5 (adj=3.72). PASS.
- **Ambiguous pack-source resolution (46/59, 2026-05-15)** — 38 confirmed via Limitless HP/attack analysis (user-confirmed, stored in `data/current/current_collection_pack_confirmations.json`), 8 via automated rarity_count inference. PASS 0 added to `resolve_ambiguous_pack_sources.py` to ingest user confirmations. EV-ready coverage: 157/224 → 203/224. 13 entries remain unresolved (same stats across candidates, or trainer rarity ambiguity). EV pipeline rebuilt. PASS.

Next steps in order:

1. **Continue in-app verification for other packs** — open PTCGP app → any pack → Pack details → Offering Rates. Priority: A4b once pack becomes available; then remaining third_party_verified packs. For each pack verified, update `pull_probability_model.json` and add a record to `data/current/in_app_rate_verification.json`.

2. **Remaining 9 entries are provenance-only gaps** — same-rarity reprints in both original set and A4b; PTCGP UI cannot distinguish which set a copy came from. Zero EV impact.

3. **Rebuild EV and reports after any update** — re-run `python3 scripts/resolve_ambiguous_pack_sources.py && python3 scripts/build_pack_ev.py && python3 scripts/generate_pack_recommendation_report.py && python3 scripts/generate_hourglass_spending_plan.py` after any rate or coverage change.

**Do not issue final pack-opening recommendations until all slot rates are verified in-app. Current status: third_party_verified_with_in_app_anchor (A4 user_in_app_verified; B3 user_in_app_verified_plus_bulbapedia; 12 packs bulbapedia_branch_verified; rarity distributions third_party_verified; A4b pending). `review/final_hourglass_spending_plan.md` is the current decision-support document for pack-opening planning.**

## 12. Anti-Overengineering Principle

Do not add infrastructure that does not measurably reduce manual confirmation work or improve recommendation quality.

- Do not build image matching or ML training pipelines.
- Do not chase perfect quantity OCR.
- Do not build complex scrapers unless trivially available.
- Do not add automation layers that require more debugging than manual work saves.
- External references are name/metadata hints only — they never write to `collection.json`.
- User verification is always required before applying confirmations.
- The shortest path to a validated collection DB and recommendation engine is always preferred.

## 13. Operating Principle

Act like a senior engineer maintaining a clean, durable repo.

Do not blindly follow narrow task wording if there is an obvious best-practice repo hygiene issue that should be addressed before moving forward. If a cleanup, validation, or organization step is clearly necessary to achieve the project goal safely, propose or perform it within the current phase if it does not violate hard constraints.

Expected proactive behavior:
- Remove redundant local artifacts once proven unnecessary.
- Avoid committing large binaries, screenshots, caches, zip files, generated temp files, or local IDE metadata.
- Keep scripts modular and reusable.
- Prefer deterministic, auditable workflows over ad hoc manual edits.
- Validate before and after meaningful changes.
- Stop before high-risk or scope-expanding work.

## 14. Critical Workflow Rule

Work in small phases.

- Do not attempt to complete the entire project in one run.
- Always stop after completing the exact requested phase.
- If the user asks for general improvement, proactively inspect the current phase for obvious repo hygiene issues.

## 15. Hard Stop Behavior

At the end of every response, stop and report only:

1. Files created or edited
2. What was completed
3. Any uncertainties or blockers
4. Validation results
5. Git status
6. The exact next recommended prompt

Do not continue into the next phase unless explicitly instructed.

## 16. Git and Repository Best Practices

Before each phase:
1. Run `git status`.
2. Confirm the current branch.
3. Confirm the working tree is clean.

During each phase:
1. Make focused, minimal changes.
2. Commit only logically related changes.
3. Do not mix unrelated work into one commit.
4. Do not commit screenshots, zip files, caches, temp files, virtual environments, local Claude config, or IDE metadata.
5. Do not force push.
6. Do not rewrite commit history unless explicitly asked.
7. Use descriptive commit messages.

After each phase:
1. Run relevant validation commands.
2. Run `git status`.
3. Commit if appropriate.
4. Push only when explicitly instructed.

Remote: `git@github.com:jackpendley/Pokemon-TCGP-DB.git`

If SSH authentication fails: check public key exists, check key is loaded in agent, test `ssh -T git@github.com`. Do not switch to HTTPS unless the user explicitly chooses that option.

## 17. Safe Operating Rules

- Use `python3`, not `python`.
- Never invent cards.
- Never invent pack sources or set/card numbers.
- Never change card quantities unless the user explicitly confirms.
- Do not mutate `collection.json` unless explicitly asked.
- Prefer generated files under `data/current/` for normalized outputs.
- Do not stage: raw HTML caches, image caches, `__pycache__`, `.DS_Store`, `node_modules`, `.env`, secrets, or large binary files.
- If validation fails, stop and document the blocker. Do not proceed.

## 18. Forbidden Behaviors

Do not:
- Claim the database is exact unless `collection.json` validates at 380 and all ambiguous entries are resolved or clearly flagged.
- Invent cards, pack sources, set codes, or card numbers.
- Change card quantities without explicit user confirmation.
- Mutate `collection.json` without explicit instruction.
- Ask the user to fill `current_pack_source_review.csv` as the default next task — manual CSV confirmation is a fallback, not the primary workflow.
- Commit large binaries, image files, or generated temp files.
- Force push.
- Switch remote authentication methods without user approval.
- Continue to the next phase without instruction.

## 19. Repo Hygiene / Cleanup Review

Every major development phase must include a repo cleanup and organization review before committing.

### Standing requirement

Run the following scan at the start or end of every major phase:

```bash
git status
find . -name "__pycache__" -o -name ".DS_Store" -o -name "*.tmp" -o -name "*.bak" -o -name "*~"
find . -maxdepth 3 -type f | sort
```

### What to look for

- `__pycache__/` directories and `.pyc` files
- `.DS_Store` and other OS metadata files
- Temporary scratch files, debug outputs, one-off exports
- Duplicate or redundant report files superseded by newer equivalents
- DRAFT files where confirmed/final versions exist
- TEMPLATE placeholder files after their pipeline is complete
- Empty directories
- Files that belong in `.gitignore` but are currently tracked
- Timestamp-only generated changes that add no information

### What to preserve — always

Never delete without explicit instruction:

- `collection.json` — active collection source of truth
- `data/reference/pack_sources.json` — pack source database
- `data/reference/pull_probability_model.json` — pull probability model
- `data/reference/external/external_card_reference.json` — used by resolve_ambiguous_pack_sources.py
- `screenshots/` — visual evidence for collection alignment
- All active generated outputs referenced by `README.md`, `CLAUDE.md`, `docs/`, `scripts/`, or current reports

### Decision rule for uncertain files

If unsure whether a file is safe to delete:

1. Check whether any active script, doc, or report references it by name.
2. Check whether a confirmed/final equivalent already exists (for DRAFT files).
3. If still uncertain — **keep the file** and add it to `review/repo_cleanup_audit.md` under "Deferred — human decision required."

Do not delete files that preserve reproducibility or pipeline provenance, even if they appear old.

### Cleanup documentation

All deletions must be documented in `review/repo_cleanup_audit.md`:
- File path
- Reason for deletion
- What supersedes it (if applicable)

Files kept after review must also be listed with the reason kept.

### Commit hygiene

- Do not stage timestamp-only generated changes (e.g. `screenshot_inventory.json` touched by a validation run) unless they are relevant to the current phase.
- Run `git status` and `git diff --stat` before every commit.
- Stage only files intentionally changed in the current phase.

### Audit record

The current cleanup audit lives at: `review/repo_cleanup_audit.md`

Update it whenever a new cleanup pass is performed. The standing workflow is documented here in section 19 — the audit file records the per-pass results.
