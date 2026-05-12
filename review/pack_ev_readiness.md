# Pack EV Readiness Report

Generated: 2026-05-12  
Pull probability model version: 0.2.0  
Source status: inferred

---

## Overall Status: PARTIALLY READY

Slot-level pull rates have been populated for all 24 packs from trusted external sources
(confidence=inferred). Aggregate `rarity_probabilities` are still null.

EV calculations can proceed with `inferred` rates with explicit uncertainty disclosure.
To fully unblock, verify slot_rates against in-app Offering Rates and populate
`rarity_probabilities` for at least one pack.

---

## Readiness by Requirement

| Requirement | Status | Details |
|---|---|---|
| Pull probability model scaffold | ✅ Ready | `data/reference/pull_probability_model.json` (24 packs) |
| Slot rates for all 24 packs | ✅ Inferred | `slot_rates` populated from trusted third-party sources |
| Pull rates verified from in-app screen | ⚠️ Unverified | confidence=inferred — user must confirm in PTCGP app |
| rarity_probabilities (aggregate rates) | ❌ Null | Requires in-app verification or computation from slot_rates |
| Pack-source coverage (EV-ready entries) | ✅ Partially ready | 157/224 entries have confirmed or high-confidence pack assignment |
| Pack-source coverage (remaining entries) | ❌ Blocked | 67 entries unresolved (59 low-confidence + 8 no-match) |
| Collection quantity data | ✅ Ready | `collection.json` — 380 cards, 224 unique entries, validated |

---

## Inferred Slot Rates Source

| Field | Value |
|---|---|
| Primary source | Game8 PTCGP offering rates guide |
| Source URL | https://game8.co/games/Pokemon-TCG-Pocket/archives/482685 |
| Accessed | 2026-05-12 |
| Corroborating sources | ShackNews, cgmagonline |
| Rate universality | Confirmed by cgmagonline (rates same across Space-Time Smackdown and Triumphant Light) |
| Shiny card note | Rates apply to non-shiny packs; pack_sources.json has no shiny rarities |
| See full lookup | `review/pull_probability_external_lookup.md` |

---

## Inferred Slot Rates (Regular Pack — 99.95% of openings)

| Slot | Rarity | Rate |
|---|---|---|
| 1–3 | one_diamond (◆) | 100% each |
| 4 | two_diamond (◆◆) | 90.000% |
| 4 | three_diamond (◆◆◆) | 5.000% |
| 4 | four_diamond (◆◆◆◆) | 1.666% |
| 4 | one_star (☆) | 2.572% |
| 4 | double_star (☆☆) | 0.500% |
| 4 | triple_star (☆☆☆) | 0.222% |
| 4 | crown (♕) | 0.040% |
| 5 | two_diamond (◆◆) | 60.000% |
| 5 | three_diamond (◆◆◆) | 20.000% |
| 5 | four_diamond (◆◆◆◆) | 6.664% |
| 5 | one_star (☆) | 10.288% |
| 5 | double_star (☆☆) | 2.000% |
| 5 | triple_star (☆☆☆) | 0.888% |
| 5 | crown (♕) | 0.160% |

Rare/God Pack (0.05% of openings) — all 5 slots: one_star=40%, double_star=50%, triple_star=5%, crown=5%

---

## Collection EV Readiness by Tier

| Tier | Entries | Status | Notes |
|---|---|---|---|
| Auto-accept (≥ 0.95) | 108 | ✅ EV-ready (inferred rates) | Exact match — confirmed pack source |
| Secondary evidence (0.80–0.949) | 49 | ✅ EV-ready (inferred rates) | Unanimous pack — high-confidence |
| Low confidence (0.50–0.799) | 59 | ❌ Pack-source blocked | Ambiguous cross-expansion |
| Unresolved (< 0.50) | 8 | ❌ No pack source | 3 Zygarde forms + 5 common trainers |
| **Total** | **224** | — | — |

157 of 224 entries (70%) have confirmed pack assignments and inferred slot rates.
EV calculation is possible for these 157 entries at inferred confidence.

---

## Packs Covered by EV-Ready Collection Entries

| Pack | Expansion |
|---|---|
| Crimson Blaze | Crimson Blaze |
| Deluxe Pack: ex | Deluxe Pack: ex |
| Fantastical Parade | Fantastical Parade |
| Mega Altaria | Mega Rising |
| Mega Blaziken | Mega Rising |
| Mega Gyarados | Mega Rising |
| Mega Shine | Mega Shine |
| Mewtwo | Genetic Apex |
| Pulsing Aura | Pulsing Aura |
| Shining Revelry | Shining Revelry |

14 packs have no collection entries at EV-ready confidence.

---

## Pull Probability Model Coverage (24 packs)

| Expansion | Pack | Pool Size | Slot Rates | Confidence |
|---|---|---|---|---|
| Celestial Guardians | Lunala | 140 | ✅ inferred | inferred |
| Celestial Guardians | Solgaleo | 140 | ✅ inferred | inferred |
| Crimson Blaze | Crimson Blaze | 103 | ✅ inferred | inferred |
| Deluxe Pack: ex | Deluxe Pack: ex | 379 | ✅ inferred | inferred |
| Eevee Grove | Eevee Grove | 107 | ✅ inferred | inferred |
| Extradimensional Crisis | Extradimensional Crisis | 103 | ✅ inferred | inferred |
| Fantastical Parade | Fantastical Parade | 234 | ✅ inferred | inferred |
| Genetic Apex | Charizard | 127 | ✅ inferred | inferred |
| Genetic Apex | Mewtwo | 126 | ✅ inferred | inferred |
| Genetic Apex | Pikachu | 127 | ✅ inferred | inferred |
| Mega Rising | Mega Altaria | 139 | ✅ inferred | inferred |
| Mega Rising | Mega Blaziken | 139 | ✅ inferred | inferred |
| Mega Rising | Mega Gyarados | 139 | ✅ inferred | inferred |
| Mega Shine | Mega Shine | 117 | ✅ inferred | inferred |
| Mythical Island | Mew | 86 | ✅ inferred | inferred |
| Paldean Wonders | Paldean Wonders | 131 | ✅ inferred | inferred |
| Pulsing Aura | Pulsing Aura | 234 | ✅ inferred | inferred |
| Secluded Springs | Secluded Springs | 105 | ✅ inferred | inferred |
| Shining Revelry | Shining Revelry | 111 | ✅ inferred | inferred |
| Space-Time Smackdown | Dialga | 126 | ✅ inferred | inferred |
| Space-Time Smackdown | Palkia | 126 | ✅ inferred | inferred |
| Triumphant Light | Arceus | 96 | ✅ inferred | inferred |
| Wisdom of Sea and Sky | Ho-Oh | 136 | ✅ inferred | inferred |
| Wisdom of Sea and Sky | Lugia | 136 | ✅ inferred | inferred |

---

## How to Fully Unblock EV Calculation

### Step 1 — Verify inferred rates from in-app Offering Rates

Open the PTCGP app → any pack → Pack details → Offering Rates.
Compare the in-app values to `slot_rates` in `data/reference/pull_probability_model.json`.
If they match, set `confidence="verified"` and populate `rarity_probabilities`.
Run `python3 scripts/validate_pull_probability_model.py` to confirm.

Even verifying one pack would confirm rate universality for all 24.

### Step 2 — Resolve 59 ambiguous cross-expansion entries

See `data/exports/current_pack_source_review.csv` for per-entry candidate lists.
This expands EV-ready coverage from 157 to up to 216/224 entries.

### Step 3 — Build EV calculator

Once slot_rates are verified, build a script that:
- For each owned card, looks up its pack, rarity, and N(cards of that rarity in pool)
- Computes P(specific card per pack) = slot_probability / N
- Sums per-pack EV across all unowned cards
- Ranks packs by marginal EV per pack opened

---

## Generated Files

| File | Description |
|---|---|
| `data/reference/pull_probability_model.json` | Pull probability model (24 packs, inferred slot rates) |
| `data/reference/pull_probability_model.schema.json` | JSON Schema for the model |
| `review/pull_probability_model.md` | Human-readable pack pool summary + slot rate tables |
| `review/pull_probability_external_lookup.md` | External lookup results and source documentation |
| `data/current/pack_ev_readiness.json` | Machine-readable readiness (this report) |
