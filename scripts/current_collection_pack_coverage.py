#!/usr/bin/env python3
"""
Compare data/current/collection_normalized.json against data/reference/pack_sources.json.
Report pack-source coverage for the active 380-card collection.

Match status categories:
    exact_match          — exactly 1 pack_sources record matches this card name
    unanimous_pack       — multiple records, all with the same pack_name
    unanimous_expansion  — multiple records, all in the same expansion (some pack_name=None/shared)
    ambiguous_same_set   — multiple records in same expansion but different named packs
    ambiguous_cross_set  — records from multiple different expansions
    no_match             — no pack_sources record found (card may be new or differently named)
    no_match_known_gap   — no match; card is a common item/promo not indexed in Limitless

This is coverage analysis only. No pack-opening recommendation is made in this report.

Outputs:
    review/current_collection_pack_coverage.md
    data/current/current_collection_pack_coverage.json
    data/exports/current_collection_pack_coverage.csv

Usage:
    python3 scripts/current_collection_pack_coverage.py
"""

import csv
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NORMALIZED_JSON = ROOT / "data" / "current" / "collection_normalized.json"
PACK_SOURCES_JSON = ROOT / "data" / "reference" / "pack_sources.json"
OUT_MD = ROOT / "review" / "current_collection_pack_coverage.md"
OUT_JSON = ROOT / "data" / "current" / "current_collection_pack_coverage.json"
OUT_CSV = ROOT / "data" / "exports" / "current_collection_pack_coverage.csv"

# Common trainer items that are not indexed in Limitless TCG Pocket
KNOWN_GAP_ITEMS = {
    "potion", "x speed", "red card", "hand scope", "pokédex", "pokedex",
    "poke ball", "poké ball", "x attack", "super potion",
}

# Manual name aliases: collection.json name → pack_sources lookup name
NAME_ALIASES: dict[str, list[str]] = {
    # Zygarde forms: not present in pack_sources under either name
    # (logged as no_match for transparency)
}


def norm(s: str) -> str:
    """Normalize name for lookup: lowercase, collapse whitespace, strip accents."""
    s = str(s or "").strip()
    # Normalize unicode (NFC first, then strip combining chars for basic comparison)
    s = unicodedata.normalize("NFC", s)
    s = re.sub(r"\s+", " ", s).lower()
    return s


def build_ps_index(records: list[dict]) -> dict[str, list[dict]]:
    index: dict[str, list[dict]] = {}
    for r in records:
        key = norm(r.get("card_name", ""))
        index.setdefault(key, []).append(r)
    # Also index with accent-stripped key for looser matching
    accent_index: dict[str, list[dict]] = {}
    for key, recs in index.items():
        stripped = unicodedata.normalize("NFD", key)
        stripped = "".join(c for c in stripped if unicodedata.category(c) != "Mn")
        accent_index.setdefault(stripped, []).extend(recs)
    return index, accent_index


def get_candidates(name: str, is_ex: bool, ptype: str, index: dict, accent_index: dict) -> list[dict]:
    key = norm(name)
    candidates = list(index.get(key, []))

    # Try accent-stripped key if no hits
    if not candidates:
        stripped = unicodedata.normalize("NFD", key)
        stripped = "".join(c for c in stripped if unicodedata.category(c) != "Mn")
        candidates = list(accent_index.get(stripped, []))

    # Try registered aliases
    for alias_key in NAME_ALIASES.get(key, []):
        if not candidates:
            candidates = list(index.get(norm(alias_key), []))

    if not candidates:
        return []

    # Filter by is_ex if pack_sources has that data
    ex_known = [r for r in candidates if r.get("is_ex") is not None]
    if ex_known:
        if is_ex:
            filtered = [r for r in candidates if r.get("is_ex") == True]
        else:
            filtered = [r for r in candidates if r.get("is_ex") == False]
        if filtered:
            candidates = filtered

    # Filter by pokemon_type if pack_sources has it
    if ptype and ptype not in ("Unknown", "", "None"):
        type_filtered = [r for r in candidates if r.get("pokemon_type") == ptype]
        if type_filtered:
            candidates = type_filtered

    return candidates


def classify(candidates: list[dict], entry_name: str, card_type: str) -> tuple[str, str]:
    """Returns (match_status, match_confidence)."""
    if not candidates:
        name_key = norm(entry_name)
        if name_key in KNOWN_GAP_ITEMS or (card_type == "Trainer" and name_key in KNOWN_GAP_ITEMS):
            return "no_match_known_gap", "none"
        return "no_match", "none"

    if len(candidates) == 1:
        return "exact_match", "high"

    pack_names = {r.get("pack_name") for r in candidates if r.get("pack_name")}
    expansions = {r.get("expansion", "") for r in candidates if r.get("expansion")}

    if len(pack_names) == 1:
        # All non-null pack_names are the same
        return "unanimous_pack", "medium"

    if len(expansions) == 1:
        if len(pack_names) == 0:
            # All have pack_name=None (shared pool of one expansion)
            return "unanimous_expansion", "medium"
        elif len(pack_names) <= 1:
            return "unanimous_expansion", "medium"
        else:
            # Different named packs within same expansion
            return "ambiguous_same_set", "low"

    # Multiple expansions
    return "ambiguous_cross_set", "low"


def resolution(match_status: str) -> str:
    return {
        "exact_match": "no_action_needed",
        "unanimous_pack": "no_action_needed",
        "unanimous_expansion": "no_action_needed",
        "ambiguous_same_set": "needs_variant_confirmation",
        "ambiguous_cross_set": "needs_card_number",
        "no_match": "needs_reference_expansion",
        "no_match_known_gap": "needs_manual_source_entry",
    }.get(match_status, "unknown")


def candidate_summary(candidates: list[dict]) -> str:
    if not candidates:
        return ""
    parts = []
    for r in candidates[:5]:  # cap display at 5
        exp = r.get("expansion", "")
        pn = r.get("pack_name") or "shared pool"
        sc = r.get("set_code", "")
        cn = r.get("card_number", "")
        rar = r.get("rarity", "")
        parts.append(f"{sc}/{cn} {exp} ({pn}) [{rar}]")
    suffix = f" … +{len(candidates) - 5} more" if len(candidates) > 5 else ""
    return "; ".join(parts) + suffix


def build_results(entries: list[dict], index: dict, accent_index: dict) -> list[dict]:
    results = []
    for entry in entries:
        name = entry.get("name", "")
        is_ex = entry.get("is_ex", False)
        ptype = entry.get("type", "")
        card_type = entry.get("card_type", "")
        count = entry.get("count", 0)

        candidates = get_candidates(name, is_ex, ptype, index, accent_index)
        match_status, confidence = classify(candidates, name, card_type)
        rec_res = resolution(match_status)

        pack_names_list = sorted({r.get("pack_name") or "shared pool" for r in candidates})
        expansions_list = sorted({r.get("expansion", "") for r in candidates if r.get("expansion")})

        results.append({
            "entry_id": entry.get("entry_id", ""),
            "name": name,
            "count": count,
            "type": ptype,
            "card_type": card_type,
            "stage": entry.get("stage"),
            "hp": entry.get("hp"),
            "is_ex": is_ex,
            "attack": entry.get("attack", ""),
            "variant": entry.get("variant", ""),
            "trainer_subtype": entry.get("trainer_subtype", ""),
            "match_status": match_status,
            "match_confidence": confidence,
            "candidate_count": len(candidates),
            "unique_packs": pack_names_list,
            "unique_expansions": expansions_list,
            "candidate_summary": candidate_summary(candidates),
            "candidates": [
                {
                    "set_code": r.get("set_code"),
                    "card_number": r.get("card_number"),
                    "expansion": r.get("expansion"),
                    "pack_name": r.get("pack_name"),
                    "rarity": r.get("rarity"),
                    "source_url": r.get("source_url"),
                }
                for r in candidates
            ],
            "recommended_resolution": rec_res,
        })
    return results


# Chase deck targets for priority section
CHASE_TARGETS = {
    "ivysaur", "incineroar ex", "zygarde ex", "magnezone ex",
    "marowak ex", "moltres ex",
}


def write_md(results: list[dict], meta: dict, out_path: Path):
    total_qty = sum(r["count"] for r in results)
    by_status = Counter(r["match_status"] for r in results)
    by_status_qty = Counter()
    for r in results:
        by_status_qty[r["match_status"]] += r["count"]

    # Coverage metrics
    resolved_entries = sum(
        v for k, v in by_status.items()
        if k in ("exact_match", "unanimous_pack", "unanimous_expansion")
    )
    resolved_qty = sum(
        v for k, v in by_status_qty.items()
        if k in ("exact_match", "unanimous_pack", "unanimous_expansion")
    )
    total_entries = len(results)

    lines = [
        "# Current Collection Pack-Source Coverage",
        "",
        "> This is coverage analysis only. No pack-opening recommendation is made in this report.",
        "",
        "## Summary",
        "",
        f"| Field | Value |",
        f"|---|---|",
        f"| Collection source | `collection.json` |",
        f"| Collection total | {meta.get('total_cards')} ({total_entries} unique entries) |",
        f"| Pack-source DB | `pack_sources.json` ({meta.get('ps_records')} records) |",
        f"| Resolved entries | {resolved_entries}/{total_entries} ({100*resolved_entries//total_entries}%) |",
        f"| Resolved quantity | {resolved_qty}/{total_qty} ({100*resolved_qty//total_qty}%) |",
        "",
        "## Coverage by Match Status",
        "",
        "| Status | Entries | Quantity | Meaning |",
        "|---|---|---|---|",
    ]

    desc = {
        "exact_match": "One candidate in pack_sources",
        "unanimous_pack": "Multiple candidates, all same pack",
        "unanimous_expansion": "Multiple candidates, same expansion (shared pool)",
        "ambiguous_same_set": "Multiple packs within same expansion — needs confirmation",
        "ambiguous_cross_set": "Candidates across multiple expansions — needs confirmation",
        "no_match": "Not found in pack_sources",
        "no_match_known_gap": "Common item not indexed in Limitless",
    }
    for status in ["exact_match", "unanimous_pack", "unanimous_expansion",
                   "ambiguous_same_set", "ambiguous_cross_set", "no_match", "no_match_known_gap"]:
        e = by_status.get(status, 0)
        q = by_status_qty.get(status, 0)
        lines.append(f"| `{status}` | {e} | {q} | {desc.get(status,'')} |")

    # EX card coverage
    ex_results = [r for r in results if r["is_ex"]]
    lines += ["", "## EX Card Coverage", "", "| Card | Count | Status | Confidence | Expansions |", "|---|---|---|---|---|"]
    for r in sorted(ex_results, key=lambda x: x["name"]):
        exps = ", ".join(r["unique_expansions"][:3]) or "—"
        lines.append(f"| {r['name']} | {r['count']} | `{r['match_status']}` | {r['match_confidence']} | {exps} |")

    # Trainer coverage by subtype
    trainer_results = [r for r in results if r["card_type"] == "Trainer"]
    lines += ["", "## Trainer Card Coverage", "", "| Card | Subtype | Count | Status | Pack/Expansion |", "|---|---|---|---|---|"]
    for r in sorted(trainer_results, key=lambda x: (x["trainer_subtype"], x["name"])):
        packs = ", ".join(r["unique_packs"][:2]) if r["unique_packs"] else "—"
        lines.append(f"| {r['name']} | {r['trainer_subtype']} | {r['count']} | `{r['match_status']}` | {packs} |")

    # Ambiguous cards
    amb = [r for r in results if r["match_status"] in ("ambiguous_same_set", "ambiguous_cross_set")]
    lines += [
        "", f"## Ambiguous Cards ({len(amb)} entries)", "",
        "These cards appear in multiple packs/expansions in pack_sources.",
        "Cannot assign a pack without knowing which specific version the user owns.",
        "", "| Card | Type | Count | Status | Expansions |", "|---|---|---|---|---|"
    ]
    for r in sorted(amb, key=lambda x: (x["match_status"], x["name"])):
        exps = ", ".join(r["unique_expansions"][:3]) or "—"
        lines.append(f"| {r['name']} | {r['type'] or r['trainer_subtype']} | {r['count']} | `{r['match_status']}` | {exps} |")

    # No-match cards
    nm = [r for r in results if r["match_status"] in ("no_match", "no_match_known_gap")]
    lines += [
        "", f"## No-Match Cards ({len(nm)} entries)", "",
        "| Card | Type | Count | Status | Notes |", "|---|---|---|---|---|"
    ]
    for r in sorted(nm, key=lambda x: x["name"]):
        note = "Common item — not in Limitless DB" if r["match_status"] == "no_match_known_gap" else "Not found in pack_sources"
        lines.append(f"| {r['name']} | {r['type'] or r['card_type']} | {r['count']} | `{r['match_status']}` | {note} |")

    # Priority resolution list
    priority = []
    for r in results:
        if r["match_status"] in ("ambiguous_cross_set", "ambiguous_same_set", "no_match"):
            prio = 1 if norm(r["name"]) in CHASE_TARGETS else 2 if r["is_ex"] else 3 if r["card_type"] == "Trainer" else 4
            priority.append((prio, r["count"], r["name"], r["match_status"], r["unique_expansions"]))

    priority.sort(key=lambda x: (x[0], -x[1]))

    lines += [
        "", "## Priority Cards for Pack EV Resolution", "",
        "Sorted by: (1) chase deck targets, (2) ex cards, (3) trainer staples, (4) other.",
        "", "| Priority | Card | Count | Status | Expansions |", "|---|---|---|---|---|"
    ]
    for prio, count, name, status, exps in priority[:30]:
        prio_label = {1: "🎯 Chase target", 2: "⭐ EX card", 3: "🃏 Trainer staple", 4: "—"}.get(prio, "—")
        lines.append(f"| {prio_label} | {name} | {count} | `{status}` | {', '.join(exps[:2]) or '—'} |")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_csv(results: list[dict], out_path: Path):
    fieldnames = [
        "entry_id", "name", "count", "type", "card_type", "stage", "hp", "is_ex",
        "attack", "variant", "trainer_subtype", "match_status", "match_confidence",
        "candidate_count", "unique_packs", "unique_expansions", "candidate_summary",
        "recommended_resolution",
    ]
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in results:
            row = dict(r)
            row["unique_packs"] = " | ".join(r["unique_packs"])
            row["unique_expansions"] = " | ".join(r["unique_expansions"])
            w.writerow(row)


def main():
    print(f"\n=== current_collection_pack_coverage.py ===")

    for p in (NORMALIZED_JSON, PACK_SOURCES_JSON):
        if not p.exists():
            print(f"ERROR: {p} not found", file=sys.stderr)
            sys.exit(1)

    norm_data = json.loads(NORMALIZED_JSON.read_text(encoding="utf-8"))
    entries = norm_data["collection"]
    meta_col = norm_data.get("meta", {})
    print(f"  Collection entries: {len(entries)}, total qty={sum(e['count'] for e in entries)}")

    ps_raw = json.loads(PACK_SOURCES_JSON.read_text(encoding="utf-8"))
    records = ps_raw["records"] if isinstance(ps_raw, dict) else ps_raw
    print(f"  Pack sources:       {len(records)} records")

    index, accent_index = build_ps_index(records)

    results = build_results(entries, index, accent_index)

    # Stats
    by_status = Counter(r["match_status"] for r in results)
    print(f"\n  Match results:")
    for status, count in sorted(by_status.items(), key=lambda x: -x[1]):
        print(f"    {status}: {count}")

    (ROOT / "data" / "current").mkdir(parents=True, exist_ok=True)
    (ROOT / "data" / "exports").mkdir(parents=True, exist_ok=True)
    (ROOT / "review").mkdir(exist_ok=True)

    ps_meta = {"total_cards": meta_col.get("total_cards"), "ps_records": len(records)}

    out_data = {
        "meta": ps_meta,
        "total_entries": len(results),
        "total_quantity": sum(r["count"] for r in results),
        "by_status": dict(by_status),
        "entries": results,
    }
    OUT_JSON.write_text(json.dumps(out_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n  Written: {OUT_JSON.relative_to(ROOT)}")

    write_csv(results, OUT_CSV)
    print(f"  Written: {OUT_CSV.relative_to(ROOT)}")

    write_md(results, ps_meta, OUT_MD)
    print(f"  Written: {OUT_MD.relative_to(ROOT)}")

    resolved = sum(1 for r in results if r["match_status"] in ("exact_match", "unanimous_pack", "unanimous_expansion"))
    total = len(results)
    print(f"\n  Coverage: {resolved}/{total} entries resolved ({100*resolved//total}%)")
    print(f"Done.")


if __name__ == "__main__":
    main()
