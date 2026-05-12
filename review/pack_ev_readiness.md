# Pack EV Readiness Report

Generated: 2026-05-11  
Pull probability model version: 0.1.0-scaffold  
Source status: scaffold_only

---

## Overall Status: BLOCKED

Pack EV calculations cannot be run until pull probability rates are populated from the
official in-app Offering Rates. All `rarity_probabilities` in the model are currently null.

---

## Readiness by Requirement

| Requirement | Status | Details |
|---|---|---|
| Pull probability model scaffold | ✅ Ready | `data/reference/pull_probability_model.json` (24 packs) |
| Pull probability rates (rarity tier rates) | ❌ Blocked | All null — must come from in-app Offering Rates |
| Pack-source coverage (EV-ready entries) | ✅ Partially ready | 157/224 entries have confirmed or high-confidence pack assignment |
| Pack-source coverage (remaining entries) | ❌ Blocked | 67 entries unresolved (59 low-confidence + 8 no-match) |
| Collection quantity data | ✅ Ready | `collection.json` — 380 cards, 224 unique entries, validated |

---

## Collection EV Readiness by Tier

| Tier | Entries | Status | Notes |
|---|---|---|---|
| Auto-accept (≥ 0.95) | 108 | ✅ EV-ready (pending rates) | Exact match — confirmed pack source |
| Secondary evidence (0.80–0.949) | 49 | ✅ EV-ready (pending rates) | Unanimous pack — high-confidence |
| Low confidence (0.50–0.799) | 59 | ❌ Pack-source blocked | Ambiguous cross-expansion — needs disambiguation |
| Unresolved (< 0.50) | 8 | ❌ No pack source | 3 Zygarde forms + 5 common trainers not in Limitless DB |
| **Total** | **224** | — | — |

157 of 224 entries (70%) are ready for EV calculation once pull rates are populated.

---

## Packs Covered by EV-Ready Collection Entries

10 of 24 modeled packs have at least one collection entry assigned to them at EV-ready confidence.

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

14 packs have no collection entries at EV-ready confidence (those packs can still be evaluated
by rarity tier once pull rates are available, but no owned-card intersection can be computed).

---

## Pull Probability Model Coverage (24 packs)

| Expansion | Pack | Pool Size | Rates Status |
|---|---|---|---|
| Celestial Guardians | Lunala | 140 | ❌ null |
| Celestial Guardians | Solgaleo | 140 | ❌ null |
| Crimson Blaze | Crimson Blaze | 103 | ❌ null |
| Deluxe Pack: ex | Deluxe Pack: ex | 379 | ❌ null |
| Eevee Grove | Eevee Grove | 107 | ❌ null |
| Extradimensional Crisis | Extradimensional Crisis | 103 | ❌ null |
| Fantastical Parade | Fantastical Parade | 234 | ❌ null |
| Genetic Apex | Charizard | 127 | ❌ null |
| Genetic Apex | Mewtwo | 126 | ❌ null |
| Genetic Apex | Pikachu | 127 | ❌ null |
| Mega Rising | Mega Altaria | 139 | ❌ null |
| Mega Rising | Mega Blaziken | 139 | ❌ null |
| Mega Rising | Mega Gyarados | 139 | ❌ null |
| Mega Shine | Mega Shine | 117 | ❌ null |
| Mythical Island | Mew | 86 | ❌ null |
| Paldean Wonders | Paldean Wonders | 131 | ❌ null |
| Pulsing Aura | Pulsing Aura | 234 | ❌ null |
| Secluded Springs | Secluded Springs | 105 | ❌ null |
| Shining Revelry | Shining Revelry | 111 | ❌ null |
| Space-Time Smackdown | Dialga | 126 | ❌ null |
| Space-Time Smackdown | Palkia | 126 | ❌ null |
| Triumphant Light | Arceus | 96 | ❌ null |
| Wisdom of Sea and Sky | Ho-Oh | 136 | ❌ null |
| Wisdom of Sea and Sky | Lugia | 136 | ❌ null |

---

## How to Unblock EV Calculation

### Step 1 — Populate pull rates from in-app Offering Rates

In the PTCGP app, open each pack → Pack details → Offering Rates.  
Record the per-rarity pull rates for each pack.  
Update `data/reference/pull_probability_model.json` `rarity_probabilities` fields.  
Re-run `python3 scripts/validate_pull_probability_model.py` to confirm rates are valid.

This is the only trusted source. Do not estimate or copy rates from unofficial sites.

### Step 2 — Resolve 59 ambiguous cross-expansion entries

Entries at low confidence (0.50–0.799) appear in multiple expansions with no way to
distinguish which version is owned without card number confirmation (OCR or manual lookup).  
See `data/exports/current_pack_source_review.csv` for per-entry candidate lists.

### Step 3 — Build EV calculator

Once Steps 1–2 are complete, build a script that:
- For each owned card, looks up its pack and rarity
- Multiplies the rarity pull rate by the card weight in the pack pool (1/n cards of that rarity)
- Sums the EV contribution per pack across all owned missing cards
- Ranks packs by marginal EV per pack opened

---

## Generated Files

| File | Description |
|---|---|
| `data/reference/pull_probability_model.json` | Pull probability model (24 packs, all rates null) |
| `data/reference/pull_probability_model.schema.json` | JSON Schema for the model |
| `review/pull_probability_model.md` | Human-readable pack pool summary |
| `data/current/pack_ev_readiness.json` | Machine-readable readiness (this report) |
