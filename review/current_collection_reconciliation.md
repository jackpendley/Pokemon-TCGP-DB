# Current Collection Reconciliation

**Status:** ✅ VALIDATED at 380

## Collection Summary

| Field | Value |
|---|---|
| Source | `collection.json` |
| Meta total_cards | 380 |
| Actual quantity sum | 380 |
| Unique entries | 224 |
| Validates at 380 | Yes ✅ |

## Screenshot Summary

| Field | Value |
|---|---|
| Screenshot files | 26 |
| Total card slots | 232 |
| Slots vs unique entries | 232 slots / 224 entries |

## Structural Analysis

- Collection total quantity (380) matches meta.total_cards (380). ✅
- Collection total is exactly 380. ✅
- Screenshots: 26 files, 232 expected card slots.
- Structural note: collection has 224 unique entries (card tiles) and 380 total quantity (sum of counts). Screenshots represent unique card tiles, not 380 separate images.
- Screenshot slots (232) >= unique collection entries (224). Structurally consistent. ✅

## Interpretation

The screenshots show the Pokémon TCG Pocket app's card collection grid.
Each visible tile represents a **unique card entry** with a quantity chip showing how many copies are owned.
The collection has 224 unique entries summing to 380 total card copies.
The screenshots provide 232 expected tile slots across 26 files.

To verify individual cards, a future phase can either:
- Use OCR to read card names and quantities from screenshots
- Or manually fill in the blank fields in `review/screenshot_manifest.md`

Pack and deck recommendations can use `collection.json` as the source of truth,
with screenshots as visual provenance.
