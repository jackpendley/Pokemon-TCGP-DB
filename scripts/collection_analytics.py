#!/usr/bin/env python3
"""
Generates collection analytics from cards.json.

Writes:
    review/collection_analytics.md
    data/exports/collection_analytics.json

Usage:
    python3 scripts/collection_analytics.py
"""

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CARDS_JSON = ROOT / "cards.json"
ANALYTICS_MD = ROOT / "review" / "collection_analytics.md"
ANALYTICS_JSON = ROOT / "data" / "exports" / "collection_analytics.json"

EXPECTED_TOTAL = 329
APP_REPORTED_TOTAL = 331
DEFERRED_NOTE = (
    "This is analytics only. Pack-opening and deck-building recommendations "
    "are intentionally deferred until metadata enrichment is stronger."
)


def load_cards():
    if not CARDS_JSON.exists():
        print(f"ERROR  cards.json not found at {CARDS_JSON}", file=sys.stderr)
        sys.exit(1)
    try:
        cards = json.loads(CARDS_JSON.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"ERROR  cards.json invalid JSON: {exc}", file=sys.stderr)
        sys.exit(1)
    if not isinstance(cards, list):
        print("ERROR  cards.json top-level is not an array", file=sys.stderr)
        sys.exit(1)
    return cards


def pct(n, total):
    if total == 0:
        return "0.0%"
    return f"{100 * n / total:.1f}%"


def is_unknown(v):
    if v is None:
        return True
    s = str(v).strip().lower()
    return s in ("", "unknown", "none", "null", "n/a")


def field_completeness(cards, field):
    total = len(cards)
    known = sum(1 for c in cards if not is_unknown(c.get(field)))
    unknown = total - known
    blank = sum(1 for c in cards if c.get(field) is None or str(c.get(field, "")).strip() == "")
    return {"total": total, "known": known, "unknown_or_blank": unknown, "blank_null": blank, "pct_known": pct(known, total)}


def build_baseline(cards):
    total_qty = sum(c.get("quantity", 0) for c in cards if isinstance(c.get("quantity"), int))
    unique_entries = len(cards)
    total_ok = total_qty == EXPECTED_TOTAL
    return {
        "total_quantity": total_qty,
        "unique_entries": unique_entries,
        "expected_total": EXPECTED_TOTAL,
        "app_reported_total": APP_REPORTED_TOTAL,
        "total_matches_expected": total_ok,
        "discrepancy_note": f"App reported {APP_REPORTED_TOTAL}; provisional baseline is {EXPECTED_TOTAL}. 2-card discrepancy documented in review/. Not forced.",
        "validation_status": "PASS" if total_ok else "FAIL",
    }


def build_metadata_completeness(cards):
    fields = [
        "set_or_pack", "set_code", "card_number", "rarity",
        "pokemon_type", "card_category", "is_ex", "special_type",
        "stage", "source_reference", "metadata_confidence",
    ]
    return {f: field_completeness(cards, f) for f in fields}


def build_ex_inventory(cards):
    ex_cards = [c for c in cards if c.get("is_ex") is True]
    result = []
    for c in ex_cards:
        result.append({
            "card_name": c.get("card_name"),
            "quantity": c.get("quantity"),
            "set_or_pack": c.get("set_or_pack"),
            "set_code": c.get("set_code"),
            "rarity": c.get("rarity"),
            "card_number": c.get("card_number"),
            "source_screenshot": c.get("source_screenshot"),
            "source_reference": c.get("source_reference"),
        })
    result.sort(key=lambda x: x["card_name"] or "")
    return result


def build_special_inventory(cards):
    special_types = {
        "full_art", "illustration_rare", "special_art",
        "immersive", "crown_gold", "special_trainer",
        "alternate_art",
    }
    specials = [c for c in cards if c.get("special_type") in special_types]
    result = []
    for c in specials:
        result.append({
            "card_name": c.get("card_name"),
            "quantity": c.get("quantity"),
            "special_type": c.get("special_type"),
            "set_or_pack": c.get("set_or_pack"),
            "source_screenshot": c.get("source_screenshot"),
            "source_reference": c.get("source_reference"),
        })
    result.sort(key=lambda x: (x["special_type"] or "", x["card_name"] or ""))
    unknown_special_count = sum(1 for c in cards if c.get("special_type") == "unknown")
    return {"items": result, "unknown_special_type_count": unknown_special_count}


def build_type_coverage(cards):
    excluded = {"none", "unknown", "", None}
    type_entries = Counter()
    type_qty = Counter()
    unknown_entries = 0
    unknown_qty = 0
    for c in cards:
        pt = c.get("pokemon_type", "Unknown")
        qty = c.get("quantity", 0) if isinstance(c.get("quantity"), int) else 0
        if str(pt).lower() in ("none", "unknown", "", "null") or pt is None:
            unknown_entries += 1
            unknown_qty += qty
        else:
            type_entries[pt] += 1
            type_qty[pt] += qty
    rows = [
        {"pokemon_type": t, "entries": type_entries[t], "total_quantity": type_qty[t]}
        for t in sorted(type_entries.keys())
    ]
    return {
        "by_type": rows,
        "unknown_or_none_entries": unknown_entries,
        "unknown_or_none_quantity": unknown_qty,
    }


def build_category_breakdown(cards):
    cat_entries = Counter()
    cat_qty = Counter()
    for c in cards:
        cat = c.get("card_category", "Unknown")
        qty = c.get("quantity", 0) if isinstance(c.get("quantity"), int) else 0
        cat_entries[cat] += 1
        cat_qty[cat] += qty
    rows = [
        {"card_category": cat, "entries": cat_entries[cat], "total_quantity": cat_qty[cat]}
        for cat in sorted(cat_entries.keys(), key=lambda x: -cat_entries[x])
    ]
    return rows


def build_duplicate_inventory(cards):
    dupes = [
        {
            "card_name": c.get("card_name"),
            "quantity": c.get("quantity"),
            "special_type": c.get("special_type"),
            "set_or_pack": c.get("set_or_pack"),
            "source_screenshot": c.get("source_screenshot"),
        }
        for c in cards
        if isinstance(c.get("quantity"), int) and c.get("quantity", 0) >= 2
    ]
    dupes.sort(key=lambda x: (-x["quantity"], x["card_name"] or ""))
    return dupes


def build_top_quantity(cards):
    top = sorted(
        cards,
        key=lambda x: -(x.get("quantity", 0) if isinstance(x.get("quantity"), int) else 0)
    )[:10]
    return [
        {
            "card_name": c.get("card_name"),
            "quantity": c.get("quantity"),
            "special_type": c.get("special_type"),
            "card_category": c.get("card_category"),
            "pokemon_type": c.get("pokemon_type"),
            "set_or_pack": c.get("set_or_pack"),
        }
        for c in top
    ]


def build_cleanup_candidates(cards):
    max_examples = 25

    def names(lst):
        return [c.get("card_name", "?") for c in lst[:max_examples]]

    unknown_special = [c for c in cards if c.get("special_type") == "unknown"]
    unknown_set = [c for c in cards if is_unknown(c.get("set_or_pack"))]
    unknown_type = [c for c in cards if is_unknown(c.get("pokemon_type")) and c.get("card_category") not in ("Trainer", "Item", "Supporter", "Tool", "Stadium", "Fossil")]
    unknown_cat = [c for c in cards if is_unknown(c.get("card_category"))]
    ambiguous = [c for c in cards if c.get("needs_review") is True]

    return {
        "unknown_special_type": {"count": len(unknown_special), "examples": names(unknown_special)},
        "unknown_set": {"count": len(unknown_set), "examples": names(unknown_set)},
        "unknown_pokemon_type_non_trainer": {"count": len(unknown_type), "examples": names(unknown_type)},
        "unknown_card_category": {"count": len(unknown_cat), "examples": names(unknown_cat)},
        "needs_review": {"count": len(ambiguous), "examples": names(ambiguous)},
    }


def build_readiness(cards, completeness, baseline):
    total = len(cards)
    if total == 0:
        return {"status": "Not ready", "score_pct": 0, "blockers": ["No cards loaded"], "next_improvements": []}

    def pct_known(field):
        fc = completeness.get(field, {})
        return fc.get("known", 0) / max(fc.get("total", 1), 1) * 100

    set_pct = pct_known("set_or_pack")
    cat_pct = pct_known("card_category")
    type_pct = pct_known("pokemon_type")
    special_pct = pct_known("special_type")
    src_pct = pct_known("source_reference")
    rarity_pct = pct_known("rarity")

    blockers = []
    improvements = []

    if not baseline["total_matches_expected"]:
        blockers.append(f"Total quantity does not match expected {EXPECTED_TOTAL}")
    if set_pct < 50:
        blockers.append(f"Set/pack known for only {set_pct:.0f}% of cards (need ≥50%)")
        improvements.append("Enrich set_code and set_or_pack from external reference")
    if cat_pct < 80:
        blockers.append(f"card_category known for only {cat_pct:.0f}% of cards (need ≥80%)")
        improvements.append("Enrich card_category from external reference")
    if type_pct < 50:
        improvements.append("Enrich pokemon_type from external reference for non-trainer cards")
    if special_pct < 50:
        blockers.append(f"special_type known for only {special_pct:.0f}% of cards (need ≥50%)")
        improvements.append("Confirm special_type via screenshot review or external reference")
    if rarity_pct < 30:
        improvements.append("Enrich rarity from external reference or Limitless TCG Pocket")
    if src_pct < 20:
        improvements.append("Add source_reference URLs for enriched cards")

    score = (
        (min(set_pct, 100) * 0.20) +
        (min(cat_pct, 100) * 0.25) +
        (min(type_pct, 100) * 0.15) +
        (min(special_pct, 100) * 0.15) +
        (min(rarity_pct, 100) * 0.15) +
        (min(src_pct, 100) * 0.10)
    )

    if blockers:
        status = "Not ready"
    elif score >= 70:
        status = "Partially ready"
    else:
        status = "Not ready"

    return {
        "status": status,
        "score_pct": round(score, 1),
        "component_scores": {
            "set_known_pct": round(set_pct, 1),
            "card_category_known_pct": round(cat_pct, 1),
            "pokemon_type_known_pct": round(type_pct, 1),
            "special_type_known_pct": round(special_pct, 1),
            "rarity_known_pct": round(rarity_pct, 1),
            "source_reference_pct": round(src_pct, 1),
        },
        "blockers": blockers,
        "next_improvements": improvements,
    }


def write_markdown(now, baseline, completeness, ex_inv, special_inv, type_cov, cat_bdown, dupe_inv, top_qty, cleanup, readiness):
    lines = []

    lines += [
        "# Collection Analytics",
        "",
        f"Generated: {now}",
        "",
        f"> **{DEFERRED_NOTE}**",
        "",
    ]

    # A. Baseline
    lines += [
        "## A. Baseline Status",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Total quantity | {baseline['total_quantity']} |",
        f"| Unique card entries | {baseline['unique_entries']} |",
        f"| Provisional expected total | {baseline['expected_total']} |",
        f"| Original app count | {baseline['app_reported_total']} (not forced) |",
        f"| Validation status | {baseline['validation_status']} |",
        "",
        f"> {baseline['discrepancy_note']}",
        "",
    ]

    # B. Metadata completeness
    lines += [
        "## B. Metadata Completeness",
        "",
        "| Field | Total | Known | Unknown/Blank | % Known |",
        "|---|---|---|---|---|",
    ]
    for field, fc in completeness.items():
        lines.append(f"| {field} | {fc['total']} | {fc['known']} | {fc['unknown_or_blank']} | {fc['pct_known']} |")
    lines.append("")

    # C. EX/Mega inventory
    lines += [
        "## C. EX / Mega Inventory",
        "",
    ]
    if ex_inv:
        lines += [
            "| Card Name | Qty | Set Code | Rarity | Card # | Screenshot | Source Ref |",
            "|---|---|---|---|---|---|---|",
        ]
        for c in ex_inv:
            lines.append(
                f"| {c['card_name']} | {c['quantity']} | {c['set_code'] or 'unknown'} | "
                f"{c['rarity']} | {c['card_number'] or 'unknown'} | "
                f"{c['source_screenshot']} | {c['source_reference'] or '—'} |"
            )
    else:
        lines.append("No cards currently marked `is_ex=true` in cards.json.")
    lines.append("")

    # D. Special card inventory
    lines += [
        "## D. Special Card Inventory",
        "",
    ]
    if special_inv["items"]:
        lines += [
            "| Card Name | Qty | Special Type | Set | Screenshot | Source Ref |",
            "|---|---|---|---|---|---|",
        ]
        for c in special_inv["items"]:
            lines.append(
                f"| {c['card_name']} | {c['quantity']} | {c['special_type']} | "
                f"{c['set_or_pack']} | {c['source_screenshot']} | {c['source_reference'] or '—'} |"
            )
    else:
        lines.append("No cards with known special types (other than normal) found.")
    lines.append(f"\n**Cards with `special_type=unknown`:** {special_inv['unknown_special_type_count']}")
    lines.append("")

    # E. Type coverage
    lines += [
        "## E. Type Coverage",
        "",
        "| Pokémon Type | Unique Entries | Total Quantity |",
        "|---|---|---|",
    ]
    for row in type_cov["by_type"]:
        lines.append(f"| {row['pokemon_type']} | {row['entries']} | {row['total_quantity']} |")
    lines += [
        "",
        f"**Unknown/None type entries:** {type_cov['unknown_or_none_entries']} "
        f"(qty: {type_cov['unknown_or_none_quantity']})",
        "",
    ]

    # F. Category breakdown
    lines += [
        "## F. Category Breakdown",
        "",
        "| Category | Unique Entries | Total Quantity |",
        "|---|---|---|",
    ]
    for row in cat_bdown:
        lines.append(f"| {row['card_category']} | {row['entries']} | {row['total_quantity']} |")
    lines.append("")

    # G. Duplicate/surplus inventory
    lines += [
        "## G. Potential Duplicate / Surplus Inventory",
        "",
        "_Label: potential duplicate inventory — not a recommendation._",
        "",
    ]
    if dupe_inv:
        lines += [
            "| Card Name | Qty | Special Type | Set | Screenshot |",
            "|---|---|---|---|---|",
        ]
        for c in dupe_inv:
            lines.append(
                f"| {c['card_name']} | {c['quantity']} | {c['special_type']} | "
                f"{c['set_or_pack']} | {c['source_screenshot']} |"
            )
    else:
        lines.append("No cards with quantity ≥ 2.")
    lines.append("")

    # H. Top cards by quantity
    lines += [
        "## H. Top 10 Cards by Quantity",
        "",
        "| Card Name | Qty | Category | Type | Special Type | Set |",
        "|---|---|---|---|---|---|",
    ]
    for c in top_qty:
        lines.append(
            f"| {c['card_name']} | {c['quantity']} | {c['card_category']} | "
            f"{c['pokemon_type']} | {c['special_type']} | {c['set_or_pack']} |"
        )
    lines.append("")

    # I. Cleanup candidates
    lines += [
        "## I. Cleanup Candidates",
        "",
        "Cards requiring metadata enrichment before recommendations are possible.",
        "",
    ]
    for section, data in cleanup.items():
        label = section.replace("_", " ").title()
        lines.append(f"### {label}")
        lines.append(f"Count: **{data['count']}**")
        if data["examples"]:
            lines.append("")
            lines.append("Examples (up to 25):")
            lines.append(", ".join(data["examples"][:25]))
        lines.append("")

    # J. Recommendation readiness
    lines += [
        "## J. Recommendation Readiness",
        "",
        f"**Status: {readiness['status']}**",
        f"**Readiness Score: {readiness['score_pct']}%**",
        "",
        "### Component Scores",
        "",
        "| Component | % Known |",
        "|---|---|",
    ]
    for k, v in readiness["component_scores"].items():
        lines.append(f"| {k.replace('_', ' ').title()} | {v}% |")

    lines += ["", "### Blockers", ""]
    if readiness["blockers"]:
        for b in readiness["blockers"]:
            lines.append(f"- {b}")
    else:
        lines.append("No blockers currently identified.")

    lines += ["", "### Next Required Data Improvements", ""]
    if readiness["next_improvements"]:
        for imp in readiness["next_improvements"]:
            lines.append(f"- {imp}")
    else:
        lines.append("None identified.")

    lines += [
        "",
        "---",
        "",
        f"> **Reminder:** {DEFERRED_NOTE}",
        "",
    ]

    return "\n".join(lines) + "\n"


def main():
    cards = load_cards()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    baseline = build_baseline(cards)
    completeness = build_metadata_completeness(cards)
    ex_inv = build_ex_inventory(cards)
    special_inv = build_special_inventory(cards)
    type_cov = build_type_coverage(cards)
    cat_bdown = build_category_breakdown(cards)
    dupe_inv = build_duplicate_inventory(cards)
    top_qty = build_top_quantity(cards)
    cleanup = build_cleanup_candidates(cards)
    readiness = build_readiness(cards, completeness, baseline)

    analytics = {
        "generated_at": now,
        "deferred_note": DEFERRED_NOTE,
        "baseline": baseline,
        "metadata_completeness": completeness,
        "ex_inventory": ex_inv,
        "special_inventory": special_inv,
        "type_coverage": type_cov,
        "category_breakdown": cat_bdown,
        "duplicate_inventory": dupe_inv,
        "top_quantity_cards": top_qty,
        "cleanup_candidates": cleanup,
        "recommendation_readiness": readiness,
    }

    md_text = write_markdown(now, baseline, completeness, ex_inv, special_inv, type_cov, cat_bdown, dupe_inv, top_qty, cleanup, readiness)

    ANALYTICS_MD.parent.mkdir(parents=True, exist_ok=True)
    ANALYTICS_MD.write_text(md_text, encoding="utf-8")

    ANALYTICS_JSON.parent.mkdir(parents=True, exist_ok=True)
    ANALYTICS_JSON.write_text(json.dumps(analytics, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Written: {ANALYTICS_MD}")
    print(f"Written: {ANALYTICS_JSON}")
    print(f"Baseline: {baseline['total_quantity']} qty / {baseline['unique_entries']} entries")
    print(f"EX cards: {len(ex_inv)}")
    print(f"Special cards: {len(special_inv['items'])} (unknown special: {special_inv['unknown_special_type_count']})")
    print(f"Readiness: {readiness['status']} ({readiness['score_pct']}%)")


if __name__ == "__main__":
    main()
