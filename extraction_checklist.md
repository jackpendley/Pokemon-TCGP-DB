# One-Screenshot Extraction Checklist

This checklist defines exactly how to process one screenshot into one batch file.
Follow every step in order. Do not skip steps or combine multiple screenshots.

---

## Core Rules (from CLAUDE.md)

- Process **exactly one screenshot per prompt**.
- Do **not** edit `cards.json` during extraction.
- Do **not** merge batches during extraction.
- Do **not** guess. If uncertain, use `"unknown"` and `needs_review: true`.
- Do **not** infer fields that are not visible or confidently known from the card art.
- Preserve same-name variants as **separate entries** unless you are certain they are the same app card.

---

## Step-by-Step Extraction Process

### Step 1 — Identify the screenshot

Record the exact filename as `source_screenshot`.

```
source_screenshot: "IMG_1524.PNG"
```

Do not abbreviate or alter the filename.

---

### Step 2 — Map the visible card grid

The Pokémon TCG Pocket app displays cards in a grid.

Scan the screenshot top-to-bottom, left-to-right.

Count visible rows and columns.

Note any partially visible cards at the top or bottom edge.

---

### Step 3 — For each card in the grid

Work through every card in reading order (left to right, top to bottom).

Record all fields below.

#### `source_row` and `source_column`

See the **Card Position Convention** section.

#### `card_name`

Record the name exactly as printed on the card.

If the name is not readable, use `"unknown"`.

Do not guess names based on art alone.

#### `quantity`

Record the number shown in the app grid for that card slot.

If the quantity is not clearly readable:
- Set `quantity: 0`
- Set `confidence: "low"`
- Set `needs_review: true`
- Set `review_reason` to explain what is unclear

#### `card_category`

Use one of: `Pokemon`, `Trainer`, `Item`, `Supporter`, `Tool`, `Stadium`, `Fossil`, `Unknown`

If the category is not certain, use `"Unknown"`.

#### `pokemon_type`

Use one of: `Grass`, `Fire`, `Water`, `Lightning`, `Psychic`, `Fighting`, `Darkness`, `Metal`, `Dragon`, `Colorless`, `None`, `Unknown`

Set to `"None"` for Trainer cards.

Set to `"Unknown"` if the energy type is not visible or confidently recognizable from the card art.

You may use well-known type associations (e.g., Charizard = Fire) only when the card name is fully confirmed and the art clearly supports it. When in doubt, use `"Unknown"`.

#### `stage`

Use one of: `Basic`, `Stage 1`, `Stage 2`, `None`, `Unknown`

Set to `"None"` for Trainer cards.

Set to `"Unknown"` if the stage is not visible on the card.

#### `hp`

Record the HP value if it is visible on the card.

If HP is not visible or not applicable, set `hp: null`.

#### `is_ex`

Set to `true` if the card name contains "ex" or the card is visually identified as an ex card.

Set to `false` otherwise.

#### `special_type`

See the **Special Type Decision Rules** section.

#### `rarity`

Record the rarity symbol or text as it appears on the card (e.g., `"1 diamond"`, `"2 diamond"`, `"1 star"`, `"crown"`).

If the rarity is not visible, use `"unknown"`.

Do not guess rarity from the card name alone.

#### `set_or_pack`

Record the set or pack name if visible.

If not visible, use `"unknown"`.

#### `variant_notes`

Leave empty `""` for normal cards with no ambiguity.

Use this field to note:
- Partial visibility ("partial visible card — top row cut off")
- Visual differences that distinguish this entry from a same-name variant
- Any other detail that helps identify this specific card in the app

#### `confidence`

- `"high"` — card name, quantity, and special_type are all clearly readable
- `"medium"` — card name and quantity are clear but some metadata is uncertain
- `"low"` — card name, quantity, or variant identity is uncertain

Every `"low"` confidence entry must have `needs_review: true`.

#### `needs_review`

Set to `true` if:
- Confidence is `"low"`
- The card name is uncertain
- The quantity is unreadable
- The special type is ambiguous
- The card appears to be a special variant but the exact type is unclear
- The card is only partially visible and not fully identifiable

#### `review_reason`

Required and non-empty when `needs_review` is `true`.

Describe specifically what is unclear and what information would resolve it.

Example: `"Card partially cut off at bottom of screen; quantity not readable. Provide a crop of the bottom edge."`

---

### Step 4 — Build the batch file

Save the extracted cards to:

```
batches/cards_batch_001.json   ← first screenshot
batches/cards_batch_002.json   ← second screenshot
batches/cards_batch_003.json   ← etc.
```

The file must be a valid JSON array of card objects matching the canonical schema.

Use `batches/cards_batch_TEMPLATE.json` as a field reference.

---

### Step 5 — Validate the batch

Run:

```bash
python3 scripts/validate_batch.py batches/cards_batch_001.json
```

Fix any validation errors before proceeding.

---

### Step 6 — Log ambiguous cards

For every card with `needs_review: true` or `confidence: "low"`:

Add an entry to `ambiguous_cards.md` with:
- Source screenshot filename
- Approximate row and column
- Suspected card name
- Suspected quantity
- Why it is ambiguous
- What crop or screenshot the user should provide to confirm it

---

### Step 7 — Stop

Do not process the next screenshot.

Do not merge batches.

Do not edit `cards.json`.

Report what was extracted and wait for the next instruction.

---

## Card Position Convention

Grid positions are recorded as 1-indexed integers.

| Field | Definition |
|-------|-----------|
| `source_row` | Row number counting from the **top** of the visible grid, starting at 1 |
| `source_column` | Column number counting from the **left** of the visible grid, starting at 1 |

**Example:** The card in the second row, third column from the left is:
```json
"source_row": 2,
"source_column": 3
```

### Partially Visible Cards

If a card is only partially visible at the top or bottom edge of the screenshot:

- Still record it as an entry.
- Add `"partial visible card"` to `variant_notes`.
- Set confidence no higher than `"medium"` — unless the card is fully identifiable despite the crop, which is rare.
- If the card name or quantity is not readable due to the crop, set confidence to `"low"` and `needs_review: true`.

---

## Special Type Decision Rules

Assign `special_type` based on visual appearance. When in doubt, use `"unknown"` and set `needs_review: true`.

### `normal`

The default type for standard cards.

**Visually:** Standard card frame, no extended art, no special border treatment. The illustration is contained within the card frame in the typical layout.

Use this when none of the special types below apply.

---

### `full_art`

**Visually:** The card artwork extends to or very near the card edges, with minimal or no standard frame border around the illustration. The card name and stats are still present but overlaid on the art.

Do not confuse with `illustration_rare` or `special_art` — full art cards have edge-to-edge artwork but standard card text layout.

---

### `illustration_rare`

**Visually:** A card with a large, elaborate illustration that extends significantly beyond the typical frame area, with a distinctive artistic treatment. Often has a textured or special background.

In Pokémon TCG Pocket, these are marked with a specific rarity indicator. If visible, note it in `rarity`.

---

### `special_art`

**Visually:** A card with a uniquely rendered illustration — different artist style, full-scene art, or a design that clearly distinguishes it from the standard version of the same card. Often has a special rarity symbol.

Typically appears as the "SAR" (Special Art Rare) or equivalent tier in TCG Pocket.

---

### `immersive`

**Visually:** A card with an art style that creates a full-frame or panoramic scene, often appearing as if the card extends into a wider world. May have animated or premium visual effects in-app.

These are among the rarest cards and have a very distinctive look distinct from standard full-art cards.

---

### `crown_gold`

**Visually:** A card with a gold/yellow crown rarity symbol and distinctive golden or metallic border/treatment. Highest rarity tier in Pokémon TCG Pocket. Usually the most visually ornate card in a set.

---

### `shiny`

**Visually:** A card showing a Shiny (alternate color) Pokémon — the Pokémon's color scheme differs from its standard version. In TCG Pocket, shiny cards may have a specific rarity indicator.

Note: Shiny refers specifically to the alternate-colored Pokémon, not to foil or holographic effects.

---

### `rainbow`

**Visually:** A card with a rainbow-colored foil or gradient treatment across the entire card surface, distinct from standard holographic effects.

---

### `promo`

**Visually:** A card with a PROMO stamp, special promotional border, or promotional markings. Often obtained through events, promotions, or special distributions rather than packs.

---

### `special_trainer`

**Visually:** A Trainer card (Item, Supporter, Tool, or Stadium) with a special art treatment — full art, illustration rare, or other premium variant. Use `card_category` to record the trainer subtype, and `special_trainer` here to denote the premium art treatment.

---

### `alternate_art`

**Visually:** A card that has the same name and function as a standard card but features a completely different illustration — different scene, different composition, or different art style. Common in collaboration sets or as bonus variants.

Distinct from `special_art` in that the alternate art may not be a higher-rarity treatment — it could be a different canonical art version at the same rarity.

---

### `unknown`

Use when:
- The card is too small or blurry to identify the treatment
- The card is partially cut off
- Multiple special types could apply and you cannot determine which
- You are not confident enough to assign any specific type

Always pair `"unknown"` with `needs_review: true` and a clear `review_reason`.

---

## ID Construction Quick Reference

Format: `normalized_card_name_special_type_set_or_pack_vN`

Rules:
- Lowercase only
- Replace spaces and punctuation with underscores
- Remove consecutive underscores
- Use `unknown` for unknown set/pack
- Use `v1` by default; increment only when needed to distinguish variants within the same batch or after merging

Examples:
```
bulbasaur_normal_unknown_v1
charizard_ex_special_art_genetic_apex_v1
misty_special_trainer_genetic_apex_v1
```
