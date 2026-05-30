#!/usr/bin/env python3
"""
generate_hourglass_spending_plan.py

Generates a single optimal hourglass spending plan from EV data.
Uses unified_score and ev_diminishing_returns_ratio to sequence batches.
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
from datetime import date
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
PACK_EV_JSON = BASE / "data/current/pack_ev.json"
RECOMMENDATIONS_JSON = BASE / "data/current/inferred_pack_recommendations.json"
PULL_MODEL_JSON = BASE / "data/reference/pull_probability_model.json"
COLLECTION_NORMALIZED_JSON = BASE / "data/current/collection_normalized.json"

OUT_JSON = BASE / "data/current/final_hourglass_spending_plan.json"
OUT_MD = BASE / "review/final_hourglass_spending_plan.md"
OUT_CSV = BASE / "data/exports/final_hourglass_spending_plan.csv"

BATCH_SIZE = 10
HOURGLASS_PER_PACK = 12
NEAR_COMPLETE_THRESHOLD = 0.85  # DR ratio below this → flag near-complete
GENERATED_AT = date.today().isoformat()

DISCLAIMER = (
    "NOT OFFICIAL: Pull rates are PZ_VERIFIED — per-card drop chances sourced directly from "
    "Pokemon Zone (not the official PTCGP in-app Offering Rates screen). "
    "EV calculations reflect actual pull probabilities with no confidence haircut applied. "
    "Rankings are suitable for planning. Re-run EV after every 20+ packs to account for "
    "collection changes."
)

VALID_CONFIDENCE_LEVELS = {
    "inferred", "third_party_verified", "verified",
    "user_in_app_verified", "in_app_verified_partial",
    "third_party_verified_with_in_app_anchor", "pending_verification",
    "bulbapedia_branch_verified", "bulbapedia_verified",
    "user_in_app_verified_plus_bulbapedia", "pz_verified",
}


def load_data():
    ev = json.loads(PACK_EV_JSON.read_text(encoding="utf-8"))
    try:
        recs = json.loads(RECOMMENDATIONS_JSON.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        recs = {}
    model = json.loads(PULL_MODEL_JSON.read_text(encoding="utf-8"))
    collection = json.loads(COLLECTION_NORMALIZED_JSON.read_text(encoding="utf-8"))
    return ev, recs, model, collection


def _make_batch(n, pack, rerun_after, notes):
    dr = pack.get("ev_diminishing_returns_ratio", 1.0)
    near_complete = dr < NEAR_COMPLETE_THRESHOLD
    return {
        "batch_number": n,
        "pack_name": pack["pack_name"],
        "expansion": pack["expansion"],
        "set_code": pack["set_code"],
        "packs_to_open": BATCH_SIZE,
        "hourglass_cost": BATCH_SIZE * HOURGLASS_PER_PACK,
        "unified_score": round(pack.get("unified_score", 0.0), 6),
        "new_card_ev_10x": round(pack.get("new_card_ev_10x", 0.0), 6),
        "cost_per_unique_card_10x": round(pack.get("cost_per_unique_card_10x", 0.0), 4),
        "ev_diminishing_returns_ratio": round(dr, 4),
        "missing_in_pool": pack["missing_in_pool"],
        "near_complete": near_complete,
        "rerun_after": rerun_after,
        "notes": notes,
    }


def build_optimal_plan(ev_data, recs_data=None, include_limited: bool = False):
    """
    Build a single optimal spending plan using unified_score.

    Batch 1: top pack by unified_score; always trigger rerun after.
    Batch 2: continue top pack if DR ratio >= threshold; switch to #2 if near-complete.
    Batches 3+: rotate through top 3, flagging near-complete packs.
    Stopping condition: when cost_per_unique_card_10x > 2× batch-1 cost, stop.
    """
    packs = sorted(
        (p for p in ev_data["packs"] if include_limited or p.get("purchasable", True)),
        key=lambda x: x.get("unified_score", 0.0), reverse=True,
    )
    if len(packs) < 3:
        raise ValueError(f"Need at least 3 scored packs, got {len(packs)}")

    top1, top2, top3 = packs[0], packs[1], packs[2]
    base_cost = top1.get("cost_per_unique_card_10x", 0.0)
    cost_ceiling = base_cost * 2.0 if base_cost > 0 else float("inf")

    dr1 = top1.get("ev_diminishing_returns_ratio", 1.0)
    near1 = dr1 < NEAR_COMPLETE_THRESHOLD

    # Batch 1: always top pack
    b1_notes = "Open first batch from the top unified-score pack."
    if near1:
        b1_notes += (
            f" WARNING: DR ratio={dr1:.3f} < {NEAR_COMPLETE_THRESHOLD} — "
            "this pool is near-complete; switch to #2 after this batch."
        )
    b1 = _make_batch(1, top1, rerun_after=True, notes=b1_notes)

    # Batch 2: switch if near-complete, else continue
    b2_pack = top2 if near1 else top1
    b2_notes = (
        f"Switched to #{2 if near1 else 'same'} pack (near-complete flag on batch 1)."
        if near1
        else "Continue top pack for batch 2."
    )
    b2 = _make_batch(2, b2_pack, rerun_after=True, notes=b2_notes)

    # Batch 3: rotate to a pack not already used in batches 1 and 2.
    # Exclude all packs opened in prior batches; fall back to a pack ≠ batch-2 if needed.
    used_b1_b2 = {top1["pack_name"], b2_pack["pack_name"]}
    b3_candidates = [p for p in [top1, top2, top3] if p["pack_name"] not in used_b1_b2]
    if not b3_candidates:
        b3_candidates = [p for p in [top1, top2, top3] if p["pack_name"] != b2_pack["pack_name"]]
    b3_pack = next(
        (p for p in b3_candidates if p.get("ev_diminishing_returns_ratio", 1.0) >= NEAR_COMPLETE_THRESHOLD),
        b3_candidates[0] if b3_candidates else top3,
    )
    b3_cost = b3_pack.get("cost_per_unique_card_10x", 0.0)
    if cost_ceiling < float("inf") and b3_cost > cost_ceiling:
        b3_stop = (
            f"STOP: cost_per_unique_card_10x={b3_cost:.1f}⧗ exceeds 2× batch-1 baseline "
            f"({cost_ceiling:.1f}⧗). Re-run EV before committing further."
        )
    else:
        b3_stop = "Re-run EV after this batch; rotate to highest unified-score pack for batch 4."
    b3 = _make_batch(3, b3_pack, rerun_after=True, notes=b3_stop)

    batches = [b1, b2, b3]
    total_hourglasses = sum(b["hourglass_cost"] for b in batches)

    stopping_condition = (
        f"Stop any batch when cost_per_unique_card_10x exceeds {cost_ceiling:.1f}⧗ "
        f"(2× batch-1 baseline of {base_cost:.1f}⧗). Re-run EV before committing further."
        if cost_ceiling < float("inf")
        else "Re-run EV after each batch to reassess. No cost ceiling computed (batch-1 EV is zero)."
    )

    chase_deck_packs = (recs_data or {}).get("chase_deck_packs", {})

    return {
        "label": "optimal",
        "description": (
            f"3-batch plan rotating through top unified-score packs. "
            f"Batch 1: {top1['pack_name']}. "
            f"{'Batch 2: switch to ' + top2['pack_name'] + ' (near-complete)' if near1 else 'Batch 2: continue ' + top1['pack_name']}. "
            f"Batch 3: {b3_pack['pack_name']}. "
            f"Always rerun EV after each batch."
        ),
        "batches": batches,
        "total_batches": len(batches),
        "total_hourglasses": total_hourglasses,
        "rerun_after_batch_n": [b["batch_number"] for b in batches if b["rerun_after"]],
        "stopping_condition": stopping_condition,
        "near_complete_threshold": NEAR_COMPLETE_THRESHOLD,
        "cost_ceiling_per_unique_card": round(cost_ceiling, 2) if cost_ceiling < float("inf") else None,
        "chase_deck_packs": chase_deck_packs,
        "top_pack_unified_score": round(top1.get("unified_score", 0.0), 4),
        "top_pack_name": top1["pack_name"],
        "include_limited_packs": include_limited,
    }


def write_json(spending_plan, ev_data, model_data, collection_data):
    out = {
        "generated_at": GENERATED_AT,
        "generated_by": "scripts/generate_hourglass_spending_plan.py",
        "disclaimer": DISCLAIMER,
        "model_confidence": ev_data["meta"]["model_confidence"],
        "collection_total": collection_data.get("actual_total_quantity", len(collection_data.get("collection", []))),
        "collection_mutated": False,
        "batch_size": BATCH_SIZE,
        "hourglass_per_pack": HOURGLASS_PER_PACK,
        "model_version": model_data["meta"]["model_version"],
        "ev_source": str(PACK_EV_JSON.relative_to(BASE)),
        "spending_plan": spending_plan,
    }
    OUT_JSON.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  Wrote: {OUT_JSON.relative_to(BASE)}")
    return out


def write_md(out_data):
    mc = out_data["model_confidence"]
    plan = out_data["spending_plan"]
    batches = plan["batches"]

    lines = [
        "# Final Hourglass Spending Plan",
        "",
        f"Generated: {out_data['generated_at']}  ",
        f"Model confidence: **{mc.upper().replace('_', ' ')}**  ",
        f"Collection total: {out_data['collection_total']} cards  ",
        f"Batch size: {BATCH_SIZE} packs ({BATCH_SIZE * HOURGLASS_PER_PACK} ⧗ per batch)  ",
        "",
        "> **DISCLAIMER**",
        ">",
        f"> {DISCLAIMER}",
        "",
        "---",
        "",
        "## Optimal Spending Plan",
        "",
        f"**{plan['description']}**",
        "",
        f"- Total batches: {plan['total_batches']}",
        f"- Total hourglasses: {plan['total_hourglasses']} ⧗",
        f"- Rerun EV after batch(es): {plan['rerun_after_batch_n']}",
        f"- Stopping condition: {plan['stopping_condition']}",
        "",
        "| # | Pack | Set | ⧗ Cost | Unified | 10x EV | ⧗/EV | DR Ratio | Missing | Near-Complete | Rerun? |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]

    for b in batches:
        nc_flag = "YES" if b["near_complete"] else "—"
        rerun_flag = "YES" if b["rerun_after"] else "—"
        lines.append(
            f"| {b['batch_number']} "
            f"| **{b['pack_name']}** "
            f"| {b['set_code']} "
            f"| {b['hourglass_cost']} ⧗ "
            f"| {b['unified_score']:.4f} "
            f"| {b['new_card_ev_10x']:.4f} "
            f"| {b['cost_per_unique_card_10x']:.1f} "
            f"| {b['ev_diminishing_returns_ratio']:.3f} "
            f"| {b['missing_in_pool']} "
            f"| {nc_flag} "
            f"| {rerun_flag} |"
        )

    lines += ["", "---", "", "### Batch Details", ""]

    for b in batches:
        lines += [
            f"#### Batch {b['batch_number']} — {b['pack_name']} ({b['set_code']})",
            "",
            f"- **Pack:** {b['pack_name']} ({b['expansion']})",
            f"- **Hourglasses:** {b['hourglass_cost']} ⧗ ({b['packs_to_open']} packs × {HOURGLASS_PER_PACK} ⧗)",
            f"- **Unified score:** {b['unified_score']:.4f}",
            f"- **New-card EV (10x):** {b['new_card_ev_10x']:.4f}",
            f"- **Cost per EV unit (⧗/EV):** {b['cost_per_unique_card_10x']:.1f} ⧗",
            f"- **DR ratio:** {b['ev_diminishing_returns_ratio']:.3f}"
            + (" ← near-complete" if b["near_complete"] else ""),
            f"- **Missing in pool:** {b['missing_in_pool']}",
            f"- **Notes:** {b['notes']}",
            f"- **Rerun after:** {'YES — re-run build_pack_ev.py before next batch' if b['rerun_after'] else 'No'}",
            "",
        ]

    if plan.get("chase_deck_packs"):
        lines += [
            "---",
            "",
            "## Chase Deck Pack Guide",
            "",
            "| Chase Deck | Missing Card | Short By | Best Pack | Notes |",
            "|---|---|---|---|---|",
        ]
        for deck_name, info in plan["chase_deck_packs"].items():
            card = info.get("card_needed", "?")
            short_by = info.get("short_by", 1)
            best_pack = info.get("best_pack") or "**UNKNOWN**"
            note = info.get("note", "")
            lines.append(f"| {deck_name} | {card} | {short_by} | {best_pack} | {note} |")
        lines.append("")

    lines += [
        "---",
        "",
        "## Notes",
        "",
        f"- **Unified score** = `new_card_ev_10x×1.0 + copy_ev×0.2 + ex_card_ev×0.5 + deck_target_ev×1.5` × confidence_weight. new_card_ev_10x is rarity-weighted; EX and deck bonuses are added separately.",
        f"- **DR ratio** = `new_card_ev_10x / (new_card_ev_1x × 10)`. Below {NEAR_COMPLETE_THRESHOLD}: pool near-complete, diminishing returns significant.",
        f"- **⧗/EV** = `{BATCH_SIZE * HOURGLASS_PER_PACK} ⧗ / new_card_ev_10x`. Lower is better. (new_card_ev_10x is rarity-weighted, so this is cost per rarity-weighted value unit, not per raw card count)",
        "- Re-run `build_pack_ev.py` after every significant collection change to keep rankings current.",
        "",
    ]

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  Wrote: {OUT_MD.relative_to(BASE)}")


def write_csv(out_data):
    plan = out_data["spending_plan"]
    fieldnames = [
        "batch_number", "pack_name", "expansion", "set_code",
        "packs_to_open", "hourglass_cost",
        "unified_score", "new_card_ev_10x", "cost_per_unique_card_10x",
        "ev_diminishing_returns_ratio", "missing_in_pool",
        "near_complete", "rerun_after", "notes",
    ]
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(plan["batches"])
    print(f"  Wrote: {OUT_CSV.relative_to(BASE)}")


def run_validate(include_limited_fallback: bool = False):
    """Validate spending plan outputs.

    include_limited_fallback: used only when the stored plan lacks the
    include_limited_packs field (i.e. plans generated before that field
    was added). For all modern plans the stored value takes precedence.
    """
    print("Running validation checks...")
    errors = []

    if not COLLECTION_NORMALIZED_JSON.exists():
        errors.append(f"Required input missing: {COLLECTION_NORMALIZED_JSON.relative_to(BASE)}")

    for path in (OUT_JSON, OUT_MD):
        if not path.exists():
            errors.append(f"Missing output file: {path.relative_to(BASE)}")

    if errors:
        for e in errors:
            print(f"  ERROR: {e}")
        print(f"\nVALIDATION: FAIL ({len(errors)} error(s))")
        return False

    plan_doc = json.loads(OUT_JSON.read_text(encoding="utf-8"))

    # spending_plan key present (not scenarios)
    if "spending_plan" not in plan_doc:
        errors.append("Missing 'spending_plan' key in JSON output")
    if "scenarios" in plan_doc:
        errors.append("Stale 'scenarios' key found — should be 'spending_plan'")

    plan = plan_doc.get("spending_plan", {})

    # batches non-empty
    batches = plan.get("batches", [])
    if not batches:
        errors.append("spending_plan.batches is empty")
    else:
        print(f"  PASS  spending_plan.batches has {len(batches)} entries")

    # each batch has required fields
    required_batch_fields = [
        "batch_number", "pack_name", "hourglass_cost",
        "unified_score", "new_card_ev_10x", "rerun_after", "notes",
    ]
    for b in batches:
        for f in required_batch_fields:
            if f not in b:
                errors.append(f"Batch {b.get('batch_number', '?')} missing field '{f}'")

    # rerun_after_batch_n present and non-empty
    rerun_list = plan.get("rerun_after_batch_n", [])
    if not rerun_list:
        errors.append("spending_plan.rerun_after_batch_n is empty — at least one rerun point required")
    else:
        print(f"  PASS  rerun_after_batch_n={rerun_list}")

    # stopping_condition present
    if not plan.get("stopping_condition"):
        errors.append("spending_plan.stopping_condition missing")
    else:
        print("  PASS  stopping_condition present")

    # collection_mutated=False
    if plan_doc.get("collection_mutated") is not False:
        errors.append("collection_mutated must be False")
    else:
        print("  PASS  collection_mutated=False")

    # model_confidence valid
    mc = plan_doc.get("model_confidence", "")
    if mc not in VALID_CONFIDENCE_LEVELS:
        errors.append(f"Unexpected model_confidence: {mc}")
    else:
        print(f"  PASS  model_confidence={mc}")

    # batch_size=10
    if plan_doc.get("batch_size") != 10:
        errors.append(f"batch_size should be 10, got: {plan_doc.get('batch_size')}")

    # disclaimer present
    if "NOT OFFICIAL" not in plan_doc.get("disclaimer", ""):
        errors.append("Disclaimer missing 'NOT OFFICIAL' language")

    # top pack matches pack_ev.json top unified pack.
    # Use the include_limited_packs flag stored in the plan itself so --validate
    # always applies the same filter that was used during generation.
    if PACK_EV_JSON.exists():
        ev = json.loads(PACK_EV_JSON.read_text(encoding="utf-8"))
        stored_flag = plan.get("include_limited_packs", include_limited_fallback)
        eligible = [p for p in ev["packs"] if stored_flag or p.get("purchasable", True)]
        if not eligible:
            errors.append("No eligible packs in pack_ev.json after purchasable filter")
        else:
            top_ev_pack = sorted(
                eligible, key=lambda x: x.get("unified_score", 0.0), reverse=True
            )[0]["pack_name"]
            plan_top = batches[0]["pack_name"] if batches else None
            if plan_top and plan_top != top_ev_pack:
                errors.append(
                    f"Batch 1 pack ({plan_top}) does not match "
                    f"top unified-score pack in pack_ev.json ({top_ev_pack})"
                )
            elif plan_top:
                print(f"  PASS  batch 1 pack matches top unified-score pack ({top_ev_pack})")

    n_checks = 10
    if errors:
        for e in errors:
            print(f"  ERROR: {e}")
        print(f"\nVALIDATION: FAIL ({len(errors)} error(s)) — {n_checks} checks run")
        return False

    print(f"\nVALIDATION: PASS (0 errors) — {n_checks} checks run")
    return True


def main():
    parser = argparse.ArgumentParser(description="Generate hourglass spending plan")
    parser.add_argument("--validate", action="store_true", help="Validate outputs only")
    parser.add_argument("--include-limited", action="store_true",
                        help="Include limited-time packs not currently purchasable (e.g. Deluxe Pack: ex)")
    args = parser.parse_args()

    if args.validate:
        ok = run_validate(include_limited_fallback=args.include_limited)
        sys.exit(0 if ok else 1)

    for req in (PACK_EV_JSON, PULL_MODEL_JSON, COLLECTION_NORMALIZED_JSON):
        if not req.exists():
            print(f"ERROR: required input not found: {req}", file=sys.stderr)
            sys.exit(1)

    print("Loading data...")
    ev_data, recs_data, model_data, collection_data = load_data()

    mc = ev_data["meta"]["model_confidence"]
    print(f"  Model confidence: {mc}")
    print(f"  Packs scored: {len(ev_data['packs'])}")
    coll_total = collection_data.get("actual_total_quantity", "?")
    print(f"  Collection total: {coll_total}")

    if mc not in VALID_CONFIDENCE_LEVELS:
        print(f"ERROR: Unexpected model_confidence: {mc}", file=sys.stderr)
        sys.exit(1)

    print("\nBuilding optimal plan...")
    try:
        spending_plan = build_optimal_plan(ev_data, recs_data, include_limited=args.include_limited)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"  Top pack: {spending_plan['top_pack_name']} (unified={spending_plan['top_pack_unified_score']:.4f})")
    print(f"  Batches: {spending_plan['total_batches']}, total ⧗: {spending_plan['total_hourglasses']}")

    print("\nWriting outputs...")
    out_data = write_json(spending_plan, ev_data, model_data, collection_data)
    write_md(out_data)
    write_csv(out_data)

    print("\nRunning validation...")
    ok = run_validate(include_limited_fallback=args.include_limited)
    if not ok:
        sys.exit(1)

    print("\nDone.")


if __name__ == "__main__":
    main()
