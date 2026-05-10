#!/usr/bin/env python3
"""
Evaluate how well the card reference covers confirmed batch card names.

Reads:
    batches/cards_batch_*.json                       (confirmed ground truth)
    data/reference/card_reference.json               (main reference)
    data/reference/external/external_card_reference.json  (Limitless, if present)

Outputs:
    data/reference/reference_coverage_report.json
    reference_coverage_report.md

Usage:
    python3 scripts/evaluate_reference_coverage.py
"""

import glob
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from rapidfuzz import process as rfprocess, fuzz
except ImportError:
    print("ERROR: rapidfuzz required.  Install: python3 -m pip install rapidfuzz")
    sys.exit(1)

BATCHES_GLOB = "batches/cards_batch_[0-9][0-9][0-9].json"
MAIN_REF = Path("data/reference/card_reference.json")
EXT_REF = Path("data/reference/external/external_card_reference.json")
OUT_JSON = Path("data/reference/reference_coverage_report.json")
OUT_MD = Path("reference_coverage_report.md")

FUZZY_THRESHOLD = 85  # minimum score to count as "covered"


def normalize(name: str) -> str:
    n = name.lower()
    n = re.sub(r"[^a-z0-9 ]", " ", n)
    return re.sub(r"\s+", " ", n).strip()


def load_names(ref_file: Path) -> set[str]:
    if not ref_file.exists():
        return set()
    data = json.loads(ref_file.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        return set()
    names = set()
    for entry in data:
        n = entry.get("name") or entry.get("card_name") or ""
        if n:
            names.add(n.strip())
    return names


def load_external_by_name(ref_file: Path) -> dict[str, dict]:
    """Return dict normalized_name → card record (first match wins)."""
    if not ref_file.exists():
        return {}
    data = json.loads(ref_file.read_text(encoding="utf-8"))
    result: dict[str, dict] = {}
    for entry in data:
        n = entry.get("name", "").strip()
        if n:
            key = normalize(n)
            if key not in result:
                result[key] = entry
    return result


def fuzzy_covered(name: str, ref_names: list[str], threshold: int) -> tuple[bool, str, float]:
    """Check if `name` fuzzy-matches any name in ref_names above threshold."""
    if not ref_names:
        return False, "", 0.0
    result = rfprocess.extractOne(
        normalize(name), [normalize(n) for n in ref_names],
        scorer=fuzz.token_sort_ratio
    )
    if result and result[1] >= threshold:
        idx = result[2]
        return True, ref_names[idx], float(result[1])
    return False, "", 0.0


def main() -> None:
    batch_files = sorted(glob.glob(BATCHES_GLOB))
    if not batch_files:
        print("No batch files found.")
        sys.exit(1)

    # Confirmed cards
    confirmed: list[dict] = []
    for bf in batch_files:
        for entry in json.loads(Path(bf).read_text(encoding="utf-8")):
            confirmed.append(entry)

    confirmed_names = sorted({c["card_name"].strip() for c in confirmed if c.get("card_name")})
    confirmed_ex = {c["card_name"].strip() for c in confirmed if c.get("is_ex")}
    confirmed_trainer = {
        c["card_name"].strip() for c in confirmed
        if c.get("card_category") in ("Item", "Supporter", "Stadium", "Tool", "Trainer")
    }
    confirmed_mega = {
        name for name in confirmed_names
        if re.match(r"^mega\s", name, re.I)
    }

    # Reference name lists
    main_names = sorted(load_names(MAIN_REF))
    ext_names = sorted(load_names(EXT_REF))
    ext_by_norm = load_external_by_name(EXT_REF)
    all_ref_names = sorted(set(main_names) | set(ext_names))

    # Per-name coverage analysis
    rows = []
    for name in confirmed_names:
        main_hit, main_match, main_score = fuzzy_covered(name, main_names, FUZZY_THRESHOLD)
        ext_hit, ext_match, ext_score = fuzzy_covered(name, ext_names, FUZZY_THRESHOLD)
        combined_hit, combined_match, combined_score = fuzzy_covered(name, all_ref_names, FUZZY_THRESHOLD)

        ext_record = ext_by_norm.get(normalize(name), {})
        ext_is_ex = ext_record.get("is_ex")
        ext_category = ext_record.get("card_category")

        rows.append({
            "name": name,
            "main_covered": main_hit,
            "main_match": main_match,
            "main_score": round(main_score, 1),
            "ext_covered": ext_hit,
            "ext_match": ext_match,
            "ext_score": round(ext_score, 1),
            "combined_covered": combined_hit,
            "ext_is_ex": ext_is_ex,
            "ext_category": ext_category,
            "is_ex_confirmed": name in confirmed_ex,
            "is_trainer_confirmed": name in confirmed_trainer,
            "is_mega": bool(re.match(r"^mega\s", name, re.I)),
        })

    # Aggregates
    total = len(confirmed_names)
    main_covered_count = sum(1 for r in rows if r["main_covered"])
    ext_covered_count = sum(1 for r in rows if r["ext_covered"])
    combined_covered_count = sum(1 for r in rows if r["combined_covered"])
    missing = [r["name"] for r in rows if not r["combined_covered"]]

    ex_total = len(confirmed_ex)
    ex_main = sum(1 for r in rows if r["is_ex_confirmed"] and r["main_covered"])
    ex_ext = sum(1 for r in rows if r["is_ex_confirmed"] and r["ext_covered"])

    trainer_total = len(confirmed_trainer)
    trainer_main = sum(1 for r in rows if r["is_trainer_confirmed"] and r["main_covered"])
    trainer_ext = sum(1 for r in rows if r["is_trainer_confirmed"] and r["ext_covered"])

    mega_total = sum(1 for r in rows if r["is_mega"])
    mega_ext = sum(1 for r in rows if r["is_mega"] and r["ext_covered"])

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "fuzzy_threshold": FUZZY_THRESHOLD,
        "confirmed_names": total,
        "confirmed_positions": len(confirmed),
        "main_ref_size": len(main_names),
        "ext_ref_size": len(ext_names),
        "combined_ref_size": len(all_ref_names),
        "main_covered": main_covered_count,
        "ext_covered": ext_covered_count,
        "combined_covered": combined_covered_count,
        "main_coverage_pct": round(main_covered_count / total * 100, 1) if total else 0,
        "ext_coverage_pct": round(ext_covered_count / total * 100, 1) if total else 0,
        "combined_coverage_pct": round(combined_covered_count / total * 100, 1) if total else 0,
        "missing_from_combined": missing,
        "ex_card_coverage": {
            "total": ex_total, "main": ex_main, "ext": ex_ext,
        },
        "trainer_coverage": {
            "total": trainer_total, "main": trainer_main, "ext": trainer_ext,
        },
        "mega_coverage": {
            "total": mega_total, "ext": mega_ext,
        },
        "per_name": rows,
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Reference Coverage Report",
        "",
        f"Generated: {report['generated_at'][:19]}Z",
        f"Fuzzy threshold: ≥ {FUZZY_THRESHOLD}",
        "",
        "## Reference Sizes",
        "",
        f"| Source | Cards |",
        f"|---|---|",
        f"| Main reference (`card_reference.json`) | {len(main_names)} |",
        f"| External reference (Limitless, partial) | {len(ext_names)} |",
        f"| Combined | {len(all_ref_names)} |",
        "",
        "## Coverage of Confirmed Card Names",
        "",
        f"| Metric | Count | % |",
        f"|---|---|---|",
        f"| Confirmed unique names | {total} | — |",
        f"| Covered by main ref | {main_covered_count} | {report['main_coverage_pct']}% |",
        f"| Covered by external ref | {ext_covered_count} | {report['ext_coverage_pct']}% |",
        f"| Covered by combined | {combined_covered_count} | {report['combined_coverage_pct']}% |",
        "",
        "## EX Card Coverage",
        "",
        f"| Metric | Count |",
        f"|---|---|",
        f"| Confirmed is_ex cards | {ex_total} |",
        f"| Covered by main ref | {ex_main} |",
        f"| Covered by external ref | {ex_ext} |",
        "",
        "## Trainer/Item/Supporter Coverage",
        "",
        f"| Metric | Count |",
        f"|---|---|",
        f"| Confirmed trainer-type | {trainer_total} |",
        f"| Covered by main ref | {trainer_main} |",
        f"| Covered by external ref | {trainer_ext} |",
        "",
        "## Mega Card Coverage",
        "",
        f"| Confirmed Mega cards | {mega_total} |",
        f"|---|---|",
        f"| Covered by external ref | {mega_ext} |",
        "",
    ]

    if missing:
        lines += [
            "## Missing from Combined Reference",
            "",
            "These confirmed card names are not covered at the fuzzy threshold:",
            "",
        ]
        for m in sorted(missing):
            lines.append(f"- `{m}`")
        lines.append("")

    lines += [
        "## Per-Name Details",
        "",
        "| Name | Main | Ext | Ext is_ex | Ext category |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        m_ok = "✓" if r["main_covered"] else "✗"
        e_ok = "✓" if r["ext_covered"] else "✗"
        ex_hint = str(r["ext_is_ex"]) if r["ext_is_ex"] is not None else "—"
        cat_hint = r["ext_category"] or "—"
        lines.append(f"| {r['name']} | {m_ok} | {e_ok} | {ex_hint} | {cat_hint} |")

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Confirmed unique names : {total}")
    print(f"Main reference size    : {len(main_names)}")
    print(f"External ref size      : {len(ext_names)}")
    print(f"Main coverage          : {main_covered_count}/{total} ({report['main_coverage_pct']}%)")
    print(f"External coverage      : {ext_covered_count}/{total} ({report['ext_coverage_pct']}%)")
    print(f"Combined coverage      : {combined_covered_count}/{total} ({report['combined_coverage_pct']}%)")
    if missing:
        print(f"Missing from combined  : {', '.join(missing)}")
    print(f"JSON → {OUT_JSON}")
    print(f"MD   → {OUT_MD}")


if __name__ == "__main__":
    main()
