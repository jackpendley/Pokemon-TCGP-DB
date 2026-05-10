#!/usr/bin/env python3
"""
Validate a user-confirmed CSV against the card name reference before batch generation.

Reads:
    data/reference/card_reference.json
    data/reference/external/external_card_reference.json  (if present)
    data/reference/confirmed_lexicon.json                  (if present)
    --input <csv>

Checks per row:
    - card_name present and non-blank
    - quantity is a non-negative integer
    - card_name matches reference (exact normalized, or fuzzy top-5 suggestions)
    - is_ex consistent with reference metadata where available
    - special_type=unknown does NOT cause failure

Exit codes:
    0  all rows PASS (warnings may still appear)
    1  one or more rows have hard errors (blank name, bad quantity, name not found)

Usage:
    python3 scripts/validate_confirmed_csv_against_reference.py \
        --input review/confirmed/IMG_1532_confirmed.csv
"""

import argparse
import csv
import json
import re
import sys
from pathlib import Path

try:
    from rapidfuzz import process as rfprocess, fuzz
except ImportError:
    print("ERROR: rapidfuzz required.  Install: python3 -m pip install rapidfuzz")
    sys.exit(1)

MAIN_REF  = Path("data/reference/card_reference.json")
EXT_REF   = Path("data/reference/external/external_card_reference.json")
LEXICON   = Path("data/reference/confirmed_lexicon.json")

FUZZY_THRESHOLD   = 80   # minimum score to offer a suggestion
HIGH_QUALITY_MIN  = 85   # score at which we treat suggestion as "found" (warn, not error)
TOP_N_SUGGESTIONS = 5


def normalize(name: str) -> str:
    n = name.lower()
    n = re.sub(r"[^a-z0-9 ]", " ", n)
    return re.sub(r"\s+", " ", n).strip()


def load_names(path: Path) -> list[str]:
    """Return list of card names from a standard reference JSON (list of dicts with 'name')."""
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return []
    names = []
    for entry in (data if isinstance(data, list) else []):
        n = (entry.get("name") or entry.get("card_name") or "").strip()
        if n:
            names.append(n)
    return names


def load_lexicon_names(path: Path) -> list[str]:
    """Return confirmed card names from the lexicon JSON."""
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return []
    return [e["card_name"] for e in data.get("entries", []) if e.get("card_name")]


def load_ext_by_norm(path: Path) -> dict[str, dict]:
    """Return normalized_name → ext record (first occurrence wins)."""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}
    result: dict[str, dict] = {}
    for entry in (data if isinstance(data, list) else []):
        n = entry.get("name", "").strip()
        if n:
            key = normalize(n)
            if key not in result:
                result[key] = entry
    return result


def fuzzy_match(query: str, names: list[str], threshold: int, top_n: int
                ) -> list[tuple[str, float]]:
    """Return list of (name, score) tuples above threshold, sorted by score desc."""
    if not names:
        return []
    norm_query = normalize(query)
    norm_names = [normalize(n) for n in names]
    results = rfprocess.extract(
        norm_query, norm_names, scorer=fuzz.token_sort_ratio, limit=top_n
    )
    out = []
    for raw_match, score, idx in results:
        if score >= threshold:
            out.append((names[idx], float(score)))
    return sorted(out, key=lambda x: -x[1])


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate a confirmed CSV against the card name reference."
    )
    parser.add_argument("--input", required=True, help="Path to confirmed CSV")
    args = parser.parse_args()

    csv_path = Path(args.input)
    if not csv_path.exists():
        print(f"ERROR: input file not found: {csv_path}")
        sys.exit(1)

    # Build merged reference name list
    main_names  = load_names(MAIN_REF)
    ext_names   = load_names(EXT_REF)
    lex_names   = load_lexicon_names(LEXICON)

    all_ref_names = list({n for n in main_names + ext_names + lex_names})
    all_norm_set  = {normalize(n) for n in all_ref_names}
    lex_norm_set  = {normalize(n) for n in lex_names}

    ext_by_norm = load_ext_by_norm(EXT_REF)

    print(f"Reference loaded: {len(main_names)} main + {len(ext_names)} external + {len(lex_names)} lexicon = {len(all_ref_names)} total")
    print(f"Input: {csv_path}")
    print()

    with csv_path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            print("ERROR: CSV appears empty or has no header.")
            sys.exit(1)
        required = {"screenshot", "row", "column", "card_name", "quantity", "special_type", "is_ex"}
        missing_cols = required - set(reader.fieldnames)
        if missing_cols:
            print(f"ERROR: CSV missing columns: {missing_cols}")
            sys.exit(1)
        rows = list(reader)

    hard_errors = 0
    warnings = 0

    for i, row in enumerate(rows, start=1):
        pos       = f"r{row.get('row','?')}c{row.get('column','?')}"
        card_name = row.get("card_name", "").strip()
        qty_raw   = row.get("quantity",  "").strip()
        is_ex_raw = row.get("is_ex",     "").strip().lower()
        stype     = row.get("special_type", "").strip()

        status_parts: list[str] = []
        row_errors  = 0
        row_warnings = 0

        # --- card_name check ---
        if not card_name:
            status_parts.append("ERROR: card_name is blank")
            hard_errors += 1
            row_errors += 1
        else:
            norm_name = normalize(card_name)
            if norm_name in all_norm_set:
                # Exact normalized match
                match_label = "PASS (exact)"
                if norm_name in lex_norm_set:
                    match_label = "PASS (confirmed lexicon)"
                status_parts.append(match_label)

                # is_ex consistency check against external reference
                ext_rec = ext_by_norm.get(norm_name, {})
                ext_is_ex = ext_rec.get("is_ex")
                if ext_is_ex is not None:
                    csv_is_ex = is_ex_raw in ("true", "1", "yes")
                    csv_is_ex_false = is_ex_raw in ("false", "0", "no", "")
                    if ext_is_ex is True and csv_is_ex_false and is_ex_raw != "":
                        status_parts.append(f"WARN: ref says is_ex=true but CSV says '{is_ex_raw}'")
                        row_warnings += 1
                    elif ext_is_ex is False and csv_is_ex and is_ex_raw != "":
                        status_parts.append(f"WARN: ref says is_ex=false but CSV says '{is_ex_raw}'")
                        row_warnings += 1
            else:
                # Fuzzy search
                suggestions = fuzzy_match(card_name, all_ref_names, FUZZY_THRESHOLD, TOP_N_SUGGESTIONS)
                top_score = suggestions[0][1] if suggestions else 0.0

                if top_score >= HIGH_QUALITY_MIN:
                    top_names = ", ".join(f"{n} ({s:.0f})" for n, s in suggestions[:3])
                    status_parts.append(f"WARN: no exact match — did you mean: {top_names}")
                    row_warnings += 1
                elif suggestions:
                    top_names = ", ".join(f"{n} ({s:.0f})" for n, s in suggestions)
                    status_parts.append(f"ERROR: name not found — low-quality suggestions: {top_names}")
                    hard_errors += 1
                    row_errors += 1
                else:
                    status_parts.append(f"ERROR: name not found — no fuzzy suggestions above {FUZZY_THRESHOLD}")
                    hard_errors += 1
                    row_errors += 1

        # --- quantity check ---
        if not qty_raw:
            status_parts.append("WARN: quantity is blank (fill before batch generation)")
            row_warnings += 1
        else:
            try:
                qty = int(qty_raw)
                if qty < 0:
                    status_parts.append(f"ERROR: quantity must be non-negative, got {qty}")
                    hard_errors += 1
                    row_errors += 1
            except ValueError:
                status_parts.append(f"ERROR: quantity must be an integer, got '{qty_raw}'")
                hard_errors += 1
                row_errors += 1

        # --- special_type note (never a failure) ---
        if stype == "unknown":
            status_parts.append("NOTE: special_type=unknown (ok, will set needs_review)")

        warnings += row_warnings

        # Format row output
        label = "ERROR" if row_errors else ("WARN " if row_warnings else "PASS ")
        print(f"  [{label}] {pos:6s}  {card_name or '(blank)'}")
        for part in status_parts:
            indent = "         "
            print(f"{indent}→ {part}")

    print()
    print(f"{'='*60}")
    print(f"Rows checked  : {len(rows)}")
    print(f"Hard errors   : {hard_errors}")
    print(f"Warnings      : {warnings}")
    if hard_errors:
        print("RESULT: FAIL — fix errors before running create_batch_from_confirmation.py")
        sys.exit(1)
    elif warnings:
        print("RESULT: PASS WITH WARNINGS — review warnings before batch generation")
    else:
        print("RESULT: PASS — all card names found in reference")


if __name__ == "__main__":
    main()
