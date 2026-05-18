#!/usr/bin/env python3
"""
generate_hourglass_spending_plan.py

Generates a pack-opening hourglass spending plan from EV data.
Outputs conservative / moderate / aggressive scenarios in 10-pack-batch format.
Does NOT assume a specific hourglass balance.

Outputs:
  review/final_hourglass_spending_plan.md
  data/current/final_hourglass_spending_plan.json
  data/exports/final_hourglass_spending_plan.csv

Usage:
  python3 scripts/generate_hourglass_spending_plan.py
  python3 scripts/generate_hourglass_spending_plan.py --validate
"""

import json
import csv
import argparse
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
PACK_EV_JSON = BASE / "data/current/pack_ev.json"
RECOMMENDATIONS_JSON = BASE / "data/current/inferred_pack_recommendations.json"
PULL_MODEL_JSON = BASE / "data/reference/pull_probability_model.json"
COLLECTION_JSON = BASE / "collection.json"  # raw JSONC — not parsed directly
COLLECTION_NORMALIZED_JSON = BASE / "data/current/collection_normalized.json"

OUT_JSON = BASE / "data/current/final_hourglass_spending_plan.json"
OUT_MD = BASE / "review/final_hourglass_spending_plan.md"
OUT_CSV = BASE / "data/exports/final_hourglass_spending_plan.csv"

BATCH_SIZE = 10
GENERATED_AT = "2026-05-12"

DISCLAIMER = (
    "IMPORTANT — NOT OFFICIAL: Slot rates are third_party_verified (confirmed by 4 independent "
    "sources: Game8, ONE Esports, CGMagazine, ShackNews) but NOT officially verified from the "
    "in-app Offering Rates screen. EV calculations are for planning purposes only. "
    "Do not treat these as guaranteed outcomes. Verify slot rates in PTCGP app "
    "(any pack → Pack details → Offering Rates) before committing large resources."
)

GLOBAL_RERUN_CHECKLIST = [
    "After every 20+ pack opens from the same pool: re-run python3 scripts/build_pack_ev.py",
    "After completing any deck target: re-run python3 scripts/build_pack_ev.py (deck_target_ev drops to zero)",
    "After official in-app rate verification: set confidence=verified and re-run python3 scripts/build_pack_ev.py",
    "After resolving 59 ambiguous collection entries: re-run python3 scripts/build_pack_ev.py for more accurate coverage",
    "After any new expansion releases: re-run python3 scripts/build_pull_probability_model.py then python3 scripts/build_pack_ev.py",
    "After updating collection.json with new cards: re-run python3 scripts/normalize_current_collection.py then python3 scripts/build_pack_ev.py",
]


def load_data():
    ev = json.loads(PACK_EV_JSON.read_text(encoding="utf-8"))
    recs = json.loads(RECOMMENDATIONS_JSON.read_text(encoding="utf-8"))
    model = json.loads(PULL_MODEL_JSON.read_text(encoding="utf-8"))
    raw_coll = json.loads(COLLECTION_NORMALIZED_JSON.read_text(encoding="utf-8"))
    coll = raw_coll  # full dict
    return ev, recs, model, coll


def _batch_ev(pack, multiplier=1.0):
    return round(pack["confidence_adjusted_ev"] * BATCH_SIZE * multiplier, 4)


def _make_batch(n, pack, stopping_condition, rerun_trigger, rerun_reason, ev_note=None):
    return {
        "batch_number": n,
        "pack_name": pack["pack_name"],
        "expansion": pack["expansion"],
        "set_code": pack["set_code"],
        "packs_to_open": BATCH_SIZE,
        "adj_ev_per_pack": round(pack["confidence_adjusted_ev"], 6),
        "expected_value_this_batch": _batch_ev(pack),
        "expected_value_note": ev_note or (
            "First batch from this pool — estimate is at current collection state. "
            "Actual EV decreases as new cards are acquired."
        ),
        "missing_in_pool": pack["missing_in_pool"],
        "stopping_condition": stopping_condition,
        "rerun_trigger": rerun_trigger,
        "rerun_reason": rerun_reason,
    }


def build_scenarios(ev_data):
    packs = sorted(
        ev_data["packs"], key=lambda x: x["confidence_adjusted_ev"], reverse=True
    )
    deck_target_packs = sorted(
        [p for p in ev_data["packs"] if p.get("deck_target_ev", 0) > 0],
        key=lambda x: x["deck_target_ev"],
        reverse=True,
    )

    top1, top2, top3 = packs[0], packs[1], packs[2]
    top_deck = deck_target_packs[0] if deck_target_packs else None

    conservative = {
        "label": "conservative",
        "description": (
            "Open 1 batch (10 packs) from the highest adj-EV pack only. "
            "Stop immediately after. Verify slot rates in-app before any further resource commitment."
        ),
        "rationale": (
            "Rates are third_party_verified — confirmed across 4 independent sources but not from the "
            "official in-app Offering Rates screen. One batch at the top adj-EV pack captures maximum "
            "expected value per 10 packs while keeping total exposure minimal. "
            "In-app verification takes ~5 minutes and could confirm or revise rankings."
        ),
        "batches": [
            _make_batch(
                1, top1,
                stopping_condition=(
                    "STOP after this batch regardless of results. "
                    "Do not open further packs until slot rates are verified in PTCGP app."
                ),
                rerun_trigger=True,
                rerun_reason=(
                    "Mandatory post-conservative check: open PTCGP app → any pack → "
                    "Pack details → Offering Rates. If rates match model, upgrade to verified confidence."
                ),
            )
        ],
        "total_batches": 1,
        "total_packs": BATCH_SIZE,
        "rerun_checklist": [
            "After batch 1: open PTCGP app → any pack → Pack details → Offering Rates.",
            "Compare displayed percentages to slot_rates in data/reference/pull_probability_model.json.",
            "If they match: update confidence=verified in the model JSON, then re-run python3 scripts/build_pack_ev.py.",
            "Re-run python3 scripts/generate_hourglass_spending_plan.py to refresh this plan at verified confidence.",
        ],
    }

    moderate_batches = [
        _make_batch(
            1, top1,
            stopping_condition="Pause after this batch. Count new unique cards acquired from this pool.",
            rerun_trigger=False,
            rerun_reason=None,
        ),
        _make_batch(
            2, top1,
            stopping_condition=(
                "STOP after this batch. Re-run EV calculator — 20 packs opened from this pool."
            ),
            rerun_trigger=True,
            rerun_reason="20 packs from same pool. EV will have dropped. Re-run before continuing.",
            ev_note=(
                "EV per pack is lower than batch 1 — cards already acquired reduce the effective pool. "
                "Actual expected value for this batch is less than the static estimate."
            ),
        ),
        _make_batch(
            3, top2,
            stopping_condition=(
                "Stop after batch 3 and re-assess. If a deck target was pulled, re-run EV. "
                "If top pack changed after re-run, adjust batch 4 accordingly."
            ),
            rerun_trigger=True,
            rerun_reason=(
                "Switching packs after re-run. Re-run EV to confirm rankings after collection update."
            ),
        ),
    ]

    deck_target_note = None
    if top_deck:
        deck_target_note = (
            f"Deck-target variant: if completing a specific chase deck is the priority goal, "
            f"replace batch 3 with {top_deck['pack_name']} ({top_deck['expansion']}, "
            f"adj_ev={top_deck['confidence_adjusted_ev']:.4f}, "
            f"deck_target_ev={top_deck['deck_target_ev']:.4f}). "
            f"This pack has the highest deck_target_ev per 10 packs. "
            f"Note: overall adj_ev is lower than the top collection-expansion packs."
        )

    moderate = {
        "label": "moderate",
        "description": (
            "Open 3 batches: 2 from the top adj-EV pack, then 1 from the #2 adj-EV pack. "
            "Re-run the EV calculator after batch 2 (20 packs from same pool). "
            "Stop after each batch to check progress."
        ),
        "rationale": (
            "Accepts third_party_verified confidence risk (~15% adjustment applied to all EVs). "
            "Prioritizes collection expansion at the highest expected value. "
            "Re-run after 20 packs prevents over-committing to a pack whose EV has dropped "
            "as new cards were pulled. Switching to #2 after re-run hedges against pool depletion."
        ),
        "deck_target_variant": deck_target_note,
        "batches": moderate_batches,
        "total_batches": 3,
        "total_packs": BATCH_SIZE * 3,
        "rerun_checklist": [
            "After batch 2: re-run python3 scripts/build_pack_ev.py.",
            "Check if top1 pack is still the highest adj-EV. If not, update batch 3 target.",
            "After batch 3: re-run python3 scripts/generate_hourglass_spending_plan.py to update this plan.",
            "If a deck target is completed after any batch: re-run python3 scripts/build_pack_ev.py.",
        ],
    }

    agg_steps_spec = [
        (top1, "Pause after batch 1. Count new cards from this pool.", False, None,
         None),
        (top1,
         "STOP after batch 2 and re-run EV calculator. 20 packs opened from this pool.",
         True, "20 packs from same pool. Re-run EV before committing further.",
         "EV lower than batch 1 — cards already acquired reduce the pool."),
        (top2, "Pause after switching to pack #2. First batch from new pool.", False, None,
         None),
        (top3, "Pause after switching to pack #3. First batch from new pool.", False, None,
         None),
    ]
    if top_deck and top_deck["pack_name"] not in (top1["pack_name"], top2["pack_name"], top3["pack_name"]):
        agg_steps_spec.append((
            top_deck,
            (
                f"Deck-target batch: {top_deck['pack_name']} has highest deck_target_ev per pack. "
                "Stop immediately if chase deck card is pulled."
            ),
            True,
            "Final aggressive batch. Re-run EV for updated plan after deck-target batch.",
            f"deck_target_ev={top_deck['deck_target_ev']:.4f} — per-pack deck completion value.",
        ))

    agg_batches = []
    for i, (pack, stop_cond, rerun, rerun_reason, ev_note) in enumerate(agg_steps_spec, 1):
        agg_batches.append(
            _make_batch(i, pack, stop_cond, rerun, rerun_reason, ev_note)
        )

    aggressive = {
        "label": "aggressive",
        "description": (
            f"Open {len(agg_batches)} batches across the top 3 adj-EV packs "
            + (f"plus the top deck-target pack ({top_deck['pack_name']}). " if top_deck and top_deck["pack_name"] not in (top1["pack_name"], top2["pack_name"], top3["pack_name"]) else ". ")
            + "Re-run EV after every 20+ packs from the same pool. "
            "Accept third_party_verified confidence risk on all decisions."
        ),
        "rationale": (
            "Maximizes collection expansion rate by rotating across the top EV packs, avoiding "
            "diminishing returns on a single pool. A deck-target batch is included for chase deck progress. "
            "Higher resource commitment — verify in-app rates as early as possible to lock in confidence."
        ),
        "batches": agg_batches,
        "total_batches": len(agg_batches),
        "total_packs": len(agg_batches) * BATCH_SIZE,
        "rerun_checklist": [
            "After batch 2 (20 packs from top1 pool): re-run python3 scripts/build_pack_ev.py.",
            "After completing any deck target: re-run python3 scripts/build_pack_ev.py.",
            "After verifying in-app rates: upgrade confidence and re-run both EV scripts.",
            "After resolving 59 ambiguous collection entries: re-run for more accurate coverage.",
        ],
    }

    return [conservative, moderate, aggressive]


def write_json(scenarios, ev_data, model_data, collection_data):
    out = {
        "generated_at": GENERATED_AT,
        "generated_by": "scripts/generate_hourglass_spending_plan.py",
        "disclaimer": DISCLAIMER,
        "model_confidence": ev_data["meta"]["model_confidence"],
        "collection_total": collection_data.get("actual_total_quantity", len(collection_data.get("collection", []))),
        "collection_mutated": False,
        "batch_size": BATCH_SIZE,
        "model_version": model_data["meta"]["model_version"],
        "ev_source": str(PACK_EV_JSON.relative_to(BASE)),
        "scenarios": scenarios,
        "global_rerun_checklist": GLOBAL_RERUN_CHECKLIST,
    }
    OUT_JSON.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  Wrote: {OUT_JSON.relative_to(BASE)}")
    return out


def write_md(out_data):
    mc = out_data["model_confidence"]
    ev_label = mc.upper().replace("_", " ")

    lines = [
        "# Final Hourglass Spending Plan",
        "",
        f"Generated: {out_data['generated_at']}  ",
        f"Model confidence: **{ev_label}**  ",
        f"Collection total: {out_data['collection_total']} cards  ",
        f"Batch size: {BATCH_SIZE} packs per batch  ",
        "",
        "> **DISCLAIMER**",
        ">",
        f"> {DISCLAIMER}",
        "",
        "---",
        "",
        "## Summary Table",
        "",
        "| Scenario | Batches | Total packs | Top pack |",
        "|---|---|---|---|",
    ]

    for s in out_data["scenarios"]:
        top_pack = s["batches"][0]["pack_name"] if s["batches"] else "—"
        lines.append(
            f"| {s['label'].capitalize()} | {s['total_batches']} | {s['total_packs']} | {top_pack} |"
        )

    lines += ["", "---", ""]

    for s in out_data["scenarios"]:
        label = s["label"].capitalize()
        lines += [
            f"## {label} Scenario",
            "",
            f"**Description:** {s['description']}",
            "",
            f"**Rationale:** {s['rationale']}",
            "",
        ]

        if s.get("deck_target_variant"):
            lines += [
                f"**Deck-target variant:** {s['deck_target_variant']}",
                "",
            ]

        lines += [
            "### Batches",
            "",
            "| # | Pack | Set | Packs | Adj EV / pack | Est. batch value | Missing in pool | Stop? | Re-run? |",
            "|---|---|---|---|---|---|---|---|---|",
        ]

        for b in s["batches"]:
            rerun_flag = "✅" if b["rerun_trigger"] else "—"
            lines.append(
                f"| {b['batch_number']} "
                f"| {b['pack_name']} "
                f"| {b['set_code']} "
                f"| {b['packs_to_open']} "
                f"| {b['adj_ev_per_pack']:.4f} "
                f"| {b['expected_value_this_batch']:.2f} "
                f"| {b['missing_in_pool']} "
                f"| {b['stopping_condition'][:60]}{'…' if len(b['stopping_condition']) > 60 else ''} "
                f"| {rerun_flag} |"
            )

        lines += [""]

        for b in s["batches"]:
            lines += [
                f"#### Batch {b['batch_number']} — {b['pack_name']} ({b['set_code']})",
                "",
                f"- **Pack:** {b['pack_name']} ({b['expansion']})",
                f"- **Packs to open:** {b['packs_to_open']}",
                f"- **Adj EV per pack:** {b['adj_ev_per_pack']:.4f}",
                f"- **Estimated batch value:** {b['expected_value_this_batch']:.2f}  ",
                f"  _{b['expected_value_note']}_",
                f"- **Missing cards in pool:** {b['missing_in_pool']}",
                f"- **Stopping condition:** {b['stopping_condition']}",
            ]
            if b["rerun_trigger"]:
                lines.append(f"- **Re-run required:** {b['rerun_reason']}")
            lines.append("")

        lines += [
            "### Re-run checklist",
            "",
        ]
        for item in s["rerun_checklist"]:
            lines.append(f"- [ ] {item}")
        lines += ["", "---", ""]

    lines += [
        "## Global Re-run Checklist",
        "",
        "Run these at any time they apply, regardless of scenario:",
        "",
    ]
    for item in out_data["global_rerun_checklist"]:
        lines.append(f"- [ ] {item}")

    lines += [
        "",
        "---",
        "",
        "## Notes",
        "",
        "- **Expected value per batch** is a rough estimate at current collection state. "
        "Actual EV decreases as you acquire cards from the same pool.",
        "- **No hourglass cost is assumed.** Hourglasses are a resource you manage in-game; "
        "this plan specifies which packs and how many, not how many hourglasses to spend.",
        "- **adj_ev** = pack_total_ev × confidence_weight (0.85 for third_party_verified). "
        "At verified confidence the weight becomes 1.0 and all adj_ev values will increase.",
        "- **Deck-target EV** is included in adj_ev for packs containing chase deck cards. "
        "Crimson Blaze has the highest deck_target_ev per pack.",
        "- Re-run `build_pack_ev.py` after every significant collection change to keep rankings current.",
    ]

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  Wrote: {OUT_MD.relative_to(BASE)}")


def write_csv(out_data):
    rows = []
    for s in out_data["scenarios"]:
        for b in s["batches"]:
            rows.append({
                "scenario": s["label"],
                "batch_number": b["batch_number"],
                "pack_name": b["pack_name"],
                "expansion": b["expansion"],
                "set_code": b["set_code"],
                "packs_to_open": b["packs_to_open"],
                "adj_ev_per_pack": b["adj_ev_per_pack"],
                "expected_value_this_batch": b["expected_value_this_batch"],
                "missing_in_pool": b["missing_in_pool"],
                "rerun_trigger": b["rerun_trigger"],
                "stopping_condition": b["stopping_condition"],
            })

    fieldnames = [
        "scenario", "batch_number", "pack_name", "expansion", "set_code",
        "packs_to_open", "adj_ev_per_pack", "expected_value_this_batch",
        "missing_in_pool", "rerun_trigger", "stopping_condition",
    ]
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  Wrote: {OUT_CSV.relative_to(BASE)}")


def run_validate():
    print("Running validation checks...")
    errors = []
    warnings = []

    # Check 1: Output files exist
    for path in (OUT_JSON, OUT_MD, OUT_CSV):
        if not path.exists():
            errors.append(f"Missing output file: {path.relative_to(BASE)}")

    if errors:
        for e in errors:
            print(f"  ERROR: {e}")
        print(f"\nVALIDATION: FAIL ({len(errors)} error(s))")
        return False

    # Load output for checks
    plan = json.loads(OUT_JSON.read_text(encoding="utf-8"))
    md_text = OUT_MD.read_text(encoding="utf-8")
    with OUT_CSV.open(encoding="utf-8") as f:
        csv_rows = list(csv.DictReader(f))

    # Check 2: Disclaimer present
    if "NOT OFFICIAL" not in plan.get("disclaimer", ""):
        errors.append("Disclaimer missing 'NOT OFFICIAL' language in JSON")
    if "NOT OFFICIAL" not in md_text and "NOT_OFFICIAL" not in md_text:
        errors.append("Disclaimer missing 'NOT OFFICIAL' in Markdown output")

    # Check 3: 3 scenarios present
    scenarios = plan.get("scenarios", [])
    scenario_labels = [s["label"] for s in scenarios]
    for expected in ("conservative", "moderate", "aggressive"):
        if expected not in scenario_labels:
            errors.append(f"Missing scenario: {expected}")

    # Check 4: Stopping points present in every batch
    for s in scenarios:
        for b in s.get("batches", []):
            sc = b.get("stopping_condition", "")
            if not sc or len(sc) < 10:
                errors.append(
                    f"Batch {b['batch_number']} in scenario '{s['label']}' has no stopping condition"
                )

    # Check 5: Rerun checklist present in every scenario
    for s in scenarios:
        if not s.get("rerun_checklist"):
            errors.append(f"Scenario '{s['label']}' missing rerun_checklist")

    # Check 6: Global rerun checklist present
    if not plan.get("global_rerun_checklist"):
        errors.append("Missing global_rerun_checklist")

    # Check 7: No official verification claims (watch for positive-only claims, not "NOT officially verified")
    disclaimer_text = plan.get("disclaimer", "").lower()
    if "officially verified" in disclaimer_text and "not officially verified" not in disclaimer_text:
        errors.append("Disclaimer may incorrectly claim official verification — review disclaimer text")
    # "rates are third_party_verified" is OK; "rates are verified" (alone) is a potential false claim
    import re as _re
    if _re.search(r"rates are verified(?!\s*\()(?!\s*\|)(?!\s*confidence)", md_text.lower()):
        if "rates are third_party_verified" not in md_text.lower():
            warnings.append("MD may contain 'rates are verified' claim without third_party qualifier — review")

    model_conf = plan.get("model_confidence", "")
    if model_conf == "verified":
        warnings.append(
            "model_confidence=verified — this plan was generated after in-app verification. "
            "Confirm this is intentional."
        )
    if model_conf not in (
        "inferred", "third_party_verified", "verified",
        "user_in_app_verified", "in_app_verified_partial",
        "third_party_verified_with_in_app_anchor", "pending_verification",
        "bulbapedia_branch_verified", "bulbapedia_verified",
        "user_in_app_verified_plus_bulbapedia",
    ):
        errors.append(f"Unexpected model_confidence: {model_conf}")

    # Check 8: Top pack in this plan matches pack_ev.json top pack
    if PACK_EV_JSON.exists():
        ev = json.loads(PACK_EV_JSON.read_text(encoding="utf-8"))
        top_ev_pack = sorted(
            ev["packs"], key=lambda x: x["confidence_adjusted_ev"], reverse=True
        )[0]["pack_name"]
        conservative = next((s for s in scenarios if s["label"] == "conservative"), None)
        if conservative and conservative["batches"]:
            plan_top = conservative["batches"][0]["pack_name"]
            if plan_top != top_ev_pack:
                errors.append(
                    f"Conservative batch 1 pack ({plan_top}) does not match "
                    f"top adj-EV pack in pack_ev.json ({top_ev_pack})"
                )

    # Check 9: collection.json unchanged (not mutated)
    if not plan.get("collection_mutated") is False:
        if plan.get("collection_mutated") is True:
            errors.append("Plan reports collection_mutated=True — collection.json should never be mutated")

    # Check 10: CSV rows match scenario batch counts
    scenario_batch_counts = {s["label"]: s["total_batches"] for s in scenarios}
    csv_counts: dict = {}
    for row in csv_rows:
        csv_counts[row["scenario"]] = csv_counts.get(row["scenario"], 0) + 1
    for label, expected_count in scenario_batch_counts.items():
        actual = csv_counts.get(label, 0)
        if actual != expected_count:
            errors.append(
                f"CSV batch count mismatch for '{label}': expected {expected_count}, got {actual}"
            )

    # Check 11: collection_normalized.json exists (load check)
    if not COLLECTION_NORMALIZED_JSON.exists():
        errors.append(f"Required file missing: {COLLECTION_NORMALIZED_JSON.relative_to(BASE)}")

    # Check 12: batch_size is 10
    if plan.get("batch_size") != 10:
        errors.append(f"batch_size should be 10, got: {plan.get('batch_size')}")

    # Report
    for e in errors:
        print(f"  ERROR: {e}")
    for w in warnings:
        print(f"  WARN:  {w}")

    n_checks = 12
    if errors:
        print(f"\nVALIDATION: FAIL ({len(errors)} error(s), {len(warnings)} warning(s)) — {n_checks} checks run")
        return False
    print(
        f"  INFO:  {len(scenarios)} scenarios, "
        f"{sum(s['total_batches'] for s in scenarios)} total batches, "
        f"model_confidence={model_conf}"
    )
    print(f"\nVALIDATION: PASS (0 errors, {len(warnings)} warning(s)) — {n_checks} checks run")
    return True


def main():
    parser = argparse.ArgumentParser(description="Generate hourglass spending plan")
    parser.add_argument("--validate", action="store_true", help="Validate outputs only")
    args = parser.parse_args()

    if args.validate:
        ok = run_validate()
        sys.exit(0 if ok else 1)

    print("Loading data...")
    ev_data, recs_data, model_data, collection_data = load_data()

    mc = ev_data["meta"]["model_confidence"]
    print(f"  Model confidence: {mc}")
    print(f"  Packs scored: {len(ev_data['packs'])}")
    coll_total = collection_data.get("actual_total_quantity", "?")
    print(f"  Collection total: {coll_total}")

    if mc not in (
        "inferred", "third_party_verified", "verified",
        "user_in_app_verified", "in_app_verified_partial",
        "third_party_verified_with_in_app_anchor", "pending_verification",
        "bulbapedia_branch_verified", "bulbapedia_verified",
        "user_in_app_verified_plus_bulbapedia",
    ):
        print(f"ERROR: Unexpected model_confidence: {mc}", file=sys.stderr)
        sys.exit(1)

    print("\nBuilding scenarios...")
    scenarios = build_scenarios(ev_data)
    for s in scenarios:
        print(f"  {s['label']}: {s['total_batches']} batches, {s['total_packs']} packs")

    print("\nWriting outputs...")
    out_data = write_json(scenarios, ev_data, model_data, collection_data)
    write_md(out_data)
    write_csv(out_data)

    print("\nRunning validation...")
    ok = run_validate()
    if not ok:
        sys.exit(1)

    print("\nDone.")
    print(f"  Top pack (all scenarios): {scenarios[0]['batches'][0]['pack_name']}")
    print(f"  Model confidence: {mc}")
    if mc != "verified":
        print(
            "  NOTE: Rates are not officially in-app verified. "
            "Open PTCGP app → any pack → Pack details → Offering Rates to verify."
        )


if __name__ == "__main__":
    main()
