# Pack Source Mapping Plan

## Why Pack Source Mapping Is Needed

Pack-opening recommendations require knowing which pack each card can be obtained from.
Without this mapping, it is impossible to answer "which pack should I open to improve
my collection?" in a principled way.

`cards.json` currently stores which cards the user owns and in what quantity.
It does NOT know which pack each card comes from. That gap is what
`data/reference/pack_sources.json` will fill.

---

## What pack_sources.json Must Contain

Each entry maps a specific card (identified by `set_code` + `card_number`) to the pack
it is obtainable from. The schema is defined in `data/reference/pack_sources.schema.json`.

Required fields per entry:
- `set_code` — e.g. `A4b`, `B1`, `B1a`
- `card_number` — integer card number within the set
- `card_name` — canonical name
- `pack_name` — which pack within the set (e.g. `Pikachu`, `Mewtwo`, `Charizard`, `All`)
- `expansion` — expansion name (e.g. `Celestial Guardians`)

Optional but important:
- `rarity` — rarity tier affects pull probability
- `is_promo` — true for promo cards not obtainable from standard packs
- `source_url` — Limitless TCG Pocket card page URL
- `confidence` — how reliable the mapping is

---

## Trusted Sources

Do not fabricate pack source data. Use only these trusted sources:

| Source | Use |
|---|---|
| `https://pocket.limitlesstcg.com/cards/<set_code>/<card_number>` | Primary — shows which pack a card is in |
| `https://pocket.limitlesstcg.com/cards` | Browse by set — list all cards in a set |
| `https://game8.co/games/Pokemon-TCG-Pocket/archives/482685` | Supplemental — complete card list with pack info |

---

## How to Avoid Guessing

- Only record pack assignments from verified source pages.
- If a card appears in multiple packs or the source is ambiguous, set `confidence: "low"` and add a note.
- If a card is promo-only or not obtainable from standard packs, set `is_promo: true`.
- Do not infer pack from set alone — different packs within the same set contain different cards.

---

## Known Sets in the Database

From `data/reference/external/external_card_reference.json`, the following set codes appear:

| Set Code | Description |
|---|---|
| A4b | Celestial Guardians (second expansion) |
| B1 | Space-Time Smackdown |
| B1a | Triumphant Light |
| B2 | Shining Revelry |
| B2a | Extradimensional Crisis |
| B2b | Unknown / pending |
| B3 | Unknown / pending |

Pack names within each set vary. Confirm from Limitless before recording.

---

## Proposed Build Steps

1. **Run validate_pack_sources.py** to confirm pack_sources.json does not exist yet (expected):
   ```bash
   python3 scripts/validate_pack_sources.py
   ```

2. **Retrieve set index from Limitless** for each known set code (A4b, B1, B1a, B2, B2a, B2b, B3).

3. **For each card in the collection** (from `data/reference/external/external_card_reference.json`),
   extract the pack name field.

4. **Build pack_sources.json** using the schema.

5. **Validate**:
   ```bash
   python3 scripts/validate_pack_sources.py
   ```

6. **Cross-reference with cards.json** — verify that cards in the user's collection
   have pack source entries available.

7. **Commit** only the clean structured JSON.

---

## What Comes After

Once `pack_sources.json` exists and validates:

1. Build a script `scripts/recommend_packs.py` that:
   - Reads `cards.json` for owned cards and quantities
   - Reads `pack_sources.json` for pack-to-card mappings
   - Computes which packs contain the most cards the user does not own
   - Accounts for rarity-weighted pull probabilities if available
   - Outputs a ranked pack recommendation with justification

2. Do NOT run this recommendation script until `pack_sources.json` exists and
   `data/reference/meta_decks.json` is built for deck-context recommendations.

---

## Hard Constraints

- Do not fabricate pack source data.
- Do not guess which pack a card comes from.
- Do not commit raw HTML or downloaded images.
- Commit only clean structured JSON.
- User verification is required before pack recommendations are generated.
