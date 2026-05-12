#!/usr/bin/env python3
"""
Generate a review package for current collection cards that are ambiguous
or no_match in current_collection_pack_coverage.json.

Outputs:
    review/current_pack_source_review.md
    data/exports/current_pack_source_review.csv
    data/exports/current_pack_source_review.json

Usage:
    python3 scripts/create_current_pack_review.py
"""

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COVERAGE_JSON = ROOT / "data" / "current" / "current_collection_pack_coverage.json"
PACK_SOURCES_JSON = ROOT / "data" / "reference" / "pack_sources.json"
OUT_MD = ROOT / "review" / "current_pack_source_review.md"
OUT_CSV = ROOT / "data" / "exports" / "current_pack_source_review.csv"
OUT_JSON = ROOT / "data" / "exports" / "current_pack_source_review.json"

REVIEW_STATUSES = {"ambiguous_same_set", "ambiguous_cross_set", "no_match", "no_match_known_gap"}

# Priority ordering for review
CHASE_TARGETS = {
    "ivysaur", "incineroar ex", "zygarde ex", "magnezone ex",
    "marowak ex", "moltres ex",
}


def priority_key(entry: dict) -> tuple:
    n = entry["name"].lower()
    is_chase = n in CHASE_TARGETS
    is_ex = entry.get("is_ex", False)
    is_trainer = entry.get("card_type") == "Trainer"
    return (not is_chase, not is_ex, not is_trainer, entry["name"])


def write_md(review_entries: list[dict], out_path: Path):
    nb_amb_cross = sum(1 for e in review_entries if e["match_status"] == "ambiguous_cross_set")
    nb_amb_same = sum(1 for e in review_entries if e["match_status"] == "ambiguous_same_set")
    nb_no_match = sum(1 for e in review_entries if e["match_status"] == "no_match")
    nb_gap = sum(1 for e in review_entries if e["match_status"] == "no_match_known_gap")

    lines = [
        "# Current Collection Pack-Source Review",
        "",
        "This package lists cards from `collection.json` that cannot be automatically assigned",
        "to a pack because they appear in multiple expansions or are not in `pack_sources.json`.",
        "",
        "**Fill in `data/exports/current_pack_source_review.csv`** to confirm which set/card number",
        "each card belongs to. Then apply with:",
        "",
        "```bash",
        "python3 scripts/apply_current_pack_confirmations.py --dry-run",
        "python3 scripts/apply_current_pack_confirmations.py --apply",
        "```",
        "",
        "## How to Check Set/Card Number",
        "",
        "1. Open the Pokémon TCG Pocket app.",
        "2. Go to your card collection.",
        "3. Tap the card you want to identify.",
        "4. The set code and card number appear at the bottom of the card detail view.",
        "   - Format: `A1/001`, `B3/124`, etc.",
        "5. Enter `confirmed_set_code` (e.g., `A1`) and `confirmed_card_number` (e.g., `1`).",
        "6. Set `confirmed_yes_no` to `yes`.",
        "",
        "## Summary",
        "",
        f"| Status | Count |",
        f"|---|---|",
        f"| Ambiguous (cross-expansion) | {nb_amb_cross} |",
        f"| Ambiguous (same expansion, different pack) | {nb_amb_same} |",
        f"| No match in pack_sources | {nb_no_match} |",
        f"| Known trainer gap (not in Limitless) | {nb_gap} |",
        f"| **Total needing review** | **{len(review_entries)}** |",
        "",
        "## Priority 1 — Chase Deck Targets",
        "",
        "Resolve these first for pack EV recommendations.",
        "",
    ]

    chase = [e for e in review_entries if e["name"].lower() in CHASE_TARGETS]
    if chase:
        for e in chase:
            lines += _card_block(e)
    else:
        lines.append("None identified.")

    lines += ["", "## Priority 2 — EX Cards", ""]
    ex_entries = [e for e in review_entries if e.get("is_ex") and e["name"].lower() not in CHASE_TARGETS]
    if ex_entries:
        for e in ex_entries:
            lines += _card_block(e)
    else:
        lines.append("None.")

    lines += ["", "## Priority 3 — Trainer/Supporter Staples", ""]
    trainer_entries = [e for e in review_entries
                       if e.get("card_type") == "Trainer"
                       and e.get("match_status") not in ("no_match_known_gap",)]
    if trainer_entries:
        for e in trainer_entries:
            lines += _card_block(e)
    else:
        lines.append("None.")

    lines += ["", "## Priority 4 — Pokemon Cards", ""]
    poke_entries = [e for e in review_entries
                    if e.get("card_type") == "Pokemon"
                    and not e.get("is_ex")
                    and e["name"].lower() not in CHASE_TARGETS]
    if poke_entries:
        lines.append("Sorted by name.")
        lines.append("")
        for e in sorted(poke_entries, key=lambda x: x["name"]):
            lines += _card_block(e)
    else:
        lines.append("None.")

    lines += [
        "", "## Known Trainer Gaps (Not in Limitless DB)", "",
        "These common trainer items are not indexed in Limitless TCG Pocket.",
        "They cannot be confirmed via pack_sources. Leave blank unless you find a reference.",
        ""
    ]
    gap_entries = [e for e in review_entries if e.get("match_status") == "no_match_known_gap"]
    for e in gap_entries:
        lines.append(f"- **{e['name']}** (×{e['count']}): Common item, likely multi-set")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _card_block(e: dict) -> list[str]:
    lines = [f"### {e['name']} (×{e['count']})", ""]
    lines.append(f"- **Status:** `{e['match_status']}`")
    lines.append(f"- **Type:** {e.get('type') or e.get('trainer_subtype') or e.get('card_type')}")
    if e.get("hp"):
        lines.append(f"- **HP:** {e['hp']}")
    if e.get("attack"):
        lines.append(f"- **Attack:** {e['attack']}")
    if e.get("variant"):
        lines.append(f"- **Variant:** {e['variant']}")
    lines.append(f"- **Recommended action:** `{e['recommended_resolution']}`")
    lines.append("")

    if e["candidates"]:
        lines.append("**Candidates:**")
        lines.append("")
        lines.append("| Set | # | Expansion | Pack | Rarity | URL |")
        lines.append("|---|---|---|---|---|---|")
        for c in e["candidates"]:
            url = c.get("source_url", "")
            pack = c.get("pack_name") or "shared pool"
            lines.append(
                f"| {c.get('set_code','')} | {c.get('card_number','')} "
                f"| {c.get('expansion','')} | {pack} | {c.get('rarity','')} | {url} |"
            )
    else:
        lines.append("_No candidates found in pack_sources._")
    lines.append("")
    return lines


def write_csv(review_entries: list[dict], out_path: Path):
    fieldnames = [
        "entry_id", "name", "count", "type", "card_type", "trainer_subtype",
        "hp", "attack", "variant", "is_ex",
        "match_status", "candidate_count", "candidate_summary",
        "recommended_resolution",
        "confirmed_set_code", "confirmed_card_number", "confirmed_pack_name",
        "confirmed_yes_no", "user_notes",
    ]
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for e in review_entries:
            row = {
                "entry_id": e.get("entry_id", ""),
                "name": e["name"],
                "count": e["count"],
                "type": e.get("type", ""),
                "card_type": e.get("card_type", ""),
                "trainer_subtype": e.get("trainer_subtype", ""),
                "hp": e.get("hp", ""),
                "attack": e.get("attack", ""),
                "variant": e.get("variant", ""),
                "is_ex": e.get("is_ex", False),
                "match_status": e["match_status"],
                "candidate_count": e["candidate_count"],
                "candidate_summary": e["candidate_summary"],
                "recommended_resolution": e["recommended_resolution"],
                "confirmed_set_code": "",
                "confirmed_card_number": "",
                "confirmed_pack_name": "",
                "confirmed_yes_no": "",
                "user_notes": "",
            }
            w.writerow(row)


def main():
    print(f"\n=== create_current_pack_review.py ===")

    if not COVERAGE_JSON.exists():
        print(f"ERROR: {COVERAGE_JSON} not found — run current_collection_pack_coverage.py first", file=sys.stderr)
        sys.exit(1)

    coverage = json.loads(COVERAGE_JSON.read_text(encoding="utf-8"))
    all_entries = coverage["entries"]

    review_entries = sorted(
        [e for e in all_entries if e["match_status"] in REVIEW_STATUSES],
        key=priority_key,
    )

    print(f"  Total entries: {len(all_entries)}")
    print(f"  Needs review:  {len(review_entries)}")
    by_status = {}
    for e in review_entries:
        by_status[e["match_status"]] = by_status.get(e["match_status"], 0) + 1
    for k, v in sorted(by_status.items()):
        print(f"    {k}: {v}")

    (ROOT / "review").mkdir(exist_ok=True)
    (ROOT / "data" / "exports").mkdir(parents=True, exist_ok=True)

    write_md(review_entries, OUT_MD)
    print(f"  Written: {OUT_MD.relative_to(ROOT)}")

    write_csv(review_entries, OUT_CSV)
    print(f"  Written: {OUT_CSV.relative_to(ROOT)}")

    out_data = {
        "total_needs_review": len(review_entries),
        "by_status": by_status,
        "entries": review_entries,
    }
    OUT_JSON.write_text(json.dumps(out_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  Written: {OUT_JSON.relative_to(ROOT)}")

    print(f"\nDone.")


if __name__ == "__main__":
    main()
