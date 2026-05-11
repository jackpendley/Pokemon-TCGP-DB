#!/usr/bin/env python3
"""
Creates a focused review package for the 10 ambiguous cards that were skipped
during apply_ambiguous_confirmations.py because they had multi-value
set codes (e.g. A1/A4b) or multiple card numbers in the filled CSV.

Reads:
    cards.json
    data/reference/pack_sources.json
    data/exports/owned_pack_coverage.json

Outputs:
    review/skipped_multi_value_review.md
    data/exports/skipped_multi_value_review.csv
    data/exports/skipped_multi_value_review.json

Usage:
    python3 scripts/create_skipped_multi_value_review.py
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
PACK_SOURCES_JSON = ROOT / "data" / "reference" / "pack_sources.json"
COVERAGE_JSON = ROOT / "data" / "exports" / "owned_pack_coverage.json"

OUT_MD = ROOT / "review" / "skipped_multi_value_review.md"
OUT_CSV = ROOT / "data" / "exports" / "skipped_multi_value_review.csv"
OUT_JSON = ROOT / "data" / "exports" / "skipped_multi_value_review.json"

CSV_FIELDS = [
    "owned_card_id",
    "card_name",
    "current_quantity",
    "current_is_ex",
    "current_special_type",
    "current_rarity",
    "source_screenshot",
    "likely_issue",
    "candidate_summary",
    # Up to 3 pre-filled options
    "option_1_set_code",
    "option_1_card_number",
    "option_1_pack_name",
    "option_1_rarity",
    "option_2_set_code",
    "option_2_card_number",
    "option_2_pack_name",
    "option_2_rarity",
    "option_3_set_code",
    "option_3_card_number",
    "option_3_pack_name",
    "option_3_rarity",
    # User fills these:
    "confirmed_action",         # apply_single | split_record | leave_unresolved
    "confirmed_set_code",
    "confirmed_card_number",
    "confirmed_quantity_for_this_version",
    "split_1_set_code",
    "split_1_card_number",
    "split_1_quantity",
    "split_2_set_code",
    "split_2_card_number",
    "split_2_quantity",
    "user_notes",
]


def norm(s):
    s = str(s or "").strip().lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def load_inputs():
    for p in (CARDS_JSON, PACK_SOURCES_JSON, COVERAGE_JSON):
        if not p.exists():
            print(f"ERROR: {p} not found", file=sys.stderr)
            sys.exit(1)
    cards = json.loads(CARDS_JSON.read_text(encoding="utf-8"))
    ps_raw = json.loads(PACK_SOURCES_JSON.read_text(encoding="utf-8"))
    ps_records = ps_raw["records"] if isinstance(ps_raw, dict) else ps_raw
    cov = json.loads(COVERAGE_JSON.read_text(encoding="utf-8"))
    return cards, ps_records, cov["detail"]


def build_ps_indexes(ps_records):
    by_norm_name = defaultdict(list)
    by_key = {}
    for r in ps_records:
        n = norm(r.get("card_name", ""))
        if n:
            by_norm_name[n].append(r)
        key = (r.get("set_code"), r.get("card_number"))
        if key[0] and key[1] is not None:
            by_key[key] = r
    return by_norm_name, by_key


def get_candidates(name, by_norm_name):
    return sorted(by_norm_name.get(norm(name), []),
                  key=lambda r: (r["set_code"], r["card_number"]))


def build_records(cards, detail, by_norm_name, by_key):
    """
    Build structured analysis for each of the 10 remaining ambiguous cards.
    Alignment between cards.json and detail is positional (1:1).
    """
    records = []
    for card, d in zip(cards, detail):
        if d["outcome"] != "name_ambiguous":
            continue

        name = card["card_name"]
        card_id = card["id"]
        qty = card.get("quantity", 0)
        is_ex = card.get("is_ex", False)
        special_type = card.get("special_type", "unknown")
        rarity = card.get("rarity", "unknown")
        screenshot = card.get("source_screenshot", "")

        # --- Determine candidates and likely issue ---

        if name == "Marowak" and is_ex:
            # is_ex=True but the name-match finds regular Marowak.
            # Look up "Marowak ex" instead.
            marowak_ex_candidates = sorted(
                by_norm_name.get("marowak ex", []),
                key=lambda r: (r["set_code"], r["card_number"])
            )
            candidates = marowak_ex_candidates
            likely_issue = (
                "ex_mismatch — card has is_ex=True but name lookup matched regular Marowak. "
                "Candidates below are for Marowak ex. "
                "Prior fill (A1/#226, A4b/#353) was incorrect (those are Lt. Surge and Red). "
                "Check card number in app — likely A1/#153 (Mewtwo, 4-diamond) or A4b/#196."
            )
            # Best options for Marowak ex
            options = [
                {"set_code": "A1", "card_number": 153, "pack_name": "Mewtwo", "rarity": "four_diamond"},
                {"set_code": "A4b", "card_number": 196, "pack_name": "Deluxe Pack: ex", "rarity": "four_diamond"},
                {"set_code": "A3", "card_number": 236, "pack_name": "Lunala", "rarity": "double_star"},
            ]

        elif name in ("Giovanni", "Sabrina", "Leaf", "Cyrus", "Lillie"):
            candidates = get_candidates(name, by_norm_name)
            likely_issue = (
                "regular vs A4b special-art — single owned card but name appears in an "
                "older set (regular 2-diamond or full-art) AND in A4b (Deluxe Pack: ex, "
                "immersive special-art). Check card artwork: A4b immersive trainers have "
                "full-bleed unique art. Rarity in app: 2♦ = two_diamond, ☆☆ = double_star."
            )
            # Extract unique options by set_code group
            by_set = defaultdict(list)
            for c in candidates:
                by_set[c["set_code"]].append(c)
            options = []
            for sc in sorted(by_set):
                first = by_set[sc][0]
                options.append({
                    "set_code": sc,
                    "card_number": first["card_number"],
                    "pack_name": first["pack_name"],
                    "rarity": first["rarity"],
                })
            options = options[:3]

        elif name in ("Rare Candy", "Giant Cape"):
            candidates = get_candidates(name, by_norm_name)
            likely_issue = (
                "regular vs A4b special version — item/tool appears in an older set "
                "(shared pool or pack-specific) AND in A4b (Deluxe Pack: ex). "
                "Check set indicator in card detail view."
            )
            by_set = defaultdict(list)
            for c in candidates:
                by_set[c["set_code"]].append(c)
            options = []
            for sc in sorted(by_set):
                first = by_set[sc][0]
                options.append({
                    "set_code": sc,
                    "card_number": first["card_number"],
                    "pack_name": str(first["pack_name"]) if first["pack_name"] else "shared (all packs)",
                    "rarity": first["rarity"],
                })
            options = options[:3]

        elif name == "Bulbasaur":
            # This is v2 — rarity=one_diamond, screenshot IMG_1535.PNG
            # v1 confirmed A1/#227, v3 confirmed B1a/#1
            # one_diamond options: A1/#1, A4b/#1, A4b/#2
            candidates = get_candidates(name, by_norm_name)
            one_diamond = [c for c in candidates if c.get("rarity") == "one_diamond"]
            # Exclude B1a/#1 (already used by v3)
            one_diamond = [c for c in one_diamond
                           if not (c["set_code"] == "B1a" and c["card_number"] == 1)]
            likely_issue = (
                "same name across multiple sets — rarity=one_diamond narrows candidates "
                "significantly. B1a/#1 is already confirmed as bulbasaur_unknown_unknown_v3. "
                "Remaining one_diamond options: A1/#1 (Mewtwo), A4b/#1, A4b/#2 (Deluxe Pack: ex)."
            )
            options = [
                {"set_code": c["set_code"], "card_number": c["card_number"],
                 "pack_name": c.get("pack_name"), "rarity": c.get("rarity")}
                for c in one_diamond
            ][:3]

        elif name == "Farfetch'd":
            candidates = get_candidates(name, by_norm_name)
            likely_issue = (
                "same name across multiple sets — appears in A1 (shared pool, one_diamond), "
                "A3b (Eevee Grove, one_star), A4a (Secluded Springs, one_diamond), and A4b "
                "(multiple versions including one_diamond and one_star). "
                "Check set indicator and card number in app."
            )
            by_set = defaultdict(list)
            for c in candidates:
                by_set[c["set_code"]].append(c)
            options = []
            for sc in sorted(by_set):
                first = by_set[sc][0]
                options.append({
                    "set_code": sc,
                    "card_number": first["card_number"],
                    "pack_name": str(first["pack_name"]) if first["pack_name"] else "shared (all packs)",
                    "rarity": first["rarity"],
                })
            options = options[:3]

        else:
            candidates = get_candidates(name, by_norm_name)
            likely_issue = "requires manual review"
            options = [
                {"set_code": c["set_code"], "card_number": c["card_number"],
                 "pack_name": c.get("pack_name"), "rarity": c.get("rarity")}
                for c in candidates
            ][:3]

        # Pad options to exactly 3
        while len(options) < 3:
            options.append({"set_code": "", "card_number": "", "pack_name": "", "rarity": ""})

        candidate_summary = " | ".join(
            f"{c['set_code']}#{c['card_number']} {c.get('pack_name','?')} [{c.get('rarity','?')}]"
            for c in candidates
        )

        records.append({
            "owned_card_id": card_id,
            "card_name": name,
            "current_quantity": qty,
            "current_is_ex": is_ex,
            "current_special_type": special_type,
            "current_rarity": rarity,
            "source_screenshot": screenshot,
            "likely_issue": likely_issue,
            "candidate_summary": candidate_summary,
            "options": options,
            "all_candidates": candidates,
        })

    return records


def write_markdown(now, records):
    lines = [
        "# Skipped Multi-Value Confirmations — Manual Review",
        "",
        f"Generated: {now}",
        "",
        f"These **{len(records)}** cards were skipped during `apply_ambiguous_confirmations.py` "
        "because the filled CSV contained multi-value set codes (e.g. `A1/A4b`) or "
        "comma-separated card numbers (e.g. `226, 353`). Each needs a single definitive "
        "answer before it can be applied.",
        "",
        "---",
        "",
        "## How to Fill the CSV",
        "",
        "Open `data/exports/skipped_multi_value_review.csv` and fill the right-hand columns.",
        "",
        "### If you own exactly ONE version of this card:",
        "",
        "```",
        "confirmed_action = apply_single",
        "confirmed_set_code = <set code from options, e.g. B3>",
        "confirmed_card_number = <card number, e.g. 89>",
        "confirmed_quantity_for_this_version = (leave blank — uses existing quantity)",
        "```",
        "",
        "### If you own TWO distinct versions (different set or card number):",
        "",
        "```",
        "confirmed_action = split_record",
        "split_1_set_code = <first version set code>",
        "split_1_card_number = <first version card number>",
        "split_1_quantity = <how many of this version you own>",
        "split_2_set_code = <second version set code>",
        "split_2_card_number = <second version card number>",
        "split_2_quantity = <how many of this version>",
        "```",
        "",
        "**Split quantities must add up to the current total quantity.** "
        "If the current quantity is 1 and you genuinely own both versions, set 1+1 and note "
        "this in `user_notes` — the apply script will require `--allow-quantity-increase` "
        "to handle that case.",
        "",
        "### If you're unsure:",
        "",
        "```",
        "confirmed_action = leave_unresolved",
        "user_notes = <why you're unsure>",
        "```",
        "",
        "After filling, run:",
        "```",
        "python3 scripts/apply_skipped_multi_value_confirmations.py --dry-run",
        "python3 scripts/apply_skipped_multi_value_confirmations.py --apply",
        "```",
        "",
        "---",
        "",
        "## How to Find the Card Number in Your App",
        "",
        "1. Open Pokémon TCG Pocket.",
        "2. Go to **Collection** → find the card by name.",
        "3. Tap the card to open its detail view.",
        "4. Look at the bottom of the card for the **set indicator icon** and "
        "**card number** (e.g. `42/234` means card 42 in a 234-card set).",
        "5. Match the set size to identify the expansion:",
        "",
        "| Set | Expansion | Cards |",
        "|---|---|---|",
        "| A1 | Genetic Apex | 286 |",
        "| A1a | Mythical Island | 86 |",
        "| A2 | Space-Time Smackdown | 207 |",
        "| A3 | Celestial Guardians | 239 |",
        "| A4b | Deluxe Pack: ex | 379 |",
        "| B1a | Crimson Blaze | 103 |",
        "",
        "---",
        "",
        "## Cards Requiring Review",
        "",
    ]

    for r in records:
        lines += [
            f"### {r['card_name']}",
            "",
            f"- **owned_card_id**: `{r['owned_card_id']}`",
            f"- **Quantity**: {r['current_quantity']}  |  **is_ex**: {r['current_is_ex']}  "
            f"|  **rarity**: {r['current_rarity']}  |  **special_type**: {r['current_special_type']}",
            f"- **Screenshot**: {r['source_screenshot']}",
            f"- **Likely issue**: {r['likely_issue']}",
            "",
            "**All candidates:**",
            "",
            "| Set | Card # | Pack | Rarity |",
            "|---|---|---|---|",
        ]
        for c in r["all_candidates"]:
            pack = str(c.get("pack_name")) if c.get("pack_name") else "shared (all packs)"
            lines.append(f"| {c['set_code']} | {c['card_number']} | {pack} | {c.get('rarity','?')} |")

        if r["card_name"] == "Marowak":
            lines += [
                "",
                "> **⚠ MAROWAK NOTE:** Your card has `is_ex=True`. The candidates above are for "
                "**Marowak ex** (not regular Marowak). Your previous fill (`A1/226`, `A4b/353`) "
                "was wrong — those are Lt. Surge and Red. The most likely options are "
                "**A1/#153** (Mewtwo pack, four-diamond) or **A4b/#196** (Deluxe Pack: ex, four-diamond). "
                "Check your card's number and pack icon in the app.",
            ]

        if r["card_name"] == "Bulbasaur":
            lines += [
                "",
                "> **BULBASAUR v2 NOTE:** `bulbasaur_unknown_unknown_v1` was confirmed as A1/#227 "
                "(one_star, Mewtwo), and `bulbasaur_unknown_unknown_v3` as B1a/#1 (Crimson Blaze). "
                "This entry (`v2`) has `rarity=one_diamond`, which rules out the one_star versions. "
                "Most likely: **A1/#1** (Mewtwo pack) or **A4b/#1** (Deluxe Pack: ex).",
            ]

        lines.append("")

    lines += [
        "---",
        "",
        f"> Generated by `scripts/create_skipped_multi_value_review.py` on {now}.",
        "> Do not edit manually — re-run the script to regenerate.",
        "",
    ]
    return "\n".join(lines) + "\n"


def write_csv(records, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for r in records:
            opts = r["options"]
            row = {
                "owned_card_id": r["owned_card_id"],
                "card_name": r["card_name"],
                "current_quantity": r["current_quantity"],
                "current_is_ex": r["current_is_ex"],
                "current_special_type": r["current_special_type"],
                "current_rarity": r["current_rarity"],
                "source_screenshot": r["source_screenshot"],
                "likely_issue": r["likely_issue"],
                "candidate_summary": r["candidate_summary"],
                "option_1_set_code": opts[0].get("set_code", ""),
                "option_1_card_number": opts[0].get("card_number", ""),
                "option_1_pack_name": str(opts[0].get("pack_name", "")) if opts[0].get("pack_name") else "shared",
                "option_1_rarity": opts[0].get("rarity", ""),
                "option_2_set_code": opts[1].get("set_code", ""),
                "option_2_card_number": opts[1].get("card_number", ""),
                "option_2_pack_name": str(opts[1].get("pack_name", "")) if opts[1].get("pack_name") else ("shared" if opts[1].get("set_code") else ""),
                "option_2_rarity": opts[1].get("rarity", ""),
                "option_3_set_code": opts[2].get("set_code", ""),
                "option_3_card_number": opts[2].get("card_number", ""),
                "option_3_pack_name": str(opts[2].get("pack_name", "")) if opts[2].get("pack_name") else ("shared" if opts[2].get("set_code") else ""),
                "option_3_rarity": opts[2].get("rarity", ""),
                # User fills:
                "confirmed_action": "",
                "confirmed_set_code": "",
                "confirmed_card_number": "",
                "confirmed_quantity_for_this_version": "",
                "split_1_set_code": "",
                "split_1_card_number": "",
                "split_1_quantity": "",
                "split_2_set_code": "",
                "split_2_card_number": "",
                "split_2_quantity": "",
                "user_notes": "",
            }
            writer.writerow(row)


def write_json(now, records, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    output = {
        "_meta": {
            "generated_at": now,
            "total_records": len(records),
            "note": (
                "These cards were skipped during apply_ambiguous_confirmations.py because "
                "the filled CSV had multi-value set codes or card numbers. "
                "Fill confirmed_action + relevant fields in the CSV, then run "
                "apply_skipped_multi_value_confirmations.py --dry-run."
            ),
        },
        "records": [
            {
                "owned_card_id": r["owned_card_id"],
                "card_name": r["card_name"],
                "current_quantity": r["current_quantity"],
                "current_is_ex": r["current_is_ex"],
                "current_special_type": r["current_special_type"],
                "current_rarity": r["current_rarity"],
                "source_screenshot": r["source_screenshot"],
                "likely_issue": r["likely_issue"],
                "all_candidates": r["all_candidates"],
                "suggested_options": r["options"],
            }
            for r in records
        ],
    }
    path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")


def main():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"\n=== create_skipped_multi_value_review.py ===")
    print(f"Generated: {now}")

    cards, ps_records, detail = load_inputs()
    print(f"  cards.json: {len(cards)}, pack_sources: {len(ps_records)}, coverage: {len(detail)}")

    by_norm_name, by_key = build_ps_indexes(ps_records)

    records = build_records(cards, detail, by_norm_name, by_key)
    print(f"  Remaining ambiguous records: {len(records)}")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(write_markdown(now, records), encoding="utf-8")
    print(f"\nWritten: {OUT_MD}")

    write_csv(records, OUT_CSV)
    print(f"Written: {OUT_CSV}")

    write_json(now, records, OUT_JSON)
    print(f"Written: {OUT_JSON}")

    print(f"\n=== Summary ===")
    for r in records:
        print(f"  {r['card_name']:20s} | qty={r['current_quantity']} is_ex={r['current_is_ex']} | {r['likely_issue'][:60]}...")


if __name__ == "__main__":
    main()
