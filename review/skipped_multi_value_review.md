# Skipped Multi-Value Confirmations — Manual Review

Generated: 2026-05-11 01:40 UTC

These **10** cards were skipped during `apply_ambiguous_confirmations.py` because the filled CSV contained multi-value set codes (e.g. `A1/A4b`) or comma-separated card numbers (e.g. `226, 353`). Each needs a single definitive answer before it can be applied.

---

## How to Fill the CSV

Open `data/exports/skipped_multi_value_review.csv` and fill the right-hand columns.

### If you own exactly ONE version of this card:

```
confirmed_action = apply_single
confirmed_set_code = <set code from options, e.g. B3>
confirmed_card_number = <card number, e.g. 89>
confirmed_quantity_for_this_version = (leave blank — uses existing quantity)
```

### If you own TWO distinct versions (different set or card number):

```
confirmed_action = split_record
split_1_set_code = <first version set code>
split_1_card_number = <first version card number>
split_1_quantity = <how many of this version you own>
split_2_set_code = <second version set code>
split_2_card_number = <second version card number>
split_2_quantity = <how many of this version>
```

**Split quantities must add up to the current total quantity.** If the current quantity is 1 and you genuinely own both versions, set 1+1 and note this in `user_notes` — the apply script will require `--allow-quantity-increase` to handle that case.

### If you're unsure:

```
confirmed_action = leave_unresolved
user_notes = <why you're unsure>
```

After filling, run:
```
python3 scripts/apply_skipped_multi_value_confirmations.py --dry-run
python3 scripts/apply_skipped_multi_value_confirmations.py --apply
```

---

## How to Find the Card Number in Your App

1. Open Pokémon TCG Pocket.
2. Go to **Collection** → find the card by name.
3. Tap the card to open its detail view.
4. Look at the bottom of the card for the **set indicator icon** and **card number** (e.g. `42/234` means card 42 in a 234-card set).
5. Match the set size to identify the expansion:

| Set | Expansion | Cards |
|---|---|---|
| A1 | Genetic Apex | 286 |
| A1a | Mythical Island | 86 |
| A2 | Space-Time Smackdown | 207 |
| A3 | Celestial Guardians | 239 |
| A4b | Deluxe Pack: ex | 379 |
| B1a | Crimson Blaze | 103 |

---

## Cards Requiring Review

### Marowak

- **owned_card_id**: `marowak_unknown_unknown_v1`
- **Quantity**: 1  |  **is_ex**: True  |  **rarity**: unknown  |  **special_type**: unknown
- **Screenshot**: IMG_1525.PNG
- **Likely issue**: ex_mismatch — card has is_ex=True but name lookup matched regular Marowak. Candidates below are for Marowak ex. Prior fill (A1/#226, A4b/#353) was incorrect (those are Lt. Surge and Red). Check card number in app — likely A1/#153 (Mewtwo, 4-diamond) or A4b/#196.

**All candidates:**

| Set | Card # | Pack | Rarity |
|---|---|---|---|
| A1 | 153 | Mewtwo | four_diamond |
| A1 | 264 | Mewtwo | double_star |
| A3 | 236 | Lunala | double_star |
| A4b | 196 | Deluxe Pack: ex | four_diamond |

> **⚠ MAROWAK NOTE:** Your card has `is_ex=True`. The candidates above are for **Marowak ex** (not regular Marowak). Your previous fill (`A1/226`, `A4b/353`) was wrong — those are Lt. Surge and Red. The most likely options are **A1/#153** (Mewtwo pack, four-diamond) or **A4b/#196** (Deluxe Pack: ex, four-diamond). Check your card's number and pack icon in the app.

### Giovanni

- **owned_card_id**: `giovanni_unknown_unknown_v1`
- **Quantity**: 1  |  **is_ex**: False  |  **rarity**: unknown  |  **special_type**: unknown
- **Screenshot**: IMG_1528.PNG
- **Likely issue**: regular vs A4b special-art — single owned card but name appears in an older set (regular 2-diamond or full-art) AND in A4b (Deluxe Pack: ex, immersive special-art). Check card artwork: A4b immersive trainers have full-bleed unique art. Rarity in app: 2♦ = two_diamond, ☆☆ = double_star.

**All candidates:**

| Set | Card # | Pack | Rarity |
|---|---|---|---|
| A1 | 223 | Mewtwo | two_diamond |
| A1 | 270 | Mewtwo | double_star |
| A4b | 334 | Deluxe Pack: ex | two_diamond |
| A4b | 335 | Deluxe Pack: ex | two_diamond |

### Sabrina

- **owned_card_id**: `sabrina_unknown_unknown_v1`
- **Quantity**: 1  |  **is_ex**: False  |  **rarity**: unknown  |  **special_type**: unknown
- **Screenshot**: IMG_1528.PNG
- **Likely issue**: regular vs A4b special-art — single owned card but name appears in an older set (regular 2-diamond or full-art) AND in A4b (Deluxe Pack: ex, immersive special-art). Check card artwork: A4b immersive trainers have full-bleed unique art. Rarity in app: 2♦ = two_diamond, ☆☆ = double_star.

**All candidates:**

| Set | Card # | Pack | Rarity |
|---|---|---|---|
| A1 | 225 | Charizard | two_diamond |
| A1 | 272 | Charizard | double_star |
| A4b | 338 | Deluxe Pack: ex | two_diamond |
| A4b | 339 | Deluxe Pack: ex | two_diamond |

### Leaf

- **owned_card_id**: `leaf_unknown_unknown_v1`
- **Quantity**: 1  |  **is_ex**: False  |  **rarity**: unknown  |  **special_type**: unknown
- **Screenshot**: IMG_1528.PNG
- **Likely issue**: regular vs A4b special-art — single owned card but name appears in an older set (regular 2-diamond or full-art) AND in A4b (Deluxe Pack: ex, immersive special-art). Check card artwork: A4b immersive trainers have full-bleed unique art. Rarity in app: 2♦ = two_diamond, ☆☆ = double_star.

**All candidates:**

| Set | Card # | Pack | Rarity |
|---|---|---|---|
| A1a | 68 | Mew | two_diamond |
| A1a | 82 | Mew | double_star |
| A4b | 346 | Deluxe Pack: ex | two_diamond |
| A4b | 347 | Deluxe Pack: ex | two_diamond |

### Cyrus

- **owned_card_id**: `cyrus_unknown_unknown_v1`
- **Quantity**: 1  |  **is_ex**: False  |  **rarity**: unknown  |  **special_type**: unknown
- **Screenshot**: IMG_1528.PNG
- **Likely issue**: regular vs A4b special-art — single owned card but name appears in an older set (regular 2-diamond or full-art) AND in A4b (Deluxe Pack: ex, immersive special-art). Check card artwork: A4b immersive trainers have full-bleed unique art. Rarity in app: 2♦ = two_diamond, ☆☆ = double_star.

**All candidates:**

| Set | Card # | Pack | Rarity |
|---|---|---|---|
| A2 | 150 | Palkia | two_diamond |
| A2 | 190 | Palkia | double_star |
| A4b | 326 | Deluxe Pack: ex | two_diamond |
| A4b | 327 | Deluxe Pack: ex | two_diamond |

### Rare Candy

- **owned_card_id**: `rare_candy_unknown_unknown_v1`
- **Quantity**: 1  |  **is_ex**: False  |  **rarity**: unknown  |  **special_type**: unknown
- **Screenshot**: IMG_1528.PNG
- **Likely issue**: regular vs A4b special version — item/tool appears in an older set (shared pool or pack-specific) AND in A4b (Deluxe Pack: ex). Check set indicator in card detail view.

**All candidates:**

| Set | Card # | Pack | Rarity |
|---|---|---|---|
| A3 | 144 | shared (all packs) | two_diamond |
| A4b | 314 | Deluxe Pack: ex | two_diamond |
| A4b | 315 | Deluxe Pack: ex | two_diamond |
| A4b | 379 | Deluxe Pack: ex | None |

### Lillie

- **owned_card_id**: `lillie_unknown_unknown_v1`
- **Quantity**: 1  |  **is_ex**: False  |  **rarity**: unknown  |  **special_type**: unknown
- **Screenshot**: IMG_1528.PNG
- **Likely issue**: regular vs A4b special-art — single owned card but name appears in an older set (regular 2-diamond or full-art) AND in A4b (Deluxe Pack: ex, immersive special-art). Check card artwork: A4b immersive trainers have full-bleed unique art. Rarity in app: 2♦ = two_diamond, ☆☆ = double_star.

**All candidates:**

| Set | Card # | Pack | Rarity |
|---|---|---|---|
| A3 | 155 | Solgaleo | two_diamond |
| A3 | 197 | Solgaleo | double_star |
| A3 | 209 | Solgaleo | triple_star |
| A4b | 348 | Deluxe Pack: ex | two_diamond |
| A4b | 349 | Deluxe Pack: ex | two_diamond |
| A4b | 374 | Deluxe Pack: ex | double_star |

### Giant Cape

- **owned_card_id**: `giant_cape_unknown_unknown_v1`
- **Quantity**: 1  |  **is_ex**: False  |  **rarity**: unknown  |  **special_type**: unknown
- **Screenshot**: IMG_1528.PNG
- **Likely issue**: regular vs A4b special version — item/tool appears in an older set (shared pool or pack-specific) AND in A4b (Deluxe Pack: ex). Check set indicator in card detail view.

**All candidates:**

| Set | Card # | Pack | Rarity |
|---|---|---|---|
| A2 | 147 | Dialga | two_diamond |
| A4b | 320 | Deluxe Pack: ex | two_diamond |
| A4b | 321 | Deluxe Pack: ex | two_diamond |

### Bulbasaur

- **owned_card_id**: `bulbasaur_unknown_unknown_v2`
- **Quantity**: 1  |  **is_ex**: False  |  **rarity**: one_diamond  |  **special_type**: unknown
- **Screenshot**: IMG_1535.PNG
- **Likely issue**: same name across multiple sets — rarity=one_diamond narrows candidates significantly. B1a/#1 is already confirmed as bulbasaur_unknown_unknown_v3. Remaining one_diamond options: A1/#1 (Mewtwo), A4b/#1, A4b/#2 (Deluxe Pack: ex).

**All candidates:**

| Set | Card # | Pack | Rarity |
|---|---|---|---|
| A1 | 1 | Mewtwo | one_diamond |
| A1 | 227 | Mewtwo | one_star |
| A3 | 210 | Solgaleo | one_star |
| A4b | 1 | Deluxe Pack: ex | one_diamond |
| A4b | 2 | Deluxe Pack: ex | one_diamond |
| B1a | 1 | Crimson Blaze | one_diamond |

> **BULBASAUR v2 NOTE:** `bulbasaur_unknown_unknown_v1` was confirmed as A1/#227 (one_star, Mewtwo), and `bulbasaur_unknown_unknown_v3` as B1a/#1 (Crimson Blaze). This entry (`v2`) has `rarity=one_diamond`, which rules out the one_star versions. Most likely: **A1/#1** (Mewtwo pack) or **A4b/#1** (Deluxe Pack: ex).

### Farfetch'd

- **owned_card_id**: `farfetch_d_unknown_unknown_v1`
- **Quantity**: 1  |  **is_ex**: False  |  **rarity**: unknown  |  **special_type**: unknown
- **Screenshot**: IMG_1536.PNG
- **Likely issue**: same name across multiple sets — appears in A1 (shared pool, one_diamond), A3b (Eevee Grove, one_star), A4a (Secluded Springs, one_diamond), and A4b (multiple versions including one_diamond and one_star). Check set indicator and card number in app.

**All candidates:**

| Set | Card # | Pack | Rarity |
|---|---|---|---|
| A1 | 198 | shared (all packs) | one_diamond |
| A3b | 102 | Eevee Grove | one_star |
| A4a | 56 | Secluded Springs | one_diamond |
| A4b | 280 | Deluxe Pack: ex | one_diamond |
| A4b | 281 | Deluxe Pack: ex | one_diamond |
| A4b | 359 | Deluxe Pack: ex | one_star |

---

> Generated by `scripts/create_skipped_multi_value_review.py` on 2026-05-11 01:40 UTC.
> Do not edit manually — re-run the script to regenerate.

