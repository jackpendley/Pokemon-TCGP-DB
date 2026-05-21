#!/usr/bin/env python3
"""
Resolve the 59 low-confidence pack-source entries using automated evidence.

A pre-pass removes candidates with confirmed HP/attack mismatches found via external
research (KNOWN_INVALID_CANDIDATES). Then four resolution passes are applied in order:

  PASS 0 — User confirmations
    Read data/current/current_collection_pack_confirmations.json (written by
    apply_current_pack_confirmations.py). These are authoritative user-verified
    resolutions with confidence 0.99. They override any automated result.

  PASS 1 — HP match
    Cross-reference collection.json HP values against external_card_reference.json.
    If the user's HP uniquely intersects with exactly one candidate set, resolve it.

  PASS 2 — Evolution chain
    If an evolution partner is already resolved (by PASS 0, PASS 1, or higher tiers),
    inherit its set assignment for same-set evolution chains. Each link uses a confirmed
    anchor.

  PASS 3 — Rarity/count inference
    When HP ties across candidates, compare rarity (one_diamond vs one_star) with
    collection count. Getting count≥2 of a one_star card is statistically implausible.
    Require count≥2 and a clear rarity asymmetry (one_star vs common).

No mutations to collection.json. All output goes to data/current/.

Inputs:
    data/current/pack_source_confidence_scores.json
    data/current/collection_normalized.json
    data/current/current_collection_pack_confirmations.json  (optional — PASS 0)
    data/reference/external/external_card_reference.json
    data/reference/pack_sources.json

Outputs:
    data/current/resolved_pack_sources.json   — machine-readable resolutions
    review/resolved_pack_sources.md           — human-readable summary

Usage:
    python3 scripts/resolve_ambiguous_pack_sources.py
    python3 scripts/resolve_ambiguous_pack_sources.py --validate
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CONFIDENCE_JSON      = ROOT / "data" / "current"   / "pack_source_confidence_scores.json"
COLLECTION_JSON      = ROOT / "data" / "current"   / "collection_normalized.json"
CONFIRMATIONS_JSON   = ROOT / "data" / "current"   / "current_collection_pack_confirmations.json"
EXT_REF_JSON         = ROOT / "data" / "reference" / "external" / "external_card_reference.json"
PACK_SOURCES_JSON    = ROOT / "data" / "reference" / "pack_sources.json"
PZ_RAW_CACHE         = ROOT / "data" / "sync" / "last_sync_raw.json"

OUT_JSON = ROOT / "data" / "current" / "resolved_pack_sources.json"
OUT_MD   = ROOT / "review"           / "resolved_pack_sources.md"

USER_CONFIRMATION_CONFIDENCE = 0.99

# Candidates definitively excluded by external research (HP/attack mismatch or rarity mismatch).
# Evidence sources noted per entry; dates are 2026-05-15.
KNOWN_INVALID_CANDIDATES = {
    # HP/attack mismatch (Limitless fetch 2026-05-15):
    # A4a/56 = HP 70, Leek Slam 60 ≠ collection HP 60, Leek Slap 40
    # Screenshot confirmed one_diamond; A3b/102 and A4b/359 are one_star (shiny):
    "farfetch_d":  [("A4a", 56), ("A3b", 102), ("A4b", 359)],

    # Screenshot confirmed four_diamond; these candidates are double_star:
    "moltres_ex":  [("A1", 255), ("A1", 274), ("A3b", 103)],
    "marowak_ex":  [("A1", 264), ("A3",  236)],

    # Screenshot confirmed two_diamond; these candidates are double_star or triple_star:
    "giovanni":    [("A1", 270)],
    "sabrina":     [("A1", 272)],
    "leaf":        [("A1a", 82)],
    "cyrus":       [("A2", 190)],
    "lillie":      [("A3", 197), ("A3", 209)],
}

# Confidence thresholds
PZ_SET_CODE_CONFIDENCE = 0.97   # PZ is source of truth for which set a card came from
HP_MATCH_CONFIDENCE   = 0.88
EVO_CHAIN_CONFIDENCE  = 0.82
RARITY_COUNT_CONF_3   = 0.90   # count >= 3, one_star vs common
RARITY_COUNT_CONF_2   = 0.85   # count == 2, one_star vs common

# EV tiers used downstream (mirrors CLAUDE.md section 7)
AUTO_ACCEPT_THRESHOLD  = 0.95
SECONDARY_THRESHOLD    = 0.80

# Evolution chains: each tuple is a pair sharing the same set.
# Order within tuple doesn't matter — both directions are tried.
EVO_CHAIN_PAIRS = [
    ("makuhita",             "hariyama"),
    ("stufful",              "bewear"),
    ("trubbish",             "garbodor"),
    ("minccino",             "cinccino"),
    ("onix_land_crush_art",  "steelix"),
    ("onix_dig_art",         "steelix"),
    ("porygon",              "porygon2"),
    ("lillipup",             "herdier"),
    ("herdier",              "stoutland"),
    ("skrelp",               "dragalge"),
    ("grimer",               "muk"),
    ("frillish",             "jellicent"),
    ("chewtle",              "drednaw"),
    ("tangela",              "tangrowth"),
    ("zorua",                "zoroark"),
    ("doublade",             "aegislash"),
    ("sandshrew",            "sandslash"),
]


def normalize(name: str) -> str:
    return name.lower().strip()


def load_data():
    scores      = json.loads(CONFIDENCE_JSON.read_text())
    coll_data   = json.loads(COLLECTION_JSON.read_text())
    ext         = json.loads(EXT_REF_JSON.read_text())
    raw_ps      = json.loads(PACK_SOURCES_JSON.read_text())
    pack_sources = raw_ps["records"]
    coll_map    = {e["entry_id"]: e for e in coll_data["collection"]}
    return scores, coll_map, ext, pack_sources


def build_ext_lookup(ext):
    """(name_lower, hp) -> list of external records."""
    idx = {}
    for r in ext:
        key = (r["name"].lower(), r.get("hp"))
        idx.setdefault(key, []).append(r)
    return idx


def best_pack_rec(pack_sources, set_code, name):
    """Return first pack_sources record matching set_code + name (case-insensitive)."""
    nl = name.lower()
    return next((r for r in pack_sources
                 if r["set_code"] == set_code and r["card_name"].lower() == nl), None)


def pass0_user_confirmations(low_entries, pack_sources):
    """
    Apply user-verified confirmations from current_collection_pack_confirmations.json.
    These are authoritative — confidence 0.99, method='user_confirmation'.
    Only applies to low_confidence entries (others are already resolved upstream).
    """
    if not CONFIRMATIONS_JSON.exists():
        return {}

    raw = json.loads(CONFIRMATIONS_JSON.read_text(encoding="utf-8"))
    conf_map = raw.get("confirmations", {})
    low_ids  = {e["entry_id"] for e in low_entries}

    resolved = {}
    for eid, c in conf_map.items():
        if eid not in low_ids:
            continue
        sc = c.get("confirmed_set_code")
        cn = c.get("confirmed_card_number")
        if not sc or cn is None:
            continue
        pack_name  = c.get("pack_name") or best_pack_rec_by_key(pack_sources, sc, cn)
        expansion  = c.get("expansion", "")
        resolved[eid] = {
            "name":       c.get("name", eid),
            "set_code":   sc,
            "pack_name":  pack_name,
            "expansion":  expansion,
            "method":     "user_confirmation",
            "confidence": USER_CONFIRMATION_CONFIDENCE,
            "evidence":   f"user confirmed via apply_current_pack_confirmations.py: ({sc}, {cn})",
        }
    return resolved


def best_pack_rec_by_key(pack_sources, set_code, card_number):
    """Return pack_name for exact (set_code, card_number) match."""
    r = next((r for r in pack_sources
              if r.get("set_code") == set_code and r.get("card_number") == card_number), None)
    return r["pack_name"] if r else None


def build_all_resolved(scores, coll_map, ext, pack_sources, ext_idx):
    """
    Build a combined resolved dict keyed by entry_id covering:
      - auto_accept and secondary tiers (from confidence_scores)
      - PASS 1 HP matches from low_confidence tier

    Used as anchor pool for evolution chain (PASS 2).
    """
    resolved = {}

    # Auto_accept and secondary
    for e in scores["entries"]:
        tier = e.get("confidence_tier", "")
        if tier in ("auto_accept", "secondary") and e.get("best_candidate"):
            bc = e["best_candidate"]
            resolved[e["entry_id"]] = {
                "name":      e["name"],
                "set_code":  bc.get("set_code"),
                "pack_name": bc.get("pack_name"),
                "expansion": bc.get("expansion"),
                "method":    tier,
                "confidence": e["final_score"],
            }

    # PASS 1 from low_confidence
    for e in scores["entries"]:
        if e["confidence_tier"] != "low_confidence":
            continue
        eid  = e["entry_id"]
        name = e["name"]
        coll_e = coll_map.get(eid, {})
        hp     = coll_e.get("hp")
        candidates     = e.get("candidates", [])
        candidate_sets = set(c.get("set_code") for c in candidates)

        if hp is None:
            continue

        matches     = ext_idx.get((name.lower(), hp), [])
        matched_sets = set(m["set_code"] for m in matches if m["set_code"] in candidate_sets)

        if len(matched_sets) == 1:
            winner = next(iter(matched_sets))
            pr = best_pack_rec(pack_sources, winner, name)
            resolved[eid] = {
                "name":       name,
                "set_code":   winner,
                "pack_name":  pr["pack_name"] if pr else None,
                "expansion":  pr["expansion"] if pr else None,
                "method":     "hp_match",
                "confidence": HP_MATCH_CONFIDENCE,
                "evidence":   f"collection hp={hp} uniquely matches {winner}",
            }

    return resolved


def pass1_hp_match(low_entries, coll_map, ext_idx, pack_sources):
    """Resolve entries where collection HP uniquely identifies one candidate set."""
    resolved = {}
    for e in low_entries:
        eid  = e["entry_id"]
        name = e["name"]
        coll_e = coll_map.get(eid, {})
        hp     = coll_e.get("hp")
        candidates     = e.get("candidates", [])
        candidate_sets = set(c.get("set_code") for c in candidates)

        if hp is None:
            continue

        matches      = ext_idx.get((name.lower(), hp), [])
        matched_sets = set(m["set_code"] for m in matches if m["set_code"] in candidate_sets)

        if len(matched_sets) == 1:
            winner = next(iter(matched_sets))
            pr = best_pack_rec(pack_sources, winner, name)
            resolved[eid] = {
                "name":       name,
                "set_code":   winner,
                "pack_name":  pr["pack_name"] if pr else None,
                "expansion":  pr["expansion"] if pr else None,
                "method":     "hp_match",
                "confidence": HP_MATCH_CONFIDENCE,
                "evidence":   f"collection hp={hp} uniquely matches {winner} in external reference",
            }
    return resolved


def pass2_evo_chain(remaining, all_resolved, pack_sources):
    """
    For each unresolved entry, scan EVO_CHAIN_PAIRS. If a chain partner is
    already resolved, and the resolved set appears in this entry's candidate_sets,
    and this card exists in pack_sources for that set, apply the chain.
    """
    resolved = {}

    # Build a name -> list of (entry_id, set_code) map from all_resolved
    # (multiple entries can share a name, e.g., two Charmander variants)
    name_to_resolutions = {}
    for eid, r in all_resolved.items():
        nm = r["name"].lower()
        name_to_resolutions.setdefault(nm, []).append((eid, r["set_code"]))

    remaining_by_id = {e["entry_id"]: e for e in remaining}

    for entry in remaining:
        eid  = entry["entry_id"]
        name = entry["name"]
        candidates     = entry.get("candidates", [])
        candidate_sets = set(c.get("set_code") for c in candidates)

        # Find chain partners for this entry
        partner_names = []
        for a, b in EVO_CHAIN_PAIRS:
            if a == eid:
                partner_names.append(b)
            elif b == eid:
                partner_names.append(a)

        for partner_id in partner_names:
            if partner_id not in all_resolved:
                continue
            anchor_set = all_resolved[partner_id]["set_code"]
            if anchor_set not in candidate_sets:
                continue

            # Verify this card exists in pack_sources for anchor_set
            pr = best_pack_rec(pack_sources, anchor_set, name)
            if not pr:
                continue

            resolved[eid] = {
                "name":       name,
                "set_code":   anchor_set,
                "pack_name":  pr["pack_name"],
                "expansion":  pr["expansion"],
                "method":     "evo_chain",
                "confidence": EVO_CHAIN_CONFIDENCE,
                "evidence":   f"evolution partner '{partner_id}' confirmed in {anchor_set}",
            }
            break   # first valid anchor is enough

    return resolved


def pass3_rarity_count(remaining, coll_map, pack_sources, scores_map):
    """
    For entries where HP ties across candidates, use rarity asymmetry + count.
    Resolve when count >= 2 and one candidate is one_star while another is common.

    Confidence:
      count >= 3 and other candidate is common: 0.90
      count == 2 and other candidate is common: 0.85
    """
    resolved = {}

    # Build rarity lookup from pack_sources
    # {(name_lower, set_code): rarity}
    rarity_idx = {}
    for r in pack_sources:
        key = (r["card_name"].lower(), r["set_code"])
        rarity_idx[key] = r.get("rarity", "")

    RARE = {"one_star", "double_star", "triple_star", "crown"}
    COMMON = {"one_diamond", "two_diamond", "three_diamond", "four_diamond"}

    for entry in remaining:
        eid  = entry["entry_id"]
        name = entry["name"]
        coll_e = coll_map.get(eid, {})
        count = coll_e.get("count", 0)
        candidates     = entry.get("candidates", [])
        candidate_sets = list(dict.fromkeys(c.get("set_code") for c in candidates))  # dedup, preserve order

        if count < 2:
            continue

        # Get rarity per candidate set
        rarity_by_set = {}
        for s in candidate_sets:
            r = rarity_idx.get((name.lower(), s))
            if r:
                rarity_by_set[s] = r

        if len(rarity_by_set) < 2:
            continue

        # Find sets with rare vs common rarity
        rare_sets   = [s for s, r in rarity_by_set.items() if r in RARE]
        common_sets = [s for s, r in rarity_by_set.items() if r in COMMON]

        # Only resolve if exactly one common set and at least one rare set
        if len(common_sets) != 1 or len(rare_sets) < 1:
            continue

        winner = common_sets[0]
        conf   = RARITY_COUNT_CONF_3 if count >= 3 else RARITY_COUNT_CONF_2
        rare_str = ", ".join(f"{s}={rarity_by_set[s]}" for s in rare_sets)
        pr = best_pack_rec(pack_sources, winner, name)
        if not pr:
            continue

        resolved[eid] = {
            "name":       name,
            "set_code":   winner,
            "pack_name":  pr["pack_name"],
            "expansion":  pr["expansion"],
            "method":     "rarity_count",
            "confidence": conf,
            "evidence":   (f"count={count} with {winner}={rarity_by_set[winner]}; "
                           f"one_star candidate(s) {rare_str} implausible at this count"),
        }

    return resolved


def pass4_pz_set_code(remaining, pack_sources):
    """
    Resolve using set codes from last_sync_raw.json (Pokemon Zone source data).
    PZ directly reports which set each owned card came from — authoritative for
    trainer cards and A-series cards that can't be disambiguated via HP.
    Only resolves when the PZ set codes intersect uniquely with one candidate set.
    """
    if not PZ_RAW_CACHE.exists():
        return {}
    try:
        raw = json.loads(PZ_RAW_CACHE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    # name_lower → set of set_codes reported by PZ for owned copies
    pz_sets: dict[str, set[str]] = {}
    for rec in raw:
        name = rec.get("cardName", "").lower()
        sc   = rec.get("setCode", "")
        if name and sc:
            pz_sets.setdefault(name, set()).add(sc)

    resolved = {}
    for entry in remaining:
        eid  = entry["entry_id"]
        name = entry["name"]
        candidate_sets = set(c.get("set_code") for c in entry.get("candidates", []))

        owned_sets   = pz_sets.get(name.lower(), set())
        intersection = owned_sets & candidate_sets

        if len(intersection) != 1:
            continue

        winner = next(iter(intersection))
        pr = best_pack_rec(pack_sources, winner, name)
        if not pr:
            continue

        resolved[eid] = {
            "name":       name,
            "set_code":   winner,
            "pack_name":  pr["pack_name"],
            "expansion":  pr["expansion"],
            "method":     "pz_set_code",
            "confidence": PZ_SET_CODE_CONFIDENCE,
            "evidence":   f"Pokemon Zone reports setCode={winner} for owned copy",
        }
    return resolved


def classify_unresolved_reason(entry, coll_map, ext_idx):
    """Return a human-readable reason code for why an entry could not be resolved."""
    eid  = entry["entry_id"]
    name = entry["name"]
    coll_e = coll_map.get(eid, {})
    hp     = coll_e.get("hp")
    candidates     = entry.get("candidates", [])
    candidate_sets = set(c.get("set_code") for c in candidates)

    a_series = all(s.startswith("A") for s in candidate_sets)
    if hp is None and a_series:
        return "trainer_card_no_hp"
    if hp is None:
        return "no_hp_field"
    if a_series:
        return "a_series_no_external_ref"

    # Check if HP is in external ref at all
    matches = ext_idx.get((name.lower(), hp), [])
    if not matches:
        return "hp_not_in_external_ref"

    matched_sets = set(m["set_code"] for m in matches if m["set_code"] in candidate_sets)
    if len(matched_sets) > 1:
        return "hp_ties_multiple_sets"

    return "no_evo_chain_available"


def run():
    scores, coll_map, ext, pack_sources = load_data()
    ext_idx    = build_ext_lookup(ext)
    scores_map = {e["entry_id"]: e for e in scores["entries"]}

    low_entries = [e for e in scores["entries"] if e["confidence_tier"] == "low_confidence"]
    print(f"Low-confidence entries to resolve: {len(low_entries)}")

    # Pre-pass: remove candidates with confirmed HP/attack mismatch from external research
    for entry in low_entries:
        eid = entry["entry_id"]
        if eid in KNOWN_INVALID_CANDIDATES:
            exclude = set(tuple(pair) for pair in KNOWN_INVALID_CANDIDATES[eid])
            before = len(entry.get("candidates", []))
            entry["candidates"] = [
                c for c in entry.get("candidates", [])
                if (c.get("set_code"), c.get("card_number")) not in exclude
            ]
            removed = before - len(entry["candidates"])
            if removed:
                print(f"  Pre-pass: excluded {removed} invalid candidate(s) for {eid}")

    # Build anchor pool (auto_accept + secondary + PASS 1)
    all_resolved_pool = build_all_resolved(scores, coll_map, ext, pack_sources, ext_idx)

    # --- PASS 0 ---
    p0 = pass0_user_confirmations(low_entries, pack_sources)
    print(f"PASS 0 (user_conf):    {len(p0):3d} resolved")

    # Include PASS 0 in anchor pool before automated passes
    all_resolved_pool = {**all_resolved_pool, **p0}

    # --- PASS 1 ---
    remaining_after_p0 = [e for e in low_entries if e["entry_id"] not in p0]
    p1 = pass1_hp_match(remaining_after_p0, coll_map, ext_idx, pack_sources)
    print(f"PASS 1 (hp_match):      {len(p1):3d} resolved")

    # --- PASS 2 ---
    # Include PASS 0 + PASS 1 results in the anchor pool before chaining
    combined_pool = {**all_resolved_pool, **p1}
    remaining_after_p1 = [e for e in remaining_after_p0 if e["entry_id"] not in p1]
    p2 = pass2_evo_chain(remaining_after_p1, combined_pool, pack_sources)
    print(f"PASS 2 (evo_chain):     {len(p2):3d} resolved")

    # --- PASS 3 ---
    remaining_after_p2 = [e for e in remaining_after_p1 if e["entry_id"] not in p2]
    p3 = pass3_rarity_count(remaining_after_p2, coll_map, pack_sources, scores_map)
    print(f"PASS 3 (rarity_count):  {len(p3):3d} resolved")

    # --- PASS 2B (evo_chain re-run with PASS 3 anchors) ---
    # porygon2 needs porygon (resolved by PASS 3) as evo anchor
    combined_pool_2b = {**combined_pool, **p2, **p3}
    remaining_after_p3 = [e for e in remaining_after_p2 if e["entry_id"] not in p3]
    p2b = pass2_evo_chain(remaining_after_p3, combined_pool_2b, pack_sources)
    print(f"PASS 2B (evo_chain+):   {len(p2b):3d} resolved")

    # --- PASS 4 ---
    remaining_after_p2b = [e for e in remaining_after_p3 if e["entry_id"] not in p2b]
    p4 = pass4_pz_set_code(remaining_after_p2b, pack_sources)
    print(f"PASS 4 (pz_set_code):  {len(p4):3d} resolved")

    # Merge all resolved (P0 highest priority, then P1, P2, P2B, P3, P4)
    new_resolved = {**p1, **p2, **p2b, **p3, **p4, **p0}
    total_new = len(new_resolved)

    remaining_final = [e for e in low_entries if e["entry_id"] not in new_resolved]
    print(f"\nTotal new resolutions: {total_new} / {len(low_entries)}")
    print(f"Still unresolved:      {len(remaining_final)} / {len(low_entries)}")

    ev_total = len(scores.get("entries", []))
    prev_ev_ready = (
        len(scores.get("auto_accept_entries", []))
        + len(scores.get("secondary_evidence_entries", []))
    )
    new_ev_ready  = prev_ev_ready + sum(
        1 for r in new_resolved.values() if r["confidence"] >= SECONDARY_THRESHOLD
    )
    print(f"\nEV-ready coverage:     {prev_ev_ready}/{ev_total} → {new_ev_ready}/{ev_total}")

    # Classify unresolved reasons
    unresolved_list = []
    for e in remaining_final:
        reason = classify_unresolved_reason(e, coll_map, ext_idx)
        unresolved_list.append({
            "entry_id":  e["entry_id"],
            "name":      e["name"],
            "candidates": [c.get("set_code") for c in e.get("candidates", [])],
            "reason":    reason,
        })

    # Build output
    out = {
        "_meta": {
            "generated":       datetime.now(timezone.utc).isoformat(),
            "source_script":   "scripts/resolve_ambiguous_pack_sources.py",
            "version":         "1.3.0",
            "passes":          ["user_confirmation", "hp_match", "evo_chain", "rarity_count", "evo_chain_2b", "pz_set_code"],
            "input_low_confidence": len(low_entries),
            "total_new_resolved": total_new,
            "total_still_unresolved": len(remaining_final),
            "ev_ready_before": prev_ev_ready,
            "ev_ready_after":  new_ev_ready,
            "ev_ready_total":  ev_total,
        },
        "resolved": new_resolved,
        "unresolved": unresolved_list,
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"\nWrote {OUT_JSON}")

    _write_markdown(out, new_resolved, unresolved_list, p0, p1, p2, p2b, p3, p4)
    print(f"Wrote {OUT_MD}")

    return out


def _write_markdown(out, new_resolved, unresolved_list, p0, p1, p2, p2b, p3, p4):
    meta = out["_meta"]
    ts   = meta["generated"]

    lines = [
        "# Resolved Ambiguous Pack Sources",
        "",
        f"Generated: {ts[:10]}  ",
        "Script: `scripts/resolve_ambiguous_pack_sources.py`",
        "",
        "---",
        "",
        "## Summary",
        "",
        f"| Metric | Value |",
        f"|---|---|",
        f"| Low-confidence input | {meta['input_low_confidence']} |",
        f"| PASS 0 — user_confirmation | {len(p0)} |",
        f"| PASS 1 — hp_match | {len(p1)} |",
        f"| PASS 2 — evo_chain | {len(p2)} |",
        f"| PASS 3 — rarity_count | {len(p3)} |",
        f"| PASS 2B — evo_chain (post-P3) | {len(p2b)} |",
        f"| PASS 4 — pz_set_code | {len(p4)} |",
        f"| **Total new resolved** | **{meta['total_new_resolved']}** |",
        f"| Still unresolved | {meta['total_still_unresolved']} |",
        f"| EV-ready before | {meta['ev_ready_before']}/{meta['ev_ready_total']} ({meta['ev_ready_before']/meta['ev_ready_total']*100:.0f}%) |",
        f"| EV-ready after  | {meta['ev_ready_after']}/{meta['ev_ready_total']} ({meta['ev_ready_after']/meta['ev_ready_total']*100:.0f}%) |",
        "",
        "---",
        "",
        "## PASS 0: User Confirmations",
        "",
        "| Entry | Set | Pack | Evidence |",
        "|---|---|---|---|",
    ]
    for eid, r in sorted(p0.items()):
        lines.append(f"| {eid} | {r['set_code']} | {r['pack_name']} | {r['evidence']} |")

    lines += [
        "",
        "## PASS 1: HP Match",
        "",
        "| Entry | Set | Pack | Confidence | Evidence |",
        "|---|---|---|---|---|",
    ]
    for eid, r in sorted(p1.items()):
        lines.append(f"| {eid} | {r['set_code']} | {r['pack_name']} | {r['confidence']} | {r['evidence']} |")

    lines += [
        "",
        "## PASS 2: Evolution Chain",
        "",
        "| Entry | Set | Pack | Confidence | Evidence |",
        "|---|---|---|---|---|",
    ]
    for eid, r in sorted(p2.items()):
        lines.append(f"| {eid} | {r['set_code']} | {r['pack_name']} | {r['confidence']} | {r['evidence']} |")

    lines += [
        "",
        "## PASS 3: Rarity / Count Inference",
        "",
        "| Entry | Set | Pack | Count | Confidence | Evidence |",
        "|---|---|---|---|---|---|",
    ]
    for eid, r in sorted(p3.items()):
        lines.append(f"| {eid} | {r['set_code']} | {r['pack_name']} | — | {r['confidence']} | {r['evidence']} |")

    lines += [
        "",
        "## PASS 2B: Evolution Chain (post-PASS 3)",
        "",
        "| Entry | Set | Pack | Confidence | Evidence |",
        "|---|---|---|---|---|",
    ]
    for eid, r in sorted(p2b.items()):
        lines.append(f"| {eid} | {r['set_code']} | {r['pack_name']} | {r['confidence']} | {r['evidence']} |")

    lines += [
        "",
        "## PASS 4: Pokemon Zone Set Code",
        "",
        "| Entry | Set | Pack | Confidence | Evidence |",
        "|---|---|---|---|---|",
    ]
    for eid, r in sorted(p4.items()):
        lines.append(f"| {eid} | {r['set_code']} | {r['pack_name']} | {r['confidence']} | {r['evidence']} |")

    lines += [
        "",
        "## Unresolved (manual review or leave as ambiguous)",
        "",
        "| Entry | Candidates | Reason |",
        "|---|---|---|",
    ]
    reason_desc = {
        "trainer_card_no_hp":         "trainer — no HP field, candidates span A1/A4b reprint",
        "no_hp_field":                "no HP in collection.json for this entry",
        "a_series_no_external_ref":   "A-series card — not in external_card_reference.json",
        "hp_not_in_external_ref":     "collection HP not found in external reference (possible data discrepancy)",
        "hp_ties_multiple_sets":      "HP matches same value across all candidate sets — no unique disambiguation",
        "no_evo_chain_available":     "HP tied, no resolved evo partner available as anchor",
    }
    for u in sorted(unresolved_list, key=lambda x: x["entry_id"]):
        cands = ", ".join(sorted(set(u["candidates"])))
        desc  = reason_desc.get(u["reason"], u["reason"])
        lines.append(f"| {u['entry_id']} | {cands} | {desc} |")

    lines += [
        "",
        "---",
        "",
        "## Confidence Tier Summary",
        "",
        "Entries resolved at confidence ≥ 0.80 are EV-ready (auto-accept or secondary tier).",
        "",
        "| Method | Confidence | Tier |",
        "|---|---|---|",
        "| user_confirmation | 0.99 | auto_accept |",
        "| pz_set_code | 0.97 | auto_accept |",
        "| hp_match | 0.88 | secondary |",
        "| evo_chain | 0.82 | secondary |",
        "| rarity_count (count≥3) | 0.90 | secondary |",
        "| rarity_count (count=2) | 0.85 | secondary |",
        "",
        "All new resolutions are at secondary tier (0.80–0.94). "
        "None reach auto-accept (≥0.95) — downstream use must weight accordingly.",
    ]

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines) + "\n")


def validate(out):
    """Spot-check key invariants."""
    errors = []
    resolved = out["resolved"]
    unresolved = out["unresolved"]
    meta = out["_meta"]

    total = meta["input_low_confidence"]
    if meta["total_new_resolved"] + meta["total_still_unresolved"] != total:
        errors.append(
            f"resolved+unresolved={meta['total_new_resolved']+meta['total_still_unresolved']} "
            f"!= input={total}")

    for eid, r in resolved.items():
        if not r.get("set_code"):
            errors.append(f"resolved entry '{eid}' missing set_code")
        if r.get("confidence", 0) < 0.80:
            errors.append(f"resolved entry '{eid}' confidence={r['confidence']} < 0.80 threshold")

    expected_min = 38   # conservative floor: 35 automated + at least some user confirmations
    if meta["total_new_resolved"] < expected_min:
        errors.append(
            f"total_new_resolved={meta['total_new_resolved']} < expected_min={expected_min}")

    return errors


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate", action="store_true",
                        help="Run output validation checks after resolution")
    args = parser.parse_args()

    out = run()

    if args.validate:
        print("\nRunning validation...")
        errors = validate(out)
        if errors:
            for e in errors:
                print(f"  ERROR: {e}")
            sys.exit(1)
        else:
            n = out["_meta"]["total_new_resolved"]
            u = out["_meta"]["total_still_unresolved"]
            print(f"  PASS  {n} resolved, {u} unresolved, all confidences ≥ 0.80")
