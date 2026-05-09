#!/usr/bin/env python3
"""
Fuzzy-match OCR title guesses against the card reference name list.

Reads:   data/reference/card_names.txt
         data/extraction/ocr_results.json
Outputs: data/extraction/match_candidates.json

Usage:
    python3 scripts/match_ocr_to_reference.py [--threshold 80] [--top-n 3]
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from rapidfuzz import process as rf_process, fuzz as rf_fuzz
except ImportError:
    print("ERROR: rapidfuzz is required.  Install with:  python3 -m pip install rapidfuzz")
    sys.exit(1)

NAMES_FILE = Path("data/reference/card_names.txt")
OCR_FILE = Path("data/extraction/ocr_results.json")
OUT_FILE = Path("data/extraction/match_candidates.json")

# ---------------------------------------------------------------------------
# Matching config
# ---------------------------------------------------------------------------
DEFAULT_THRESHOLD = 80   # minimum score (0–100) to auto-suggest a card name
DEFAULT_TOP_N = 3        # number of candidate matches to include


def normalize(name: str) -> str:
    name = name.lower()
    name = re.sub(r"[^a-z0-9 ]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def main():
    parser = argparse.ArgumentParser(
        description="Fuzzy-match OCR text to PTCGP card name reference."
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=DEFAULT_THRESHOLD,
        help=f"Minimum match score to auto-suggest (default: {DEFAULT_THRESHOLD})",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=DEFAULT_TOP_N,
        help=f"Number of top matches to include per crop (default: {DEFAULT_TOP_N})",
    )
    args = parser.parse_args()

    for path, label in [(NAMES_FILE, "card_names.txt"), (OCR_FILE, "ocr_results.json")]:
        if not path.exists():
            print(f"ERROR: {label} not found at {path}.")
            if path == NAMES_FILE:
                print("  Run: python3 scripts/build_card_reference.py")
            else:
                print("  Run: python3 scripts/ocr_card_crops.py")
            sys.exit(1)

    reference_names = [
        line.strip() for line in NAMES_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not reference_names:
        print("ERROR: card_names.txt is empty.  Rebuild the reference first.")
        sys.exit(1)

    normalized_refs = [normalize(n) for n in reference_names]

    ocr_data = json.loads(OCR_FILE.read_text(encoding="utf-8"))
    ocr_results = ocr_data.get("results", [])

    candidates = []
    for item in ocr_results:
        crop_id = item["crop_id"]
        guess = item.get("cleaned_title_guess", "")
        norm_guess = normalize(guess)

        if not norm_guess:
            candidates.append({
                "crop_id": crop_id,
                "title_guess": guess,
                "top_matches": [],
                "suggested_card_name": None,
                "needs_review": True,
                "reason": "OCR produced no text",
            })
            print(f"  {crop_id:30s}  (no OCR text)")
            continue

        matches = rf_process.extract(
            norm_guess,
            normalized_refs,
            scorer=rf_fuzz.token_sort_ratio,
            limit=args.top_n,
        )

        top_matches = [
            {"name": reference_names[idx], "score": round(score, 1)}
            for _, score, idx in matches
        ]

        best_score = top_matches[0]["score"] if top_matches else 0
        best_name = top_matches[0]["name"] if best_score >= args.threshold else None
        needs_review = best_score < args.threshold

        reason = ""
        if needs_review:
            if not guess:
                reason = "OCR produced no text"
            elif best_score < args.threshold:
                reason = f"Best match score {best_score:.0f} < threshold {args.threshold}"

        candidates.append({
            "crop_id": crop_id,
            "title_guess": guess,
            "top_matches": top_matches,
            "suggested_card_name": best_name,
            "needs_review": needs_review,
            "reason": reason,
        })

        status = (
            f"→ {best_name!r} ({best_score:.0f})"
            if best_name
            else f"needs_review (best {best_score:.0f})"
        )
        print(f"  {crop_id:30s}  {status}")

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "threshold": args.threshold,
        "top_n": args.top_n,
        "total_crops": len(candidates),
        "auto_matched": sum(1 for c in candidates if not c["needs_review"]),
        "needs_review": sum(1 for c in candidates if c["needs_review"]),
        "candidates": candidates,
    }
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    print(
        f"\nMatch results: {output['auto_matched']} auto-matched, "
        f"{output['needs_review']} need review  →  {OUT_FILE}"
    )


if __name__ == "__main__":
    main()
