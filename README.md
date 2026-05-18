# Pokemon TCG Pocket Collection Database

Tracks the user's Pokémon TCG Pocket card collection and generates pack-opening and deck-building recommendations.

## Collection Baseline

`collection.json` is the **active collection source of truth** as of 2026-05-11.

| File | Cards | Status |
|---|---|---|
| `collection.json` | **380 verified ✅** (224 unique entries) | Active — use for all recommendations |
| `data/reference/pack_sources.json` | 3110 records | Card-to-pack mappings (all sets A1–B3) |
| `data/reference/pull_probability_model.json` | 24 packs | Pull rates, v0.6.0 |
| `screenshots/` | 26 files (IMG_1556–IMG_1581) | Cropped 3×3 grid screenshots, gitignored |

Pack-source coverage: **207/224 entries (92%) EV-ready**. 9 entries are permanently unresolvable (same-rarity reprints in original set + A4b — PTCGP UI groups them together).

## Validate and Normalize

```bash
python3 scripts/validate_current_collection.py --expected-total 380
python3 scripts/normalize_current_collection.py
python3 scripts/current_collection_pack_coverage.py
python3 scripts/validate_deck_recommendations.py
python3 scripts/validate_pack_sources.py
```

## EV Pipeline

Ranks all 24 packs by expected new-card value. Top pack: **Paldean Wonders** (adj EV=4.20).

```bash
python3 scripts/resolve_ambiguous_pack_sources.py
python3 scripts/build_pack_ev.py
python3 scripts/generate_pack_recommendation_report.py
python3 scripts/generate_hourglass_spending_plan.py
```

Outputs: `review/inferred_pack_recommendations.md`, `review/final_hourglass_spending_plan.md`, `review/pack_ev.md`

## Pull Probability Model

Model v0.6.0 — `source_status=third_party_verified_with_in_app_anchor`.

- A4 (Ho-Oh/Lugia): `user_in_app_verified`
- B3 (Pulsing Aura): `user_in_app_verified_plus_bulbapedia`
- 12 packs: `bulbapedia_branch_verified`
- 8 packs: `third_party_verified` (two-branch)
- 1 pack: `pending_verification` (A4b — unavailable in app)

```bash
python3 scripts/build_pull_probability_model.py
python3 scripts/validate_pull_probability_model.py
```

See `review/in_app_rate_verification.md` and `review/pull_rate_cross_check.md` for verification history.

## Pack-Source Confidence

```bash
python3 scripts/build_screenshot_collection_alignment.py
python3 scripts/validate_screenshot_collection_alignment.py
python3 scripts/score_pack_source_confidence.py
python3 scripts/resolve_ambiguous_pack_sources.py
```

Outputs: `data/current/pack_source_confidence_scores.json`, `review/pack_source_confidence_scores.md`, `data/current/resolved_pack_sources.json`

Manual confirmation (fallback only, when automated confidence < threshold):

```bash
python3 scripts/create_current_pack_review.py
python3 scripts/apply_current_pack_confirmations.py --dry-run
python3 scripts/apply_current_pack_confirmations.py --apply
```

## Deck Recommendations

4 buildable decks, 4 chase decks (1 ex card short each). See `review/deck_recommendation_validation.md`.

```bash
python3 scripts/validate_deck_recommendations.py
```

Prototype UI: `deck-recommendations.jsx`

## Pack Source Mapping

```bash
python3 scripts/build_pack_sources.py
python3 scripts/validate_pack_sources.py
```

Pack name rules:
- Multi-pack expansions (A1, A2, A3, A4, B1): `high` confidence for pack-specific cards; `medium` for shared-pool cards
- Single-pack expansions (A1a, A2a, A2b, A3a, A3b, A4a, A4b, B1a, B2, B2a, B2b, B3): `medium` — expansion name is the pack name
- `pack_name=null` = shared across all packs in that expansion

## Screenshots

`screenshots/` is gitignored — local only. Re-generate inventory:

```bash
python3 scripts/inventory_screenshots.py
python3 scripts/reconcile_current_collection_sources.py
```

Outputs: `review/screenshot_inventory.md`, `review/screenshot_manifest.md`

## Repo Hygiene

Cleanup policy: `CLAUDE.md` section 19. Per-pass results: `review/repo_cleanup_audit.md`.

## Key Reports

| Report | Description |
|---|---|
| `review/final_hourglass_spending_plan.md` | Current decision-support document for pack-opening |
| `review/inferred_pack_recommendations.md` | 5-metric pack ranking with chase-deck guide |
| `review/pack_ev.md` | EV scores for all 24 packs |
| `review/deck_recommendation_validation.md` | Deck-by-deck buildability report |
| `review/in_app_rate_verification.md` | In-app pull rate verification log |
| `review/pull_rate_cross_check.md` | Third-party source cross-check |
| `review/resolved_pack_sources.md` | Final pack-source resolution summary |

See `docs/product_roadmap.md` for the full project roadmap.
