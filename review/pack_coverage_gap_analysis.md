# Pack Coverage Gap Analysis

Generated: 2026-05-10

## Current Coverage Baseline

| Outcome | Count | Description |
|---|---|---|
| Exact match (set_code + card_number) | 93 | High confidence — fully resolved |
| Name-agreed (single global match) | 36 | Medium confidence — one match in pack_sources |
| Name-ambiguous (multiple packs) | 62 | Unresolved — multiple packs possible |
| No match | 20 | Not in current reference |
| **Total owned entries** | **211** | |

---

## Blocker Type Analysis

### Blocker 1: Missing set_code / card_number (118 cards)

The metadata enrichment phase only assigned `set_code` + `card_number` to cards with a
**unique** name match in the external reference. Cards with multiple matches across sets
(e.g., Bulbasaur in A4b and B1a) were not given `set_code` or `card_number`.

The 36 name-agreed cards and 62 name-ambiguous cards all fall into this group.

**Resolution paths:**
- For the 36 name-agreed: all name matches agree on the same pack → safe to assign source_packs (Rule D).
- For the 62 name-ambiguous: visual confirmation or external set data would be required.

### Blocker 2: Card name appears in multiple sets with different packs (62 cards)

Examples:

| Card Name | Sets | Packs |
|---|---|---|
| Blaziken | B1, B3 | Mega Blaziken, Pulsing Aura |
| Bulbasaur | A4b, B1a | Deluxe Pack: ex, Crimson Blaze |
| Magneton | A4b, B1a, B3 | Deluxe Pack: ex, Crimson Blaze, Pulsing Aura |
| Sandslash | B1, B1a, B2 | None (shared), Crimson Blaze, Fantastical Parade |
| Furfrou | B1, B1a, B2, B2b, B3 | Multiple packs |

**Root cause:** B3 (Pulsing Aura) contains many reprints of cards from earlier sets.
B1a, B2, B2a, B2b also contain reprints. Without knowing which print the user owns
(set_code + card_number), these cannot be resolved from name alone.

**Why source_reference URL cannot disambiguate:** The enrichment script assigned
`source_reference` to the first match in the external reference (sorted by set_code
alphabetically). This is not the actual owned card's print — it's an arbitrary selection
from the ambiguous matches. Using this URL for disambiguation would silently guess wrong.

**Resolution paths:**
- Cannot safely resolve from name alone.
- Would require the user to provide set_code or card_number from the app.
- Future: if screenshots are re-taken with card detail visible, set can be confirmed.

### Blocker 3: Name mismatch — is_ex cards without "ex" suffix (2 cards)

Cards marked `is_ex=True` in cards.json but whose `card_name` does not include "ex":

| Card Name in cards.json | is_ex | Expected Reference Name |
|---|---|---|
| Marowak | True | Marowak ex |
| Incineroar | True | Incineroar ex |

**Marowak:** "Marowak ex" exists in pack_sources with ONE match (A4b #196, Deluxe Pack: ex).
→ **Safely resolvable** with medium confidence.

**Incineroar:** "Incineroar ex" exists in pack_sources with TWO matches (A4b and B1, different packs).
→ **NOT safely resolvable** — ambiguous pack.

### Blocker 4: Cards not in current reference sets (18 cards)

Our reference covers only sets A4b, B1, B1a, B2, B2a, B2b, B3 (all relatively recent).
The following owned cards do not appear in any of these sets:

**Trainer/Item/Supporter cards (likely from older sets A1–A4):**
- Giovanni, Sabrina, Leaf, Lillie (trainers)
- Potion, X Speed, Hand Scope, Pokédex, Poké Ball, Red Card (items)
- Professor's Research (supporter)

**Pokémon (not in A4b–B3):**
- Venonat, Rattata, Raticate (likely A1/A2)
- Eelektross (unconfirmed set)
- Zygarde (2 entries — unconfirmed set)

**Resolution paths:**
- Would require expanding pack_sources.json to cover older sets (A1, A1a, A2, A2a, A3, A3a, A4, A4a).
- Source: https://pocket.limitlesstcg.com/cards for older set codes.
- This is a separate phase of work.

### Blocker 5: Name variant ambiguity — form names (2 cards)

| Card Name | Variants in reference | Issue |
|---|---|---|
| Urshifu | Rapid Strike Urshifu, Single Strike Urshifu | Form unknown from name alone |

**Resolution path:** Requires visual confirmation from screenshot — the card art distinguishes forms.

### Blocker 6: Within-set pack ambiguity (1 card)

| Card Name | Set | Packs |
|---|---|---|
| Flame Patch | B1 | Mega Blaziken (card #217), shared/null (card #331) |

Flame Patch appears twice in B1 — once as a pack-specific card and once as a higher-rarity
shared card. Cannot determine which version without card number.

---

## Safe Resolution Summary

| Rule | Cards | Strategy |
|---|---|---|
| Rule D — single global name match | 36 | Add source_packs at medium confidence |
| is_ex suffix rule (Marowak only) | 1 | Try name + " ex", 1 unique match → medium confidence |
| **Total safely resolvable** | **37** | |

---

## Remaining After Resolution

| Category | Count |
|---|---|
| Exact (pre-existing) | 93 |
| Newly resolved (Rule D + is_ex) | 37 |
| Still ambiguous (multi-pack names) | 61 |
| Still no match (not in reference) | 18 |
| Unresolvable without data (Incineroar, Urshifu, Flame Patch) | 3 |

---

## Fields Needed to Resolve Remaining Ambiguous Cards

| Blocker | Needed field | Source |
|---|---|---|
| Multi-set reprints | set_code + card_number | App screenshots with card detail, or user inspection |
| Cards from older sets | Extended pack_sources (A1–A4) | Fetch from Limitless for older set codes |
| Form variants (Urshifu) | Visual confirmation | Screenshot review |
| Within-set pack ambiguity | card_number | App card detail |

---

## Next Recommended Steps

1. **Immediate (this phase):** Apply Rule D (36 name-agreed) and Marowak is_ex rule (1 card).
2. **Next data phase:** Expand pack_sources.json to cover A1, A1a, A2, A2a, A3, A3a, A4, A4a.
   This would likely resolve all 18 no-match cards and potentially some ambiguous ones.
3. **Future:** Build pull probability model and pack recommendation engine after coverage improves.
