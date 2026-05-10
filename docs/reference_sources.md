# External Reference Sources

## Purpose

External references improve card-name fuzzy matching, is_ex detection, and metadata hints
(type, stage, rarity) during the screenshot extraction workflow.  They do **not** replace
human confirmation of card names and quantities — those always come from the app screenshots.

---

## Limitless TCG Pocket (Primary)

**URL:** https://pocket.limitlesstcg.com/cards

**Use:**
- Structured card/set/rarity data (name, type, HP, stage, is_ex, rarity)
- Set code list and card index
- Individual card detail pages: `/cards/{set}/{number}`
- Tournament/deck data for future meta-deck recommendations

**Script:** `scripts/build_external_reference.py --source limitless`

**Output:**
- `data/reference/external/external_card_reference.json` — parsed card objects
- `data/reference/external/external_card_names.txt` — one name per line
- `data/reference/external/reference_source_report.md`

**Caching:** HTML pages are cached locally in `data/reference/external/html_cache/` (gitignored).
Use `--use-cache` to skip network fetches; `--refresh` to re-fetch everything.

**Rate limiting:** 0.5 s between page requests.  No public API — site is scraped politely.

**Coverage:** Sets B3, B2x, B1x scraped; A-series sets require additional run.
Re-run with `--use-cache` to avoid re-fetching cached pages.

---

## Game8 (Supplemental)

**URL:** https://game8.co/games/Pokemon-TCG-Pocket/

**Key pages:**
- All cards: https://game8.co/games/Pokemon-TCG-Pocket/archives/482685
- EX cards: https://game8.co/games/Pokemon-TCG-Pocket/archives/474856
- Full art / special cards: https://game8.co/games/Pokemon-TCG-Pocket/archives/483152

**Use:**
- Supplemental card list cross-reference
- EX card identification
- Special/full-art card identification
- Guide and meta-tier information

**Status:** Not yet scraped.  Documented for future integration.
Game8 uses a hub-and-spoke page structure requiring linked-page crawling.
Recommend using Limitless as the primary structured reference; use Game8 for
special-type coverage gaps or when Limitless is incomplete.

---

## What External References Provide

| Field | From reference | From screenshots |
|---|---|---|
| `card_name` hints | Yes (fuzzy match) | User confirms |
| `is_ex` hint | Yes (name pattern + Limitless data) | User confirms |
| `pokemon_type` | Yes | Ignored during extraction |
| `stage` | Yes | Ignored during extraction |
| `hp` | Yes | Ignored during extraction |
| `rarity` hint | Yes | Ignored during extraction |
| `special_type` hint | Partial (from rarity) | User confirms |
| `quantity` | **Never** | Always from screenshot chip |
| `set_or_pack` | Yes | User may correct |

**Quantity always comes from the app screenshot.** References are name/metadata hints only.

---

## Workflow

```
External reference build (run once, use --use-cache after):
    python3 scripts/build_external_reference.py --source limitless

Merge external into main reference:
    python3 scripts/build_card_reference.py --seed data/reference/manual_card_names_seed.txt --merge-external

Check reference coverage:
    python3 scripts/evaluate_reference_coverage.py

Proceed to OCR matching:
    python3 scripts/match_ocr_to_reference.py
```

---

## Planned Future Use

- **Meta deck recommendations:** Limitless tournament/deck pages (`/tournaments`, `/decks`) can
  provide current meta tier lists once `cards.json` is populated.
- **Image matching:** Not currently implemented. External card images from Limitless could
  support template matching as a fallback when OCR is ambiguous.
- **A-series coverage:** Complete the Limitless scrape for A1–A4 sets to cover the full PTCGP
  card pool.
