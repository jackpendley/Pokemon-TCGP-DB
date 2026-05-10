#!/usr/bin/env python3
"""
Conservatively enriches cards.json with metadata from local reference files.

Sources (in priority order):
    1. data/reference/external/external_card_reference.json  (primary: Limitless TCG Pocket)
    2. data/reference/card_reference.json                    (secondary: mixed sources)

Rules:
    - Never changes quantity.
    - Never deletes records.
    - Only fills fields currently "unknown" or missing.
    - Requires exact name match in trusted references.
    - Single match -> high confidence.
    - Multiple matches with unanimous metadata -> medium confidence (no set_code/card_number).
    - Multiple matches with disagreeing metadata -> ambiguous, skip.
    - No match -> unchanged.

Usage:
    python3 scripts/enrich_metadata.py --dry-run   # preview only
    python3 scripts/enrich_metadata.py             # apply changes
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CARDS_JSON = ROOT / "cards.json"
EXT_REF = ROOT / "data" / "reference" / "external" / "external_card_reference.json"
LOCAL_REF = ROOT / "data" / "reference" / "card_reference.json"
REPORT_MD = ROOT / "review" / "metadata_enrichment_report.md"
REPORT_JSON = ROOT / "data" / "exports" / "metadata_enrichment_report.json"

UNKNOWN_VALUES = {"unknown", "none", "null", "n/a", ""}

# Fields that can be filled from external reference when currently unknown
ENRICHABLE_FIELDS = [
    "card_category",
    "pokemon_type",
    "stage",
    "hp",
    "rarity",
]
# New fields added by enrichment
NEW_FIELDS = [
    "set_code",
    "card_number",
    "source_reference",
    "metadata_confidence",
    "metadata_notes",
]


def norm_name(s):
    s = str(s or "").strip().lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def is_unknown(v):
    if v is None:
        return True
    return str(v).strip().lower() in UNKNOWN_VALUES


def load_json(path, label):
    if not path.exists():
        print(f"  SKIP  {label} not found at {path}")
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        print(f"  OK    {label}: {len(data)} entries")
        return data
    except json.JSONDecodeError as exc:
        print(f"  WARN  {label} invalid JSON: {exc}")
        return None


def build_ext_index(ext_data):
    """Index external reference by normalized name."""
    index = defaultdict(list)
    if not ext_data:
        return index
    for entry in ext_data:
        n = norm_name(entry.get("name", ""))
        if n:
            index[n].append(entry)
    return index


def build_local_index(local_data):
    """Index local reference by normalized name."""
    index = defaultdict(list)
    if not local_data:
        return index
    for entry in local_data:
        n = norm_name(entry.get("name", ""))
        if n:
            index[n].append(entry)
    return index


def resolve_match(matches, source_label):
    """
    Given a list of reference matches for a card name, determine enrichment outcome.

    Returns:
        (outcome, enrichment_dict, notes)
        outcome: 'unique' | 'multi_agree' | 'multi_disagree' | 'no_match'
    """
    if not matches:
        return "no_match", {}, ""

    if len(matches) == 1:
        m = matches[0]
        enrich = {
            "card_category": m.get("card_category"),
            "pokemon_type": m.get("pokemon_type"),
            "stage": m.get("stage"),
            "hp": m.get("hp"),
            "rarity": m.get("rarity"),
            "set_code": m.get("set_code"),
            "card_number": m.get("number"),
            "source_reference": m.get("source_url"),
        }
        return "unique", enrich, f"Unique match in {source_label}"

    # Multiple matches: check if key fields agree
    cats = set(m.get("card_category") for m in matches)
    types = set(m.get("pokemon_type") for m in matches)
    stages = set(m.get("stage") for m in matches)
    is_exs = set(m.get("is_ex") for m in matches)
    rarities = set(m.get("rarity") for m in matches)
    hps = set(m.get("hp") for m in matches)

    if len(cats) == 1 and len(types) == 1 and len(stages) == 1 and len(is_exs) == 1:
        # Agreed on core metadata
        enrich = {
            "card_category": list(cats)[0],
            "pokemon_type": list(types)[0],
            "stage": list(stages)[0],
            "hp": list(hps)[0] if len(hps) == 1 else None,
            "rarity": list(rarities)[0] if len(rarities) == 1 else None,
            "set_code": None,
            "card_number": None,
            "source_reference": matches[0].get("source_url"),
        }
        n_sets = len(set(m.get("set_code") for m in matches))
        return "multi_agree", enrich, f"{len(matches)} matches in {n_sets} set(s) in {source_label}; core metadata unanimous"

    # Disagreement on core metadata
    disagreements = []
    if len(cats) > 1:
        disagreements.append(f"card_category={cats}")
    if len(types) > 1:
        disagreements.append(f"pokemon_type={types}")
    if len(stages) > 1:
        disagreements.append(f"stage={stages}")
    if len(is_exs) > 1:
        disagreements.append(f"is_ex={is_exs}")
    return "multi_disagree", {}, f"{len(matches)} matches in {source_label}; disagreements: {'; '.join(disagreements)}"


def apply_enrichment(card, enrich, confidence, notes, dry_run):
    """
    Apply enrichment fields to a card dict.

    Returns:
        fields_changed: list of (field, old_value, new_value)
    """
    changed = []

    # Enrich existing fields only when currently unknown
    for field in ENRICHABLE_FIELDS:
        new_val = enrich.get(field)
        if new_val is None:
            continue
        old_val = card.get(field)
        if is_unknown(old_val):
            if not dry_run:
                card[field] = new_val
            changed.append((field, old_val, new_val))

    # Add new fields (never overwrite existing non-unknown)
    for field in ("set_code", "card_number", "source_reference"):
        new_val = enrich.get(field)
        if new_val is None:
            continue
        old_val = card.get(field)
        if old_val is None or is_unknown(old_val):
            if not dry_run:
                card[field] = new_val
            changed.append((field, old_val, new_val))

    # Always set metadata tracking fields if we enriched anything
    if changed:
        if not dry_run:
            card["metadata_confidence"] = confidence
            existing_notes = card.get("metadata_notes", "")
            card["metadata_notes"] = (existing_notes + "; " + notes).strip("; ") if existing_notes else notes
        changed.append(("metadata_confidence", None, confidence))

    return changed


def enrich_cards(cards, ext_index, local_index, dry_run):
    stats = {
        "examined": 0,
        "enriched": 0,
        "fields_enriched": 0,
        "unique_match": 0,
        "multi_agree": 0,
        "multi_disagree": 0,
        "no_match": 0,
        "unchanged": 0,
        "warnings": [],
    }
    enriched_cards = []
    ambiguous_cards = []

    for card in cards:
        stats["examined"] += 1
        name = norm_name(card.get("card_name", ""))

        # Try external reference first
        ext_matches = ext_index.get(name, [])
        outcome, enrich, notes = resolve_match(ext_matches, "external_card_reference")

        # Fall back to local reference if no match
        if outcome == "no_match":
            local_matches = local_index.get(name, [])
            if local_matches:
                # Local reference has different field names
                adapted = []
                for m in local_matches:
                    adapted.append({
                        "card_category": "Pokemon" if m.get("is_ex") is not None else None,
                        "pokemon_type": m.get("type"),
                        "stage": m.get("stage"),
                        "hp": m.get("hp"),
                        "rarity": m.get("rarity"),
                        "set_code": m.get("set"),
                        "number": None,
                        "source_url": m.get("image_url"),
                        "is_ex": m.get("is_ex"),
                    })
                outcome, enrich, notes = resolve_match(adapted, "card_reference")

        if outcome == "no_match":
            stats["no_match"] += 1
            stats["unchanged"] += 1
            continue

        confidence = "high" if outcome == "unique" else "medium"

        if outcome == "multi_disagree":
            stats["multi_disagree"] += 1
            stats["unchanged"] += 1
            ambiguous_cards.append({
                "card_name": card.get("card_name"),
                "id": card.get("id"),
                "reason": notes,
            })
            continue

        if outcome == "unique":
            stats["unique_match"] += 1
        elif outcome == "multi_agree":
            stats["multi_agree"] += 1

        changed = apply_enrichment(card, enrich, confidence, notes, dry_run)

        if changed:
            stats["enriched"] += 1
            stats["fields_enriched"] += len([c for c in changed if c[0] != "metadata_confidence"])
            enriched_cards.append({
                "card_name": card.get("card_name"),
                "id": card.get("id"),
                "outcome": outcome,
                "confidence": confidence,
                "fields_changed": [(f, str(o), str(n)) for f, o, n in changed],
                "notes": notes,
            })
        else:
            stats["unchanged"] += 1

    return stats, enriched_cards, ambiguous_cards


def write_report(now, dry_run, stats, enriched_cards, ambiguous_cards, sources_used):
    mode = "DRY RUN" if dry_run else "APPLIED"

    md_lines = [
        f"# Metadata Enrichment Report ({mode})",
        "",
        f"Generated: {now}",
        "",
        "> Quantities were not changed. Enrichment is additive only.",
        "",
        "## Summary",
        "",
        "| Metric | Count |",
        "|---|---|",
        f"| Cards examined | {stats['examined']} |",
        f"| Cards enriched | {stats['enriched']} |",
        f"| Fields enriched | {stats['fields_enriched']} |",
        f"| Unique match | {stats['unique_match']} |",
        f"| Multi-match (agreed) | {stats['multi_agree']} |",
        f"| Multi-match (disagreed, skipped) | {stats['multi_disagree']} |",
        f"| No match | {stats['no_match']} |",
        f"| Unchanged | {stats['unchanged']} |",
        "",
        "## Sources Used",
        "",
    ]
    for s in sources_used:
        md_lines.append(f"- {s}")
    md_lines += [""]

    if enriched_cards:
        md_lines += [
            "## Enriched Cards (sample, up to 30)",
            "",
            "| Card Name | Outcome | Confidence | Fields Changed |",
            "|---|---|---|---|",
        ]
        for ec in enriched_cards[:30]:
            fields = ", ".join(f[0] for f in ec["fields_changed"] if f[0] != "metadata_confidence")
            md_lines.append(f"| {ec['card_name']} | {ec['outcome']} | {ec['confidence']} | {fields} |")
        if len(enriched_cards) > 30:
            md_lines.append(f"\n_...and {len(enriched_cards) - 30} more_")
        md_lines.append("")

    if ambiguous_cards:
        md_lines += [
            "## Ambiguous Cards Skipped",
            "",
            "| Card Name | Reason |",
            "|---|---|",
        ]
        for ac in ambiguous_cards:
            md_lines.append(f"| {ac['card_name']} | {ac['reason']} |")
        md_lines.append("")

    if stats["warnings"]:
        md_lines += ["## Warnings", ""]
        for w in stats["warnings"]:
            md_lines.append(f"- {w}")
        md_lines.append("")

    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    report_data = {
        "generated_at": now,
        "mode": mode,
        "quantities_changed": False,
        "sources_used": sources_used,
        "stats": stats,
        "enriched_cards": enriched_cards,
        "ambiguous_cards": ambiguous_cards,
    }
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report_data, indent=2, ensure_ascii=False), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Enrich cards.json metadata from trusted references")
    parser.add_argument("--dry-run", action="store_true", help="Preview enrichment without writing cards.json")
    args = parser.parse_args()

    dry_run = args.dry_run
    mode_label = "DRY RUN" if dry_run else "APPLY"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    print(f"\n=== enrich_metadata.py [{mode_label}] ===")
    print(f"Generated: {now}")
    print("\nLoading references...")

    if not CARDS_JSON.exists():
        print(f"ERROR  cards.json not found at {CARDS_JSON}", file=sys.stderr)
        sys.exit(1)
    cards = json.loads(CARDS_JSON.read_text(encoding="utf-8"))
    print(f"  OK    cards.json: {len(cards)} entries")

    ext_data = load_json(EXT_REF, "external_card_reference")
    local_data = load_json(LOCAL_REF, "card_reference")

    sources_used = []
    if ext_data:
        sources_used.append(f"external_card_reference.json ({len(ext_data)} entries, source: Limitless TCG Pocket)")
    if local_data:
        sources_used.append(f"card_reference.json ({len(local_data)} entries, source: mixed)")

    ext_index = build_ext_index(ext_data)
    local_index = build_local_index(local_data)

    print(f"\nRunning enrichment ({mode_label})...")
    stats, enriched_cards, ambiguous_cards = enrich_cards(cards, ext_index, local_index, dry_run)

    # Write updated cards.json only if not dry-run
    if not dry_run and stats["enriched"] > 0:
        CARDS_JSON.write_text(json.dumps(cards, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n  WRITTEN  cards.json ({len(cards)} entries)")

    write_report(now, dry_run, stats, enriched_cards, ambiguous_cards, sources_used)

    print(f"\n=== Results ===")
    print(f"  Examined:           {stats['examined']}")
    print(f"  Enriched:           {stats['enriched']}")
    print(f"  Fields enriched:    {stats['fields_enriched']}")
    print(f"  Unique match:       {stats['unique_match']}")
    print(f"  Multi agree:        {stats['multi_agree']}")
    print(f"  Multi disagree:     {stats['multi_disagree']} (skipped)")
    print(f"  No match:           {stats['no_match']}")
    print(f"  Unchanged:          {stats['unchanged']}")
    if stats["warnings"]:
        print(f"  Warnings:           {len(stats['warnings'])}")
        for w in stats["warnings"]:
            print(f"    - {w}")

    print(f"\nWritten: {REPORT_MD}")
    print(f"Written: {REPORT_JSON}")

    if dry_run:
        print(f"\nDRY RUN complete. Run without --dry-run to apply changes.")
    else:
        print(f"\nEnrichment complete.")


if __name__ == "__main__":
    main()
