#!/usr/bin/env python3
"""
Compares cards.json against pack_sources.json to report pack source coverage.

Matching strategy (in priority order):
    1. Exact match by set_code + card_number  (high confidence — from metadata enrichment)
    2. User-confirmed match by source_set_code + source_card_number  (high confidence — from manual review)
    3. Name-only match with unanimous pack_name  (medium confidence — documented)
    4. Name-only match with disagreeing pack_names  (ambiguous)
    5. No match  (unresolved)

Outputs:
    review/owned_pack_coverage.md
    data/exports/owned_pack_coverage.json

Usage:
    python3 scripts/owned_pack_coverage.py
"""

import json
import re
import sys
from collections import defaultdict, Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CARDS_JSON = ROOT / "cards.json"
PACK_SOURCES_JSON = ROOT / "data" / "reference" / "pack_sources.json"
REPORT_MD = ROOT / "review" / "owned_pack_coverage.md"
REPORT_JSON = ROOT / "data" / "exports" / "owned_pack_coverage.json"

DEFERRED_NOTE = (
    "Pack-opening recommendations are intentionally deferred. "
    "This report is coverage analysis only."
)


def norm_name(s):
    s = str(s or "").strip().lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def load_cards():
    if not CARDS_JSON.exists():
        print(f"ERROR cards.json not found", file=sys.stderr)
        sys.exit(1)
    return json.loads(CARDS_JSON.read_text(encoding="utf-8"))


def load_pack_sources():
    if not PACK_SOURCES_JSON.exists():
        print("ERROR pack_sources.json not found. Run: python3 scripts/build_pack_sources.py", file=sys.stderr)
        sys.exit(1)
    raw = json.loads(PACK_SOURCES_JSON.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return raw
    elif isinstance(raw, dict) and "records" in raw:
        return raw["records"]
    else:
        print("ERROR pack_sources.json has unexpected structure", file=sys.stderr)
        sys.exit(1)


def build_indexes(records):
    by_key = {}
    by_name = defaultdict(list)
    for r in records:
        key = (r.get("set_code"), r.get("card_number"))
        if key[0] and key[1] is not None:
            by_key[key] = r
        n = norm_name(r.get("card_name", ""))
        if n:
            by_name[n].append(r)
    return by_key, by_name


def classify_card(card, by_key, by_name):
    """
    Returns (outcome, pack_info_list, match_confidence, notes)
    outcome: 'exact' | 'name_agree' | 'name_ambiguous' | 'no_match'
    """
    # Priority 1: enrichment-phase exact match
    key = (card.get("set_code"), card.get("card_number"))
    if key[0] and key[1] is not None and key in by_key:
        r = by_key[key]
        return "exact", [r], "high", f"Matched by set_code={key[0]} card_number={key[1]}"

    # Priority 2: user-confirmed match (apply_ambiguous_confirmations.py)
    if card.get("source_pack_confidence") == "user_confirmed":
        src_key = (card.get("source_set_code"), None)
        # Extract card number from source_pack_notes "Manually confirmed by user: SC/CN"
        notes_str = card.get("source_pack_notes", "")
        import re as _re
        m = _re.search(r"/(\d+)$", notes_str)
        src_cn = int(m.group(1)) if m else None
        src_key = (card.get("source_set_code"), src_cn)
        if src_key[0] and src_key[1] is not None and src_key in by_key:
            r = by_key[src_key]
            return "exact", [r], "high", (
                f"User-confirmed: source_set_code={src_key[0]} card_number={src_key[1]}"
            )
        # Fallback if key not found: treat as exact using stored source_packs
        sp = card.get("source_packs")
        se = card.get("source_expansion")
        if sp is not None:
            pack_name = sp[0] if sp else None
            synthetic = {
                "set_code": card.get("source_set_code", ""),
                "card_number": src_cn,
                "card_name": card.get("card_name", ""),
                "pack_name": pack_name,
                "expansion": se or "",
                "confidence": "user_confirmed",
            }
            return "exact", [synthetic], "high", (
                f"User-confirmed: source_set_code={card.get('source_set_code')} (card_number not in index)"
            )

    name = norm_name(card.get("card_name", ""))
    matches = by_name.get(name, [])

    if not matches:
        return "no_match", [], "low", "No match in pack_sources by name"

    packs = set(m.get("pack_name") for m in matches)
    sets = set(m.get("set_code") for m in matches)
    expansions = set(m.get("expansion") for m in matches)

    if len(packs) == 1:
        return "name_agree", matches, "medium", (
            f"Name match across {len(matches)} records in set(s) {sorted(sets)}; "
            f"all agree on pack_name={list(packs)[0]!r}"
        )
    else:
        return "name_ambiguous", matches, "low", (
            f"Name match across {len(matches)} records in set(s) {sorted(sets)}; "
            f"pack disagrees: {sorted(str(p) for p in packs)}"
        )


def analyze(cards, by_key, by_name):
    results = []
    for card in cards:
        outcome, matches, conf, notes = classify_card(card, by_key, by_name)
        pack_names = sorted(set(m.get("pack_name") for m in matches), key=lambda x: (x is None, x))
        expansions = sorted(set(m.get("expansion") for m in matches), key=lambda x: (x is None, x))
        set_codes = sorted(set(m.get("set_code") for m in matches), key=lambda x: (x is None, x))
        results.append({
            "card_name": card.get("card_name"),
            "quantity": card.get("quantity"),
            "owned_set_code": card.get("set_code"),
            "owned_card_number": card.get("card_number"),
            "outcome": outcome,
            "match_confidence": conf,
            "pack_names": pack_names,
            "expansions": expansions,
            "set_codes": set_codes,
            "notes": notes,
            "source_screenshot": card.get("source_screenshot"),
        })
    return results


def summarize(results, cards):
    total_entries = len(cards)
    total_qty = sum(c.get("quantity", 0) for c in cards if isinstance(c.get("quantity"), int))

    by_outcome = Counter(r["outcome"] for r in results)
    exact = by_outcome["exact"]
    name_agree = by_outcome["name_agree"]
    ambiguous = by_outcome["name_ambiguous"]
    no_match = by_outcome["no_match"]

    resolved = exact
    partially_resolved = name_agree
    unresolved = ambiguous + no_match

    coverage_pct = round(100 * resolved / total_entries, 1) if total_entries else 0
    partial_pct = round(100 * (resolved + partially_resolved) / total_entries, 1) if total_entries else 0

    # By set_code (exact matches)
    by_set = Counter()
    for r in results:
        if r["outcome"] == "exact":
            sc = r.get("owned_set_code") or "unknown"
            by_set[sc] += 1

    # By pack_name (exact matches only)
    by_pack = Counter()
    for r in results:
        if r["outcome"] == "exact":
            for pn in r["pack_names"]:
                by_pack[str(pn)] += 1

    return {
        "total_entries": total_entries,
        "total_quantity": total_qty,
        "exact_match": exact,
        "name_agree_match": name_agree,
        "name_ambiguous": ambiguous,
        "no_match": no_match,
        "resolved_entries": resolved,
        "partially_resolved_entries": partially_resolved,
        "unresolved_entries": unresolved,
        "exact_coverage_pct": coverage_pct,
        "broad_coverage_pct": partial_pct,
        "by_set_code_exact": dict(by_set.most_common()),
        "by_pack_name_exact": dict(by_pack.most_common()),
    }


def write_markdown(now, summary, results):
    exact_results = [r for r in results if r["outcome"] == "exact"]
    agree_results = [r for r in results if r["outcome"] == "name_agree"]
    ambig_results = [r for r in results if r["outcome"] == "name_ambiguous"]
    no_match_results = [r for r in results if r["outcome"] == "no_match"]

    lines = [
        "# Owned Pack Coverage Report",
        "",
        f"Generated: {now}",
        "",
        f"> **{DEFERRED_NOTE}**",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Total owned entries | {summary['total_entries']} |",
        f"| Total owned quantity | {summary['total_quantity']} |",
        f"| Exact pack match (set+number) | {summary['exact_match']} |",
        f"| Name-only match, pack agreed | {summary['name_agree_match']} |",
        f"| Name-only match, pack ambiguous | {summary['name_ambiguous']} |",
        f"| No match in pack_sources | {summary['no_match']} |",
        f"| Exact coverage % | {summary['exact_coverage_pct']}% |",
        f"| Broad coverage % (exact + agreed) | {summary['broad_coverage_pct']}% |",
        "",
        "## Notes on Matching",
        "",
        "- **Exact match**: card has `set_code` + `card_number` from metadata enrichment phase; "
        "matched directly to pack_sources record.",
        "- **Name agree**: no set_code/card_number in owned data; matched by card name only; "
        "all name matches agree on the same pack_name. Useful but not authoritative.",
        "- **Ambiguous**: name matches multiple records with different pack_names. "
        "Cannot determine which specific set/pack without set_code + card_number.",
        "- **No match**: card name not found in pack_sources at all. "
        "May be a trainer/promo card not in our reference, or a name variant.",
        "",
        "## Coverage by Set Code (Exact Matches)",
        "",
        "| Set Code | Owned Cards Resolved |",
        "|---|---|",
    ]
    for sc, cnt in sorted(summary["by_set_code_exact"].items()):
        lines.append(f"| {sc} | {cnt} |")
    lines.append("")

    lines += [
        "## Coverage by Pack Name (Exact Matches)",
        "",
        "| Pack Name | Owned Cards |",
        "|---|---|",
    ]
    for pn, cnt in sorted(summary["by_pack_name_exact"].items(), key=lambda x: -x[1]):
        lines.append(f"| {pn} | {cnt} |")
    lines.append("")

    if agree_results:
        lines += [
            "## Name-Agreed Pack Assignments (Medium Confidence, up to 30)",
            "",
            "_These cards have a unique pack assignment from name matching, but not confirmed by set_code+card_number._",
            "",
            "| Card Name | Qty | Pack(s) | Expansion(s) |",
            "|---|---|---|---|",
        ]
        for r in agree_results[:30]:
            packs = ", ".join(str(p) for p in r["pack_names"])
            exps = ", ".join(r["expansions"])
            lines.append(f"| {r['card_name']} | {r['quantity']} | {packs} | {exps} |")
        if len(agree_results) > 30:
            lines.append(f"\n_...and {len(agree_results) - 30} more_")
        lines.append("")

    if ambig_results:
        lines += [
            "## Ambiguous Pack Assignments (up to 30)",
            "",
            "_These cards match multiple records in pack_sources with different pack names. "
            "Cannot resolve without set_code + card_number._",
            "",
            "| Card Name | Qty | Possible Packs | Sets |",
            "|---|---|---|---|",
        ]
        for r in ambig_results[:30]:
            packs = ", ".join(str(p) for p in r["pack_names"])
            sets = ", ".join(r["set_codes"])
            lines.append(f"| {r['card_name']} | {r['quantity']} | {packs} | {sets} |")
        if len(ambig_results) > 30:
            lines.append(f"\n_...and {len(ambig_results) - 30} more_")
        lines.append("")

    if no_match_results:
        lines += [
            "## Unresolved Cards (No Match in pack_sources, up to 30)",
            "",
            "| Card Name | Qty | Screenshot |",
            "|---|---|---|",
        ]
        for r in no_match_results[:30]:
            lines.append(f"| {r['card_name']} | {r['quantity']} | {r['source_screenshot']} |")
        if len(no_match_results) > 30:
            lines.append(f"\n_...and {len(no_match_results) - 30} more_")
        lines.append("")

    lines += [
        "## Why Pack Recommendations Are Still Deferred",
        "",
        f"- **{summary['unresolved_entries']} owned cards** have no definitive pack assignment.",
        "- `set_or_pack` is still unknown for all 211 owned cards in cards.json.",
        "- Pack pull probability tables are not yet modeled.",
        "- Current meta tier list data is not integrated.",
        "",
        "Next step: resolve set_code + card_number for the remaining owned cards "
        "to improve exact match coverage, then build recommendation engine.",
        "",
        "---",
        "",
        f"> **Reminder:** {DEFERRED_NOTE}",
        "",
    ]

    return "\n".join(lines) + "\n"


def main():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    cards = load_cards()
    ps_records = load_pack_sources()

    print(f"Loaded {len(cards)} owned cards, {len(ps_records)} pack source records")

    by_key, by_name = build_indexes(ps_records)
    results = analyze(cards, by_key, by_name)
    summary = summarize(results, cards)

    md_text = write_markdown(now, summary, results)
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text(md_text, encoding="utf-8")

    output = {
        "generated_at": now,
        "deferred_note": DEFERRED_NOTE,
        "summary": summary,
        "detail": results,
    }
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n=== Coverage Summary ===")
    print(f"  Exact match:           {summary['exact_match']} / {summary['total_entries']} ({summary['exact_coverage_pct']}%)")
    print(f"  Name agree (medium):   {summary['name_agree_match']}")
    print(f"  Ambiguous:             {summary['name_ambiguous']}")
    print(f"  No match:              {summary['no_match']}")
    print(f"  Broad coverage:        {summary['broad_coverage_pct']}%")
    print(f"\nWritten: {REPORT_MD}")
    print(f"Written: {REPORT_JSON}")


if __name__ == "__main__":
    main()
