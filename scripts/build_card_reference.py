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
