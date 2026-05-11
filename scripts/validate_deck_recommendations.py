#!/usr/bin/env python3
"""
Validate deck-recommendations.jsx against collection.json.

Parses deck-recommendations.jsx as text (no React execution).
Extracts DECKS and PACK_RECS by regex.
Compares each deck's card requirements against the 380-card collection.

Outputs:
    review/deck_recommendation_validation.md
    data/exports/deck_recommendation_validation.json

Usage:
    python3 scripts/validate_deck_recommendations.py
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COLLECTION_JSON = ROOT / "collection.json"
JSX_FILE = ROOT / "deck-recommendations.jsx"
OUT_MD = ROOT / "review" / "deck_recommendation_validation.md"
OUT_JSON = ROOT / "data" / "exports" / "deck_recommendation_validation.json"


def strip_comments(text):
    return re.sub(r"//[^\n]*", "", text)


def load_collection():
    if not COLLECTION_JSON.exists():
        print(f"ERROR: {COLLECTION_JSON} not found", file=sys.stderr)
        sys.exit(1)
    raw = COLLECTION_JSON.read_text(encoding="utf-8")
    cleaned = strip_comments(raw)
    data = json.loads(cleaned)
    name_totals = {}
    for entry in data.get("collection", []):
        name = entry.get("name", "")
        name_totals[name] = name_totals.get(name, 0) + entry.get("count", 0)
    return name_totals, data.get("meta", {})


def normalize_name(name):
    return re.sub(r"\s+", " ", name.strip()).lower()


def build_lookup(name_totals):
    return {normalize_name(k): v for k, v in name_totals.items()}


def lookup_owned(name, lookup):
    norm = normalize_name(name)
    if norm in lookup:
        return lookup[norm], "exact"
    # Try partial match (first word)
    for key, val in lookup.items():
        if norm in key or key in norm:
            return val, f"partial_match:{key}"
    return 0, "no_match"


def extract_deck_blocks(jsx_text):
    """
    Extract the DECKS object from the JSX file.
    Returns raw text of the object for further parsing.
    """
    m = re.search(r"const\s+DECKS\s*=\s*\{", jsx_text)
    if not m:
        return None
    start = m.start()
    depth = 0
    for i in range(m.start(), len(jsx_text)):
        if jsx_text[i] == "{":
            depth += 1
        elif jsx_text[i] == "}":
            depth -= 1
            if depth == 0:
                return jsx_text[start:i+1]
    return None


def extract_pack_recs_block(jsx_text):
    m = re.search(r"const\s+PACK_RECS\s*=\s*\[", jsx_text)
    if not m:
        return None
    start = m.start()
    depth = 0
    for i in range(m.start(), len(jsx_text)):
        if jsx_text[i] == "[":
            depth += 1
        elif jsx_text[i] == "]":
            depth -= 1
            if depth == 0:
                return jsx_text[start:i+1]
    return None


def extract_cards_from_deck(deck_text):
    """
    Extract card list from a deck block: { name: "...", qty: N, ... }
    """
    pattern = r'\{\s*name:\s*"([^"]+)",\s*qty:\s*(\d+)'
    return [(m.group(1), int(m.group(2))) for m in re.finditer(pattern, deck_text)]


def extract_deck_meta(deck_text):
    """Extract id, name, tier, missing list from a deck block text."""
    id_m = re.search(r'id:\s*"([^"]+)"', deck_text)
    name_m = re.search(r'name:\s*"([^"]+)"', deck_text)
    tier_m = re.search(r'tier:\s*"([^"]+)"', deck_text)
    missing_items = re.findall(r'"(\d+[×x]\s*[^"]+)"', deck_text)

    have_note_m = re.search(r'haveNote:\s*"([^"]+)"', deck_text)
    have_note = have_note_m.group(1) if have_note_m else None

    return {
        "id": id_m.group(1) if id_m else "unknown",
        "name": name_m.group(1) if name_m else "unknown",
        "tier": tier_m.group(1) if tier_m else "?",
        "missing": missing_items,
        "have_note": have_note,
    }


def split_deck_objects(block_text):
    """
    Split DECKS.buildable/chase sections and individual deck objects.
    Returns [(category, deck_text), ...]
    """
    # Find buildable and chase sections
    results = []
    for category in ("buildable", "chase"):
        m = re.search(rf"{category}:\s*\[", block_text)
        if not m:
            continue
        start = m.end() - 1  # position of '['
        depth = 0
        for i in range(start, len(block_text)):
            if block_text[i] == "[":
                depth += 1
            elif block_text[i] == "]":
                depth -= 1
                if depth == 0:
                    section = block_text[start:i+1]
                    break

        # Within this section, find individual deck objects (top-level { })
        depth = 0
        obj_start = None
        for i in range(len(section)):
            if section[i] == "{":
                if depth == 0:
                    obj_start = i
                depth += 1
            elif section[i] == "}":
                depth -= 1
                if depth == 0 and obj_start is not None:
                    results.append((category, section[obj_start:i+1]))
                    obj_start = None

    return results


def extract_pack_recs(block_text):
    pattern = (
        r'\{\s*priority:\s*(\d+),\s*card:\s*"([^"]+)",\s*deck:\s*"([^"]+)",\s*note:\s*"([^"]+)"\s*\}'
    )
    recs = []
    for m in re.finditer(pattern, block_text):
        recs.append({
            "priority": int(m.group(1)),
            "card": m.group(2),
            "deck": m.group(3),
            "note": m.group(4),
        })
    return recs


def validate_deck(deck_meta, cards, lookup, category):
    result = {
        "id": deck_meta["id"],
        "name": deck_meta["name"],
        "tier": deck_meta["tier"],
        "category": category,
        "cards": [],
        "fully_buildable": True,
        "missing_cards": [],
        "questionable_names": [],
        "stated_missing": deck_meta["missing"],
        "have_note": deck_meta["have_note"],
        "discrepancies": [],
    }

    for card_name, qty_required in cards:
        owned, match_type = lookup_owned(card_name, lookup)
        if match_type == "no_match":
            status = "missing"
            result["questionable_names"].append(card_name)
        elif owned >= qty_required:
            status = "owned_enough"
        else:
            status = "short"

        if status in ("missing", "short"):
            result["fully_buildable"] = False
            result["missing_cards"].append({
                "name": card_name,
                "required": qty_required,
                "owned": owned,
                "short_by": qty_required - owned,
            })

        result["cards"].append({
            "name": card_name,
            "required": qty_required,
            "owned": owned,
            "status": status,
            "match_type": match_type,
        })

    # For chase decks: check if stated missing matches actual
    if category == "chase" and deck_meta["missing"]:
        for stated in deck_meta["missing"]:
            m = re.match(r"(\d+)[×x]\s*(.+)", stated.strip())
            if not m:
                continue
            qty_needed = int(m.group(1))
            name = m.group(2).strip()
            owned, _ = lookup_owned(name, lookup)
            short_by = qty_needed - owned
            if short_by != qty_needed - owned:
                result["discrepancies"].append(
                    f"Stated missing '{stated}' but actual owned={owned}"
                )

    return result


def write_markdown(results, pack_rec_results, out_path):
    lines = []
    lines.append("# Deck Recommendation Validation")
    lines.append("")
    lines.append("Validates `deck-recommendations.jsx` against `collection.json`.")
    lines.append("")

    for category in ("buildable", "chase"):
        lines.append(f"## {category.title()} Decks")
        lines.append("")
        for deck in results:
            if deck["category"] != category:
                continue
            buildable_str = "✅ Fully buildable" if deck["fully_buildable"] else "⚠️ Not fully buildable"
            lines.append(f"### {deck['name']} (Tier {deck['tier']})")
            lines.append("")
            lines.append(f"**Status:** {buildable_str}")
            lines.append("")

            if deck["have_note"]:
                lines.append(f"**Have note:** {deck['have_note']}")
                lines.append("")

            lines.append("| Card | Required | Owned | Status |")
            lines.append("|---|---|---|---|")
            for c in deck["cards"]:
                status_icon = {
                    "owned_enough": "✅",
                    "short": "⚠️ short",
                    "missing": "❌ missing",
                }.get(c["status"], c["status"])
                lines.append(f"| {c['name']} | {c['required']} | {c['owned']} | {status_icon} |")

            if deck["missing_cards"]:
                lines.append("")
                lines.append("**Missing or short:**")
                for m in deck["missing_cards"]:
                    lines.append(f"- {m['name']}: need {m['required']}, have {m['owned']} (short by {m['short_by']})")

            if deck["questionable_names"]:
                lines.append("")
                lines.append("**Possible name mismatches (not found in collection):**")
                for n in deck["questionable_names"]:
                    lines.append(f"- {n!r}")

            if deck["stated_missing"] and category == "chase":
                lines.append("")
                lines.append(f"**Stated missing in JSX:** {', '.join(deck['stated_missing'])}")

            if deck["discrepancies"]:
                lines.append("")
                lines.append("**Discrepancies:**")
                for d in deck["discrepancies"]:
                    lines.append(f"- {d}")

            lines.append("")

    lines.append("## Pack Recommendations Validation")
    lines.append("")
    lines.append("| Priority | Target Card | For Deck | Status | Note |")
    lines.append("|---|---|---|---|---|")
    for pr in pack_rec_results:
        lines.append(
            f"| {pr['priority']} | {pr['card']} | {pr['deck']} | {pr['status']} | {pr['note']} |"
        )
    lines.append("")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    print(f"\n=== validate_deck_recommendations.py ===")

    if not JSX_FILE.exists():
        print(f"ERROR: {JSX_FILE} not found", file=sys.stderr)
        sys.exit(1)

    name_totals, meta = load_collection()
    lookup = build_lookup(name_totals)
    print(f"  Collection: {len(name_totals)} unique names, {sum(name_totals.values())} total cards")

    jsx_text = JSX_FILE.read_text(encoding="utf-8")
    print(f"  JSX file: {len(jsx_text)} chars")

    decks_block = extract_deck_blocks(jsx_text)
    if not decks_block:
        print("ERROR: Could not find DECKS object in deck-recommendations.jsx", file=sys.stderr)
        sys.exit(1)

    deck_objects = split_deck_objects(decks_block)
    print(f"  Found {len(deck_objects)} deck objects")

    results = []
    for category, deck_text in deck_objects:
        deck_meta = extract_deck_meta(deck_text)
        cards = extract_cards_from_deck(deck_text)
        result = validate_deck(deck_meta, cards, lookup, category)
        results.append(result)

        status = "BUILDABLE" if result["fully_buildable"] else f"MISSING {len(result['missing_cards'])} card(s)"
        print(f"  [{category:10s}] {result['name']} (Tier {result['tier']}): {status}")

    pack_recs_block = extract_pack_recs_block(jsx_text)
    pack_rec_results = []
    if pack_recs_block:
        recs = extract_pack_recs(pack_recs_block)
        for rec in recs:
            owned, match_type = lookup_owned(rec["card"], lookup)
            if match_type == "no_match":
                status = "❌ not in collection"
            elif owned >= 2:
                status = f"✅ owned enough ({owned})"
            elif owned == 1:
                status = f"⚠️ have {owned}, likely need 2"
            else:
                status = f"❌ none owned"
            pack_rec_results.append({**rec, "owned": owned, "status": status})
    else:
        print("  WARNING: Could not find PACK_RECS block")

    (ROOT / "review").mkdir(exist_ok=True)
    (ROOT / "data" / "exports").mkdir(parents=True, exist_ok=True)

    write_markdown(results, pack_rec_results, OUT_MD)
    print(f"\n  Written: {OUT_MD}")

    out_data = {
        "decks": results,
        "pack_recommendations": pack_rec_results,
    }
    OUT_JSON.write_text(json.dumps(out_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  Written: {OUT_JSON}")

    buildable_count = sum(1 for r in results if r["fully_buildable"])
    total_count = len(results)
    print(f"\n  {buildable_count}/{total_count} decks fully buildable from current collection")
    print(f"Done.")


if __name__ == "__main__":
    main()
