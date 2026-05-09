#!/usr/bin/env python3
"""
Download and cache a Pokémon TCG Pocket card reference index.

Outputs:
    data/reference/card_reference.json   — normalized card objects
    data/reference/card_names.txt        — one card name per line (for fuzzy matching)

Usage:
    python3 scripts/build_card_reference.py

If the online download fails, you can supply a local JSON file instead:
    python3 scripts/build_card_reference.py --local path/to/cards.json

The local file must be a JSON array of objects that each have at least a
"name" field.  All other fields are optional and will be extracted when
present.
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
        "  1. Download or create a JSON file containing a list of card objects\n"
        "     (each object must have at minimum a 'name' field).\n"
        "  2. Run:\n"
        "       python3 scripts/build_card_reference.py --local path/to/cards.json\n"
    )


def main():
    parser = argparse.ArgumentParser(description="Build PTCGP card reference index.")
    parser.add_argument(
        "--local",
        type=Path,
        metavar="FILE",
        help="Use a local JSON file instead of downloading.",
    )
    args = parser.parse_args()

    REFERENCE_DIR.mkdir(parents=True, exist_ok=True)

    raw = load_from_local(args.local) if args.local else load_from_url(REFERENCE_URL)
    print(f"  Loaded {len(raw)} raw card entries.")

    normalized = []
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
        names.append(str(name))

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
