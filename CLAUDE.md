# Claude Code Project Instructions

## 1. Project Overview

Pokemon-TCGP-DB tracks the user's Pokémon TCG Pocket collection.

**Ultimate goal:** Support accurate, automated deck-building and pack-opening decisions.

- **Active collection:** `collection.json` — source of truth, JSONC format, strictly validated.
- **Primary sync path:** Pokemon Zone bookmarklet + `sync_collection.py --json-import` — no manual card entry.

Everything built must serve the collection tracking and recommendation goal. Do not add infrastructure that does not measurably improve recommendation quality or reduce manual work.

---

## 2. Current Validated State

| Item | Value |
|---|---|
| `collection.json` total | **582** (last_updated: 2026-05-20) |
| `collection.json` unique entries | **279** |
| `pack_sources.json` records | 3110 validated |
| EV pipeline status | **STALE** — last built against 584-card collection; must rebuild against 582 |
| Pull rate model version | **v0.6.0** |
| Pull rate data source | Pokemon Zone (source of truth); third_party cross-checked |
| Deck status | 4 buildable; 4 chase (1 ex short each) |
| Pack-source coverage | **207/224** (EV-ready); 9 permanently unresolvable |
| Known discrepancy | **RESOLVED 2026-05-20** — collection.json=582, PTCGP app=573; gap=9 real PZ-untracked cards (trainers, promos) |

The `sum(count)` across all entries in `collection.json` must always equal `meta.total_cards`. Validation enforces this strictly.

---

## 3. Collection Sync (Primary Update Path)

**Cloudflare note:** Pokemon Zone uses Cloudflare bot protection that blocks Python's `requests` library (TLS fingerprinting). The bookmarklet runs in the real browser and bypasses this entirely. `curl-cffi` (in `requirements.txt`) impersonates Chrome's TLS stack for stored-auth headless syncs.

---

**Option A — Browser bookmarklet (recommended, always works):**

Add this as a browser bookmark named "PZ Sync":

```
javascript:(async()=>{const b='https://www.pokemon-zone.com/api/';const[cr,or]=await Promise.all([fetch(b+'cards/search/'),fetch(b+'players/mine/')]);const cb=await cr.json();const ob=await or.json();const cat={};for(const i of(cb.data?.results??cb.data??[])){const m=(i.url||'').match(/\/cards\/[^/]+\/(\d+)\//);cat[i.cardDefKey]={name:i.name,set_code:i.expansionId||'',card_number:m?parseInt(m[1]):null}}const cards=[];for(const c of(ob.data?.cards??[])){if(!c.amount||c.amount<=0)continue;const info=cat[c.cardId];if(!info)continue;const sc=((c.expansionIds||[])[0]||info.set_code||'').toUpperCase();cards.push({cardName:info.name,setCode:sc,cardNumber:info.card_number,ownedCount:c.amount})}const bl=new Blob([JSON.stringify(cards,null,2)],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(bl);a.download='pz_collection.json';a.click();alert('Done: '+cards.length+' cards downloaded as pz_collection.json')})();
```

To install in Chrome: Bookmarks → Bookmark Manager (Cmd+Option+B) → three-dot menu → Add new bookmark → paste the full `javascript:` one-liner as the URL.

Usage:
1. Open `https://www.pokemon-zone.com/collection-tracker/` (must be logged in)
2. Click the "PZ Sync" bookmark — `pz_collection.json` downloads automatically
3. Run:
```bash
python3 scripts/sync_collection.py --json-import ~/Downloads/pz_collection.json --dry-run
python3 scripts/sync_collection.py --json-import ~/Downloads/pz_collection.json
```

---

**Option B — HAR import (reliable fallback):**
```bash
# 1. Open https://www.pokemon-zone.com/collection-tracker/ (logged in)
# 2. DevTools → Network tab → reload → wait for cards to load → Export HAR
python3 scripts/sync_collection.py --har-import ~/Downloads/www.pokemon-zone.com.har --dry-run
python3 scripts/sync_collection.py --har-import ~/Downloads/www.pokemon-zone.com.har
```

---

**Option C — Stored auth / headless:**
```bash
# First-time setup (paste a cURL from DevTools — saves auth to data/sync/.auth.json):
python3 scripts/sync_collection.py --curl-import
# pbpaste | python3 scripts/sync_collection.py --curl-import  (if Ctrl+D is fussy)

# Subsequent syncs (headless, curl-cffi Chrome TLS impersonation):
python3 scripts/sync_collection.py --dry-run
python3 scripts/sync_collection.py

# Re-run --curl-import when auth expires.
```

---

**Playwright fallback (Cloudflare CAPTCHA risk — use A/B instead):**
```bash
python3 scripts/sync_collection.py --login
python3 scripts/sync_collection.py --discover
```

**Known sync limitation:** Cards with identical HP across variants (e.g., both Grovyle variants at HP 80) cannot be disambiguated by the sync. Total count is correct across both entries; individual variant attribution may be wrong. Do not re-run sync to fix this.

**Review queue:** After sync, `data/sync/sync_review_queue.json` lists new cards and ambiguous matches requiring manual addition to `collection.json`. Resolve all items before next sync or use `--force`.

---

## 4. Scripts Reference

### Full pipeline

```bash
python3 scripts/run_recommendations.py             # sync → validate → EV → all reports
python3 scripts/run_recommendations.py --skip-sync # use current collection.json, skip sync
python3 scripts/run_recommendations.py --login     # Playwright re-auth before sync
```

### Collection validation

```bash
python3 scripts/validate_current_collection.py --expected-total 582
python3 scripts/normalize_current_collection.py
```

### EV pipeline (individual steps)

```bash
python3 scripts/resolve_ambiguous_pack_sources.py
python3 scripts/build_pack_ev.py
python3 scripts/generate_pack_recommendation_report.py
python3 scripts/generate_hourglass_spending_plan.py
```

### Pack-source resolution

```bash
python3 scripts/current_collection_pack_coverage.py
python3 scripts/score_pack_source_confidence.py
python3 scripts/resolve_ambiguous_pack_sources.py
python3 scripts/create_current_pack_review.py          # generates review CSV — not a required step
python3 scripts/apply_current_pack_confirmations.py --dry-run   # only after CSV is filled
python3 scripts/apply_current_pack_confirmations.py --apply
```

### Deck validation

```bash
python3 scripts/validate_deck_recommendations.py
```

### Pull probability model

```bash
python3 scripts/build_pull_probability_model.py
python3 scripts/validate_pull_probability_model.py
```

---

## 5. Generated Outputs

| File | Description |
|---|---|
| `data/current/collection_normalized.json` | Clean JSON, no comments, generated fields |
| `data/current/collection_summary.json` | Aggregated statistics |
| `data/current/current_collection_pack_coverage.json` | Pack-source match results per entry |
| `data/current/pack_source_confidence_scores.json` | Per-entry confidence scores |
| `data/current/resolved_pack_sources.json` | Final resolved pack sources |
| `data/current/current_collection_pack_confirmations.json` | Applied user confirmations |
| `data/current/pack_ev.json` | EV scores for all 24 packs |
| `data/current/pack_ev_readiness.json` | EV readiness status per pack |
| `data/current/inferred_pack_recommendations.json` | 5-metric pack ranking |
| `data/current/final_hourglass_spending_plan.json` | Conservative/moderate/aggressive scenarios |
| `data/current/in_app_rate_verification.json` | In-app verified pull rate records |
| `data/current/pull_rate_cross_check.json` | Cross-check verification results |
| `data/current/pending_pack_in_app_verification_checklist.json` | Packs awaiting in-app verification |
| `review/final_hourglass_spending_plan.md` | **Primary decision-support document** |
| `data/exports/current_pack_source_review.csv` | Fallback: manual confirmation for unresolved entries |

---

## 6. Pack-Source Coverage

**Key model note:** `build_pack_ev.py` matches owned cards by normalized name only. All 279 entries are EV-correct regardless of pack source resolution status. Pack-source resolution is provenance metadata — not required for EV accuracy.

| Status | Detail |
|---|---|
| Base known source | exact_match + unanimous_pack entries |
| Source-ambiguous (provenance gap only) | 9 entries — original set vs A4b at identical rarity; PTCGP UI cannot distinguish |
| No match | 3 Zygarde form entries — not in Limitless DB |
| Known trainer gap | Potion, X Speed, Red Card, Hand Scope, Pokédex |

The 9 remaining ambiguous entries are: moltres_ex, marowak_ex, farfetch_d, giovanni, sabrina, leaf, cyrus, lillie, giant_cape — all original set vs A4b (Deluxe Pack: ex) at identical rarity. Functionally unresolvable without pack opening history. Zero EV impact.

Manual CSV confirmation (`data/exports/current_pack_source_review.csv`) is a **fallback tool only** — not the default next step.

---

## 7. Pull Rate Data Source Policy

**Pokemon Zone is the source of truth for collection tracking and pull rate data.**

In-app PTCGP verification is no longer required. Pull rate data from Pokemon Zone, Bulbapedia,
or other third-party sources is sufficient. Only fall back to in-app verification if pull rate
data for a specific pack is inaccessible via Pokemon Zone or external resources.

| Pack group | Status |
|---|---|
| A4 Ho-Oh / Lugia | `user_in_app_verified` (v0.6.0, 2026-05-14) |
| B3 Pulsing Aura | `user_in_app_verified_plus_bulbapedia` (v0.4.0, 2026-05-13) |
| 12 packs | `bulbapedia_branch_verified` (v0.5.0) |
| A4b Deluxe Pack: ex | `pending` — rates not publicly available yet |
| Remaining packs | `third_party_verified` |

Overall model status: **`third_party_verified_with_in_app_anchor`**, model_version=0.6.0.

Current decision-support document: `review/final_hourglass_spending_plan.md`.

If pull rate data for a new pack becomes available on Pokemon Zone or Bulbapedia, update
`data/reference/pull_probability_model.json` and rebuild EV:
```bash
python3 scripts/build_pack_ev.py && python3 scripts/generate_pack_recommendation_report.py && python3 scripts/generate_hourglass_spending_plan.py
```

---

## 8. Recommendation Status

- **4 buildable decks:** Mega Charizard Y ex, Victini + Darmanitan, Crobat Darkness Pivot, Staraptor Blitz
- **4 chase decks (1 ex short each):** Mega Venusaur ex, Incineroar ex, Zygarde ex, Magnezone ex

**Do not issue final automated pack-opening recommendations yet.** Remaining blockers:
1. Deck scoring model not built — needed to weight EV toward packs containing chase cards
2. Optional meta/tier data not integrated

---

## 9. Standard Validation Checklist

Run before and after any meaningful collection change:

```bash
python3 scripts/validate_current_collection.py --expected-total 582
python3 scripts/normalize_current_collection.py
python3 scripts/current_collection_pack_coverage.py
python3 scripts/validate_pack_sources.py
python3 scripts/validate_deck_recommendations.py
```

---

## 10. Next Phase Roadmap

**Completed — do not rebuild:**
- Pokemon Zone bookmarklet + `--json-import` sync pipeline (2026-05-20)
- curl-cffi Chrome TLS impersonation for stored-auth headless syncs (2026-05-20)
- EV pipeline rebuilt against 584-card collection (2026-05-20); top pack: Paldean Wonders ev=4.94
- Inferred pack recommendation report (5-metric ranking, 3 planning scenarios)
- Hourglass spending plan (conservative/moderate/aggressive, 10-pack batches)
- Pull rate cross-check (ONE Esports + 3 sources, model_version=0.3.0)
- Pulsing Aura in-app verification (v0.4.0, 2026-05-13)
- Bulbapedia branch-verified pack rates (v0.5.0, 12 packs + A4a/B2b)
- A4 in-app verification (v0.6.0, 2026-05-14)
- Ambiguous pack-source resolution: 38 user-confirmed + 8 automated (2026-05-15)
- Collection sync: 25 count updates + 18 new card entries → 584 total (2026-05-20)
- Screenshot alignment pipeline removed; score_pack_source_confidence.py made optional (2026-05-20)
- Local crops/ and screenshots/ directories deleted (282 files, not tracked) (2026-05-20)
- Riolu Fighting Fast phantom corrected: count 5→3, total_cards 584→582 (2026-05-20)
- 582 vs 573 discrepancy resolved: gap=9 real PZ-untracked cards (trainers, promos) (2026-05-20)

**Next steps in priority order:**

1. **Rebuild EV pipeline** against corrected 582-card collection: `python3 scripts/run_recommendations.py --skip-sync`
2. **Upgrade sync_collection.py** to match by setCode+cardNumber via pack_sources.json lookup (eliminates all variant disambiguation failures)
3. **Build deck scoring model** — weight EV recommendations toward packs containing chase cards
4. **Final recommendations** — only after deck scoring built

---

## 11. Anti-Overengineering Principle

Do not add infrastructure that does not measurably reduce manual work or improve recommendation quality.

- Do not build image matching, OCR, or ML training pipelines.
- Do not build complex scrapers beyond what exists.
- Do not add automation layers that require more debugging than manual work saves.
- External references are name/metadata hints only — they never write to `collection.json`.
- The shortest path to a validated DB and recommendation engine is always preferred.

---

## 12. Operating Principle

Act like a senior engineer maintaining a clean, durable repo.

Expected proactive behavior:
- Remove redundant artifacts once proven unnecessary.
- Avoid committing binaries, caches, temp files, or OS metadata.
- Keep scripts modular and reusable.
- Prefer deterministic, auditable workflows.
- Validate before and after meaningful changes.
- Stop before high-risk or scope-expanding work.

---

## 13. Workflow Rules

Work in small phases. Do not attempt to complete the entire project in one run. Always stop after the exact requested phase.

**At the end of every response, report only:**
1. Files created or edited
2. What was completed
3. Uncertainties or blockers
4. Validation results
5. Git status
6. Exact next recommended prompt

Do not continue to the next phase without explicit instruction.

---

## 14. Git and Repository Practices

Before each phase: `git status` — confirm branch and clean working tree.

During each phase:
- Make focused, minimal changes.
- Commit only logically related changes.
- Do not commit screenshots, binaries, caches, `__pycache__`, `.DS_Store`, `.env`, or secrets.
- Do not force push. Do not rewrite history unless explicitly asked.
- Use descriptive commit messages.

After each phase: validate, then `git status`. Commit if appropriate. Push only when explicitly instructed.

Remote: `git@github.com:jackpendley/Pokemon-TCGP-DB.git`

If SSH fails: verify public key exists, key loaded in agent, test `ssh -T git@github.com`. Do not switch to HTTPS without user approval.

---

## 15. Repo Cleanup Policy

The screenshot-based pipeline has been fully removed. Future cleanup follows these rules.

**Standard cleanup procedure (run after any major phase):**
1. `git status` — confirm clean tree.
2. Check for local-only leftover directories (`crops/`, `screenshots/`, `ocr_temp/`, `.browser_session/`) — delete them. They are gitignored and have no repo value.
3. For tracked files: verify no active script references them before deleting.
4. Document all tracked-file deletions in `review/repo_cleanup_audit.md`.
5. Commit tracked-file removals as a standalone commit.

**Local directories to delete (gitignored, not tracked — delete without hesitation):**
- `crops/` — cropped card images from old OCR pipeline
- `screenshots/` — PTCGP app screenshots from old manual pipeline
- `ocr_temp/` — OCR scratch directory
- `.browser_session/` — Playwright session cache
- `data/reference/images/` — downloaded card images
- `data/reference/external/html_cache/` — scraped HTML cache

**Always preserve — never delete without explicit instruction:**
- `collection.json`
- `data/reference/pack_sources.json`
- `data/reference/pull_probability_model.json`
- `data/reference/external/external_card_reference.json`
- `data/current/current_collection_pack_confirmations.json`
- All active EV/recommendation outputs in `data/current/`
- `review/final_hourglass_spending_plan.md`

---

## 16. Safe Operating Rules

- Use `python3`, not `python`.
- Never invent cards, pack sources, set codes, or card numbers.
- Never change card quantities without explicit user confirmation.
- Do not mutate `collection.json` without explicit instruction.
- Prefer generated files under `data/current/` for outputs.
- Do not stage: `__pycache__`, `.DS_Store`, `.env`, secrets, binaries, image files.
- If validation fails, stop and document the blocker. Do not proceed.

---

## 17. Forbidden Behaviors

Do not:
- Claim the database is exact unless `collection.json` validates and all ambiguous entries are resolved or flagged.
- Invent cards, pack sources, set codes, or card numbers.
- Change card quantities without explicit confirmation.
- Mutate `collection.json` without explicit instruction.
- Ask the user to fill `current_pack_source_review.csv` as the default next task — it is a fallback.
- Commit large binaries, image files, or generated temp files.
- Force push.
- Switch remote auth methods without user approval.
- Continue to the next phase without instruction.

---

## 18. Context Window Management

Monitor context window usage throughout every session.

- At approximately **50% of the session context window**, pause and alert the user:
  > "Context window check: approximately 50% used. Generating handoff plan."
  Then auto-generate a self-contained handoff plan covering: current validated state, files changed (with status), uncommitted work, blockers, and the exact next recommended prompt.
- At approximately **80% of the session context window**, alert again and regenerate the handoff plan if significant work has been done since the 50% alert.
- The handoff plan must be complete enough that a fresh Claude Code session can resume without any prior context.

This rule exists to prevent silent degradation of accuracy as context fills, and to ensure development can be resumed efficiently.

---

## 19. collection.json vs PTCGP Discrepancy — RESOLVED

**Status (2026-05-20): RESOLVED.** collection.json=582, PTCGP app=573. Gap=9 real PZ-untracked cards.

**Root cause (identified and corrected):** The PZ sync preserves historical counts for cards it can't match (`missing_from_pz`). Direct comparison of PZ `sum(ownedCount)=573` vs PTCGP count=573 confirmed PZ data is exact. The 11-card gap from collection.json=584 was entirely due to 2 phantom Riolu (Fighting Fast art) copies from the pre-PZ screenshot pipeline.

**Phantom corrected:**
- Riolu Fighting Fast art (B3/79, one_diamond): count 5→3 (PZ shows 3, collection.json had 5 from screenshot era)

**Confirmed real — PZ can't track these 9 cards:**

| Name | Count | Reason PZ can't track |
|---|---|---|
| Zygarde 10% Forme | 1 | PROMO-B; PZ returns "Zygarde" not full form name |
| Zygarde 50% Forme | 3 | PROMO-B; same issue |
| Zygarde ex | 1 | PROMO-B |
| Moltres ex | 1 | A1 vs A4b ambiguity; both sets same rarity — unresolvable |
| Marowak ex | 1 | A1 vs A4b ambiguity; both sets same rarity — unresolvable |
| Mega Heracross ex | 1 | Not present in PZ records |
| Red Card | 2 | Trainer; not in PZ card tracking |
| X Speed | 2 | Trainer; not in PZ card tracking |
| Jigglypuff | 1 | Name mismatch in PZ |

Total PZ-untracked: 9 entries, 13 cards. collection.json=582 = 569 PZ-tracked + 13 PZ-untracked. ✓

**Remaining variant collision entries (confirmed owned — NOT phantom):**
- Bulbasaur ×2 variants: PZ total=5, collection.json total=5 — correct
- Mienfoo ×2 variants: PZ total=3, collection.json total=3 — correct
- Mienshao ×2 variants: PZ total=3, collection.json total=3 — correct
- Onix ×2 variants: PZ total=3, collection.json total=3 — correct

These appear in `missing_from_pz` because the sync uses name-only matching and one variant absorbs all PZ count. The fix is upgrading the sync to use setCode+cardNumber matching (see Section 10 next steps).

**Do not change collection.json quantities without explicit user confirmation.**
