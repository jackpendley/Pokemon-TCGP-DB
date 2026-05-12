#!/usr/bin/env python3
"""
Build the pull probability model scaffold for all PTCGP packs.

Card pool counts per rarity are derived from pack_sources.json.
Pull probability rates are NOT invented — all probability values are set to null
until populated from verified in-app offering rates.

The in-app offering rates are the only trusted source for pull probabilities.
To populate rates: record the "Offering Rates" values from each pack detail
screen in the Pokémon TCG Pocket app, or from the official disclosure page.

Inputs:
    data/reference/pack_sources.json
    data/current/pack_source_confidence_scores.json

Outputs:
    data/reference/pull_probability_model.json
    review/pull_probability_model.md

Usage:
    python3 scripts/build_pull_probability_model.py
    python3 scripts/build_pull_probability_model.py --validate
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACK_SOURCES_JSON = ROOT / "data" / "reference" / "pack_sources.json"
CONFIDENCE_SCORES_JSON = ROOT / "data" / "current" / "pack_source_confidence_scores.json"
OUT_JSON = ROOT / "data" / "reference" / "pull_probability_model.json"
OUT_MD = ROOT / "review" / "pull_probability_model.md"

RARITY_FIELDS = [
    "one_diamond", "two_diamond", "three_diamond", "four_diamond",
    "one_star", "double_star", "triple_star", "crown", "promo", "unknown",
]

# Standard PTCGP pack: 5 cards per pack.
# Slot model is documented structurally; per-slot probabilities require verified source.
STANDARD_SLOT_MODEL = {
    "cards_per_pack": 5,
    "slot_count": 5,
    "notes": (
        "Standard PTCGP pack: 5 cards. "
        "Per-slot probability breakdown requires verified in-app Offering Rates."
    ),
}


def rarity_counts(cards: list) -> dict:
    """Return dict of rarity → count, using only defined RARITY_FIELDS keys."""
    raw = Counter(c.get("rarity") for c in cards)
    out = {}
    for r in RARITY_FIELDS:
        v = raw.get(r, 0)
        if v > 0:
            out[r] = v
    # Anything not in RARITY_FIELDS goes to 'unknown'
    unknowns = sum(v for k, v in raw.items() if k not in RARITY_FIELDS)
    if unknowns > 0:
        out["unknown"] = out.get("unknown", 0) + unknowns
    return out


def add_rarity_dicts(a: dict, b: dict) -> dict:
    """Element-wise sum of two rarity-count dicts."""
    keys = set(a) | set(b)
    return {k: a.get(k, 0) + b.get(k, 0) for k in keys}


def build_pack_records(records: list) -> list:
    """
    Return list of pack records — one per distinct pullable named pack.
    Shared-pool cards are folded into each named pack's combined_pool.
    """
    # Index by (expansion, pack_name) — None pack_name = shared pool
    by_exp_pack = defaultdict(list)
    for r in records:
        exp = r.get("expansion", "")
        pn = r.get("pack_name")
        by_exp_pack[(exp, pn)].append(r)

    # Group expansions: find all named packs and shared pool per expansion
    expansions = defaultdict(lambda: {"named": {}, "shared": []})
    for (exp, pn), cards in by_exp_pack.items():
        if pn is None:
            expansions[exp]["shared"] = cards
        else:
            expansions[exp]["named"][pn] = cards

    pack_records = []
    for exp in sorted(expansions):
        d = expansions[exp]
        shared = d["shared"]
        shared_by_rarity = rarity_counts(shared)
        shared_total = len(shared)

        # Derive set_code from first card
        all_exp_cards = shared + [c for cc in d["named"].values() for c in cc]
        set_code = all_exp_cards[0].get("set_code", "") if all_exp_cards else ""

        named_packs = d["named"]
        if not named_packs:
            # Expansion has only shared pool — should not happen but handle defensively
            continue

        for pn in sorted(named_packs):
            pack_cards = named_packs[pn]
            pack_by_rarity = rarity_counts(pack_cards)
            pack_total = len(pack_cards)
            combined_by_rarity = add_rarity_dicts(pack_by_rarity, shared_by_rarity)
            combined_total = pack_total + shared_total

            pack_records.append({
                "pack_name": pn,
                "expansion": exp,
                "set_code": set_code,
                "is_shared_pool": False,
                "source_url": None,
                "source_name": "in_app_offering_rates_not_yet_recorded",
                "confidence": "unknown",
                "slot_model": STANDARD_SLOT_MODEL,
                "card_pool": {
                    "pack_specific_total": pack_total,
                    "shared_pool_total": shared_total,
                    "combined_total": combined_total,
                    "pack_specific_by_rarity": pack_by_rarity,
                    "shared_pool_by_rarity": shared_by_rarity,
                    "combined_by_rarity": combined_by_rarity,
                },
                "rarity_probabilities": {f: None for f in RARITY_FIELDS},
                "notes": (
                    "Probability rates not yet populated. "
                    "Source required: in-app Offering Rates screen for this pack, "
                    "or official PTCGP probability disclosure."
                ),
            })

    return pack_records


def write_json(pack_records: list) -> dict:
    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generated_by": "build_pull_probability_model.py",
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "model_version": "0.1.0-scaffold",
            "source_status": "scaffold_only",
            "verified_source": None,
            "notes": (
                "This is a scaffold model. Card pool counts per rarity are derived from "
                "pack_sources.json (Limitless TCG Pocket). "
                "Pull probability rates (rarity_probabilities) are ALL null — "
                "they must be populated from the official in-app Offering Rates screen "
                "or the official Pokémon TCG Pocket probability disclosure page. "
                "Do not invent or estimate pull rates. "
                "Required source: open each pack in the PTCGP app > Pack details > Offering Rates."
            ),
        },
        "probability_source_required": {
            "status": "MISSING",
            "description": (
                "Verified in-app offering rates have not been recorded. "
                "All rarity_probabilities are null."
            ),
            "how_to_populate": (
                "In the Pokémon TCG Pocket app: tap a pack > view 'Offering Rates' / "
                "'Card Rates' section. Record the per-rarity probability for each slot. "
                "Then populate rarity_probabilities in this file and set confidence='verified'."
            ),
            "official_disclosure": (
                "The Pokémon Company discloses pack pull rates in-app as required. "
                "Rates vary by rarity tier; typical structure is 5 cards per pack "
                "with slot-specific probability tables."
            ),
        },
        "packs": pack_records,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


def write_md(out: dict, pack_records: list):
    n_packs = len(pack_records)
    lines = [
        "# Pull Probability Model",
        "",
        "> **Scaffold only — pull rates are NOT populated.**",
        "> All `rarity_probabilities` values are `null`.",
        "> Card pool counts (how many cards of each rarity exist per pack) are from `pack_sources.json`.",
        "> Pull rates must come from the official in-app Offering Rates screen.",
        "",
        "## Status",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Model version | {out['meta']['model_version']} |",
        f"| Source status | **{out['meta']['source_status']}** |",
        f"| Verified source | {out['meta']['verified_source'] or 'None — rates unverified'} |",
        f"| Total packs modeled | {n_packs} |",
        f"| Probability values | **all null** |",
        "",
        "## How to Populate Pull Rates",
        "",
        "1. Open the Pokémon TCG Pocket app.",
        "2. Navigate to the pack you want to record.",
        "3. View the **Offering Rates** / **Card Rates** section (disclosed in-app).",
        "4. Record the per-rarity probability for the pack.",
        "5. Populate `rarity_probabilities` in `data/reference/pull_probability_model.json`.",
        "6. Set `confidence: 'verified'` and `source_name: 'ptcgp_in_app_offering_rates'`.",
        "7. Re-run `python3 scripts/validate_pull_probability_model.py`.",
        "",
        "## Pack Pool Summary",
        "",
        "| Pack | Expansion | Set | Pool Total | 1◆ | 2◆ | 3◆ | 4◆ | ☆ | ☆☆ | ☆☆☆ |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]

    for p in pack_records:
        cp = p["card_pool"]["combined_by_rarity"]
        lines.append(
            f"| {p['pack_name']} | {p['expansion']} | {p['set_code']} "
            f"| {p['card_pool']['combined_total']} "
            f"| {cp.get('one_diamond', 0)} "
            f"| {cp.get('two_diamond', 0)} "
            f"| {cp.get('three_diamond', 0)} "
            f"| {cp.get('four_diamond', 0)} "
            f"| {cp.get('one_star', 0)} "
            f"| {cp.get('double_star', 0)} "
            f"| {cp.get('triple_star', 0)} |"
        )

    lines += [
        "",
        "## Probability Rates Status",
        "",
        "All rarity probability values are currently `null`.",
        "The following rates are required per pack before pack EV can be computed:",
        "",
        "- `one_diamond` — probability that a card slot contains a 1-diamond rarity card",
        "- `two_diamond` — 2-diamond",
        "- `three_diamond` — 3-diamond (rare)",
        "- `four_diamond` — 4-diamond (ex Pokémon)",
        "- `one_star` — full-art / illustration rare",
        "- `double_star` — special-art / shiny",
        "- `triple_star` — immersive / rainbow",
        "- `crown` — crown / gold (if applicable)",
        "",
        "> **Do not estimate or infer these rates.** Use only the official in-app Offering Rates.",
        "",
        "## Rarity Field Mapping",
        "",
        "Rarity names in this model match `pack_sources.json`:",
        "",
        "| Field | Meaning |",
        "|---|---|",
        "| `one_diamond` | Common (◆) |",
        "| `two_diamond` | Uncommon (◆◆) |",
        "| `three_diamond` | Rare (◆◆◆) |",
        "| `four_diamond` | EX / Ultra Rare (◆◆◆◆) |",
        "| `one_star` | Full Art / Illustration Rare (☆) |",
        "| `double_star` | Special Art / Shiny (☆☆) |",
        "| `triple_star` | Immersive / Rainbow (☆☆☆) |",
        "| `crown` | Crown / Gold |",
        "| `promo` | Promo card |",
        "",
    ]

    (ROOT / "review").mkdir(exist_ok=True)
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def run_validate() -> bool:
    print("\n=== build_pull_probability_model.py [VALIDATE] ===")
    errors = 0

    if not OUT_JSON.exists():
        print("  ERROR: output JSON not found — run without --validate first")
        return False

    out = json.loads(OUT_JSON.read_text(encoding="utf-8"))

    # 1. top-level meta and packs
    for field in ("meta", "packs"):
        if field not in out:
            print(f"  ERROR: missing top-level field '{field}'")
            errors += 1
    if errors:
        return False
    print("  PASS  meta and packs fields present")

    packs = out["packs"]

    # 2. every pack has pack_name, expansion, set_code
    bad_identity = [p for p in packs
                    if not p.get("pack_name") and not p.get("is_shared_pool")]
    if bad_identity:
        print(f"  ERROR: {len(bad_identity)} packs missing pack_name/is_shared_pool")
        errors += 1
    else:
        print(f"  PASS  all packs have pack_name or is_shared_pool")

    bad_exp = [p for p in packs if not p.get("expansion")]
    if bad_exp:
        print(f"  ERROR: {len(bad_exp)} packs missing expansion")
        errors += 1
    else:
        print(f"  PASS  all packs have expansion")

    bad_sc = [p for p in packs if not p.get("set_code")]
    if bad_sc:
        print(f"  ERROR: {len(bad_sc)} packs missing set_code")
        errors += 1
    else:
        print(f"  PASS  all packs have set_code")

    # 3. probability values are null or numbers in [0, 1]
    prob_errors = 0
    for p in packs:
        rp = p.get("rarity_probabilities", {})
        for field, val in rp.items():
            if val is not None and not (isinstance(val, (int, float)) and 0 <= val <= 1):
                print(f"  ERROR: {p['pack_name']}.{field} = {val} (must be null or 0–1)")
                prob_errors += 1
    if prob_errors:
        errors += prob_errors
    else:
        print(f"  PASS  all probability values are null or in [0, 1]")

    # 4. confidence field valid
    valid_conf = {"verified", "inferred", "unknown"}
    bad_conf = [p for p in packs if p.get("confidence") not in valid_conf]
    if bad_conf:
        print(f"  ERROR: {len(bad_conf)} packs have invalid confidence value")
        errors += 1
    else:
        print(f"  PASS  all confidence values valid")

    # 5. if confidence=verified, source_url or source_name must be present
    bad_verified = [p for p in packs
                    if p.get("confidence") == "verified"
                    and not p.get("source_url") and not p.get("source_name")]
    if bad_verified:
        print(f"  ERROR: {len(bad_verified)} verified packs missing source_url/source_name")
        errors += 1
    else:
        print(f"  PASS  verified packs have source attribution (or none are verified yet)")

    # 6. card pool totals are non-negative
    bad_pools = [
        p for p in packs
        if p.get("card_pool", {}).get("combined_total", -1) < 0
    ]
    if bad_pools:
        print(f"  ERROR: {len(bad_pools)} packs have negative combined_total")
        errors += 1
    else:
        print(f"  PASS  all card pool totals non-negative")

    # 7. model is valid even with unknown probabilities (just document it)
    unknown_count = sum(
        1 for p in packs
        if all(v is None for v in p.get("rarity_probabilities", {}).values())
    )
    print(f"  INFO  {unknown_count}/{len(packs)} packs have all-null probabilities "
          f"(scaffold_only — expected)")

    if errors == 0:
        print(f"\nVALIDATION PASSED  ({len(packs)} packs, source_status="
              f"{out['meta']['source_status']})")
    else:
        print(f"\nVALIDATION FAILED  ({errors} error(s))")
    return errors == 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Build or validate the pull probability model scaffold"
    )
    parser.add_argument("--validate", action="store_true",
                        help="Validate existing output rather than regenerating")
    args = parser.parse_args()

    if args.validate:
        ok = run_validate()
        sys.exit(0 if ok else 1)

    print("\n=== build_pull_probability_model.py ===")

    if not PACK_SOURCES_JSON.exists():
        print(f"ERROR: {PACK_SOURCES_JSON} not found", file=sys.stderr)
        sys.exit(1)

    ps_raw = json.loads(PACK_SOURCES_JSON.read_text(encoding="utf-8"))
    records = ps_raw["records"] if isinstance(ps_raw, dict) else ps_raw
    print(f"  Pack sources: {len(records)} records")

    pack_records = build_pack_records(records)
    print(f"  Pullable packs: {len(pack_records)}")

    out = write_json(pack_records)
    write_md(out, pack_records)

    print(f"  Written: {OUT_JSON.relative_to(ROOT)}")
    print(f"  Written: {OUT_MD.relative_to(ROOT)}")
    print(f"\n=== Summary ===")
    print(f"  Packs modeled:        {len(pack_records)}")
    print(f"  Source status:        {out['meta']['source_status']}")
    print(f"  Verified rates:       NONE — all null (scaffold only)")
    print(f"\nDone.")


if __name__ == "__main__":
    main()
