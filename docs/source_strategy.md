# External Source Strategy

## Source Roles

### User Screenshots (Source of Truth for Ownership)

**What it provides:** Actual owned cards and quantities.

User screenshots are the only authoritative source for:
- Which cards the user owns
- How many copies of each card the user owns

No external source substitutes for this. Quantity is always read from the app's quantity chip by a human.

---

### Limitless TCG Pocket (Primary Structured Reference)

**URL:** https://pocket.limitlesstcg.com/
**Cards/sets:** https://pocket.limitlesstcg.com/cards

**What it provides:**
- Structured card name index (current: 771 unique names from B1/B2/B3 sets; A-series pending)
- Card metadata: type, HP, stage, rarity, is_ex
- Set/pack metadata: which set a card belongs to
- Card number within set (useful for deduplication and collection tracking)

**Future use:**
- Tournament decklist data from `/tournaments` for meta deck recommendations
- Top deck rankings for Phase 5

**Script:** `scripts/build_external_reference.py --source limitless`

**Coverage gap:** A1–A4b not yet scraped. Resume with `--use-cache` to add ~1000+ additional cards.

---

### Pokémon GO Hub Pocket Database (Supplemental Reference)

**URL:** https://pocket.pokemongohub.net/en

**What it provides:**
- Alternative card database with pack-level organization
- Useful for cross-referencing pack contents when recommending which pack to open
- Type, rarity, and collection-progress metadata

**Current status:** Not yet integrated. Recommended for Phase 4 (pack recommendations).

---

### Game8 (Supplemental Guide Source)

**URL:** https://game8.co/games/Pokemon-TCG-Pocket/

**Key pages:**
- All cards: https://game8.co/games/Pokemon-TCG-Pocket/archives/482685
- EX cards: https://game8.co/games/Pokemon-TCG-Pocket/archives/474856
- Full art / special cards: https://game8.co/games/Pokemon-TCG-Pocket/archives/483152

**What it provides:**
- EX card and special card lists (supplemental validation)
- Deck guides and tier lists for meta recommendations
- Beginner progression guides
- Human-readable explanations useful for recommendation output

**Current status:** Not yet scraped. Recommend integrating at Phase 5 (meta decks) for tier lists.
Game8's hub-and-spoke HTML structure requires crawling; not worth building now.

---

### Official Pokémon Card Database

**URL:** https://www.pokemon.com/us/pokemon-tcg/pokemon-cards

**What it provides:**
- Official TCG card database (not Pocket-specific)
- May include Pocket promo cards

**Current status:** Not integrated. Low priority — Limitless is more Pocket-specific and better structured.
Use only if Limitless has coverage gaps for specific promo or special cards.

---

## What Each Source Contributes to the Pipeline

| Field | Source | Notes |
|---|---|---|
| `card_name` (hint) | Limitless, Game8 | Fuzzy matched against OCR; human confirms |
| `card_name` (confirmed) | User screenshot | Human reads card name from app |
| `quantity` | **User screenshot only** | Never from reference |
| `is_ex` | Name pattern + Limitless | Reliable for explicit "ex" in name; human confirms edge cases |
| `card_category` | Limitless | Item/Supporter/Pokemon/etc. from detail page |
| `pokemon_type` | Limitless | Grass/Fire/Water/etc. |
| `stage` | Limitless | Basic/Stage 1/Stage 2 |
| `hp` | Limitless | Numeric HP from detail page |
| `rarity` | Limitless | Diamond/star rarity from prints section |
| `special_type` | Conservative inference from rarity | Crown→crown_gold, triple_star→illustration_rare; human confirms |
| `set_or_pack` | Limitless set_code | A1, B3, etc. |
| `meta relevance` | Limitless tournaments + Game8 | Phase 5 only |
| `pack recommendation` | GO Hub + Limitless set contents | Phase 4 only |

---

## Integration Priority

| Priority | Source | Phase |
|---|---|---|
| ✅ Done | Limitless B/B-series scrape (1,171 cards) | Active |
| Next | Complete Limitless A-series scrape | Phase 1 |
| Phase 4 | Pokémon GO Hub pack metadata | Pack recommendations |
| Phase 5 | Limitless tournament decks | Meta deck recommendations |
| Phase 5 | Game8 tier lists and deck guides | Meta deck recommendations |
| Optional | Official Pokémon.com | Promo card gaps only |
