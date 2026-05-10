#!/usr/bin/env python3
"""
Download and cache a Pokémon TCG Pocket card reference index.

Outputs:
    data/reference/card_reference.json   — normalized card objects
    data/reference/card_names.txt        — one card name per line (for fuzzy matching)

Usage:
    python3 scripts/build_card_reference.py

If the online download fails, supply a local JSON file or a seed text file:
    python3 scripts/build_card_reference.py --local path/to/cards.json
    python3 scripts/build_card_reference.py --seed data/reference/manual_card_names_seed.txt

The --local file must be a JSON array of objects each with at least a "name" field.
The --seed file must be plain text with one card name per line (# comment lines ignored).
"""

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: 'requests' is required.  Install with:  python3 -m pip install requests")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Configuration — change REFERENCE_URL if a better community source becomes
# available.  The URL must return a JSON array of card objects.
# ---------------------------------------------------------------------------
REFERENCE_URL = (
    "https://raw.githubusercontent.com/chase-manning/pokemon-tcg-pocket-cards"
    "/main/v3/cards.json"
)

REFERENCE_DIR = Path("data/reference")
OUT_REFERENCE = REFERENCE_DIR / "card_reference.json"
OUT_NAMES = REFERENCE_DIR / "card_names.txt"
EXT_REFERENCE = REFERENCE_DIR / "external" / "external_card_reference.json"

# Fields to extract from each source card object.
# Keys are our output field names; values are candidate source field names to
# try in order (first match wins, empty string written if none found).
FIELD_MAP = {
    "card_id":   ["id", "card_id"],
    "name":      ["name", "card_name", "cardName"],
    "set":       ["set", "set_name", "expansion"],
    "pack":      ["pack", "pack_name"],
    "rarity":    ["rarity", "rarity_name"],
    "type":      ["type", "pokemon_type", "energy_type"],
    "hp":        ["hp", "hit_points"],
    "stage":     ["stage", "evolution_stage"],
    "is_ex":     ["is_ex", "ex"],
    "image_url": ["image", "image_url", "imageUrl"],
}


def normalize_name(name: str) -> str:
    name = name.lower()
    name = re.sub(r"[^a-z0-9 ]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def extract_field(src: dict, candidates: list):
    for key in candidates:
        if key in src:
            return src[key]
    return None


def build_entry(src: dict) -> dict:
    entry = {}
    for out_key, candidates in FIELD_MAP.items():
        entry[out_key] = extract_field(src, candidates)
    entry["source"] = REFERENCE_URL
    return entry


def load_from_url(url: str) -> list:
    print(f"Fetching card reference from:\n  {url}")
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
    except requests.exceptions.ConnectionError:
        print(
            "\nERROR: Could not connect to the reference URL.  Check your internet connection."
        )
        _print_local_instructions()
        sys.exit(1)
    except requests.exceptions.HTTPError as exc:
        print(f"\nERROR: HTTP error fetching reference: {exc}")
        _print_local_instructions()
        sys.exit(1)
    except requests.exceptions.Timeout:
        print("\nERROR: Request timed out after 30 seconds.")
        _print_local_instructions()
        sys.exit(1)

    try:
        data = resp.json()
    except ValueError:
        print("\nERROR: Response was not valid JSON.")
        _print_local_instructions()
        sys.exit(1)

    if not isinstance(data, list):
        # Some APIs wrap the array; try common wrapper keys.
        for key in ("cards", "data", "results"):
            if isinstance(data, dict) and isinstance(data.get(key), list):
                data = data[key]
                break
        else:
            print(
                "\nERROR: Expected a JSON array (or a dict with a 'cards'/'data'/'results' key)."
            )
            _print_local_instructions()
            sys.exit(1)

    return data


def load_from_seed(path: Path) -> list:
    if not path.exists():
        print(f"ERROR: Seed file not found: {path}")
        sys.exit(1)
    lines = path.read_text(encoding="utf-8").splitlines()
    names = [ln.strip() for ln in lines if ln.strip() and not ln.strip().startswith("#")]
    if not names:
        print(f"ERROR: No card names found in seed file: {path}")
        sys.exit(1)
    print(f"  Loaded {len(names)} names from seed file: {path}")
    return [{"name": name, "_seed": True} for name in names]


def load_from_local(path: Path) -> list:
    if not path.exists():
        print(f"ERROR: Local file not found: {path}")
        sys.exit(1)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        print(f"ERROR: Could not parse {path}: {exc}")
        sys.exit(1)
    if not isinstance(data, list):
        for key in ("cards", "data", "results"):
            if isinstance(data, dict) and isinstance(data.get(key), list):
                return data[key]
        print("ERROR: Local file must contain a JSON array of card objects.")
        sys.exit(1)
    return data


def _print_local_instructions():
    print(
        "\nTo provide a local card list instead:\n"
        "  Option A — local JSON (array of objects with a 'name' field):\n"
        "       python3 scripts/build_card_reference.py --local path/to/cards.json\n"
        "  Option B — seed text file (one card name per line):\n"
        "       python3 scripts/build_card_reference.py --seed data/reference/manual_card_names_seed.txt\n"
    )


def load_external(path: Path) -> list:
    """Load external reference JSON (from build_external_reference.py output)."""
    if not path.exists():
        print(f"  WARN: External reference not found at {path}. Skipping --merge-external.")
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        print(f"  WARN: Could not parse external reference: {exc}")
        return []
    if not isinstance(data, list):
        print("  WARN: External reference is not a list. Skipping.")
        return []
    print(f"  Loaded {len(data)} external card entries from {path}")
    return data


def build_external_entry(src: dict) -> dict:
    """Convert external reference card to internal schema."""
    name = src.get("name", "")
    return {
        "card_id": f"{src.get('set_code','?')}_{src.get('number','?')}",
        "name": name,
        "set": src.get("set_code"),
        "pack": None,
        "rarity": src.get("rarity"),
        "type": src.get("pokemon_type"),
        "hp": src.get("hp"),
        "stage": src.get("stage"),
        "is_ex": src.get("is_ex", False),
        "image_url": src.get("source_url"),
        "source": "limitless",
        "normalized_name": normalize_name(name),
    }


def main():
    parser = argparse.ArgumentParser(description="Build PTCGP card reference index.")
    parser.add_argument(
        "--local",
        type=Path,
        metavar="FILE",
        help="Use a local JSON file instead of downloading.",
    )
    parser.add_argument(
        "--seed",
        type=Path,
        metavar="FILE",
        help="Use a plain-text seed file (one card name per line) as fallback reference.",
    )
    parser.add_argument(
        "--merge-external",
        action="store_true",
        help=(
            "Merge external reference data from "
            f"{EXT_REFERENCE} into card_reference.json and card_names.txt."
        ),
    )
    args = parser.parse_args()

    if args.local and args.seed:
        print("ERROR: Specify either --local or --seed, not both.")
        sys.exit(1)

    REFERENCE_DIR.mkdir(parents=True, exist_ok=True)

    if args.local:
        raw = load_from_local(args.local)
    elif args.seed:
        raw = load_from_seed(args.seed)
    else:
        raw = load_from_url(REFERENCE_URL)
    print(f"  Loaded {len(raw)} raw card entries.")

    normalized = []
    seen_names: set[str] = set()
    names = []
    for src in raw:
        if not isinstance(src, dict):
            continue
        entry = build_entry(src)
        name = entry.get("name")
        if not name:
            continue
        entry["normalized_name"] = normalize_name(str(name))
        normalized.append(entry)
        seen_names.add(entry["normalized_name"])
        names.append(str(name))

    if args.merge_external:
        ext_raw = load_external(EXT_REFERENCE)
        ext_added = 0
        for ext_src in ext_raw:
            if not isinstance(ext_src, dict):
                continue
            ext_name = ext_src.get("name", "").strip()
            if not ext_name:
                continue
            norm = normalize_name(ext_name)
            if norm in seen_names:
                continue  # Already present — skip to avoid duplicates
            entry = build_external_entry(ext_src)
            normalized.append(entry)
            seen_names.add(norm)
            names.append(ext_name)
            ext_added += 1
        print(f"  Merged {ext_added} new names from external reference.")

    if not normalized:
        print("ERROR: No cards with a 'name' field were found in the source data.")
        sys.exit(1)

    OUT_REFERENCE.write_text(json.dumps(normalized, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_NAMES.write_text("\n".join(names) + "\n", encoding="utf-8")

    print(f"  Wrote {len(normalized)} cards  →  {OUT_REFERENCE}")
    print(f"  Wrote {len(names)} names     →  {OUT_NAMES}")
    print("Done.")


if __name__ == "__main__":
    main()
