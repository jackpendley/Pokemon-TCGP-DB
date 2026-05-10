#!/usr/bin/env python3
"""
Conservatively upgrades owned card pack coverage by applying safe resolution rules.

Safe resolution rules applied:

    Rule D — name-only unanimous pack match:
        If all records in pack_sources.json that share the card name (normalized)
        agree on the same pack_name, the pack assignment is unambiguous.
        Covers cards with 2–3 rarity variants within a single set/expansion.
        Confidence: medium.

    Rule EX — is_ex suffix variant:
        If a card has is_ex=True in cards.json but its card_name does not contain
        "ex", try matching "<card_name> ex" in pack_sources.
        Only applies if there is exactly one global match for "<card_name> ex".
        Confidence: medium.
        Notes: name variant inferred from is_ex flag.

Unsafe rules (NOT applied):
    - source_reference URL extraction for multi-match cards (URL reflects first
      alphabetical match in reference, not necessarily the correct print).
    - name-only match when multiple candidates have different packs.
    - is_ex suffix when multiple "<name> ex" candidates exist with different packs.
    - Any match requiring visual confirmation of card variant.

Idempotent: running twice produces the same result. Cards with source_packs
already set from a confirmed exact match are never overwritten.

Usage:
    python3 scripts/resolve_pack_coverage.py --dry-run   # preview only
    python3 scripts/resolve_pack_coverage.py             # apply changes
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
PACK_SOURCES_JSON = ROOT / "data" / "reference" / "pack_sources.json"
REPORT_MD = ROOT / "review" / "pack_coverage_resolution_report.md"
REPORT_JSON = ROOT / "data" / "exports" / "pack_coverage_resolution_report.json"

DEFERRED_NOTE = (
    "Pack-opening and deck-building recommendations are intentionally deferred. "
    "This script only improves pack source coverage metadata."
)


def norm_name(s):
    s = str(s or "").strip().lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def load_cards():
    data = json.loads(CARDS_JSON.read_text(encoding="utf-8"))
    return data


def load_pack_sources():
    raw = json.loads(PACK_SOURCES_JSON.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return raw
    elif isinstance(raw, dict) and "records" in raw:
        return raw["records"]
    raise ValueError("pack_sources.json has unexpected structure")


def build_indexes(records):
    by_key = {}
    by_norm_name = defaultdict(list)

    for r in records:
        sc = r.get("set_code")
        cn = r.get("card_number")
        if sc and cn is not None:
            by_key[(sc, cn)] = r
        n = norm_name(r.get("card_name", ""))
        if n:
            by_norm_name[n].append(r)

    return by_key, by_norm_name


def is_already_exact(card):
    """True if this card already has a pack assignment from any prior phase."""
    return card.get("source_packs") is not None


def try_rule_d(card, by_key, by_norm_name):
    """
    Rule D: all name matches in pack_sources agree on the same pack.
    Returns (pack_record, confidence, rule, notes) or None.
    """
    if is_already_exact(card):
        return None

    name = norm_name(card.get("card_name", ""))
    matches = by_norm_name.get(name, [])

    if not matches:
        return None

    packs = set(m.get("pack_name") for m in matches)
    if len(packs) != 1:
        return None  # Multiple packs — ambiguous

    m = matches[0]
    sets = sorted(set(r["set_code"] for r in matches))
    return (
        m,
        "medium",
        "D",
        f"All {len(matches)} pack_sources record(s) agree on pack='{m['pack_name']}' "
        f"(set(s)={sets} expansion='{m['expansion']}')",
    )


def try_rule_ex(card, by_norm_name):
    """
    Rule EX: is_ex=True card whose name lacks 'ex' suffix.
    Try matching '<name> ex' in pack_sources.
    Only safe if exactly one global match.
    Returns (pack_record, confidence, rule, notes) or None.
    """
    if is_already_exact(card):
        return None

    if card.get("is_ex") is not True:
        return None

    name = card.get("card_name", "")
    norm_n = norm_name(name)

    if "ex" in norm_n.split():
        return None  # Already has 'ex' in name

    ex_name = norm_n + " ex"
    matches = by_norm_name.get(ex_name, [])

    if len(matches) != 1:
        return None

    m = matches[0]
    return (
        m,
        "medium",
        "EX",
        f"is_ex=True card; name '{name}' matched as '{m['card_name']}' "
        f"(set={m['set_code']} num={m['card_number']} pack='{m['pack_name']}'). "
        "Name variant inferred from is_ex flag — visual confirmation recommended.",
    )


def apply_resolution(card, pack_record, confidence, rule, notes, dry_run):
    """Apply source_packs to a card. Returns True if a change was made."""
    pack_name = pack_record.get("pack_name")
    expansion = pack_record.get("expansion")
    set_code = pack_record.get("set_code")

    new_source_packs = [pack_name] if pack_name else []

    existing = card.get("source_packs")
    existing_conf = card.get("source_pack_confidence", "")

    # Never overwrite a higher-confidence assignment
    if existing_conf == "high":
        return False

    # If same data already present (idempotency), skip write
    if (
        existing == new_source_packs
        and card.get("source_expansion") == expansion
        and card.get("source_pack_confidence") == confidence
        and f"Rule {rule}" in card.get("source_pack_notes", "")
    ):
        return False

    if not dry_run:
        card["source_packs"] = new_source_packs
        card["source_expansion"] = expansion
        card["source_set_code"] = set_code
        card["source_pack_confidence"] = confidence
        card["source_pack_notes"] = f"Rule {rule}: {notes}"

    return True


def resolve(cards, by_key, by_norm_name, dry_run):
    stats = {
        "examined": 0,
        "already_exact": 0,
        "resolved_rule_d": 0,
        "resolved_rule_ex": 0,
        "still_ambiguous": 0,
        "still_no_match": 0,
        "skipped_multi_ex": 0,
        "skipped_multi_name": 0,
        "unchanged_already_medium": 0,
    }
    resolved_details = []
    skipped_details = []

    for card in cards:
        stats["examined"] += 1
        name = card.get("card_name", "")
        norm_n = norm_name(name)

        # Already exact → skip
        if is_already_exact(card):
            stats["already_exact"] += 1
            continue

        # Try Rule D first
        result = try_rule_d(card, by_key, by_norm_name)
        if result:
            pack_rec, conf, rule, notes = result
            changed = apply_resolution(card, pack_rec, conf, rule, notes, dry_run)
            if changed:
                stats["resolved_rule_d"] += 1
                resolved_details.append({
                    "card_name": name,
                    "rule": rule,
                    "confidence": conf,
                    "set_code": pack_rec.get("set_code"),
                    "card_number": pack_rec.get("card_number"),
                    "pack_name": pack_rec.get("pack_name"),
                    "expansion": pack_rec.get("expansion"),
                    "notes": notes,
                })
            else:
                stats["unchanged_already_medium"] += 1
            continue

        # Try Rule EX
        result = try_rule_ex(card, by_norm_name)
        if result:
            pack_rec, conf, rule, notes = result
            changed = apply_resolution(card, pack_rec, conf, rule, notes, dry_run)
            if changed:
                stats["resolved_rule_ex"] += 1
                resolved_details.append({
                    "card_name": name,
                    "rule": rule,
                    "confidence": conf,
                    "set_code": pack_rec.get("set_code"),
                    "card_number": pack_rec.get("card_number"),
                    "pack_name": pack_rec.get("pack_name"),
                    "expansion": pack_rec.get("expansion"),
                    "notes": notes,
                })
            else:
                stats["unchanged_already_medium"] += 1
            continue

        # Categorize why it couldn't be resolved
        matches = by_norm_name.get(norm_n, [])
        ex_matches = by_norm_name.get(norm_n + " ex", [])

        if not matches and not ex_matches:
            stats["still_no_match"] += 1
            skipped_details.append({"card_name": name, "reason": "no_match_in_pack_sources"})
        elif len(matches) > 1:
            packs = set(m.get("pack_name") for m in matches)
            if len(packs) > 1:
                stats["still_ambiguous"] += 1
                skipped_details.append({
                    "card_name": name,
                    "reason": "multiple_packs_ambiguous",
                    "packs": sorted(str(p) for p in packs),
                })
            else:
                stats["skipped_multi_name"] += 1
                skipped_details.append({
                    "card_name": name,
                    "reason": "multi_name_same_pack_already_covered",
                })
        elif card.get("is_ex") is True and len(ex_matches) > 1:
            stats["skipped_multi_ex"] += 1
            skipped_details.append({
                "card_name": name,
                "reason": "is_ex_but_multiple_ex_matches_ambiguous",
            })
        else:
            stats["still_no_match"] += 1
            skipped_details.append({"card_name": name, "reason": "no_single_safe_match"})

    total_newly_resolved = stats["resolved_rule_d"] + stats["resolved_rule_ex"]
    stats["total_newly_resolved"] = total_newly_resolved
    return stats, resolved_details, skipped_details


def write_report(now, dry_run, stats, resolved_details, skipped_details):
    mode = "DRY RUN" if dry_run else "APPLIED"
    lines = [
        f"# Pack Coverage Resolution Report ({mode})",
        "",
        f"Generated: {now}",
        "",
        "> Quantities were not changed. Only source_packs metadata was added.",
        "",
        "## Summary",
        "",
        "| Metric | Count |",
        "|---|---|",
        f"| Cards examined | {stats['examined']} |",
        f"| Already exact (high confidence, skipped) | {stats['already_exact']} |",
        f"| Newly resolved — Rule D (single global name match) | {stats['resolved_rule_d']} |",
        f"| Newly resolved — Rule EX (is_ex name variant) | {stats['resolved_rule_ex']} |",
        f"| Total newly resolved | {stats['total_newly_resolved']} |",
        f"| Still ambiguous (multiple packs) | {stats['still_ambiguous']} |",
        f"| Still no match | {stats['still_no_match']} |",
        f"| Skipped (multi is_ex candidates) | {stats['skipped_multi_ex']} |",
        f"| Unchanged (already medium) | {stats['unchanged_already_medium']} |",
        "",
        "## Resolved Cards",
        "",
        "| Card Name | Rule | Confidence | Set | # | Pack | Expansion |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in resolved_details:
        lines.append(
            f"| {r['card_name']} | {r['rule']} | {r['confidence']} | "
            f"{r['set_code']} | {r['card_number']} | {r['pack_name']} | {r['expansion']} |"
        )
    lines.append("")

    if skipped_details:
        reason_groups = {}
        for s in skipped_details:
            reason = s["reason"]
            reason_groups.setdefault(reason, []).append(s["card_name"])

        lines += ["## Skipped Cards by Reason", ""]
        for reason, names in sorted(reason_groups.items()):
            lines.append(f"### {reason.replace('_', ' ').title()}")
            lines.append(f"Count: {len(names)}")
            lines.append(", ".join(names[:25]))
            if len(names) > 25:
                lines.append(f"_(and {len(names) - 25} more)_")
            lines.append("")

    lines += [
        "---",
        "",
        f"> {DEFERRED_NOTE}",
        "",
    ]

    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    report_data = {
        "generated_at": now,
        "mode": mode,
        "quantities_changed": False,
        "stats": stats,
        "resolved": resolved_details,
        "skipped": skipped_details,
    }
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report_data, indent=2, ensure_ascii=False), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Conservatively resolve pack coverage gaps")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing cards.json")
    args = parser.parse_args()

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    mode = "DRY RUN" if args.dry_run else "APPLY"
    print(f"\n=== resolve_pack_coverage.py [{mode}] ===")
    print(f"Generated: {now}")

    if not CARDS_JSON.exists():
        print("ERROR: cards.json not found", file=sys.stderr)
        sys.exit(1)
    if not PACK_SOURCES_JSON.exists():
        print("ERROR: pack_sources.json not found. Run build_pack_sources.py first.", file=sys.stderr)
        sys.exit(1)

    cards = load_cards()
    ps_records = load_pack_sources()
    print(f"Loaded {len(cards)} owned cards, {len(ps_records)} pack source records")

    by_key, by_norm_name = build_indexes(ps_records)
    stats, resolved, skipped = resolve(cards, by_key, by_norm_name, args.dry_run)

    if not args.dry_run and stats["total_newly_resolved"] > 0:
        CARDS_JSON.write_text(json.dumps(cards, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nUpdated cards.json ({len(cards)} entries)")

    write_report(now, args.dry_run, stats, resolved, skipped)

    print(f"\n=== Results ===")
    print(f"  Examined:              {stats['examined']}")
    print(f"  Already exact:         {stats['already_exact']}")
    print(f"  Resolved (Rule D):     {stats['resolved_rule_d']}")
    print(f"  Resolved (Rule EX):    {stats['resolved_rule_ex']}")
    print(f"  Total newly resolved:  {stats['total_newly_resolved']}")
    print(f"  Still ambiguous:       {stats['still_ambiguous']}")
    print(f"  Still no match:        {stats['still_no_match']}")
    print(f"  Skipped (multi-ex):    {stats['skipped_multi_ex']}")
    print(f"  Unchanged (medium):    {stats['unchanged_already_medium']}")
    print(f"\nWritten: {REPORT_MD}")
    print(f"Written: {REPORT_JSON}")

    if args.dry_run:
        print(f"\nDRY RUN: run without --dry-run to apply changes.")


if __name__ == "__main__":
    main()
