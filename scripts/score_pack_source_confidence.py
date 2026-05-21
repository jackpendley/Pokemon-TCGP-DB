#!/usr/bin/env python3
"""
Score pack-source confidence for all 224 current collection entries.

Uses match status from current_collection_pack_coverage.json as the primary
signal, adjusted by pack_sources metadata agreement and screenshot alignment.

Does NOT mutate collection.json. Does NOT apply any pack assignments.
Does NOT make pack-opening recommendations.

Inputs:
    data/current/collection_normalized.json
    data/reference/pack_sources.json
    data/current/current_collection_pack_coverage.json
    data/current/screenshot_collection_alignment.json

Outputs:
    data/current/pack_source_confidence_scores.json
    data/exports/pack_source_confidence_scores.csv
    review/pack_source_confidence_scores.md

Usage:
    python3 scripts/score_pack_source_confidence.py
    python3 scripts/score_pack_source_confidence.py --validate
"""

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COLLECTION_JSON = ROOT / "data" / "current" / "collection_normalized.json"
PACK_SOURCES_JSON = ROOT / "data" / "reference" / "pack_sources.json"
COVERAGE_JSON = ROOT / "data" / "current" / "current_collection_pack_coverage.json"
ALIGNMENT_JSON = ROOT / "data" / "current" / "screenshot_collection_alignment.json"
OUT_JSON = ROOT / "data" / "current" / "pack_source_confidence_scores.json"
OUT_CSV = ROOT / "data" / "exports" / "pack_source_confidence_scores.csv"
OUT_MD = ROOT / "review" / "pack_source_confidence_scores.md"

# ---------------------------------------------------------------------------
# Scoring model constants
# ---------------------------------------------------------------------------

BASE_SCORES = {
    "exact_match": 0.95,
    "exact_name_unique": 0.95,
    "unanimous_pack": 0.85,
    "unanimous_expansion": 0.75,
    "ambiguous_same_set": 0.65,
    "ambiguous_cross_set": 0.50,
    "ambiguous": 0.50,
    "no_match_known_gap": 0.10,
    "no_match": 0.10,
}

# Alignment adjustments (screenshot order-only evidence)
ALN_BONUS = 0.02          # alignment record exists and confidence >= 0.60
ALN_NO_RECORD_PENALTY = 0.0   # screenshot pipeline removed — no penalty when no alignment file

# Metadata agreement adjustments (pack_sources vs collection entry)
META_IS_EX_AGREE = 0.02
META_IS_EX_CONFLICT = -0.05
META_TYPE_AGREE = 0.02
META_TYPE_CONFLICT = -0.03
# Stage not available in pack_sources — never applied

# Thresholds
TIER_AUTO_ACCEPT = 0.95
TIER_SECONDARY = 0.80
TIER_LOW = 0.50
TIER_UNRESOLVED_MAX = 0.50   # < 0.50 → unresolved

# Statuses where best_candidate must be None
NO_CANDIDATE_STATUSES = {"no_match", "no_match_known_gap"}

# Statuses where we pick a representative candidate
PICK_REPRESENTATIVE_STATUSES = {"exact_match", "exact_name_unique",
                                 "unanimous_pack", "unanimous_expansion"}

VALID_TIERS = {"auto_accept", "secondary_evidence", "low_confidence", "unresolved"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def confidence_tier(score: float) -> str:
    if score >= TIER_AUTO_ACCEPT:
        return "auto_accept"
    if score >= TIER_SECONDARY:
        return "secondary_evidence"
    if score >= TIER_LOW:
        return "low_confidence"
    return "unresolved"


def next_action(tier: str, match_status: str) -> str:
    if tier == "auto_accept":
        return "no_action_needed"
    if tier == "secondary_evidence":
        return "needs_secondary_evidence"
    if tier == "low_confidence":
        if match_status in ("ambiguous_cross_set", "ambiguous_same_set", "ambiguous"):
            return "needs_candidate_disambiguation"
        return "needs_confidence_improvement"
    # unresolved
    if match_status == "no_match_known_gap":
        return "not_in_limitless_db_skip_or_manual"
    return "needs_reference_expansion_or_manual_fallback"


def build_ps_index(records: list) -> dict:
    """Build pack_sources index keyed by (set_code, card_number)."""
    idx = {}
    for r in records:
        key = (r.get("set_code"), r.get("card_number"))
        if key[0] and key[1] is not None:
            idx[key] = r
    return idx


def build_aln_index(alignment_records: list) -> dict:
    """Build alignment index keyed by entry_id."""
    return {r["entry_id"]: r for r in alignment_records if r.get("entry_id")}


def pick_best_candidate(coverage_entry: dict) -> dict | None:
    """Return the best candidate dict or None based on match status."""
    status = coverage_entry["match_status"]
    candidates = coverage_entry.get("candidates", [])
    if status in NO_CANDIDATE_STATUSES or not candidates:
        return None
    if status in PICK_REPRESENTATIVE_STATUSES:
        return candidates[0]
    # ambiguous statuses — no authoritative pick
    return None


def meta_adjustments(collection_entry: dict, best_candidate: dict | None,
                     ps_index: dict) -> tuple:
    """Return (total_adjustment, adjustments_list). Looks up ps_record for metadata."""
    if best_candidate is None:
        return 0.0, []

    ps_rec = ps_index.get((best_candidate.get("set_code"),
                            best_candidate.get("card_number")))
    if ps_rec is None:
        return 0.0, []

    adjustments = []
    total = 0.0

    # is_ex
    col_is_ex = collection_entry.get("is_ex", False)
    ps_is_ex = ps_rec.get("is_ex")
    if ps_is_ex is not None:
        if bool(col_is_ex) == bool(ps_is_ex):
            total += META_IS_EX_AGREE
            adjustments.append(f"is_ex_agree:{col_is_ex}(+{META_IS_EX_AGREE})")
        else:
            total += META_IS_EX_CONFLICT
            adjustments.append(
                f"is_ex_conflict:col={col_is_ex},ps={ps_is_ex}({META_IS_EX_CONFLICT})"
            )

    # pokemon_type
    col_type = (collection_entry.get("type") or "").strip().lower()
    ps_type = (ps_rec.get("pokemon_type") or "").strip().lower()
    if col_type and ps_type:
        if col_type == ps_type:
            total += META_TYPE_AGREE
            adjustments.append(f"type_agree:{col_type}(+{META_TYPE_AGREE})")
        else:
            total += META_TYPE_CONFLICT
            adjustments.append(
                f"type_conflict:col={col_type},ps={ps_type}({META_TYPE_CONFLICT})"
            )

    # Stage not available in pack_sources — skip

    return round(total, 4), adjustments


def alignment_adjustment(entry_id: str, aln_index: dict) -> tuple:
    """Return (adjustment, evidence_note)."""
    aln_rec = aln_index.get(entry_id)
    if aln_rec is None:
        return ALN_NO_RECORD_PENALTY, f"no_alignment_record({ALN_NO_RECORD_PENALTY})"
    aln_score = aln_rec.get("confidence_score", 0.0)
    if aln_score >= 0.60:
        return ALN_BONUS, f"alignment_confidence={aln_score}(+{ALN_BONUS})"
    return 0.0, f"alignment_confidence={aln_score}_below_threshold(+0)"


def build_blockers(collection_entry: dict, match_status: str, tier: str,
                   meta_adjs: list) -> list:
    blockers = []
    if match_status == "no_match":
        blockers.append("card_not_in_pack_sources_database")
    elif match_status == "no_match_known_gap":
        blockers.append("common_trainer_not_indexed_in_limitless_db")
    elif match_status in ("ambiguous_cross_set", "ambiguous"):
        blockers.append("card_appears_in_multiple_expansions_cannot_determine_which")
    elif match_status == "ambiguous_same_set":
        blockers.append("card_appears_in_multiple_packs_within_same_expansion")
    if any("is_ex_conflict" in a for a in meta_adjs):
        blockers.append("is_ex_mismatch_between_collection_and_pack_sources")
    if any("type_conflict" in a for a in meta_adjs):
        blockers.append("pokemon_type_mismatch_between_collection_and_pack_sources")
    return blockers


def score_entry(collection_entry: dict, coverage_entry: dict,
                ps_index: dict, aln_index: dict) -> dict:
    """Compute full confidence score record for one collection entry."""
    entry_id = collection_entry["entry_id"]
    match_status = coverage_entry["match_status"]
    candidates = coverage_entry.get("candidates", [])

    base = BASE_SCORES.get(match_status, 0.10)

    best_cand = pick_best_candidate(coverage_entry)

    meta_adj_total, meta_adjs = meta_adjustments(collection_entry, best_cand, ps_index)

    aln_adj, aln_note = alignment_adjustment(entry_id, aln_index)

    # For ambiguous statuses: clamp so alignment alone can't push above 0.80
    if match_status in ("ambiguous_cross_set", "ambiguous_same_set", "ambiguous"):
        raw = base + meta_adj_total + aln_adj
        final = min(raw, 0.79)
    else:
        final = base + meta_adj_total + aln_adj

    final = round(max(0.0, min(1.0, final)), 4)
    tier = confidence_tier(final)
    action = next_action(tier, match_status)
    blockers = build_blockers(collection_entry, match_status, tier, meta_adjs)

    adjustments = []
    if meta_adjs:
        adjustments.extend(meta_adjs)
    adjustments.append(aln_note)

    evidence = [f"match_status:{match_status}", f"base_score:{base}"]
    evidence.extend(adjustments)
    evidence.append(f"final_score:{final}")

    return {
        "entry_id": entry_id,
        "name": collection_entry["name"],
        "count": collection_entry["count"],
        "card_type": collection_entry.get("card_type", ""),
        "type": collection_entry.get("type", ""),
        "stage": collection_entry.get("stage_label", ""),
        "hp": collection_entry.get("hp"),
        "is_ex": collection_entry.get("is_ex", False),
        "match_status": match_status,
        "base_score": base,
        "adjustments": adjustments,
        "final_score": final,
        "confidence_tier": tier,
        "best_candidate": best_cand,
        "candidate_count": len(candidates),
        "candidates": candidates,
        "alignment_evidence": {
            "entry_id": entry_id,
            "alignment_confidence": aln_index.get(entry_id, {}).get("confidence_score"),
            "adjustment_applied": aln_adj,
            "note": aln_note,
        },
        "evidence": evidence,
        "blockers": blockers,
        "next_action": action,
    }


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------

def write_json(scored: list) -> dict:
    tiers = {"auto_accept": [], "secondary_evidence": [], "low_confidence": [],
             "unresolved": []}
    for s in scored:
        tiers[s["confidence_tier"]].append(s)

    tier_counts = {k: len(v) for k, v in tiers.items()}
    avg_score = round(sum(s["final_score"] for s in scored) / len(scored), 4) if scored else 0.0

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generated_by": "score_pack_source_confidence.py",
        "note": (
            "Pack-source confidence scores only. "
            "No pack assignments applied. collection.json not mutated."
        ),
        "meta": {
            "total_entries": len(scored),
            "average_final_score": avg_score,
            "tier_counts": tier_counts,
        },
        "thresholds": {
            "auto_accept": f">= {TIER_AUTO_ACCEPT}",
            "secondary_evidence": f"{TIER_SECONDARY} – {TIER_AUTO_ACCEPT - 0.001}",
            "low_confidence": f"{TIER_LOW} – {TIER_SECONDARY - 0.001}",
            "unresolved": f"< {TIER_LOW}",
        },
        "scoring_model": {
            "primary_signal": "match_status from current_collection_pack_coverage.json",
            "base_scores": BASE_SCORES,
            "alignment_bonus": ALN_BONUS,
            "alignment_bonus_threshold": 0.60,
            "alignment_no_record_penalty": ALN_NO_RECORD_PENALTY,
            "meta_is_ex_agree": META_IS_EX_AGREE,
            "meta_is_ex_conflict": META_IS_EX_CONFLICT,
            "meta_type_agree": META_TYPE_AGREE,
            "meta_type_conflict": META_TYPE_CONFLICT,
            "ambiguous_cap": 0.79,
            "stage_adjustment": "not_applied_stage_not_in_pack_sources",
        },
        "summary": {
            "by_match_status": {},
            "by_card_type": {},
            "by_pokemon_type": {},
            "ex_cards": {},
        },
        "entries": scored,
        "auto_accept_entries": [s["entry_id"] for s in tiers["auto_accept"]],
        "secondary_evidence_entries": [s["entry_id"] for s in tiers["secondary_evidence"]],
        "low_confidence_entries": [s["entry_id"] for s in tiers["low_confidence"]],
        "unresolved_entries": [s["entry_id"] for s in tiers["unresolved"]],
    }

    # Summaries
    from collections import Counter, defaultdict

    by_status = defaultdict(list)
    by_type = defaultdict(list)
    by_ct = defaultdict(list)
    for s in scored:
        by_status[s["match_status"]].append(s["final_score"])
        by_ct[s["card_type"]].append(s["final_score"])
        if s.get("type"):
            by_type[s["type"]].append(s["final_score"])

    out["summary"]["by_match_status"] = {
        k: {"count": len(v), "avg_score": round(sum(v) / len(v), 4)}
        for k, v in sorted(by_status.items())
    }
    out["summary"]["by_card_type"] = {
        k: {"count": len(v), "avg_score": round(sum(v) / len(v), 4)}
        for k, v in sorted(by_ct.items())
    }
    out["summary"]["by_pokemon_type"] = {
        k: {"count": len(v), "avg_score": round(sum(v) / len(v), 4)}
        for k, v in sorted(by_type.items())
    }

    ex = [s for s in scored if s.get("is_ex")]
    out["summary"]["ex_cards"] = {
        "count": len(ex),
        "avg_score": round(sum(s["final_score"] for s in ex) / len(ex), 4) if ex else 0,
        "tier_counts": dict(Counter(s["confidence_tier"] for s in ex)),
        "entries": [s["entry_id"] for s in ex],
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


def write_csv(scored: list):
    fieldnames = [
        "entry_id", "name", "count", "card_type", "type", "is_ex",
        "match_status", "candidate_count",
        "best_set_code", "best_card_number", "best_pack_name", "best_expansion",
        "base_score", "final_score", "confidence_tier", "next_action", "blockers",
    ]
    (ROOT / "data" / "exports").mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for s in scored:
            bc = s.get("best_candidate") or {}
            w.writerow({
                "entry_id": s["entry_id"],
                "name": s["name"],
                "count": s["count"],
                "card_type": s["card_type"],
                "type": s["type"],
                "is_ex": s["is_ex"],
                "match_status": s["match_status"],
                "candidate_count": s["candidate_count"],
                "best_set_code": bc.get("set_code", ""),
                "best_card_number": bc.get("card_number", ""),
                "best_pack_name": bc.get("pack_name", ""),
                "best_expansion": bc.get("expansion", ""),
                "base_score": s["base_score"],
                "final_score": s["final_score"],
                "confidence_tier": s["confidence_tier"],
                "next_action": s["next_action"],
                "blockers": "; ".join(s["blockers"]),
            })


def write_md(out: dict, scored: list):
    meta = out["meta"]
    tc = meta["tier_counts"]
    sm = out["summary"]

    auto = [s for s in scored if s["confidence_tier"] == "auto_accept"]
    sec = [s for s in scored if s["confidence_tier"] == "secondary_evidence"]
    low = [s for s in scored if s["confidence_tier"] == "low_confidence"]
    unres = [s for s in scored if s["confidence_tier"] == "unresolved"]

    lines = [
        "# Pack-Source Confidence Scores",
        "",
        "> **No pack-opening recommendation is made here.**",
        "> This report scores pack-source confidence for each collection entry.",
        "> No pack assignments have been applied. `collection.json` was not modified.",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Total entries | {meta['total_entries']} |",
        f"| Average confidence score | {meta['average_final_score']} |",
        f"| Auto-accept (≥ 0.95) | **{tc['auto_accept']}** |",
        f"| Secondary evidence (0.80–0.949) | {tc['secondary_evidence']} |",
        f"| Low confidence (0.50–0.799) | {tc['low_confidence']} |",
        f"| Unresolved (< 0.50) | {tc['unresolved']} |",
        "",
        "## Confidence Distribution by Match Status",
        "",
        "| Match Status | Count | Avg Score |",
        "|---|---|---|",
    ]
    for status, info in sm["by_match_status"].items():
        lines.append(f"| {status} | {info['count']} | {info['avg_score']} |")

    lines += [
        "",
        "## Confidence by Card Type",
        "",
        "| Card Type | Count | Avg Score |",
        "|---|---|---|",
    ]
    for ct, info in sm["by_card_type"].items():
        lines.append(f"| {ct} | {info['count']} | {info['avg_score']} |")

    lines += [
        "",
        "## Confidence by Pokémon Type",
        "",
        "| Type | Count | Avg Score |",
        "|---|---|---|",
    ]
    for pt, info in sm["by_pokemon_type"].items():
        lines.append(f"| {pt} | {info['count']} | {info['avg_score']} |")

    ex_info = sm["ex_cards"]
    lines += [
        "",
        "## EX Card Confidence",
        "",
        f"- **{ex_info['count']} EX entries** — avg score: {ex_info['avg_score']}",
        f"- Tier distribution: {ex_info['tier_counts']}",
        f"- Entry IDs: {', '.join(ex_info['entries'])}",
        "",
        "## Auto-Accept Entries",
        "",
        f"**{len(auto)} entries** have score ≥ 0.95 (single unambiguous pack candidate with metadata agreement).",
        "",
    ]
    if auto:
        lines.append("| Entry ID | Name | Score | Pack | Expansion |")
        lines.append("|---|---|---|---|---|")
        for s in sorted(auto, key=lambda x: -x["final_score"])[:30]:
            bc = s.get("best_candidate") or {}
            lines.append(
                f"| {s['entry_id']} | {s['name']} | {s['final_score']} "
                f"| {bc.get('pack_name', '–')} | {bc.get('expansion', '–')} |"
            )
        if len(auto) > 30:
            lines.append(f"_…and {len(auto) - 30} more. See CSV for full list._")
    else:
        lines.append("None.")

    lines += [
        "",
        "## Secondary Evidence Entries",
        "",
        f"**{len(sec)} entries** (0.80–0.949) — pack assignment likely correct but not auto-accepted.",
        "",
    ]
    if sec:
        lines.append("| Entry ID | Name | Score | Match Status | Pack |")
        lines.append("|---|---|---|---|---|")
        for s in sorted(sec, key=lambda x: -x["final_score"])[:20]:
            bc = s.get("best_candidate") or {}
            lines.append(
                f"| {s['entry_id']} | {s['name']} | {s['final_score']} "
                f"| {s['match_status']} | {bc.get('pack_name', '–')} |"
            )
    else:
        lines.append("None.")

    lines += [
        "",
        "## Unresolved Entries",
        "",
        f"**{len(unres)} entries** (< 0.50) — require reference expansion or are known gaps.",
        "",
    ]
    if unres:
        lines.append("| Entry ID | Name | Score | Match Status | Blockers |")
        lines.append("|---|---|---|---|---|")
        for s in sorted(unres, key=lambda x: x["final_score"]):
            bl = "; ".join(s["blockers"]) if s["blockers"] else "–"
            lines.append(
                f"| {s['entry_id']} | {s['name']} | {s['final_score']} "
                f"| {s['match_status']} | {bl} |"
            )
    else:
        lines.append("None.")

    # Known gaps
    gaps = [s for s in scored if s["match_status"] == "no_match_known_gap"]
    no_match = [s for s in scored if s["match_status"] == "no_match"]

    lines += [
        "",
        "## Known Trainer Gaps (not in Limitless DB)",
        "",
        "These common trainer items are not indexed in pack_sources.json.",
        "",
    ]
    for s in gaps:
        lines.append(f"- **{s['name']}** (×{s['count']}) — score: {s['final_score']}")

    lines += [
        "",
        "## No-Match Entries (Zygarde forms)",
        "",
        "These cards have no entry in pack_sources.json. A reference expansion is needed.",
        "",
    ]
    for s in no_match:
        lines.append(f"- **{s['name']}** (×{s['count']}) — score: {s['final_score']}")

    lines += [
        "",
        "## Scoring Model",
        "",
        "Primary signal: `match_status` from `current_collection_pack_coverage.json`.",
        "",
        "| Factor | Effect |",
        "|---|---|",
        f"| exact_match base | {BASE_SCORES['exact_match']} |",
        f"| unanimous_pack base | {BASE_SCORES['unanimous_pack']} |",
        f"| unanimous_expansion base | {BASE_SCORES['unanimous_expansion']} |",
        f"| ambiguous_same_set base | {BASE_SCORES['ambiguous_same_set']} |",
        f"| ambiguous_cross_set base | {BASE_SCORES['ambiguous_cross_set']} |",
        f"| no_match / no_match_known_gap base | {BASE_SCORES['no_match']} |",
        f"| alignment record (confidence ≥ 0.60) | +{ALN_BONUS} |",
        f"| no alignment record | {ALN_NO_RECORD_PENALTY} |",
        f"| is_ex agrees with pack_sources | +{META_IS_EX_AGREE} |",
        f"| is_ex conflicts with pack_sources | {META_IS_EX_CONFLICT} |",
        f"| pokemon_type agrees | +{META_TYPE_AGREE} |",
        f"| pokemon_type conflicts | {META_TYPE_CONFLICT} |",
        f"| ambiguous cap | max 0.79 |",
        f"| stage adjustment | not applied (not in pack_sources) |",
        "",
        "## Warnings",
        "",
        "- Scores are based on automated signals only. No human verification has occurred.",
        "- Auto-accept (≥ 0.95) means the pack assignment is structurally unambiguous — "
        "not that it has been confirmed by the user.",
        "- Low-confidence and unresolved entries should be improved via automated "
        "reference enrichment, not defaulted to manual CSV review.",
        "- Manual CSV review remains available as a fallback for unresolved entries.",
        "",
    ]

    (ROOT / "review").mkdir(exist_ok=True)
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def run_validate() -> bool:
    print("\n=== score_pack_source_confidence.py [VALIDATE] ===")
    errors = 0

    if not OUT_JSON.exists():
        print("  ERROR: output JSON not found — run without --validate first")
        return False
    if not COLLECTION_JSON.exists():
        print(f"  ERROR: {COLLECTION_JSON} not found")
        return False

    col_data = json.loads(COLLECTION_JSON.read_text(encoding="utf-8"))
    entries = col_data["collection"]
    expected_total_qty = sum(e["count"] for e in entries)

    out = json.loads(OUT_JSON.read_text(encoding="utf-8"))
    scored = out["entries"]

    # 1. Entry count == 224
    if len(scored) != len(entries):
        print(f"  ERROR: scored entries={len(scored)}, expected {len(entries)}")
        errors += 1
    else:
        print(f"  PASS  entry count = {len(scored)}")

    # 2. No duplicate entry_id
    ids = [s["entry_id"] for s in scored]
    if len(ids) != len(set(ids)):
        from collections import Counter
        dupes = [eid for eid, n in Counter(ids).items() if n > 1]
        print(f"  ERROR: duplicate entry_ids: {dupes}")
        errors += 1
    else:
        print(f"  PASS  no duplicate entry_ids")

    # 3. All final_scores in [0, 1]
    bad = [s for s in scored if not (0.0 <= s["final_score"] <= 1.0)]
    if bad:
        print(f"  ERROR: {len(bad)} entries with out-of-range scores")
        errors += 1
    else:
        print(f"  PASS  all final_scores in [0, 1]")

    # 4. Confidence tiers valid
    bad_tiers = [s for s in scored if s["confidence_tier"] not in VALID_TIERS]
    if bad_tiers:
        print(f"  ERROR: {len(bad_tiers)} entries with invalid tiers")
        errors += 1
    else:
        print(f"  PASS  all confidence_tiers valid")

    # 5. auto_accept entries have score >= 0.95
    bad_aa = [s for s in scored
              if s["confidence_tier"] == "auto_accept" and s["final_score"] < 0.95]
    if bad_aa:
        print(f"  ERROR: {len(bad_aa)} auto_accept entries with score < 0.95")
        errors += 1
    else:
        print(f"  PASS  all auto_accept entries have score >= 0.95")

    # 6. unresolved entries have score < 0.50
    bad_ur = [s for s in scored
              if s["confidence_tier"] == "unresolved" and s["final_score"] >= 0.50]
    if bad_ur:
        print(f"  ERROR: {len(bad_ur)} unresolved entries with score >= 0.50")
        errors += 1
    else:
        print(f"  PASS  all unresolved entries have score < 0.50")

    # 7. no_match / no_match_known_gap have no best_candidate
    bad_nm = [s for s in scored
              if s["match_status"] in NO_CANDIDATE_STATUSES
              and s.get("best_candidate") is not None]
    if bad_nm:
        print(f"  ERROR: {len(bad_nm)} no_match entries with non-null best_candidate")
        errors += 1
    else:
        print(f"  PASS  no_match entries have null best_candidate")

    # 8. candidate_count matches candidates length
    bad_cc = [s for s in scored if s["candidate_count"] != len(s.get("candidates", []))]
    if bad_cc:
        print(f"  ERROR: {len(bad_cc)} entries with mismatched candidate_count")
        errors += 1
    else:
        print(f"  PASS  all candidate_count values match candidates list length")

    # 9. Collection total unchanged
    scored_qty_sum = sum(s["count"] for s in scored)
    if scored_qty_sum != expected_total_qty:
        print(f"  ERROR: scored quantity sum={scored_qty_sum}, "
              f"collection total={expected_total_qty}")
        errors += 1
    else:
        print(f"  PASS  collection quantity total unchanged ({expected_total_qty})")

    # 10. Output CSV and MD exist
    for path, label in [(OUT_CSV, "CSV"), (OUT_MD, "Markdown")]:
        if not path.exists():
            print(f"  WARN  {label} output not found")
        else:
            print(f"  PASS  {label} output exists")

    if errors == 0:
        tc = out["meta"]["tier_counts"]
        print(f"\nVALIDATION PASSED  ({len(scored)} entries, "
              f"auto_accept={tc['auto_accept']}, "
              f"secondary={tc['secondary_evidence']}, "
              f"low={tc['low_confidence']}, "
              f"unresolved={tc['unresolved']})")
    else:
        print(f"\nVALIDATION FAILED  ({errors} error(s))")
    return errors == 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Score pack-source confidence for collection entries"
    )
    parser.add_argument("--validate", action="store_true",
                        help="Validate existing output rather than regenerating")
    args = parser.parse_args()

    if args.validate:
        ok = run_validate()
        sys.exit(0 if ok else 1)

    print("\n=== score_pack_source_confidence.py ===")

    for path, label in [
        (COLLECTION_JSON, "collection_normalized.json"),
        (PACK_SOURCES_JSON, "pack_sources.json"),
        (COVERAGE_JSON, "current_collection_pack_coverage.json"),
    ]:
        if not path.exists():
            print(f"ERROR: {label} not found at {path}", file=sys.stderr)
            sys.exit(1)

    col_data = json.loads(COLLECTION_JSON.read_text(encoding="utf-8"))
    entries = col_data["collection"]
    print(f"  Collection entries: {len(entries)}")

    ps_raw = json.loads(PACK_SOURCES_JSON.read_text(encoding="utf-8"))
    ps_records = ps_raw["records"] if isinstance(ps_raw, dict) else ps_raw
    ps_index = build_ps_index(ps_records)
    print(f"  Pack sources:       {len(ps_index)} indexed records")

    cov_data = json.loads(COVERAGE_JSON.read_text(encoding="utf-8"))
    cov_by_id = {e["entry_id"]: e for e in cov_data["entries"]}
    print(f"  Coverage entries:   {len(cov_by_id)}")

    if ALIGNMENT_JSON.exists():
        aln_data = json.loads(ALIGNMENT_JSON.read_text(encoding="utf-8"))
        aln_index = build_aln_index(aln_data["alignment_records"])
        print(f"  Alignment records:  {len(aln_index)} with entry_id")
    else:
        aln_index = {}
        print(f"  Alignment records:  0 (screenshot pipeline removed — no_record_penalty applies to all)")

    # Score every entry
    scored = []
    missing_coverage = []
    for entry in entries:
        eid = entry["entry_id"]
        cov_entry = cov_by_id.get(eid)
        if cov_entry is None:
            missing_coverage.append(eid)
            continue
        scored.append(score_entry(entry, cov_entry, ps_index, aln_index))

    if missing_coverage:
        print(f"  WARN: {len(missing_coverage)} entries not in coverage data: "
              f"{missing_coverage[:5]}", file=sys.stderr)

    out = write_json(scored)

    tc = out["meta"]["tier_counts"]
    print(f"\n=== Summary ===")
    print(f"  Entries scored:     {len(scored)}")
    print(f"  Avg score:          {out['meta']['average_final_score']}")
    print(f"  auto_accept:        {tc['auto_accept']}")
    print(f"  secondary_evidence: {tc['secondary_evidence']}")
    print(f"  low_confidence:     {tc['low_confidence']}")
    print(f"  unresolved:         {tc['unresolved']}")
    print(f"\nDone.")


if __name__ == "__main__":
    main()
