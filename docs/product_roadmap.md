# Product Roadmap

## Goal

Build a practical Pokémon TCG Pocket collection database that:
1. Tracks owned cards and quantities accurately
2. Tracks sets and variants for collection progress
3. Enables AI to give precise pack-opening recommendations
4. Enables AI to recommend current meta decks based on owned cards
5. Supports future updates via screenshot uploads with minimal manual work

---

## Phase 1 — Finish Collection Ingestion (current)

**Status: In progress — batches 001–006 complete (screenshots 1–6 of 24)**

- Continue confirmed batch workflow for screenshots IMG_1530–IMG_1547 (batches 007–024)
- Use `scripts/create_screenshot_review_package.py` to generate per-screenshot review packages
- User visually confirms card names and quantities from contact sheets and app
- Convert confirmed CSV to batch JSON with `scripts/create_batch_from_confirmation.py`
- Validate each batch immediately with `scripts/validate_batch.py`
- Do not require perfect OCR — reference hints reduce manual work, but human confirmation remains required

**Tools:**
```bash
python3 scripts/create_screenshot_review_package.py --screenshot IMG_1530.PNG
# → review/screenshot_reviews/IMG_1530_review.md
# → review/confirmed/IMG_1530_confirmed_TEMPLATE.csv

# After filling in template:
python3 scripts/create_batch_from_confirmation.py \
  --input review/confirmed/IMG_1530_confirmed.csv \
  --screenshot IMG_1530.PNG \
  --output batches/cards_batch_007.json
python3 scripts/validate_batch.py batches/cards_batch_007.json
```

---

## Phase 2 — Merge Batches into cards.json

**Trigger: all 24 batches exist and validate**

- Run `python3 scripts/merge_batches.py`
- Validate total quantity equals 331: `python3 scripts/validate_cards.py --expected-total 331`
- Enrich card metadata from external references (type, stage, rarity, is_ex)
- Preserve `special_type=unknown` for any cards that could not be visually confirmed
- Resolve remaining `needs_review=true` entries manually
- Export to CSV: `python3 scripts/export_cards_csv.py`

---

## Phase 3 — Collection Analytics

**Trigger: cards.json validated**

Analytics to generate:
- Set/pack completion percentage (cards owned vs. cards in set)
- Duplicate card counts and trade value
- Missing cards by set/pack, sorted by rarity and meta relevance
- Type coverage (Grass, Fire, Water, etc.)
- EX/Mega/special-card inventory
- Solo battle stage readiness (basic Pokémon coverage)

Output: `collection_analytics.md` and/or machine-readable JSON

---

## Phase 4 — Pack Recommendation Engine

**Trigger: Phase 3 complete**

- Use collection gaps + pack contents + user goals
- Prioritize: meta deck completion > type coverage > collection progress
- Apply hourglass budget constraints (current: 143 spendable = 1× 10-pack + 23 leftover)
- Score each available pack by expected value given current collection
- Recommend whether to open, wait, or target a specific pack

Output: `pack_recommendations.md`

---

## Phase 5 — Meta Deck Recommendation Engine

**Trigger: Phase 4 complete**

- Source current tournament decklists from Limitless TCG Pocket
- Source deck guides from Game8 (tier lists, beginner decks, meta analysis)
- Compare owned cards against full 20-card decklists
- Rank decks by: closest-to-complete, meta power level, pack efficiency to finish
- Include: which packs are needed to complete each shortlisted deck
- Account for missing staples (Giovanni, Sabrina, etc.)

Deck candidates to evaluate:
- Fire / Mega Charizard Y ex (B1a)
- Mega Charizard X ex
- Suicune ex / Greninja
- Mega Sceptile ex (B3)
- Mega Lucario ex
- Mega Altaria ex
- Mega Absol ex
- Any archetype clearly supported by confirmed cards.json

Output: `deck_recommendations.md`

---

## Phase 6 — Future Update Workflow

**Trigger: Initial cards.json validated; new pack opened**

1. User takes new screenshots after opening packs
2. Pipeline generates review package for each new screenshot
3. User confirms changes (new cards or quantity increments)
4. `create_batch_from_confirmation.py` creates a delta batch
5. Updater script increments quantities / adds new card entries
6. Validator checks new total and schema integrity

Goal: less than 5 minutes of manual work per pack opening.

---

## What Is Permanently Postponed

| Item | Reason |
|---|---|
| Image matching / template matching | Requires custom ML; too expensive relative to benefit |
| Perfect quantity OCR | PTCGP chip style defeats Tesseract; manual read is faster |
| Heavy ML training on card images | Far exceeds scope; human confirmation is more accurate |
| Full Game8 scraper | Hub-and-spoke structure requires significant engineering; Limitless covers structured data |
| Official Pokémon.com TCG integration | Not Pocket-specific; low marginal value |

---

## Anti-Overengineering Principles

- Do not add infrastructure unless it measurably reduces human confirmation work or improves recommendation quality
- Quantity always comes from human reading of the app — no automated substitutes
- External references are name/metadata hints only; they never write to cards.json
- User verification is always required before any batch file is created
- Stop before any step that is harder than "copy template, fill in names and quantities, run one script"
