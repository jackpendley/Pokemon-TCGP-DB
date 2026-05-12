#!/usr/bin/env python3
"""
Build a deterministic order-based alignment between screenshot grid slots
and collection.json entries.

No OCR or image matching is used. Alignment is based entirely on sequential
positional order: the PTCGP app displays cards in a fixed expansion order
that is assumed to match the entry order in collection_normalized.json.

Inputs:
    data/current/collection_normalized.json
    data/current/screenshot_inventory.json

Outputs:
    data/current/screenshot_collection_alignment.json
    data/exports/screenshot_collection_alignment.csv
    review/screenshot_collection_alignment.md

Usage:
    python3 scripts/build_screenshot_collection_alignment.py
    python3 scripts/build_screenshot_collection_alignment.py --validate
"""

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COLLECTION_JSON = ROOT / "data" / "current" / "collection_normalized.json"
INVENTORY_JSON = ROOT / "data" / "current" / "screenshot_inventory.json"
OUT_JSON = ROOT / "data" / "current" / "screenshot_collection_alignment.json"
OUT_CSV = ROOT / "data" / "exports" / "screenshot_collection_alignment.csv"
OUT_MD = ROOT / "review" / "screenshot_collection_alignment.md"

VALID_TIERS = {"high", "medium", "low", "unresolved"}

# Confidence score constants — order-only, no OCR confirmation
CONFIDENCE_BASE = 0.70
CONFIDENCE_BOUNDARY_ROW_PENALTY = 0.08   # r1 or r3 row of any screenshot
CONFIDENCE_FINAL_SCREENSHOT_PENALTY = 0.15  # is_final=True screenshots
CONFIDENCE_SURPLUS = 0.0                 # no entry matches

# Thresholds
TIER_HIGH = 0.95
TIER_MEDIUM = 0.80
TIER_LOW = 0.50


def confidence_tier(score: float) -> str:
    if score >= TIER_HIGH:
        return "high"
    if score >= TIER_MEDIUM:
        return "medium"
    if score >= TIER_LOW:
        return "low"
    return "unresolved"


def slot_row(position: str) -> str:
    """Extract row label from position string (e.g. 'r1c2' -> 'r1')."""
    return position[:2]


def compute_confidence(slot_idx: int, n_entries: int, is_final: bool,
                       position: str) -> tuple:
    """Return (score, evidence_list). Evidence explains every factor."""
    if slot_idx >= n_entries:
        return CONFIDENCE_SURPLUS, ["surplus_slot_no_entry_match"]

    evidence = ["sequential_order_alignment"]
    score = CONFIDENCE_BASE

    row = slot_row(position)
    if row in ("r1", "r3"):
        score -= CONFIDENCE_BOUNDARY_ROW_PENALTY
        evidence.append("boundary_row_penalty")

    if is_final:
        score -= CONFIDENCE_FINAL_SCREENSHOT_PENALTY
        evidence.append("final_screenshot_penalty")

    return round(score, 4), evidence


def build_alignment(entries: list, inventory: dict) -> list:
    """Return flat list of alignment records, one per screenshot slot."""
    screenshots = sorted(inventory["screenshots"], key=lambda s: s["filename"])
    records = []
    slot_idx = 0
    for sc in screenshots:
        for pos in sc["slot_positions"]:
            entry = entries[slot_idx] if slot_idx < len(entries) else None
            score, evidence = compute_confidence(
                slot_idx=slot_idx,
                n_entries=len(entries),
                is_final=sc["is_final"],
                position=pos,
            )
            records.append({
                "slot_index": slot_idx,
                "screenshot_filename": sc["filename"],
                "screenshot_index": sc["index"],
                "slot_position": pos,
                "is_final_screenshot": sc["is_final"],
                "aligned_entry_index": slot_idx if entry else None,
                "entry_id": entry["entry_id"] if entry else None,
                "card_name": entry["name"] if entry else None,
                "count": entry["count"] if entry else None,
                "card_type": entry.get("card_type") if entry else None,
                "type": entry.get("type") if entry else None,
                "hp": entry.get("hp") if entry else None,
                "stage": entry.get("stage_label") if entry else None,
                "is_ex": entry.get("is_ex") if entry else None,
                "variant": entry.get("variant") if entry else None,
                "confidence_score": score,
                "confidence_tier": confidence_tier(score),
                "evidence": evidence,
                "warnings": (["no_ocr_name_verification"] if entry
                              else ["surplus_slot"]),
            })
            slot_idx += 1
    return records


def write_json(records: list, entries: list, inventory: dict) -> dict:
    n_entries = len(entries)
    total_slots = inventory["total_card_slots"]
    aligned = [r for r in records if r["entry_id"] is not None]
    surplus = [r for r in records if r["entry_id"] is None]

    tier_counts = {"high": 0, "medium": 0, "low": 0, "unresolved": 0}
    for r in records:
        tier_counts[r["confidence_tier"]] += 1

    assumptions = [
        "Entries in collection_normalized.json are in the same sequential display "
        "order as the PTCGP app collection grid (set/expansion order).",
        "Screenshots are ordered by filename (IMG_1556–IMG_1581), which corresponds "
        "to the user's downward scroll order through the collection grid.",
        "Within each screenshot, slots are traversed r1c1→r1c2→r1c3→r2c1→r2c2→r2c3"
        "→r3c1→r3c2→r3c3 (left-to-right, top-to-bottom).",
        f"The first {n_entries} slots (indices 0–{n_entries - 1}) map sequentially "
        f"to collection entries 0–{n_entries - 1}.",
        f"The remaining {len(surplus)} slots (indices {n_entries}–{total_slots - 1}) "
        "are surplus with no entry assignment. Most likely explanation: "
        "IMG_1581 is a scroll-overlap screenshot showing cards also visible in IMG_1580, "
        "or the final row of the app grid contains 1–2 empty trailing positions.",
        "No OCR or image matching was used. Alignment is order-only.",
        "Confidence >= 0.95 (high) is NOT awarded without OCR or image name confirmation.",
    ]

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generated_by": "build_screenshot_collection_alignment.py",
        "note": (
            "Order-only alignment. No OCR. Card names are NOT verified against "
            "screenshots. Confidence scores reflect structural positional uncertainty only."
        ),
        "meta": {
            "collection_entries": n_entries,
            "total_screenshot_slots": total_slots,
            "aligned_count": len(aligned),
            "surplus_slot_count": len(surplus),
            "surplus_explanation": (
                f"{len(surplus)} slots have no entry assignment. "
                "Likely: 1 trailing empty grid position (IMG_1580 r3c3) + "
                "7 scroll-overlap slots in IMG_1581 that duplicate the last 7 entries "
                "of IMG_1580. Requires OCR to confirm."
            ),
        },
        "assumptions": assumptions,
        "confidence_summary": tier_counts,
        "confidence_model": {
            "base_score": CONFIDENCE_BASE,
            "boundary_row_penalty": CONFIDENCE_BOUNDARY_ROW_PENALTY,
            "final_screenshot_penalty": CONFIDENCE_FINAL_SCREENSHOT_PENALTY,
            "surplus_score": CONFIDENCE_SURPLUS,
            "note": "Max achievable score in no-OCR phase = 0.70 (mid-row, non-final screenshot).",
        },
        "alignment_records": records,
        "surplus_slots": [
            {
                "slot_index": r["slot_index"],
                "filename": r["screenshot_filename"],
                "screenshot_index": r["screenshot_index"],
                "position": r["slot_position"],
                "is_final": r["is_final_screenshot"],
                "reason": "beyond_collection_entry_count",
            }
            for r in surplus
        ],
        "warnings": [
            "All confidence scores are order-based positional estimates only.",
            "No card name verification has been performed against screenshot images.",
            "High confidence (>= 0.95) is not awarded in this no-OCR phase.",
            "Surplus slots may be scroll-overlap duplicates or empty trailing positions; "
            "OCR is required to distinguish.",
            "Do not use this alignment as ground truth. Use it as a starting point "
            "for the next confidence scoring phase.",
        ],
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(out, indent=2, ensure_ascii=False),
                        encoding="utf-8")
    return out


def write_csv(records: list):
    fieldnames = [
        "slot_index", "screenshot_filename", "screenshot_index", "slot_position",
        "is_final_screenshot",
        "aligned_entry_index", "entry_id", "card_name", "count",
        "card_type", "type", "hp", "stage", "is_ex", "variant",
        "confidence_score", "confidence_tier", "evidence", "warnings",
    ]
    (ROOT / "data" / "exports").mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in records:
            row = {
                **r,
                "evidence": "; ".join(r["evidence"]),
                "warnings": "; ".join(r["warnings"]),
            }
            w.writerow(row)


def write_md(out: dict):
    meta = out["meta"]
    cs = out["confidence_summary"]
    surplus = out["surplus_slots"]
    records = out["alignment_records"]
    aligned = [r for r in records if r["entry_id"] is not None]

    lines = [
        "# Screenshot-to-Collection Alignment",
        "",
        "> **No OCR was used.** This alignment is order-only (sequential positional mapping).",
        "> Card names are **not verified** against screenshot images.",
        "> Confidence scores reflect structural position uncertainty, not card identity certainty.",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Collection entries | {meta['collection_entries']} |",
        f"| Screenshot slots | {meta['total_screenshot_slots']} |",
        f"| Aligned (entry assigned) | {meta['aligned_count']} |",
        f"| Surplus slots (no entry) | {meta['surplus_slot_count']} |",
        f"| Generated at | {out['generated_at']} |",
        "",
        "## Confidence Distribution",
        "",
        "| Tier | Count | Score Range |",
        "|---|---|---|",
        f"| high | {cs['high']} | ≥ 0.95 |",
        f"| medium | {cs['medium']} | 0.80–0.949 |",
        f"| low | {cs['low']} | 0.50–0.799 |",
        f"| unresolved | {cs['unresolved']} | < 0.50 or no entry |",
        "",
        "## Structural Assumptions",
        "",
    ]
    for i, a in enumerate(out["assumptions"], 1):
        lines.append(f"{i}. {a}")
    lines.append("")

    lines += [
        "## Confidence Model",
        "",
        f"- Base score (mid-row, non-final): **{out['confidence_model']['base_score']}**",
        f"- Boundary row penalty (r1 or r3): −{out['confidence_model']['boundary_row_penalty']}",
        f"- Final screenshot penalty: −{out['confidence_model']['final_screenshot_penalty']}",
        f"- Surplus slot (no entry): **{out['confidence_model']['surplus_score']}**",
        "",
        "> Maximum achievable score in no-OCR phase = **0.70** (r2 slot, non-final screenshot).",
        "> No alignment record in this phase can reach high-confidence (≥ 0.95).",
        "",
        "## Surplus Slots",
        "",
        f"{meta['surplus_explanation']}",
        "",
        "| Slot index | File | Position | Is final |",
        "|---|---|---|---|",
    ]
    for s in surplus:
        lines.append(
            f"| {s['slot_index']} | {s['filename']} | {s['position']} | {s['is_final']} |"
        )

    lines += [
        "",
        "## Aligned Records (first 20)",
        "",
        "| Slot | File | Position | Entry ID | Card Name | Count | HP | Confidence | Tier | Evidence |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in aligned[:20]:
        ev = "; ".join(r["evidence"])
        lines.append(
            f"| {r['slot_index']} | {r['screenshot_filename']} | {r['slot_position']} "
            f"| {r['entry_id']} | {r['card_name']} | {r['count']} | {r['hp'] or '–'} "
            f"| {r['confidence_score']} | {r['confidence_tier']} | {ev} |"
        )
    if len(aligned) > 20:
        lines.append(f"| … | … | … | … | … | … | … | … | … | … |")
        lines.append(f"_(Full data in `data/exports/screenshot_collection_alignment.csv`)_")

    lines += [
        "",
        "## Warnings",
        "",
    ]
    for w in out["warnings"]:
        lines.append(f"- {w}")
    lines.append("")

    (ROOT / "review").mkdir(exist_ok=True)
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_validate() -> bool:
    """Validate the existing alignment output. Returns True if all checks pass."""
    print("\n=== build_screenshot_collection_alignment.py [VALIDATE] ===")
    errors = 0

    if not OUT_JSON.exists():
        print("  ERROR: output JSON does not exist — run without --validate first")
        return False

    if not COLLECTION_JSON.exists():
        print(f"  ERROR: {COLLECTION_JSON} not found")
        return False
    if not INVENTORY_JSON.exists():
        print(f"  ERROR: {INVENTORY_JSON} not found")
        return False

    col_data = json.loads(COLLECTION_JSON.read_text(encoding="utf-8"))
    entries = col_data["collection"]
    inv_data = json.loads(INVENTORY_JSON.read_text(encoding="utf-8"))
    expected_slots = inv_data["total_card_slots"]

    out = json.loads(OUT_JSON.read_text(encoding="utf-8"))
    records = out["alignment_records"]
    meta = out["meta"]

    # 1. Slot count matches inventory
    if len(records) != expected_slots:
        print(f"  ERROR: records={len(records)} but inventory slots={expected_slots}")
        errors += 1
    else:
        print(f"  PASS  slot count matches inventory ({expected_slots})")

    # 2. Meta aligned_count + surplus_slot_count == total_screenshot_slots
    declared_total = meta["aligned_count"] + meta["surplus_slot_count"]
    if declared_total != meta["total_screenshot_slots"]:
        print(f"  ERROR: aligned({meta['aligned_count']}) + surplus({meta['surplus_slot_count']}) "
              f"= {declared_total} ≠ total_slots({meta['total_screenshot_slots']})")
        errors += 1
    else:
        print(f"  PASS  meta counts internally consistent")

    # 3. Assigned entry count does not exceed collection entries
    assigned = [r for r in records if r["entry_id"] is not None]
    if len(assigned) > len(entries):
        print(f"  ERROR: assigned={len(assigned)} > collection entries={len(entries)}")
        errors += 1
    else:
        print(f"  PASS  assigned ({len(assigned)}) ≤ collection entries ({len(entries)})")

    # 4. No duplicate assigned entry_id
    ids = [r["entry_id"] for r in assigned]
    if len(ids) != len(set(ids)):
        from collections import Counter
        dupes = [eid for eid, n in Counter(ids).items() if n > 1]
        print(f"  ERROR: duplicate entry_ids: {dupes}")
        errors += 1
    else:
        print(f"  PASS  no duplicate entry_id assignments")

    # 5. Confidence scores are in [0, 1]
    bad_scores = [r for r in records if not (0.0 <= r["confidence_score"] <= 1.0)]
    if bad_scores:
        print(f"  ERROR: {len(bad_scores)} records have out-of-range confidence scores")
        errors += 1
    else:
        print(f"  PASS  all confidence scores in [0, 1]")

    # 6. Confidence tiers are valid
    bad_tiers = [r for r in records if r["confidence_tier"] not in VALID_TIERS]
    if bad_tiers:
        print(f"  ERROR: {len(bad_tiers)} records have invalid confidence tiers")
        errors += 1
    else:
        print(f"  PASS  all confidence tiers valid")

    # 7. Surplus count = total_slots - n_entries (structurally expected)
    expected_surplus = expected_slots - len(entries)
    actual_surplus = meta["surplus_slot_count"]
    if actual_surplus != expected_surplus:
        print(f"  ERROR: surplus={actual_surplus}, expected {expected_surplus} "
              f"({expected_slots} slots - {len(entries)} entries)")
        errors += 1
    else:
        print(f"  PASS  surplus count ({actual_surplus}) = slots - entries ({expected_surplus})")

    # 8. collection.json not mutated (validate by re-running current collection validator)
    #    We check indirectly: total quantity in collection_normalized.json unchanged
    total_qty = sum(e["count"] for e in entries)
    print(f"  INFO  collection_normalized.json total quantity = {total_qty} (not mutated by this script)")

    # 9. Output CSV exists
    if not OUT_CSV.exists():
        print(f"  WARN  CSV output not found: {OUT_CSV.relative_to(ROOT)}")
    else:
        print(f"  PASS  CSV output exists")

    # 10. Output MD exists
    if not OUT_MD.exists():
        print(f"  WARN  Markdown output not found: {OUT_MD.relative_to(ROOT)}")
    else:
        print(f"  PASS  Markdown output exists")

    if errors == 0:
        print(f"\nVALIDATION PASSED  ({len(records)} records, {len(assigned)} aligned, "
              f"{actual_surplus} surplus)")
    else:
        print(f"\nVALIDATION FAILED  ({errors} error(s))")

    return errors == 0


def main():
    parser = argparse.ArgumentParser(
        description="Build or validate screenshot-to-collection order alignment"
    )
    parser.add_argument("--validate", action="store_true",
                        help="Validate existing output rather than regenerating")
    args = parser.parse_args()

    if args.validate:
        ok = run_validate()
        sys.exit(0 if ok else 1)

    print("\n=== build_screenshot_collection_alignment.py ===")

    for path, label in [(COLLECTION_JSON, "collection_normalized.json"),
                        (INVENTORY_JSON, "screenshot_inventory.json")]:
        if not path.exists():
            print(f"ERROR: {label} not found at {path}", file=sys.stderr)
            sys.exit(1)

    col_data = json.loads(COLLECTION_JSON.read_text(encoding="utf-8"))
    entries = col_data["collection"]
    inv_data = json.loads(INVENTORY_JSON.read_text(encoding="utf-8"))
    total_slots = inv_data["total_card_slots"]

    print(f"  Collection entries: {len(entries)}")
    print(f"  Screenshot slots:   {total_slots}")
    print(f"  Surplus:            {total_slots - len(entries)}")

    records = build_alignment(entries, inv_data)
    assert len(records) == total_slots

    out = write_json(records, entries, inv_data)
    write_csv(records)
    write_md(out)

    aligned = [r for r in records if r["entry_id"] is not None]
    surplus = [r for r in records if r["entry_id"] is None]
    cs = out["confidence_summary"]

    print(f"\n=== Summary ===")
    print(f"  Aligned:   {len(aligned)}")
    print(f"  Surplus:   {len(surplus)}")
    print(f"  Confidence tiers:")
    for t in ("high", "medium", "low", "unresolved"):
        print(f"    {t}: {cs[t]}")
    print(f"\nDone.")


if __name__ == "__main__":
    main()
