# Screenshots Manifest

Generated: 2026-05-09 14:19:57

---

## Summary

- **Total image entries scanned:** 48 (across all sources)
- **Unique images (by sha256):** 24
- **In Archive.zip:** 24 images
- **In screenshots/:** 24 images (excluding `__MACOSX` metadata)
- **Exact duplicate pairs (by sha256):** 24 groups
- **Basename duplicates (same filename, different source):** 24 groups

## Archive.zip vs screenshots/ Redundancy

**Result: FULLY REDUNDANT.** Archive.zip and screenshots/ contain byte-for-byte identical image files.

- `Archive.zip` is the compressed source (86 MB)
- `screenshots/` is the extracted copy plus `__MACOSX/` metadata junk

**Recommendation:** Keep `Archive.zip` as the canonical backup.
The `screenshots/` directory is the working copy used for extraction.
Both are gitignored. No action is required right now.
After all extraction is complete and validated, `screenshots/` can be safely deleted
since `Archive.zip` is a lossless backup of the same files.

## __MACOSX Metadata

`screenshots/__MACOSX/` contains 24 `._*.PNG` files — these are macOS AppleDouble
resource fork metadata artifacts created when macOS zipped the files. They contain
no image data and are safe to ignore. They are not counted in the image totals above.

---

## Screenshot Inventory (Processing Order)

Files are listed in filename order, which is the intended extraction sequence.

No card extraction has been performed.

| # | Filename | Source | Size | Dimensions | SHA256 (12) |
|---|----------|--------|------|------------|-------------|
| 1 | `IMG_1524.PNG` | screenshots_dir | 4403 KB | 1179×2556 | `2ea754c53eb6` |
| 2 | `IMG_1525.PNG` | screenshots_dir | 4361 KB | 1179×2556 | `5015e1cbf5f3` |
| 3 | `IMG_1526.PNG` | screenshots_dir | 4278 KB | 1179×2556 | `e431d2ab9b21` |
| 4 | `IMG_1527.PNG` | screenshots_dir | 3895 KB | 1179×2556 | `2e3904877768` |
| 5 | `IMG_1528.PNG` | screenshots_dir | 3396 KB | 1179×2556 | `88e99f80cc66` |
| 6 | `IMG_1529.PNG` | screenshots_dir | 3558 KB | 1179×2556 | `084f4d7f010d` |
| 7 | `IMG_1530.PNG` | screenshots_dir | 3704 KB | 1179×2556 | `2b3fe27a0909` |
| 8 | `IMG_1531.PNG` | screenshots_dir | 3615 KB | 1179×2556 | `f0c7f0e32803` |
| 9 | `IMG_1532.PNG` | screenshots_dir | 3707 KB | 1179×2556 | `123d9320891c` |
| 10 | `IMG_1533.PNG` | screenshots_dir | 3752 KB | 1179×2556 | `b108ab45d6d9` |
| 11 | `IMG_1534.PNG` | screenshots_dir | 3709 KB | 1179×2556 | `fc668da1b6bb` |
| 12 | `IMG_1535.PNG` | screenshots_dir | 3553 KB | 1179×2556 | `a64823aef53d` |
| 13 | `IMG_1536.PNG` | screenshots_dir | 3616 KB | 1179×2556 | `a462e8004d50` |
| 14 | `IMG_1537.PNG` | screenshots_dir | 3607 KB | 1179×2556 | `a5b7793b0f5f` |
| 15 | `IMG_1538.PNG` | screenshots_dir | 3650 KB | 1179×2556 | `6ff5a4e93c4a` |
| 16 | `IMG_1539.PNG` | screenshots_dir | 3663 KB | 1179×2556 | `574c8da63314` |
| 17 | `IMG_1540.PNG` | screenshots_dir | 3644 KB | 1179×2556 | `f02c65bbc3d8` |
| 18 | `IMG_1541.PNG` | screenshots_dir | 3586 KB | 1179×2556 | `19520955d9cf` |
| 19 | `IMG_1542.PNG` | screenshots_dir | 3660 KB | 1179×2556 | `df7d017ea4dd` |
| 20 | `IMG_1543.PNG` | screenshots_dir | 3535 KB | 1179×2556 | `7873725210e5` |
| 21 | `IMG_1544.PNG` | screenshots_dir | 3597 KB | 1179×2556 | `3763f5aab6b2` |
| 22 | `IMG_1545.PNG` | screenshots_dir | 3632 KB | 1179×2556 | `173317b1805b` |
| 23 | `IMG_1546.PNG` | screenshots_dir | 3320 KB | 1179×2556 | `0d7dbef8784b` |
| 24 | `IMG_1547.PNG` | screenshots_dir | 2467 KB | 1179×2556 | `2fd7393d0543` |

---

## Exact Duplicate Groups (by SHA256)

**Hash:** `2ea754c53eb6...`
  - `IMG_1524.PNG` (archive_zip)
  - `screenshots/IMG_1524.PNG` (screenshots_dir)

**Hash:** `5015e1cbf5f3...`
  - `IMG_1525.PNG` (archive_zip)
  - `screenshots/IMG_1525.PNG` (screenshots_dir)

**Hash:** `e431d2ab9b21...`
  - `IMG_1526.PNG` (archive_zip)
  - `screenshots/IMG_1526.PNG` (screenshots_dir)

**Hash:** `2e3904877768...`
  - `IMG_1527.PNG` (archive_zip)
  - `screenshots/IMG_1527.PNG` (screenshots_dir)

**Hash:** `88e99f80cc66...`
  - `IMG_1528.PNG` (archive_zip)
  - `screenshots/IMG_1528.PNG` (screenshots_dir)

**Hash:** `084f4d7f010d...`
  - `IMG_1529.PNG` (archive_zip)
  - `screenshots/IMG_1529.PNG` (screenshots_dir)

**Hash:** `2b3fe27a0909...`
  - `IMG_1530.PNG` (archive_zip)
  - `screenshots/IMG_1530.PNG` (screenshots_dir)

**Hash:** `f0c7f0e32803...`
  - `IMG_1531.PNG` (archive_zip)
  - `screenshots/IMG_1531.PNG` (screenshots_dir)

**Hash:** `123d9320891c...`
  - `IMG_1532.PNG` (archive_zip)
  - `screenshots/IMG_1532.PNG` (screenshots_dir)

**Hash:** `b108ab45d6d9...`
  - `IMG_1533.PNG` (archive_zip)
  - `screenshots/IMG_1533.PNG` (screenshots_dir)

**Hash:** `fc668da1b6bb...`
  - `IMG_1534.PNG` (archive_zip)
  - `screenshots/IMG_1534.PNG` (screenshots_dir)

**Hash:** `a64823aef53d...`
  - `IMG_1535.PNG` (archive_zip)
  - `screenshots/IMG_1535.PNG` (screenshots_dir)

**Hash:** `a462e8004d50...`
  - `IMG_1536.PNG` (archive_zip)
  - `screenshots/IMG_1536.PNG` (screenshots_dir)

**Hash:** `a5b7793b0f5f...`
  - `IMG_1537.PNG` (archive_zip)
  - `screenshots/IMG_1537.PNG` (screenshots_dir)

**Hash:** `6ff5a4e93c4a...`
  - `IMG_1538.PNG` (archive_zip)
  - `screenshots/IMG_1538.PNG` (screenshots_dir)

**Hash:** `574c8da63314...`
  - `IMG_1539.PNG` (archive_zip)
  - `screenshots/IMG_1539.PNG` (screenshots_dir)

**Hash:** `f02c65bbc3d8...`
  - `IMG_1540.PNG` (archive_zip)
  - `screenshots/IMG_1540.PNG` (screenshots_dir)

**Hash:** `19520955d9cf...`
  - `IMG_1541.PNG` (archive_zip)
  - `screenshots/IMG_1541.PNG` (screenshots_dir)

**Hash:** `df7d017ea4dd...`
  - `IMG_1542.PNG` (archive_zip)
  - `screenshots/IMG_1542.PNG` (screenshots_dir)

**Hash:** `7873725210e5...`
  - `IMG_1543.PNG` (archive_zip)
  - `screenshots/IMG_1543.PNG` (screenshots_dir)

**Hash:** `3763f5aab6b2...`
  - `IMG_1544.PNG` (archive_zip)
  - `screenshots/IMG_1544.PNG` (screenshots_dir)

**Hash:** `173317b1805b...`
  - `IMG_1545.PNG` (archive_zip)
  - `screenshots/IMG_1545.PNG` (screenshots_dir)

**Hash:** `0d7dbef8784b...`
  - `IMG_1546.PNG` (archive_zip)
  - `screenshots/IMG_1546.PNG` (screenshots_dir)

**Hash:** `2fd7393d0543...`
  - `IMG_1547.PNG` (archive_zip)
  - `screenshots/IMG_1547.PNG` (screenshots_dir)

---

## No Card Extraction Performed

This manifest documents file organization only.
No card names, quantities, or database entries have been created.
Extraction will proceed one screenshot at a time using `batches/cards_batch_XXX.json`.
