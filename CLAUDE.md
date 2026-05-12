# Claude Code Project Instructions

## 1. Project Overview

Pokemon-TCGP-DB tracks the user's Pokémon TCG Pocket collection.

The active goal is to support accurate deck-building and pack-opening decisions.

The project has two baselines:

- **Active current collection baseline:** `collection.json` — 380 cards, 224 unique entries, manually authored, validated.
- **Historical screenshot-ingestion baseline:** `cards.json` — 329 cards, 211 entries, screenshot pipeline artifact. Preserved for provenance only.

Everything added to this project must serve the collection tracking and recommendation goal.

## 2. Source of Truth

- `collection.json` is the **active source of truth** for all new recommendation work.
- `data/current/collection_normalized.json` is the generated machine-readable normalized version.
- `screenshots/` is the **visual evidence source** for training, alignment, and confidence validation.
- For current work, `collection.json` + `screenshots/` together are sufficient to train and validate automated matching and confidence scoring.
- `cards.json` is **historical/provenance only**. Do not use it for current recommendations.
- Do not try to reconcile `cards.json` up to 380 by guessing.
- Do not continue the old skipped multi-value confirmation workflow unless explicitly requested by the user.

## 3. Current Validated State

| Item | Status |
|---|---|
| `collection.json` total | **380 validated ✅** |
| `collection.json` unique entries | 224 |
| `cards.json` total (historical) | **329 validated ✅** |
| `pack_sources.json` records | **3110 validated ✅** |
| Screenshots | 26 cropped grid images, `IMG_1556–IMG_1581` |
| Screenshot slots | 232 (25 × 9 standard + 1 × 7 final) |
| Structural reconciliation | **PASS** — 232 slots ≥ 224 unique entries |
| Pack-source coverage | **157/224 entries resolved (70%)** |

Screenshots are local user-provided evidence under `screenshots/`. They are gitignored. Do not delete them.

## 4. Important Scripts

### Active collection

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

### Automated confidence scoring (next phase to build)

```bash
python3 scripts/build_screenshot_collection_alignment.py
python3 scripts/score_pack_source_confidence.py
```

### Deck validation

```bash
python3 scripts/validate_deck_recommendations.py
```

### Historical baseline (provenance only)

```bash
python3 scripts/validate_cards.py --expected-total 329
python3 scripts/validate_pack_sources.py
python3 scripts/owned_pack_coverage.py
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

Planned automated confidence outputs (to be built):

| File | Description |
|---|---|
| `data/current/screenshot_collection_alignment.json` | Screenshot slot → collection entry mapping |
| `data/current/pack_source_confidence_scores.json` | Per-entry confidence scores from automated matching |
| `review/automated_confidence_readiness.md` | Human-readable confidence report |

## 6. Current Pack-Source Coverage

| Metric | Value |
|---|---|
| Entries resolved | **157/224 (70%)** |
| Exact match | 108 entries |
| Unanimous pack | 49 entries |
| Unresolved total | 67 entries |
| Ambiguous cross-set | 59 entries |
| No match (Zygarde forms) | 3 entries — not in Limitless DB |
| Known trainer gap | 5 entries (Potion, X Speed, Red Card, Hand Scope, Pokédex) |

These 67 unresolved entries are the **target set for automated confidence scoring and screenshot/collection alignment** — not a mandate for manual CSV review.

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

Next scripts to build:
- `scripts/build_screenshot_collection_alignment.py` — align screenshot slots to collection entries
- `scripts/score_pack_source_confidence.py` — score each entry's best pack candidate
- These produce: `data/current/screenshot_collection_alignment.json`, `data/current/pack_source_confidence_scores.json`, `review/automated_confidence_readiness.md`

## 9. Current Recommendation Status

- Deck recommendations are currently **manual/prototype** via `deck-recommendations.jsx`.
- `validate_deck_recommendations.py` found **4 buildable decks** and **4 chase decks** (each 1 ex card short).
- Buildable: Mega Charizard Y ex, Victini + Darmanitan, Crobat Darkness Pivot, Staraptor Blitz.
- Chase (need 1 more ex each): Mega Venusaur ex, Incineroar ex, Zygarde ex, Magnezone ex.
- **Do not make final automated pack-opening recommendations yet.**

Current blockers before automated pack recommendations:
- Automated pack-source confidence model not built
- Screenshot-to-collection alignment not built
- Pull probability model not built
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
python3 scripts/validate_cards.py --expected-total 329
python3 scripts/inventory_screenshots.py
python3 scripts/reconcile_current_collection_sources.py
```

## 11. Next Recommended Phase

Build automated screenshot-to-collection alignment and pack-source confidence scoring.

Concretely:

1. Create `scripts/build_screenshot_collection_alignment.py`
   - Inputs: `data/current/screenshot_manifest.json`, `data/current/collection_normalized.json`
   - Output: `data/current/screenshot_collection_alignment.json` — slot → entry mapping with confidence

2. Create `scripts/score_pack_source_confidence.py`
   - Inputs: `data/current/collection_normalized.json`, `data/reference/pack_sources.json`, alignment output
   - Output: `data/current/pack_source_confidence_scores.json` — per-entry best candidate + score
   - Output: `review/automated_confidence_readiness.md` — readable confidence report

3. Only flag entries below threshold (< 0.80) as needing manual review.

**Do not require the user to fill `current_pack_source_review.csv` before this phase proceeds.**

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
- Preserve `cards.json` and old batch files as historical provenance.
- Do not stage: raw HTML caches, image caches, `__pycache__`, `.DS_Store`, `node_modules`, `.env`, secrets, or large binary files.
- If validation fails, stop and document the blocker. Do not proceed.

## 18. Forbidden Behaviors

Do not:
- Claim the database is exact unless `collection.json` validates at 380 and all ambiguous entries are resolved or clearly flagged.
- Use `cards.json` for current recommendations.
- Invent cards, pack sources, set codes, or card numbers.
- Change card quantities without explicit user confirmation.
- Mutate `collection.json` without explicit instruction.
- Ask the user to fill `current_pack_source_review.csv` as the default next task — manual CSV confirmation is a fallback, not the primary workflow.
- Continue the old 329-card skipped multi-value confirmation workflow unless explicitly requested.
- Commit large binaries, image files, or generated temp files.
- Force push.
- Switch remote authentication methods without user approval.
- Continue to the next phase without instruction.
