# Ambiguous Pack Assignment — Manual Review

Generated: 2026-05-11 00:32 UTC

This file lists the **83** owned card entries that could not be automatically assigned to a pack because they appear in multiple sets with different pack names. Manual confirmation of the correct set/pack is required to resolve them.

## How to Confirm a Card

1. Open your Pokémon TCG Pocket app.
2. Go to **Collection** (or **Cards** tab).
3. Find the card by name.
4. Tap on it to open the card detail view.
5. Look for the **set indicator** (a small icon or text in the corner showing the expansion logo or abbreviation like A1, B3, etc.).
6. Match that to the candidate sets listed here.
7. Note the card number shown in the detail view (e.g., '42/234').
8. Fill in `confirmed_set_code` and `confirmed_card_number` in the CSV.
9. Set `confirmed_yes_no` to `yes` when done.

After filling in the CSV, run:
```
python3 scripts/apply_ambiguous_confirmations.py --dry-run
```
to preview changes, then without `--dry-run` to apply them.

---

## A4b Special Art vs Regular Print (28 cards)

_These cards appear in A4b (Deluxe Pack: ex) as special/full-art or immersive trainer versions, AND in an older set as a regular print. Look at your card's artwork — special-art cards have unique full-bleed art._

### Bulbasaur
- **Owned qty**: 1  |  **Special type**: unknown  |  **Rarity**: one_diamond  |  **Screenshot**: IMG_1524.PNG
- **card_id**: `bulbasaur_unknown_unknown_v1`
- **Candidates**:
  - A1 (Genetic Apex): card #s1, 227 — pack: Mewtwo
  - A3 (Celestial Guardians): card #210 — pack: Solgaleo
  - A4b (Deluxe Pack: ex): card #s1, 2 — pack: Deluxe Pack: ex
  - B1a (Crimson Blaze): card #1 — pack: Crimson Blaze

### Riolu
- **Owned qty**: 1  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1525.PNG
- **card_id**: `riolu_unknown_unknown_v1`
- **Candidates**:
  - A2 (Space-Time Smackdown): card #91 — pack: Dialga
  - A2b (Shining Revelry): card #s42, 104 — pack: Shining Revelry
  - A4b (Deluxe Pack: ex): card #s210, 211 — pack: Deluxe Pack: ex
  - B3 (Pulsing Aura): card #s79, 169 — pack: Pulsing Aura

### Vaporeon
- **Owned qty**: 1  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1526.PNG
- **card_id**: `vaporeon_unknown_unknown_v1`
- **Candidates**:
  - A1 (Genetic Apex): card #80 — pack: Mewtwo
  - A1a (Mythical Island): card #s19, 72 — pack: Mew
  - A3b (Eevee Grove): card #s16, 72 — pack: Eevee Grove
  - A4 (Wisdom of Sea and Sky): card #216 — pack: Lugia
  - A4b (Deluxe Pack: ex): card #s99, 100 — pack: Deluxe Pack: ex

### Crobat
- **Owned qty**: 1  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1527.PNG
- **card_id**: `crobat_unknown_unknown_v1`
- **Candidates**:
  - A2a (Triumphant Light): card #50 — pack: Arceus
  - A4b (Deluxe Pack: ex): card #s230, 231 — pack: Deluxe Pack: ex
  - B3 (Pulsing Aura): card #s100, 214 — pack: Pulsing Aura

### Giovanni
- **Owned qty**: 1  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1528.PNG
- **card_id**: `giovanni_unknown_unknown_v1`
- **Candidates**:
  - A1 (Genetic Apex): card #s223, 270 — pack: Mewtwo
  - A4b (Deluxe Pack: ex): card #s334, 335 — pack: Deluxe Pack: ex

### Sabrina
- **Owned qty**: 1  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1528.PNG
- **card_id**: `sabrina_unknown_unknown_v1`
- **Candidates**:
  - A1 (Genetic Apex): card #s225, 272 — pack: Charizard
  - A4b (Deluxe Pack: ex): card #s338, 339 — pack: Deluxe Pack: ex

### Leaf
- **Owned qty**: 1  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1528.PNG
- **card_id**: `leaf_unknown_unknown_v1`
- **Candidates**:
  - A1a (Mythical Island): card #s68, 82 — pack: Mew
  - A4b (Deluxe Pack: ex): card #s346, 347 — pack: Deluxe Pack: ex

### Cyrus
- **Owned qty**: 1  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1528.PNG
- **card_id**: `cyrus_unknown_unknown_v1`
- **Candidates**:
  - A2 (Space-Time Smackdown): card #s150, 190 — pack: Palkia
  - A4b (Deluxe Pack: ex): card #s326, 327 — pack: Deluxe Pack: ex

### Rare Candy
- **Owned qty**: 1  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1528.PNG
- **card_id**: `rare_candy_unknown_unknown_v1`
- **Candidates**:
  - A3 (Celestial Guardians): card #144 — pack: None
  - A4b (Deluxe Pack: ex): card #s314, 315, 379 — pack: Deluxe Pack: ex

### Lillie
- **Owned qty**: 1  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1528.PNG
- **card_id**: `lillie_unknown_unknown_v1`
- **Candidates**:
  - A3 (Celestial Guardians): card #s155, 197, 209 — pack: Solgaleo
  - A4b (Deluxe Pack: ex): card #s348, 349, 374 — pack: Deluxe Pack: ex

### Giant Cape
- **Owned qty**: 1  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1528.PNG
- **card_id**: `giant_cape_unknown_unknown_v1`
- **Candidates**:
  - A2 (Space-Time Smackdown): card #147 — pack: Dialga
  - A4b (Deluxe Pack: ex): card #s320, 321 — pack: Deluxe Pack: ex

### Ivysaur
- **Owned qty**: 1  |  **Special type**: unknown  |  **Rarity**: two_diamond  |  **Screenshot**: IMG_1529.PNG
- **card_id**: `ivysaur_unknown_unknown_v1`
- **Candidates**:
  - A1 (Genetic Apex): card #2 — pack: Mewtwo
  - A3 (Celestial Guardians): card #211 — pack: Solgaleo
  - A4b (Deluxe Pack: ex): card #s3, 4 — pack: Deluxe Pack: ex
  - B1a (Crimson Blaze): card #2 — pack: Crimson Blaze

### Magneton
- **Owned qty**: 1  |  **Special type**: unknown  |  **Rarity**: two_diamond  |  **Screenshot**: IMG_1529.PNG
- **card_id**: `magneton_unknown_unknown_v1`
- **Candidates**:
  - A1 (Genetic Apex): card #98 — pack: Pikachu
  - A2 (Space-Time Smackdown): card #52 — pack: None
  - A2a (Triumphant Light): card #54 — pack: Arceus
  - A4 (Wisdom of Sea and Sky): card #218 — pack: Lugia
  - A4b (Deluxe Pack: ex): card #s135, 136 — pack: Deluxe Pack: ex
  - B1a (Crimson Blaze): card #25 — pack: Crimson Blaze
  - B3 (Pulsing Aura): card #53 — pack: Pulsing Aura

### Charmeleon
- **Owned qty**: 2  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1531.PNG
- **card_id**: `charmeleon_unknown_unknown_v1`
- **Candidates**:
  - A1 (Genetic Apex): card #34 — pack: Charizard
  - A2b (Shining Revelry): card #s9, 100 — pack: Shining Revelry
  - A4b (Deluxe Pack: ex): card #s57, 58 — pack: Deluxe Pack: ex
  - B1a (Crimson Blaze): card #12 — pack: Crimson Blaze
  - B2b (Mega Shine): card #s8, 92 — pack: Mega Shine

### Magneton
- **Owned qty**: 2  |  **Special type**: unknown  |  **Rarity**: two_diamond  |  **Screenshot**: IMG_1533.PNG
- **card_id**: `magneton_unknown_unknown_v2`
- **Candidates**:
  - A1 (Genetic Apex): card #98 — pack: Pikachu
  - A2 (Space-Time Smackdown): card #52 — pack: None
  - A2a (Triumphant Light): card #54 — pack: Arceus
  - A4 (Wisdom of Sea and Sky): card #218 — pack: Lugia
  - A4b (Deluxe Pack: ex): card #s135, 136 — pack: Deluxe Pack: ex
  - B1a (Crimson Blaze): card #25 — pack: Crimson Blaze
  - B3 (Pulsing Aura): card #53 — pack: Pulsing Aura

### Golbat
- **Owned qty**: 1  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1533.PNG
- **card_id**: `golbat_unknown_unknown_v1`
- **Candidates**:
  - A1 (Genetic Apex): card #s173, 242 — pack: Mewtwo
  - A2a (Triumphant Light): card #49 — pack: Arceus
  - A4 (Wisdom of Sea and Sky): card #108 — pack: Ho-Oh
  - A4b (Deluxe Pack: ex): card #s228, 229 — pack: Deluxe Pack: ex
  - B3 (Pulsing Aura): card #s99, 213 — pack: Pulsing Aura

### Bulbasaur
- **Owned qty**: 1  |  **Special type**: unknown  |  **Rarity**: one_diamond  |  **Screenshot**: IMG_1535.PNG
- **card_id**: `bulbasaur_unknown_unknown_v2`
- **Candidates**:
  - A1 (Genetic Apex): card #s1, 227 — pack: Mewtwo
  - A3 (Celestial Guardians): card #210 — pack: Solgaleo
  - A4b (Deluxe Pack: ex): card #s1, 2 — pack: Deluxe Pack: ex
  - B1a (Crimson Blaze): card #1 — pack: Crimson Blaze

### Dratini
- **Owned qty**: 1  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1536.PNG
- **card_id**: `dratini_unknown_unknown_v1`
- **Candidates**:
  - A1 (Genetic Apex): card #183 — pack: Mewtwo
  - A3b (Eevee Grove): card #51 — pack: Eevee Grove
  - A4b (Deluxe Pack: ex): card #s267, 268 — pack: Deluxe Pack: ex
  - B2b (Mega Shine): card #s51, 105 — pack: Mega Shine

### Farfetch'd
- **Owned qty**: 1  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1536.PNG
- **card_id**: `farfetch_d_unknown_unknown_v1`
- **Candidates**:
  - A1 (Genetic Apex): card #198 — pack: None
  - A3b (Eevee Grove): card #102 — pack: Eevee Grove
  - A4a (Secluded Springs): card #56 — pack: Secluded Springs
  - A4b (Deluxe Pack: ex): card #s280, 281, 359 — pack: Deluxe Pack: ex

### Cherubi
- **Owned qty**: 1  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1536.PNG
- **card_id**: `cherubi_unknown_unknown_v1`
- **Candidates**:
  - A2a (Triumphant Light): card #6 — pack: Arceus
  - A4 (Wisdom of Sea and Sky): card #23 — pack: None
  - A4b (Deluxe Pack: ex): card #s25, 26 — pack: Deluxe Pack: ex

### Bulbasaur
- **Owned qty**: 3  |  **Special type**: unknown  |  **Rarity**: one_diamond  |  **Screenshot**: IMG_1537.PNG
- **card_id**: `bulbasaur_unknown_unknown_v3`
- **Candidates**:
  - A1 (Genetic Apex): card #s1, 227 — pack: Mewtwo
  - A3 (Celestial Guardians): card #210 — pack: Solgaleo
  - A4b (Deluxe Pack: ex): card #s1, 2 — pack: Deluxe Pack: ex
  - B1a (Crimson Blaze): card #1 — pack: Crimson Blaze

### Charmander
- **Owned qty**: 4  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1537.PNG
- **card_id**: `charmander_unknown_unknown_v1`
- **Candidates**:
  - A1 (Genetic Apex): card #s33, 230 — pack: Charizard
  - A2b (Shining Revelry): card #s8, 99 — pack: Shining Revelry
  - A4b (Deluxe Pack: ex): card #s55, 56 — pack: Deluxe Pack: ex
  - B1a (Crimson Blaze): card #11 — pack: Crimson Blaze
  - B2b (Mega Shine): card #s7, 91 — pack: Mega Shine

### Magnemite
- **Owned qty**: 1  |  **Special type**: unknown  |  **Rarity**: one_diamond  |  **Screenshot**: IMG_1538.PNG
- **card_id**: `magnemite_unknown_unknown_v1`
- **Candidates**:
  - A1 (Genetic Apex): card #97 — pack: Pikachu
  - A2 (Space-Time Smackdown): card #51 — pack: None
  - A2a (Triumphant Light): card #s53, 80 — pack: Arceus
  - A4 (Wisdom of Sea and Sky): card #217 — pack: Lugia
  - A4b (Deluxe Pack: ex): card #s133, 134 — pack: Deluxe Pack: ex
  - B1a (Crimson Blaze): card #24 — pack: Crimson Blaze
  - B3 (Pulsing Aura): card #52 — pack: Pulsing Aura

### Misdreavus
- **Owned qty**: 4  |  **Special type**: unknown  |  **Rarity**: one_diamond  |  **Screenshot**: IMG_1538.PNG
- **card_id**: `misdreavus_unknown_unknown_v1`
- **Candidates**:
  - A2 (Space-Time Smackdown): card #66 — pack: Palkia
  - A4 (Wisdom of Sea and Sky): card #220 — pack: Ho-Oh
  - A4a (Secluded Springs): card #32 — pack: Secluded Springs
  - A4b (Deluxe Pack: ex): card #s161, 162 — pack: Deluxe Pack: ex
  - B1 (Mega Rising): card #99 — pack: None
  - B1a (Crimson Blaze): card #30 — pack: Crimson Blaze

### Charmander
- **Owned qty**: 2  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1541.PNG
- **card_id**: `charmander_unknown_unknown_v2`
- **Candidates**:
  - A1 (Genetic Apex): card #s33, 230 — pack: Charizard
  - A2b (Shining Revelry): card #s8, 99 — pack: Shining Revelry
  - A4b (Deluxe Pack: ex): card #s55, 56 — pack: Deluxe Pack: ex
  - B1a (Crimson Blaze): card #11 — pack: Crimson Blaze
  - B2b (Mega Shine): card #s7, 91 — pack: Mega Shine

### Magnemite
- **Owned qty**: 2  |  **Special type**: unknown  |  **Rarity**: one_diamond  |  **Screenshot**: IMG_1543.PNG
- **card_id**: `magnemite_unknown_unknown_v2`
- **Candidates**:
  - A1 (Genetic Apex): card #97 — pack: Pikachu
  - A2 (Space-Time Smackdown): card #51 — pack: None
  - A2a (Triumphant Light): card #s53, 80 — pack: Arceus
  - A4 (Wisdom of Sea and Sky): card #217 — pack: Lugia
  - A4b (Deluxe Pack: ex): card #s133, 134 — pack: Deluxe Pack: ex
  - B1a (Crimson Blaze): card #24 — pack: Crimson Blaze
  - B3 (Pulsing Aura): card #52 — pack: Pulsing Aura

### Oricorio
- **Owned qty**: 2  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1543.PNG
- **card_id**: `oricorio_unknown_unknown_v1`
- **Candidates**:
  - A3 (Celestial Guardians): card #s34, 66, 76, 77, 165 — pack: Lunala / Solgaleo
  - A4b (Deluxe Pack: ex): card #s146, 147, 178, 179 — pack: Deluxe Pack: ex
  - B1 (Mega Rising): card #303 — pack: Mega Gyarados
  - B2 (Fantastical Parade): card #s22, 161 — pack: Fantastical Parade
  - B3 (Pulsing Aura): card #s68, 166 — pack: Pulsing Aura

### Riolu
- **Owned qty**: 2  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1544.PNG
- **card_id**: `riolu_unknown_unknown_v2`
- **Candidates**:
  - A2 (Space-Time Smackdown): card #91 — pack: Dialga
  - A2b (Shining Revelry): card #s42, 104 — pack: Shining Revelry
  - A4b (Deluxe Pack: ex): card #s210, 211 — pack: Deluxe Pack: ex
  - B3 (Pulsing Aura): card #s79, 169 — pack: Pulsing Aura

## Within-Set: Pack-Specific vs Shared (1 cards)

_These cards appear within a single expansion but in two forms: a pack-specific version (only in one named pack) and a shared version (obtainable from any pack). Look up the exact card number in your app to determine which version you own._

### Flame Patch
- **Owned qty**: 2  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1529.PNG
- **card_id**: `flame_patch_unknown_unknown_v1`
- **Candidates**:
  - B1 (Mega Rising): card #s217, 331 — pack: Mega Blaziken / None

## Two Candidate Packs (14 cards)

### Blaziken
- **Owned qty**: 1  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1524.PNG
- **card_id**: `blaziken_unknown_unknown_v1`
- **Candidates**:
  - B1 (Mega Rising): card #35 — pack: Mega Blaziken
  - B3 (Pulsing Aura): card #208 — pack: Pulsing Aura

### Morpeko
- **Owned qty**: 1  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1525.PNG
- **card_id**: `morpeko_unknown_unknown_v1`
- **Candidates**:
  - B2b (Mega Shine): card #s45, 73 — pack: Mega Shine
  - B3 (Pulsing Aura): card #s62, 164 — pack: Pulsing Aura

### Marowak
- **Owned qty**: 1  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1525.PNG
- **card_id**: `marowak_unknown_unknown_v1`
- **Candidates**:
  - A1 (Genetic Apex): card #152 — pack: Mewtwo
  - A3 (Celestial Guardians): card #227 — pack: Lunala

### Eelektross
- **Owned qty**: 1  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1526.PNG
- **card_id**: `eelektross_unknown_unknown_v1`
- **Candidates**:
  - A1 (Genetic Apex): card #109 — pack: Mewtwo
  - A4a (Secluded Springs): card #28 — pack: Secluded Springs

### Charizard
- **Owned qty**: 1  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1526.PNG
- **card_id**: `charizard_unknown_unknown_v1`
- **Candidates**:
  - A1 (Genetic Apex): card #35 — pack: Charizard
  - B1a (Crimson Blaze): card #s13, 91 — pack: Crimson Blaze

### Meloetta
- **Owned qty**: 3  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1527.PNG
- **card_id**: `meloetta_unknown_unknown_v1`
- **Candidates**:
  - B2 (Fantastical Parade): card #s70, 233 — pack: Fantastical Parade
  - B3 (Pulsing Aura): card #s89, 170 — pack: Pulsing Aura

### Doublade
- **Owned qty**: 1  |  **Special type**: unknown  |  **Rarity**: two_diamond  |  **Screenshot**: IMG_1531.PNG
- **card_id**: `doublade_unknown_unknown_v1`
- **Candidates**:
  - B1 (Mega Rising): card #171 — pack: Mega Blaziken
  - B2 (Fantastical Parade): card #119 — pack: Fantastical Parade

### Quagsire
- **Owned qty**: 1  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1532.PNG
- **card_id**: `quagsire_unknown_unknown_v1`
- **Candidates**:
  - A4 (Wisdom of Sea and Sky): card #52 — pack: Lugia
  - B3 (Pulsing Aura): card #s39, 162 — pack: Pulsing Aura

### Malamar
- **Owned qty**: 1  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1533.PNG
- **card_id**: `malamar_unknown_unknown_v1`
- **Candidates**:
  - A4a (Secluded Springs): card #52 — pack: Secluded Springs
  - B3 (Pulsing Aura): card #s112, 175 — pack: Pulsing Aura

### Corvisquire
- **Owned qty**: 1  |  **Special type**: unknown  |  **Rarity**: two_diamond  |  **Screenshot**: IMG_1534.PNG
- **card_id**: `corvisquire_unknown_unknown_v1`
- **Candidates**:
  - B1 (Mega Rising): card #210 — pack: Mega Blaziken
  - B3 (Pulsing Aura): card #146 — pack: Pulsing Aura

### Morpeko
- **Owned qty**: 1  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1543.PNG
- **card_id**: `morpeko_unknown_unknown_v2`
- **Candidates**:
  - B2b (Mega Shine): card #s45, 73 — pack: Mega Shine
  - B3 (Pulsing Aura): card #s62, 164 — pack: Pulsing Aura

### Bramblin
- **Owned qty**: 2  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1543.PNG
- **card_id**: `bramblin_unknown_unknown_v1`
- **Candidates**:
  - B2a (Paldean Wonders): card #10 — pack: Paldean Wonders
  - B3 (Pulsing Aura): card #72 — pack: Pulsing Aura

### Rolycoly
- **Owned qty**: 2  |  **Special type**: unknown  |  **Rarity**: one_diamond  |  **Screenshot**: IMG_1544.PNG
- **card_id**: `rolycoly_unknown_unknown_v1`
- **Candidates**:
  - B1 (Mega Rising): card #145 — pack: Mega Gyarados
  - B3 (Pulsing Aura): card #92 — pack: Pulsing Aura

### Seviper
- **Owned qty**: 2  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1545.PNG
- **card_id**: `seviper_unknown_unknown_v1`
- **Candidates**:
  - A4a (Secluded Springs): card #48 — pack: Secluded Springs
  - B3 (Pulsing Aura): card #s104, 173 — pack: Pulsing Aura

## Pack-Specific vs Shared Pool (9 cards)

_One candidate is a 'shared' card (available in all packs of that expansion). If your card is from that expansion, pack_name is not critical — it was available from any pack in the set._

### Shroomish
- **Owned qty**: 1  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1524.PNG
- **card_id**: `shroomish_unknown_unknown_v1`
- **Candidates**:
  - B1 (Mega Rising): card #11 — pack: None
  - B3 (Pulsing Aura): card #s11, 158 — pack: Pulsing Aura

### Breloom
- **Owned qty**: 1  |  **Special type**: unknown  |  **Rarity**: two_diamond  |  **Screenshot**: IMG_1532.PNG
- **card_id**: `breloom_unknown_unknown_v1`
- **Candidates**:
  - B1 (Mega Rising): card #12 — pack: None
  - B3 (Pulsing Aura): card #12 — pack: Pulsing Aura

### Bisharp
- **Owned qty**: 1  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1534.PNG
- **card_id**: `bisharp_unknown_unknown_v1`
- **Candidates**:
  - A1 (Genetic Apex): card #180 — pack: None
  - B3 (Pulsing Aura): card #s120, 176 — pack: Pulsing Aura

### Rattata
- **Owned qty**: 2  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1536.PNG
- **card_id**: `rattata_unknown_unknown_v1`
- **Candidates**:
  - A1 (Genetic Apex): card #189 — pack: None
  - A2b (Shining Revelry): card #58 — pack: Shining Revelry

### Raticate
- **Owned qty**: 1  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1536.PNG
- **card_id**: `raticate_unknown_unknown_v1`
- **Candidates**:
  - A1 (Genetic Apex): card #190 — pack: None
  - A2b (Shining Revelry): card #59 — pack: Shining Revelry

### Spritzee
- **Owned qty**: 6  |  **Special type**: unknown  |  **Rarity**: one_diamond  |  **Screenshot**: IMG_1538.PNG
- **card_id**: `spritzee_unknown_unknown_v1`
- **Candidates**:
  - B1 (Mega Rising): card #115 — pack: None
  - B1a (Crimson Blaze): card #35 — pack: Crimson Blaze

### Aromatisse
- **Owned qty**: 2  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1539.PNG
- **card_id**: `aromatisse_unknown_unknown_v1`
- **Candidates**:
  - B1 (Mega Rising): card #116 — pack: None
  - B1a (Crimson Blaze): card #36 — pack: Crimson Blaze

### Shroomish
- **Owned qty**: 1  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1541.PNG
- **card_id**: `shroomish_unknown_unknown_v2`
- **Candidates**:
  - B1 (Mega Rising): card #11 — pack: None
  - B3 (Pulsing Aura): card #s11, 158 — pack: Pulsing Aura

### Watchog
- **Owned qty**: 2  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1545.PNG
- **card_id**: `watchog_unknown_unknown_v1`
- **Candidates**:
  - B1 (Mega Rising): card #200 — pack: None
  - B3 (Pulsing Aura): card #136 — pack: Pulsing Aura

## Multiple Sets Including Shared Pool (11 cards)

### Sandslash
- **Owned qty**: 2  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1527.PNG
- **card_id**: `sandslash_unknown_unknown_v1`
- **Candidates**:
  - A1 (Genetic Apex): card #138 — pack: None
  - B1 (Mega Rising): card #123 — pack: None
  - B1a (Crimson Blaze): card #95 — pack: Crimson Blaze
  - B2 (Fantastical Parade): card #78 — pack: Fantastical Parade

### Mismagius
- **Owned qty**: 2  |  **Special type**: unknown  |  **Rarity**: two_diamond  |  **Screenshot**: IMG_1530.PNG
- **card_id**: `mismagius_unknown_unknown_v1`
- **Candidates**:
  - A4a (Secluded Springs): card #33 — pack: Secluded Springs
  - B1 (Mega Rising): card #100 — pack: None
  - B1a (Crimson Blaze): card #31 — pack: Crimson Blaze

### Hariyama
- **Owned qty**: 2  |  **Special type**: unknown  |  **Rarity**: two_diamond  |  **Screenshot**: IMG_1530.PNG
- **card_id**: `hariyama_unknown_unknown_v1`
- **Candidates**:
  - A3 (Celestial Guardians): card #91 — pack: None
  - B1 (Mega Rising): card #127 — pack: Mega Blaziken
  - B1a (Crimson Blaze): card #40 — pack: Crimson Blaze

### Garbodor
- **Owned qty**: 3  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1530.PNG
- **card_id**: `garbodor_unknown_unknown_v1`
- **Candidates**:
  - A3 (Celestial Guardians): card #114 — pack: None
  - B1a (Crimson Blaze): card #50 — pack: Crimson Blaze
  - B2b (Mega Shine): card #42 — pack: Mega Shine

### Darmanitan
- **Owned qty**: 3  |  **Special type**: unknown  |  **Rarity**: two_diamond  |  **Screenshot**: IMG_1532.PNG
- **card_id**: `darmanitan_unknown_unknown_v1`
- **Candidates**:
  - A4 (Wisdom of Sea and Sky): card #36 — pack: None
  - B1 (Mega Rising): card #40 — pack: Mega Gyarados
  - B3 (Pulsing Aura): card #30 — pack: Pulsing Aura

### Sandshrew
- **Owned qty**: 2  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1535.PNG
- **card_id**: `sandshrew_unknown_unknown_v1`
- **Candidates**:
  - A1 (Genetic Apex): card #137 — pack: None
  - B1 (Mega Rising): card #122 — pack: None
  - B1a (Crimson Blaze): card #94 — pack: Crimson Blaze
  - B2 (Fantastical Parade): card #s77, 170 — pack: Fantastical Parade

### Makuhita
- **Owned qty**: 1  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1539.PNG
- **card_id**: `makuhita_unknown_unknown_v1`
- **Candidates**:
  - A3 (Celestial Guardians): card #90 — pack: None
  - B1 (Mega Rising): card #s126, 240 — pack: Mega Blaziken
  - B1a (Crimson Blaze): card #39 — pack: Crimson Blaze

### Trubbish
- **Owned qty**: 1  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1539.PNG
- **card_id**: `trubbish_unknown_unknown_v1`
- **Candidates**:
  - A3 (Celestial Guardians): card #113 — pack: None
  - B1a (Crimson Blaze): card #s49, 74 — pack: Crimson Blaze
  - B2b (Mega Shine): card #41 — pack: Mega Shine

### Darumaka
- **Owned qty**: 2  |  **Special type**: unknown  |  **Rarity**: one_diamond  |  **Screenshot**: IMG_1542.PNG
- **card_id**: `darumaka_unknown_unknown_v1`
- **Candidates**:
  - A4 (Wisdom of Sea and Sky): card #35 — pack: None
  - B1 (Mega Rising): card #39 — pack: Mega Gyarados
  - B3 (Pulsing Aura): card #29 — pack: Pulsing Aura

### Minccino
- **Owned qty**: 4  |  **Special type**: unknown  |  **Rarity**: one_diamond  |  **Screenshot**: IMG_1546.PNG
- **card_id**: `minccino_unknown_unknown_v1`
- **Candidates**:
  - A1 (Genetic Apex): card #212 — pack: None
  - A3b (Eevee Grove): card #62 — pack: Eevee Grove
  - B2b (Mega Shine): card #62 — pack: Mega Shine
  - B3 (Pulsing Aura): card #142 — pack: Pulsing Aura

### Cinccino
- **Owned qty**: 2  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1546.PNG
- **card_id**: `cinccino_unknown_unknown_v1`
- **Candidates**:
  - A1 (Genetic Apex): card #213 — pack: None
  - A3b (Eevee Grove): card #63 — pack: Eevee Grove
  - B2b (Mega Shine): card #63 — pack: Mega Shine
  - B3 (Pulsing Aura): card #s143, 179 — pack: Pulsing Aura

## Multiple Sets (20 cards)

### Skrelp
- **Owned qty**: 1  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1524.PNG
- **card_id**: `skrelp_unknown_unknown_v1`
- **Candidates**:
  - A4a (Secluded Springs): card #53 — pack: Secluded Springs
  - B1 (Mega Rising): card #159 — pack: Mega Blaziken
  - B3 (Pulsing Aura): card #218 — pack: Pulsing Aura

### Meltan
- **Owned qty**: 1  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1525.PNG
- **card_id**: `meltan_unknown_unknown_v1`
- **Candidates**:
  - A1 (Genetic Apex): card #181 — pack: Charizard
  - A3b (Eevee Grove): card #49 — pack: Eevee Grove
  - B1 (Mega Rising): card #173 — pack: Mega Gyarados
  - B3 (Pulsing Aura): card #s122, 177 — pack: Pulsing Aura

### Stoutland
- **Owned qty**: 1  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1527.PNG
- **card_id**: `stoutland_unknown_unknown_v1`
- **Candidates**:
  - A3a (Extradimensional Crisis): card #56 — pack: Extradimensional Crisis
  - B1 (Mega Rising): card #s203, 249 — pack: Mega Altaria
  - B3 (Pulsing Aura): card #139 — pack: Pulsing Aura

### Onix
- **Owned qty**: 1  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1527.PNG
- **card_id**: `onix_unknown_unknown_v1`
- **Candidates**:
  - A1 (Genetic Apex): card #150 — pack: Pikachu
  - A4 (Wisdom of Sea and Sky): card #92 — pack: Ho-Oh
  - B1a (Crimson Blaze): card #38 — pack: Crimson Blaze
  - B3 (Pulsing Aura): card #211 — pack: Pulsing Aura

### Steelix
- **Owned qty**: 3  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1530.PNG
- **card_id**: `steelix_unknown_unknown_v1`
- **Candidates**:
  - A4 (Wisdom of Sea and Sky): card #122 — pack: Ho-Oh
  - B1a (Crimson Blaze): card #51 — pack: Crimson Blaze
  - B3 (Pulsing Aura): card #219 — pack: Pulsing Aura

### Porygon2
- **Owned qty**: 1  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1530.PNG
- **card_id**: `porygon2_unknown_unknown_v1`
- **Candidates**:
  - A2 (Space-Time Smackdown): card #128 — pack: Palkia
  - A4 (Wisdom of Sea and Sky): card #136 — pack: Lugia
  - B1a (Crimson Blaze): card #57 — pack: Crimson Blaze
  - B3 (Pulsing Aura): card #223 — pack: Pulsing Aura

### Furfrou
- **Owned qty**: 1  |  **Special type**: unknown  |  **Rarity**: two_diamond  |  **Screenshot**: IMG_1531.PNG
- **card_id**: `furfrou_unknown_unknown_v1`
- **Candidates**:
  - B1 (Mega Rising): card #s206, 207, 208 — pack: Mega Altaria / Mega Blaziken / Mega Gyarados
  - B1a (Crimson Blaze): card #65 — pack: Crimson Blaze
  - B2 (Fantastical Parade): card #141 — pack: Fantastical Parade
  - B2b (Mega Shine): card #64 — pack: Mega Shine
  - B3 (Pulsing Aura): card #144 — pack: Pulsing Aura

### Poliwhirl
- **Owned qty**: 2  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1532.PNG
- **card_id**: `poliwhirl_unknown_unknown_v1`
- **Candidates**:
  - A1 (Genetic Apex): card #60 — pack: Charizard
  - A4 (Wisdom of Sea and Sky): card #39 — pack: Lugia
  - A4a (Secluded Springs): card #14 — pack: Secluded Springs
  - B1 (Mega Rising): card #296 — pack: Mega Gyarados
  - B3 (Pulsing Aura): card #34 — pack: Pulsing Aura

### Paldean Tauros
- **Owned qty**: 2  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1532.PNG
- **card_id**: `paldean_tauros_unknown_unknown_v1`
- **Candidates**:
  - A2b (Shining Revelry): card #13 — pack: Shining Revelry
  - B2a (Paldean Wonders): card #58 — pack: Paldean Wonders
  - B2b (Mega Shine): card #14 — pack: Mega Shine
  - B3 (Pulsing Aura): card #36 — pack: Pulsing Aura

### Bewear
- **Owned qty**: 2  |  **Special type**: unknown  |  **Rarity**: two_diamond  |  **Screenshot**: IMG_1533.PNG
- **card_id**: `bewear_unknown_unknown_v1`
- **Candidates**:
  - A3 (Celestial Guardians): card #s139, 178 — pack: Lunala
  - A3a (Extradimensional Crisis): card #58 — pack: Extradimensional Crisis
  - B1 (Mega Rising): card #142 — pack: Mega Blaziken
  - B3 (Pulsing Aura): card #91 — pack: Pulsing Aura

### Herdier
- **Owned qty**: 1  |  **Special type**: unknown  |  **Rarity**: two_diamond  |  **Screenshot**: IMG_1534.PNG
- **card_id**: `herdier_unknown_unknown_v1`
- **Candidates**:
  - A3a (Extradimensional Crisis): card #55 — pack: Extradimensional Crisis
  - B1 (Mega Rising): card #202 — pack: Mega Altaria
  - B3 (Pulsing Aura): card #138 — pack: Pulsing Aura

### Onix
- **Owned qty**: 2  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1539.PNG
- **card_id**: `onix_unknown_unknown_v2`
- **Candidates**:
  - A1 (Genetic Apex): card #150 — pack: Pikachu
  - A4 (Wisdom of Sea and Sky): card #92 — pack: Ho-Oh
  - B1a (Crimson Blaze): card #38 — pack: Crimson Blaze
  - B3 (Pulsing Aura): card #211 — pack: Pulsing Aura

### Grimer
- **Owned qty**: 3  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1539.PNG
- **card_id**: `grimer_unknown_unknown_v1`
- **Candidates**:
  - A1 (Genetic Apex): card #174 — pack: Mewtwo
  - B1a (Crimson Blaze): card #45 — pack: Crimson Blaze
  - B3 (Pulsing Aura): card #215 — pack: Pulsing Aura

### Porygon
- **Owned qty**: 3  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1539.PNG
- **card_id**: `porygon_unknown_unknown_v1`
- **Candidates**:
  - A1 (Genetic Apex): card #s209, 249 — pack: Mewtwo
  - A2 (Space-Time Smackdown): card #127 — pack: Palkia
  - A4 (Wisdom of Sea and Sky): card #135 — pack: Lugia
  - B1a (Crimson Blaze): card #56 — pack: Crimson Blaze
  - B3 (Pulsing Aura): card #222 — pack: Pulsing Aura

### Buneary
- **Owned qty**: 2  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1540.PNG
- **card_id**: `buneary_unknown_unknown_v1`
- **Candidates**:
  - A2 (Space-Time Smackdown): card #137 — pack: Dialga
  - A2b (Shining Revelry): card #66 — pack: Shining Revelry
  - B1a (Crimson Blaze): card #s62, 75 — pack: Crimson Blaze

### Tangela
- **Owned qty**: 1  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1541.PNG
- **card_id**: `tangela_unknown_unknown_v1`
- **Candidates**:
  - A1 (Genetic Apex): card #24 — pack: Charizard
  - A2 (Space-Time Smackdown): card #4 — pack: Dialga
  - A4 (Wisdom of Sea and Sky): card #4 — pack: Ho-Oh
  - B2 (Fantastical Parade): card #205 — pack: Fantastical Parade
  - B3 (Pulsing Aura): card #1 — pack: Pulsing Aura

### Stufful
- **Owned qty**: 1  |  **Special type**: unknown  |  **Rarity**: one_diamond  |  **Screenshot**: IMG_1544.PNG
- **card_id**: `stufful_unknown_unknown_v1`
- **Candidates**:
  - A3 (Celestial Guardians): card #138 — pack: Lunala
  - A3a (Extradimensional Crisis): card #57 — pack: Extradimensional Crisis
  - B1 (Mega Rising): card #141 — pack: Mega Blaziken
  - B3 (Pulsing Aura): card #90 — pack: Pulsing Aura

### Zorua
- **Owned qty**: 1  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1545.PNG
- **card_id**: `zorua_unknown_unknown_v1`
- **Candidates**:
  - A4a (Secluded Springs): card #49 — pack: Secluded Springs
  - B2b (Mega Shine): card #s43, 102 — pack: Mega Shine
  - B3 (Pulsing Aura): card #s105, 174 — pack: Pulsing Aura

### Chansey
- **Owned qty**: 1  |  **Special type**: unknown  |  **Rarity**: unknown  |  **Screenshot**: IMG_1545.PNG
- **card_id**: `chansey_unknown_unknown_v1`
- **Candidates**:
  - A1 (Genetic Apex): card #202 — pack: Pikachu
  - A4 (Wisdom of Sea and Sky): card #131 — pack: Ho-Oh
  - B3 (Pulsing Aura): card #s127, 220 — pack: Pulsing Aura

### Lillipup
- **Owned qty**: 2  |  **Special type**: unknown  |  **Rarity**: one_diamond  |  **Screenshot**: IMG_1546.PNG
- **card_id**: `lillipup_unknown_unknown_v1`
- **Candidates**:
  - A3a (Extradimensional Crisis): card #54 — pack: Extradimensional Crisis
  - B1 (Mega Rising): card #201 — pack: Mega Altaria
  - B3 (Pulsing Aura): card #137 — pack: Pulsing Aura

---

> Generated by `scripts/create_ambiguous_review_package.py` on 2026-05-11 00:32 UTC.
> Do not edit this file manually — re-run the script to regenerate.

