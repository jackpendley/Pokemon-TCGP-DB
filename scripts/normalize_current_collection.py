#!/usr/bin/env python3
"""
Normalize collection.json to clean machine-readable outputs.

Reads collection.json (JSONC-style, supports // comments).
Writes:
    data/current/collection_normalized.json  — clean JSON, no comments, added generated fields
    data/current/collection_summary.json     — aggregated statistics
    review/current_collection_summary.md     — human-readable summary report

Usage:
    python3 scripts/normalize_current_collection.py
"""

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COLLECTION_JSON = ROOT / "collection.json"
OUT_DIR = ROOT / "data" / "current"
NORMALIZED_JSON = OUT_DIR / "collection_normalized.json"
SUMMARY_JSON = OUT_DIR / "collection_summary.json"
REVIEW_MD = ROOT / "review" / "current_collection_summary.md"


def strip_comments(text):
    return re.sub(r"//[^\n]*", "", text)


def normalize_name(name):
    s = name.lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = re.sub(r"\s+", "_", s).strip("_")
    return s


def make_entry_id(entry, seen_ids):
    base = normalize_name(entry.get("name", "unknown"))
    variant = entry.get("variant", "")
    if variant:
        base = base + "_" + normalize_name(variant)
    candidate = base
    n = 2
    while candidate in seen_ids:
        candidate = f"{base}_v{n}"
        n += 1
    seen_ids.add(candidate)
    return candidate


def stage_label(stage):
    if stage == 0:
        return "Basic"
    if stage == 1:
        return "Stage 1"
    if stage == 2:
        return "Stage 2"
    return f"Stage {stage}"


def load_collection():
    if not COLLECTION_JSON.exists():
        print(f"ERROR: {COLLECTION_JSON} not found", file=sys.stderr)
        sys.exit(1)
    raw = COLLECTION_JSON.read_text(encoding="utf-8")
    cleaned = strip_comments(raw)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"ERROR: collection.json parse error: {e}", file=sys.stderr)
        sys.exit(1)


def build_normalized(collection):
    seen_ids = set()
    normalized = []
    for entry in collection:
        new_entry = dict(entry)
        new_entry["normalized_name"] = normalize_name(entry.get("name", ""))
        new_entry["entry_id"] = make_entry_id(entry, seen_ids)
        if "is_ex" not in new_entry:
            new_entry["is_ex"] = False
        if isinstance(new_entry.get("stage"), int):
            new_entry["stage_label"] = stage_label(new_entry["stage"])
        normalized.append(new_entry)
    return normalized


def build_summary(normalized, meta):
    total_quantity = sum(e["count"] for e in normalized)
    unique_entries = len(normalized)

    by_card_type = Counter()
    by_pokemon_type = Counter()
    by_stage = Counter()
    ex_entries = 0
    ex_quantity = 0
    trainer_subtypes = Counter()
    name_totals = Counter()

    for e in normalized:
        ct = e.get("card_type", "Unknown")
        by_card_type[ct] += e["count"]
        name_totals[e["name"]] += e["count"]

        if ct == "Pokemon":
            ptype = e.get("type", "Unknown")
            by_pokemon_type[ptype] += e["count"]
            stage = e.get("stage")
            if stage is not None:
                by_stage[stage_label(stage)] += e["count"]
            if e.get("is_ex"):
                ex_entries += 1
                ex_quantity += e["count"]

        if ct == "Trainer":
            sub = e.get("trainer_subtype", "Unknown")
            trainer_subtypes[sub] += e["count"]

    # Top cards by total count
    top_cards = sorted(name_totals.items(), key=lambda x: -x[1])[:15]

    # Duplicate names (entries with same name appear more than once)
    name_entry_count = Counter(e["name"] for e in normalized)
    variant_names = {n: c for n, c in name_entry_count.items() if c > 1}

    # Evolution lines (infer from names)
    evolution_groups = _infer_evolution_lines(normalized)

    # Deck readiness
    deck_readiness = _assess_deck_readiness(normalized)

    return {
        "meta": meta,
        "total_quantity": total_quantity,
        "meta_total_cards": meta.get("total_cards"),
        "count_matches_meta": total_quantity == meta.get("total_cards"),
        "unique_entries": unique_entries,
        "by_card_type": dict(by_card_type),
        "by_pokemon_type": dict(by_pokemon_type),
        "by_stage": dict(by_stage),
        "ex_entries": ex_entries,
        "ex_quantity": ex_quantity,
        "trainer_subtypes": dict(trainer_subtypes),
        "top_cards_by_count": top_cards,
        "variant_names": variant_names,
        "evolution_groups": evolution_groups,
        "deck_readiness": deck_readiness,
    }


EVOLUTION_LINES = [
    ["Charmander", "Charmeleon", "Charizard"],
    ["Charmander", "Charmeleon", "Mega Charizard Y ex"],
    ["Tepig", "Pignite", "Incineroar ex"],
    ["Bulbasaur", "Ivysaur", "Mega Venusaur ex"],
    ["Treecko", "Grovyle", "Sceptile"],
    ["Sewaddle", "Swadloon", "Leavanny"],
    ["Sobble", "Drizzile", "Inteleon"],
    ["Magnemite", "Magneton", "Magnezone ex"],
    ["Starly", "Staravia", "Staraptor"],
    ["Lillipup", "Herdier", "Stoutland"],
    ["Darumaka", "Darmanitan"],
    ["Zubat", "Golbat", "Crobat"],
    ["Rattata", "Raticate"],
    ["Minccino", "Cinccino"],
    ["Sandshrew", "Sandslash"],
    ["Cubone", "Marowak ex"],
    ["Zygarde 10% Forme", "Zygarde 50% Forme", "Zygarde ex"],
    ["Misdreavus", "Mismagius"],
    ["Spritzee", "Aromatisse"],
    ["Hatenna", "Hattrem"],
    ["Grimer", "Garbodor"],
    ["Trubbish", "Garbodor"],
    ["Vullaby", "Mandibuzz"],
    ["Zorua", "Zoroark"],
    ["Riolu", "Lucario"],
    ["Helioptile", "Heliolisk"],
    ["Porygon", "Porygon2"],
    ["Eevee", "Vaporeon ex"],
    ["Bronzor", "Bronzong"],
    ["Pawniard", "Bisharp"],
]


def _infer_evolution_lines(normalized):
    owned_names = {e["name"] for e in normalized}
    name_to_count = {}
    for e in normalized:
        name_to_count[e["name"]] = name_to_count.get(e["name"], 0) + e["count"]

    lines = []
    for line in EVOLUTION_LINES:
        present = [n for n in line if n in owned_names]
        missing = [n for n in line if n not in owned_names]
        if not present:
            continue
        lines.append({
            "line": line,
            "owned": present,
            "missing": missing,
            "complete": len(missing) == 0,
        })
    return lines


def _assess_deck_readiness(normalized):
    name_to_count = {}
    for e in normalized:
        name_to_count[e["name"]] = name_to_count.get(e["name"], 0) + e["count"]

    notable_ex = [
        e["name"] for e in normalized
        if e.get("is_ex") and e["count"] >= 1
    ]

    trainers = [e for e in normalized if e.get("card_type") == "Trainer"]
    trainer_count = sum(e["count"] for e in trainers)

    strong_lines = []
    partial_lines = []
    for e in normalized:
        name = e["name"]
        line = next((l for l in EVOLUTION_LINES if name in l), None)
        if not line:
            continue
        complete = all(n in name_to_count for n in line)
        label = " → ".join(line)
        if complete and label not in strong_lines:
            strong_lines.append(label)
        elif not complete and label not in partial_lines:
            partial_lines.append(label)

    return {
        "notable_ex_cards": notable_ex,
        "strong_evolution_lines": list(dict.fromkeys(strong_lines)),
        "partial_evolution_lines": list(dict.fromkeys(partial_lines)),
        "total_trainer_cards": trainer_count,
    }


def write_markdown(summary, out_path):
    meta = summary["meta"]
    lines = []
    lines.append("# Current Collection Summary")
    lines.append("")
    lines.append(f"**Last updated:** {meta.get('last_updated', 'unknown')}  ")
    lines.append(f"**Format:** {meta.get('format', 'unknown')}  ")
    lines.append(f"**Meta declared total:** {summary['meta_total_cards']}  ")
    lines.append(f"**Actual card count:** {summary['total_quantity']}  ")
    lines.append(f"**Unique entries:** {summary['unique_entries']}  ")

    if not summary["count_matches_meta"]:
        diff = summary["total_quantity"] - summary["meta_total_cards"]
        lines.append("")
        lines.append(f"> **WARNING:** Actual count ({summary['total_quantity']}) does not match "
                     f"meta.total_cards ({summary['meta_total_cards']}). "
                     f"Difference: {diff:+d}. "
                     f"User should verify collection.json is complete.")

    lines.append("")
    lines.append("## By Card Type")
    lines.append("")
    lines.append("| Card Type | Count |")
    lines.append("|---|---|")
    for k, v in sorted(summary["by_card_type"].items()):
        lines.append(f"| {k} | {v} |")

    lines.append("")
    lines.append("## By Pokémon Type")
    lines.append("")
    lines.append("| Type | Count |")
    lines.append("|---|---|")
    for k, v in sorted(summary["by_pokemon_type"].items(), key=lambda x: -x[1]):
        lines.append(f"| {k} | {v} |")

    lines.append("")
    lines.append("## By Stage")
    lines.append("")
    lines.append("| Stage | Count |")
    lines.append("|---|---|")
    for k, v in sorted(summary["by_stage"].items()):
        lines.append(f"| {k} | {v} |")

    lines.append("")
    lines.append("## Trainer Cards")
    lines.append("")
    lines.append("| Subtype | Count |")
    lines.append("|---|---|")
    for k, v in sorted(summary["trainer_subtypes"].items(), key=lambda x: -x[1]):
        lines.append(f"| {k} | {v} |")

    lines.append("")
    lines.append(f"## Ex Pokémon")
    lines.append("")
    lines.append(f"- **Ex entries:** {summary['ex_entries']}")
    lines.append(f"- **Ex card count:** {summary['ex_quantity']}")
    lines.append("")
    lines.append("| Ex Card |")
    lines.append("|---|")
    for name in sorted(summary["deck_readiness"]["notable_ex_cards"]):
        lines.append(f"| {name} |")

    lines.append("")
    lines.append("## Top Cards by Total Count")
    lines.append("")
    lines.append("| Card | Total Count |")
    lines.append("|---|---|")
    for name, total in summary["top_cards_by_count"]:
        lines.append(f"| {name} | {total} |")

    lines.append("")
    lines.append("## Variant Cards (Same Name, Different Version)")
    lines.append("")
    if summary["variant_names"]:
        lines.append("| Card Name | Variant Entries |")
        lines.append("|---|---|")
        for name, ct in sorted(summary["variant_names"].items(), key=lambda x: -x[1]):
            lines.append(f"| {name} | {ct} entries |")
    else:
        lines.append("None.")

    lines.append("")
    lines.append("## Deck Readiness")
    lines.append("")
    dr = summary["deck_readiness"]

    lines.append("### Complete Evolution Lines")
    lines.append("")
    for ln in dr["strong_evolution_lines"]:
        lines.append(f"- {ln}")
    if not dr["strong_evolution_lines"]:
        lines.append("None.")

    lines.append("")
    lines.append("### Partial Evolution Lines (Missing at Least One Stage)")
    lines.append("")
    for ln in dr["partial_evolution_lines"][:20]:
        lines.append(f"- {ln}")
    if not dr["partial_evolution_lines"]:
        lines.append("None.")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    print(f"\n=== normalize_current_collection.py ===")
    print(f"  Reading: {COLLECTION_JSON}")

    data = load_collection()
    meta = data.get("meta", {})
    collection = data.get("collection", [])
    print(f"  Entries: {len(collection)}, Meta total: {meta.get('total_cards')}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (ROOT / "review").mkdir(exist_ok=True)

    normalized = build_normalized(collection)
    actual_total = sum(e["count"] for e in normalized)

    output = {
        "meta": meta,
        "generated_note": "Normalized output — do not edit. Source: collection.json",
        "actual_total_quantity": actual_total,
        "unique_entries": len(normalized),
        "collection": normalized,
    }

    NORMALIZED_JSON.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  Written: {NORMALIZED_JSON}")

    summary = build_summary(normalized, meta)
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  Written: {SUMMARY_JSON}")

    write_markdown(summary, REVIEW_MD)
    print(f"  Written: {REVIEW_MD}")

    print(f"\n  Actual total quantity: {actual_total}")
    if actual_total != meta.get("total_cards"):
        print(f"  WARNING: actual count ({actual_total}) != meta.total_cards ({meta.get('total_cards')})")
        print(f"           Discrepancy of {abs(actual_total - meta.get('total_cards', 0))} cards.")
        print(f"           collection.json may be incomplete. User should verify.")
    print(f"\nDone.")


if __name__ == "__main__":
    main()
