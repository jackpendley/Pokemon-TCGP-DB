#!/usr/bin/env python3
"""
Creates a manual review package for all ambiguous and no-match owned cards.

The review package lets the user confirm the correct set/pack for each card
by checking their Pokémon TCG Pocket app collection view.

Inputs:
    cards.json                              — owned card metadata (id, name, special_type, etc.)
    data/exports/owned_pack_coverage.json   — ambiguity classification per card
    data/reference/pack_sources.json        — candidate set_code + card_number per name

Outputs:
    review/ambiguous_cards_review.md        — readable grouped summary with how-to instructions
    data/exports/ambiguous_cards_review.csv — flat rows with blank confirmation columns
    data/exports/ambiguous_cards_review.json — full candidate data (machine-readable)
    review/no_match_cards_review.md
    data/exports/no_match_cards_review.csv
    data/exports/no_match_cards_review.json

Usage:
    python3 scripts/create_ambiguous_review_package.py
"""

import csv
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CARDS_JSON = ROOT / "cards.json"
COVERAGE_JSON = ROOT / "data" / "exports" / "owned_pack_coverage.json"
PACK_SOURCES_JSON = ROOT / "data" / "reference" / "pack_sources.json"

OUT_AMBIG_MD = ROOT / "review" / "ambiguous_cards_review.md"
OUT_AMBIG_CSV = ROOT / "data" / "exports" / "ambiguous_cards_review.csv"
OUT_AMBIG_JSON = ROOT / "data" / "exports" / "ambiguous_cards_review.json"

OUT_NOMATCH_MD = ROOT / "review" / "no_match_cards_review.md"
OUT_NOMATCH_CSV = ROOT / "data" / "exports" / "no_match_cards_review.csv"
OUT_NOMATCH_JSON = ROOT / "data" / "exports" / "no_match_cards_review.json"


def norm_name(s):
    s = str(s or "").strip().lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def load_inputs():
    for p in (CARDS_JSON, COVERAGE_JSON, PACK_SOURCES_JSON):
        if not p.exists():
            print(f"ERROR: required file not found: {p}", file=sys.stderr)
            sys.exit(1)

    cards = json.loads(CARDS_JSON.read_text(encoding="utf-8"))

    cov = json.loads(COVERAGE_JSON.read_text(encoding="utf-8"))
    detail = cov["detail"]

    if len(cards) != len(detail):
        print(
            f"ERROR: cards.json ({len(cards)}) and coverage detail ({len(detail)}) "
            f"are misaligned. Re-run owned_pack_coverage.py first.",
            file=sys.stderr,
        )
        sys.exit(1)

    raw_ps = json.loads(PACK_SOURCES_JSON.read_text(encoding="utf-8"))
    ps_records = raw_ps["records"] if isinstance(raw_ps, dict) else raw_ps

    return cards, detail, ps_records


def build_ps_index(ps_records):
    """Index pack_sources by normalized card name -> list of records."""
    by_norm = defaultdict(list)
    for r in ps_records:
        n = norm_name(r.get("card_name", ""))
        if n:
            by_norm[n].append(r)
    return by_norm


def build_candidates(card_name, set_codes, ps_by_norm):
    """
    For each candidate set_code, gather all matching pack_sources records
    (there may be multiple card_numbers per set if the card appears in multiple
    rarity tiers).

    Returns: list of dicts, one per candidate set_code, with card numbers list.
    """
    n = norm_name(card_name)
    all_records = ps_by_norm.get(n, [])

    # Group by set_code
    by_set = defaultdict(list)
    for r in all_records:
        sc = r.get("set_code")
        if sc in set_codes:
            by_set[sc].append(r)

    candidates = []
    for sc in sorted(set_codes):
        recs = sorted(by_set.get(sc, []), key=lambda r: r.get("card_number", 0))
        numbers = [r.get("card_number") for r in recs]
        packs = sorted(set(r.get("pack_name") for r in recs), key=lambda x: (x is None, x))
        rarities = sorted(set(r.get("rarity") for r in recs if r.get("rarity")))
        expansion = recs[0].get("expansion", "") if recs else ""
        candidates.append({
            "set_code": sc,
            "expansion": expansion,
            "pack_name": packs[0] if len(packs) == 1 else (None if None in packs else packs),
            "pack_names": packs,
            "card_numbers": numbers,
            "rarities": rarities,
        })
    return candidates


def categorize_ambiguity(card_name, set_codes, pack_names):
    """
    Returns a short ambiguity category label for grouping in the markdown.
    """
    has_a4b = "A4b" in set_codes
    has_shared = None in pack_names
    n_sets = len(set_codes)

    if has_a4b and any(sc not in ("A4b",) for sc in set_codes):
        return "special-art-vs-regular"
    elif n_sets == 1:
        # Within-set ambiguity: same set has pack-specific and shared-pool cards
        return "within-set-shared"
    elif n_sets == 2 and not has_shared:
        return "two-pack"
    elif n_sets == 2 and has_shared:
        return "shared-pool"
    elif n_sets >= 3 and has_shared:
        return "multi-set-with-shared"
    else:
        return "multi-set"


def build_ambiguous_records(cards, detail, ps_by_norm):
    """Build structured records for all ambiguous owned cards."""
    records = []
    for card, cov in zip(cards, detail):
        if cov["outcome"] != "name_ambiguous":
            continue

        set_codes = cov.get("set_codes", [])
        pack_names = cov.get("pack_names", [])
        candidates = build_candidates(card["card_name"], set_codes, ps_by_norm)
        category = categorize_ambiguity(card["card_name"], set_codes, pack_names)

        records.append({
            "card_id": card["id"],
            "card_name": card["card_name"],
            "quantity": card.get("quantity", 0),
            "special_type": card.get("special_type", "unknown"),
            "is_ex": card.get("is_ex", False),
            "rarity": card.get("rarity", "unknown"),
            "source_screenshot": card.get("source_screenshot", ""),
            "ambiguity_category": category,
            "candidate_sets": set_codes,
            "candidate_packs": [str(p) if p is not None else "shared (all packs)" for p in pack_names],
            "candidates": candidates,
            "notes": cov.get("notes", ""),
            # Blank confirmation fields for user
            "confirmed_set_code": "",
            "confirmed_card_number": "",
            "confirmed_yes_no": "",
        })
    return records


def build_nomatch_records(cards, detail):
    """Build structured records for all no-match owned cards."""
    records = []
    for card, cov in zip(cards, detail):
        if cov["outcome"] != "no_match":
            continue

        records.append({
            "card_id": card["id"],
            "card_name": card["card_name"],
            "quantity": card.get("quantity", 0),
            "special_type": card.get("special_type", "unknown"),
            "is_ex": card.get("is_ex", False),
            "rarity": card.get("rarity", "unknown"),
            "source_screenshot": card.get("source_screenshot", ""),
            "notes": cov.get("notes", ""),
            # Blank confirmation fields
            "confirmed_set_code": "",
            "confirmed_card_number": "",
            "confirmed_pack_name": "",
            "confirmed_yes_no": "",
        })
    return records


# ─── Markdown: Ambiguous ────────────────────────────────────────────────────


def write_ambiguous_md(now, records):
    lines = [
        "# Ambiguous Pack Assignment — Manual Review",
        "",
        f"Generated: {now}",
        "",
        "This file lists the **{count}** owned card entries that could not be automatically "
        "assigned to a pack because they appear in multiple sets with different pack names. "
        "Manual confirmation of the correct set/pack is required to resolve them.".format(
            count=len(records)
        ),
        "",
        "## How to Confirm a Card",
        "",
        "1. Open your Pokémon TCG Pocket app.",
        "2. Go to **Collection** (or **Cards** tab).",
        "3. Find the card by name.",
        "4. Tap on it to open the card detail view.",
        "5. Look for the **set indicator** (a small icon or text in the corner showing the expansion "
        "logo or abbreviation like A1, B3, etc.).",
        "6. Match that to the candidate sets listed here.",
        "7. Note the card number shown in the detail view (e.g., '42/234').",
        "8. Fill in `confirmed_set_code` and `confirmed_card_number` in the CSV.",
        "9. Set `confirmed_yes_no` to `yes` when done.",
        "",
        "After filling in the CSV, run:",
        "```",
        "python3 scripts/apply_ambiguous_confirmations.py --dry-run",
        "```",
        "to preview changes, then without `--dry-run` to apply them.",
        "",
        "---",
        "",
    ]

    # Group by category
    from itertools import groupby
    categories = {
        "special-art-vs-regular": "A4b Special Art vs Regular Print",
        "within-set-shared": "Within-Set: Pack-Specific vs Shared",
        "two-pack": "Two Candidate Packs",
        "shared-pool": "Pack-Specific vs Shared Pool",
        "multi-set-with-shared": "Multiple Sets Including Shared Pool",
        "multi-set": "Multiple Sets",
    }

    by_category = defaultdict(list)
    for r in records:
        by_category[r["ambiguity_category"]].append(r)

    for cat_key, cat_label in categories.items():
        group = by_category.get(cat_key, [])
        if not group:
            continue

        lines += [
            f"## {cat_label} ({len(group)} cards)",
            "",
        ]

        if cat_key == "special-art-vs-regular":
            lines += [
                "_These cards appear in A4b (Deluxe Pack: ex) as special/full-art or immersive "
                "trainer versions, AND in an older set as a regular print. "
                "Look at your card's artwork — special-art cards have unique full-bleed art._",
                "",
            ]
        elif cat_key == "within-set-shared":
            lines += [
                "_These cards appear within a single expansion but in two forms: a pack-specific "
                "version (only in one named pack) and a shared version (obtainable from any pack). "
                "Look up the exact card number in your app to determine which version you own._",
                "",
            ]
        elif cat_key == "shared-pool":
            lines += [
                "_One candidate is a 'shared' card (available in all packs of that expansion). "
                "If your card is from that expansion, pack_name is not critical — it was available "
                "from any pack in the set._",
                "",
            ]

        for r in group:
            cand_parts = []
            for c in r["candidates"]:
                nums = ", ".join(str(n) for n in c["card_numbers"])
                packs = " / ".join(str(p) for p in c["pack_names"])
                cand_parts.append(
                    f"{c['set_code']} ({c['expansion']}): card #{'s' if len(c['card_numbers']) > 1 else ''}"
                    f"{nums} — pack: {packs}"
                )

            lines += [
                f"### {r['card_name']}",
                f"- **Owned qty**: {r['quantity']}  |  **Special type**: {r['special_type']}"
                f"  |  **Rarity**: {r['rarity']}  |  **Screenshot**: {r['source_screenshot']}",
                f"- **card_id**: `{r['card_id']}`",
                "- **Candidates**:",
            ]
            for part in cand_parts:
                lines.append(f"  - {part}")
            lines.append("")

    lines += [
        "---",
        "",
        f"> Generated by `scripts/create_ambiguous_review_package.py` on {now}.",
        "> Do not edit this file manually — re-run the script to regenerate.",
        "",
    ]

    return "\n".join(lines) + "\n"


# ─── Markdown: No-match ─────────────────────────────────────────────────────


def write_nomatch_md(now, records):
    lines = [
        "# No-Match Cards — Manual Review",
        "",
        f"Generated: {now}",
        "",
        "These **{count}** owned cards have **no match** in `pack_sources.json` by card name. "
        "They cannot be resolved automatically.".format(count=len(records)),
        "",
        "## Known Reasons for No Match",
        "",
        "| Reason | Cards |",
        "|---|---|",
        "| Common trainer items not tracked by Limitless | Potion, X Speed, Hand Scope, Pokédex, Red Card |",
        "| Form variant requiring visual confirmation | Urshifu (Rapid Strike vs Single Strike) |",
        "| Set identity unknown | Zygarde |",
        "",
        "## How to Resolve",
        "",
        "For **Urshifu**: check your card's form in the app. "
        "Rapid Strike Urshifu (blue) is in a different set than Single Strike Urshifu (red).",
        "",
        "For **Zygarde**: check the set indicator in your card detail view.",
        "",
        "For **common trainer items** (Potion, X Speed, etc.): these are not tracked by Limitless "
        "at all. You can confirm the pack by checking your card detail in the app, but they will "
        "not resolve via pack_sources.json without adding a manual entry.",
        "",
        "Fill in `confirmed_set_code`, `confirmed_card_number`, and `confirmed_pack_name` in the CSV, "
        "then set `confirmed_yes_no` to `yes`.",
        "",
        "---",
        "",
        "## Cards",
        "",
        "| Card Name | Qty | Special Type | Rarity | Screenshot | Notes |",
        "|---|---|---|---|---|---|",
    ]

    for r in records:
        lines.append(
            f"| {r['card_name']} | {r['quantity']} | {r['special_type']} "
            f"| {r['rarity']} | {r['source_screenshot']} | {r['notes']} |"
        )

    lines += [
        "",
        "---",
        "",
        f"> Generated by `scripts/create_ambiguous_review_package.py` on {now}.",
        "> Do not edit this file manually — re-run the script to regenerate.",
        "",
    ]

    return "\n".join(lines) + "\n"


# ─── CSV writers ────────────────────────────────────────────────────────────


AMBIG_CSV_FIELDS = [
    "card_id",
    "card_name",
    "quantity",
    "special_type",
    "is_ex",
    "rarity",
    "source_screenshot",
    "ambiguity_category",
    "candidate_sets",
    "candidate_packs",
    "candidate_card_numbers_by_set",
    "confirmed_set_code",
    "confirmed_card_number",
    "confirmed_yes_no",
]

NOMATCH_CSV_FIELDS = [
    "card_id",
    "card_name",
    "quantity",
    "special_type",
    "is_ex",
    "rarity",
    "source_screenshot",
    "notes",
    "confirmed_set_code",
    "confirmed_card_number",
    "confirmed_pack_name",
    "confirmed_yes_no",
]


def write_ambiguous_csv(records, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=AMBIG_CSV_FIELDS)
        writer.writeheader()
        for r in records:
            # Flatten candidate info for CSV
            cands_by_set = "; ".join(
                f"{c['set_code']}: #{','.join(str(n) for n in c['card_numbers'])}"
                for c in r["candidates"]
            )
            writer.writerow({
                "card_id": r["card_id"],
                "card_name": r["card_name"],
                "quantity": r["quantity"],
                "special_type": r["special_type"],
                "is_ex": r["is_ex"],
                "rarity": r["rarity"],
                "source_screenshot": r["source_screenshot"],
                "ambiguity_category": r["ambiguity_category"],
                "candidate_sets": "|".join(r["candidate_sets"]),
                "candidate_packs": "|".join(r["candidate_packs"]),
                "candidate_card_numbers_by_set": cands_by_set,
                "confirmed_set_code": "",
                "confirmed_card_number": "",
                "confirmed_yes_no": "",
            })


def write_nomatch_csv(records, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=NOMATCH_CSV_FIELDS)
        writer.writeheader()
        for r in records:
            writer.writerow({
                "card_id": r["card_id"],
                "card_name": r["card_name"],
                "quantity": r["quantity"],
                "special_type": r["special_type"],
                "is_ex": r["is_ex"],
                "rarity": r["rarity"],
                "source_screenshot": r["source_screenshot"],
                "notes": r["notes"],
                "confirmed_set_code": "",
                "confirmed_card_number": "",
                "confirmed_pack_name": "",
                "confirmed_yes_no": "",
            })


# ─── Main ────────────────────────────────────────────────────────────────────


def main():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"\n=== create_ambiguous_review_package.py ===")
    print(f"Generated: {now}")

    print("\nLoading inputs...")
    cards, detail, ps_records = load_inputs()
    print(f"  cards.json: {len(cards)} entries")
    print(f"  coverage detail: {len(detail)} entries")
    print(f"  pack_sources: {len(ps_records)} records")

    ps_by_norm = build_ps_index(ps_records)

    print("\nBuilding ambiguous card records...")
    ambig_records = build_ambiguous_records(cards, detail, ps_by_norm)
    print(f"  Ambiguous cards: {len(ambig_records)}")

    print("Building no-match card records...")
    nomatch_records = build_nomatch_records(cards, detail)
    print(f"  No-match cards: {len(nomatch_records)}")

    # Write ambiguous outputs
    OUT_AMBIG_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_AMBIG_MD.write_text(write_ambiguous_md(now, ambig_records), encoding="utf-8")
    print(f"\nWritten: {OUT_AMBIG_MD}")

    write_ambiguous_csv(ambig_records, OUT_AMBIG_CSV)
    print(f"Written: {OUT_AMBIG_CSV}")

    ambig_json_out = {
        "_meta": {
            "generated_at": now,
            "total_ambiguous": len(ambig_records),
            "note": (
                "Fill in confirmed_set_code + confirmed_card_number + confirmed_yes_no "
                "then run apply_ambiguous_confirmations.py --dry-run to preview."
            ),
        },
        "records": ambig_records,
    }
    OUT_AMBIG_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_AMBIG_JSON.write_text(
        json.dumps(ambig_json_out, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Written: {OUT_AMBIG_JSON}")

    # Write no-match outputs
    OUT_NOMATCH_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_NOMATCH_MD.write_text(write_nomatch_md(now, nomatch_records), encoding="utf-8")
    print(f"Written: {OUT_NOMATCH_MD}")

    write_nomatch_csv(nomatch_records, OUT_NOMATCH_CSV)
    print(f"Written: {OUT_NOMATCH_CSV}")

    nomatch_json_out = {
        "_meta": {
            "generated_at": now,
            "total_no_match": len(nomatch_records),
            "note": (
                "These cards have no match in pack_sources.json. "
                "Fill confirmed fields and run apply_ambiguous_confirmations.py to apply."
            ),
        },
        "records": nomatch_records,
    }
    OUT_NOMATCH_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_NOMATCH_JSON.write_text(
        json.dumps(nomatch_json_out, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Written: {OUT_NOMATCH_JSON}")

    print(f"\n=== Summary ===")
    print(f"  Ambiguous: {len(ambig_records)} cards -> review/ambiguous_cards_review.md")
    print(f"  No-match:  {len(nomatch_records)} cards -> review/no_match_cards_review.md")
    print(
        f"\nNext: open data/exports/ambiguous_cards_review.csv, fill confirmed columns, "
        f"then run: python3 scripts/apply_ambiguous_confirmations.py --dry-run"
    )


if __name__ == "__main__":
    main()
