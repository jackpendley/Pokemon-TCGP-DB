#!/usr/bin/env python3
"""
Inventories screenshot image files from Archive.zip and screenshots/.

Outputs:
    screenshots_inventory.json  — machine-readable full inventory
    screenshots_manifest.md     — human-readable manifest

Does NOT modify, move, or delete any files.

Usage:
    python3 scripts/inventory_screenshots.py
"""

import hashlib
import json
import struct
import zipfile
from collections import defaultdict
from datetime import datetime
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCREENSHOTS_DIR = ROOT / "screenshots"
ARCHIVE_ZIP = ROOT / "Archive.zip"
INVENTORY_JSON = ROOT / "screenshots_inventory.json"
MANIFEST_MD = ROOT / "screenshots_manifest.md"

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


# ---------------------------------------------------------------------------
# Dimension readers (no external deps — PNG header decode + fallback)
# ---------------------------------------------------------------------------

def _dimensions_from_bytes(data: bytes, filename: str) -> tuple[int | None, int | None]:
    """Try Pillow first, fall back to PNG struct decode, then return None."""
    try:
        from PIL import Image  # type: ignore
        with Image.open(BytesIO(data)) as img:
            return img.size  # (width, height)
    except Exception:
        pass

    ext = Path(filename).suffix.lower()
    if ext == ".png":
        return _png_dimensions(data)

    return None, None


def _png_dimensions(data: bytes) -> tuple[int | None, int | None]:
    """Read width/height from PNG IHDR chunk (bytes 16–23)."""
    try:
        if data[:8] != b"\x89PNG\r\n\x1a\n":
            return None, None
        w, h = struct.unpack(">II", data[16:24])
        return w, h
    except Exception:
        return None, None


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------

def sha256_of_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# Collectors
# ---------------------------------------------------------------------------

def collect_from_dir(directory: Path) -> list[dict]:
    """Collect image entries from a directory tree (ignores __MACOSX / dot-files)."""
    entries = []
    if not directory.exists():
        return entries

    for path in sorted(directory.rglob("*")):
        if not path.is_file():
            continue
        # Skip macOS metadata junk
        if "__MACOSX" in path.parts or path.name.startswith("._"):
            continue
        if path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue

        data = path.read_bytes()
        w, h = _dimensions_from_bytes(data, path.name)
        digest = sha256_of_bytes(data)
        rel = path.relative_to(ROOT)

        entries.append({
            "filename": path.name,
            "source": "screenshots_dir",
            "path": str(rel),
            "size_bytes": len(data),
            "width": w,
            "height": h,
            "sha256": digest,
            "sha256_short": digest[:12],
        })

    return entries


def collect_from_zip(zip_path: Path) -> list[dict]:
    """Collect image entries from a zip archive (ignores __MACOSX / dot-files)."""
    entries = []
    if not zip_path.exists():
        return entries

    with zipfile.ZipFile(zip_path, "r") as zf:
        for info in sorted(zf.infolist(), key=lambda i: i.filename):
            name = info.filename
            # Skip directories and macOS metadata
            if name.endswith("/"):
                continue
            if "__MACOSX" in name or Path(name).name.startswith("._"):
                continue
            if Path(name).suffix.lower() not in IMAGE_EXTENSIONS:
                continue

            data = zf.read(name)
            w, h = _dimensions_from_bytes(data, name)
            digest = sha256_of_bytes(data)

            entries.append({
                "filename": Path(name).name,
                "source": "archive_zip",
                "path": name,
                "size_bytes": len(data),
                "width": w,
                "height": h,
                "sha256": digest,
                "sha256_short": digest[:12],
            })

    return entries


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def find_hash_duplicates(entries: list[dict]) -> dict[str, list[dict]]:
    """Return groups of entries sharing the same sha256 (exact byte duplicates)."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for e in entries:
        groups[e["sha256"]].append(e)
    return {h: g for h, g in groups.items() if len(g) > 1}


def find_basename_duplicates(entries: list[dict]) -> dict[str, list[dict]]:
    """Return groups of entries sharing the same filename across sources."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for e in entries:
        groups[e["filename"]].append(e)
    return {n: g for n, g in groups.items() if len(g) > 1}


def zip_vs_dir_redundancy(zip_entries: list[dict], dir_entries: list[dict]) -> dict:
    """Compare zip and dir contents by sha256."""
    zip_hashes = {e["sha256"] for e in zip_entries}
    dir_hashes = {e["sha256"] for e in dir_entries}
    zip_names = {e["filename"] for e in zip_entries}
    dir_names = {e["filename"] for e in dir_entries}

    return {
        "zip_count": len(zip_entries),
        "dir_count": len(dir_entries),
        "zip_only_hashes": sorted(zip_hashes - dir_hashes),
        "dir_only_hashes": sorted(dir_hashes - zip_hashes),
        "shared_hashes": len(zip_hashes & dir_hashes),
        "zip_only_names": sorted(zip_names - dir_names),
        "dir_only_names": sorted(dir_names - zip_names),
        "identical_content": zip_hashes == dir_hashes,
    }


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------

def write_inventory_json(all_entries, hash_dupes, name_dupes, redundancy, zip_entries, dir_entries):
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "total_images": len(all_entries),
        "archive_zip_images": len(zip_entries),
        "screenshots_dir_images": len(dir_entries),
        "exact_duplicate_groups": len(hash_dupes),
        "basename_duplicate_groups": len(name_dupes),
        "zip_vs_dir": redundancy,
        "entries": all_entries,
        "exact_duplicate_groups_detail": [
            {"sha256": h, "files": [{"source": e["source"], "path": e["path"]} for e in g]}
            for h, g in hash_dupes.items()
        ],
    }
    INVENTORY_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {INVENTORY_JSON.relative_to(ROOT)}")


def write_manifest_md(all_entries, hash_dupes, name_dupes, redundancy, zip_entries, dir_entries):
    lines = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines += [
        "# Screenshots Manifest",
        "",
        f"Generated: {now}",
        "",
        "---",
        "",
        "## Summary",
        "",
    ]
    unique_hashes = {e["sha256"] for e in all_entries}
    lines += [
        f"- **Total image entries scanned:** {len(all_entries)} (across all sources)",
        f"- **Unique images (by sha256):** {len(unique_hashes)}",
        f"- **In Archive.zip:** {len(zip_entries)} images",
        f"- **In screenshots/:** {len(dir_entries)} images (excluding `__MACOSX` metadata)",
        f"- **Exact duplicate pairs (by sha256):** {len(hash_dupes)} groups",
        f"- **Basename duplicates (same filename, different source):** {len(name_dupes)} groups",
        "",
    ]

    # Redundancy assessment
    lines += ["## Archive.zip vs screenshots/ Redundancy", ""]
    if redundancy["identical_content"]:
        lines += [
            "**Result: FULLY REDUNDANT.** Archive.zip and screenshots/ contain byte-for-byte identical image files.",
            "",
            "- `Archive.zip` is the compressed source (86 MB)",
            "- `screenshots/` is the extracted copy plus `__MACOSX/` metadata junk",
            "",
            "**Recommendation:** Keep `Archive.zip` as the canonical backup.",
            "The `screenshots/` directory is the working copy used for extraction.",
            "Both are gitignored. No action is required right now.",
            "After all extraction is complete and validated, `screenshots/` can be safely deleted",
            "since `Archive.zip` is a lossless backup of the same files.",
            "",
        ]
    else:
        zip_only = redundancy["zip_only_names"]
        dir_only = redundancy["dir_only_names"]
        lines += [
            "**Result: NOT FULLY REDUNDANT.** There are differences between the two sources.",
            "",
        ]
        if zip_only:
            lines += [f"- In zip only: {', '.join(zip_only)}"]
        if dir_only:
            lines += [f"- In screenshots/ only: {', '.join(dir_only)}"]
        lines += [""]

    # __MACOSX note
    lines += [
        "## __MACOSX Metadata",
        "",
        "`screenshots/__MACOSX/` contains 24 `._*.PNG` files — these are macOS AppleDouble",
        "resource fork metadata artifacts created when macOS zipped the files. They contain",
        "no image data and are safe to ignore. They are not counted in the image totals above.",
        "",
    ]

    # Image list (processing order = filename sort = IMG_1524 first)
    lines += [
        "---",
        "",
        "## Screenshot Inventory (Processing Order)",
        "",
        "Files are listed in filename order, which is the intended extraction sequence.",
        "",
        "No card extraction has been performed.",
        "",
        "| # | Filename | Source | Size | Dimensions | SHA256 (12) |",
        "|---|----------|--------|------|------------|-------------|",
    ]

    # Deduplicate entries by (filename, source) for the table
    seen = set()
    ordered = []
    for e in sorted(all_entries, key=lambda x: (x["filename"], x["source"])):
        key = (e["filename"], e["source"])
        if key not in seen:
            seen.add(key)
            ordered.append(e)

    # For the ordered list, prefer dir entries; if a filename appears in both, show dir first
    by_name: dict[str, list[dict]] = defaultdict(list)
    for e in ordered:
        by_name[e["filename"]].append(e)

    seq = 1
    for fname in sorted(by_name.keys()):
        group = by_name[fname]
        # Show dir entry if available, else zip
        entry = next((e for e in group if e["source"] == "screenshots_dir"), group[0])
        dims = f"{entry['width']}×{entry['height']}" if entry["width"] else "unknown"
        size_kb = entry["size_bytes"] // 1024
        lines.append(
            f"| {seq} | `{entry['filename']}` | {entry['source']} "
            f"| {size_kb} KB | {dims} | `{entry['sha256_short']}` |"
        )
        seq += 1

    lines += [""]

    # Duplicate groups
    lines += ["---", "", "## Exact Duplicate Groups (by SHA256)", ""]
    if not hash_dupes:
        lines += ["No exact duplicates found across all sources.", ""]
    else:
        for h, group in hash_dupes.items():
            lines += [f"**Hash:** `{h[:12]}...`"]
            for e in group:
                lines += [f"  - `{e['path']}` ({e['source']})"]
            lines += [""]

    lines += ["---", "", "## No Card Extraction Performed", ""]
    lines += [
        "This manifest documents file organization only.",
        "No card names, quantities, or database entries have been created.",
        "Extraction will proceed one screenshot at a time using `batches/cards_batch_XXX.json`.",
        "",
    ]

    MANIFEST_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {MANIFEST_MD.relative_to(ROOT)}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Collecting from Archive.zip ...")
    zip_entries = collect_from_zip(ARCHIVE_ZIP)
    print(f"  Found {len(zip_entries)} images in Archive.zip")

    print("Collecting from screenshots/ ...")
    dir_entries = collect_from_dir(SCREENSHOTS_DIR)
    print(f"  Found {len(dir_entries)} images in screenshots/")

    all_entries = zip_entries + dir_entries

    hash_dupes = find_hash_duplicates(all_entries)
    name_dupes = find_basename_duplicates(all_entries)
    redundancy = zip_vs_dir_redundancy(zip_entries, dir_entries)

    print(f"Exact duplicate groups: {len(hash_dupes)}")
    print(f"Basename duplicate groups: {len(name_dupes)}")
    print(f"zip == dir (identical content): {redundancy['identical_content']}")

    write_inventory_json(all_entries, hash_dupes, name_dupes, redundancy, zip_entries, dir_entries)
    write_manifest_md(all_entries, hash_dupes, name_dupes, redundancy, zip_entries, dir_entries)

    print("Done.")


if __name__ == "__main__":
    main()
