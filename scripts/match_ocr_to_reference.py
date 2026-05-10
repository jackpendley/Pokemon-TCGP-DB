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
CONFIRMED_NAMES_FILE = Path("data/reference/confirmed_card_names.txt")
OCR_FILE = Path("data/extraction/ocr_results.json")
OUT_FILE = Path("data/extraction/match_candidates.json")

# ---------------------------------------------------------------------------
# Matching config
# ---------------------------------------------------------------------------
DEFAULT_THRESHOLD = 80   # minimum score (0–100) to auto-suggest a card name
DEFAULT_TOP_N = 3        # number of candidate matches to include

# Confirmed lexicon tie-breaker: if a confirmed name scores within this many
# points of the top full-reference match, prefer the confirmed name.
LEXICON_BOOST_WINDOW = 5


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

    # Load confirmed lexicon if available (used as tie-breaker only)
    confirmed_name_set: set = set()
    if CONFIRMED_NAMES_FILE.exists():
        confirmed_name_set = {
            line.strip() for line in CONFIRMED_NAMES_FILE.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        print(f"  Loaded {len(confirmed_name_set)} names from confirmed lexicon ({CONFIRMED_NAMES_FILE})")

    ocr_data = json.loads(OCR_FILE.read_text(encoding="utf-8"))
    ocr_results = ocr_data.get("results", [])

    def best_match_for_text(text: str) -> tuple:
        """Return (best_name, best_score, top_matches_list) for a text string."""
        norm = normalize(text)
        if not norm:
            return None, 0, []
        matches = rf_process.extract(
            norm,
            normalized_refs,
            scorer=rf_fuzz.token_sort_ratio,
            limit=args.top_n,
        )
        top = [
            {"name": reference_names[idx], "score": round(score, 1)}
            for _, score, idx in matches
        ]
        score = top[0]["score"] if top else 0
        name = top[0]["name"] if score >= args.threshold else None
        return name, score, top

    def apply_lexicon_boost(top_matches: list, threshold: int) -> tuple:
        """
        If a confirmed-lexicon name is within LEXICON_BOOST_WINDOW points of
        the top full-reference match, prefer it as a tie-breaker.
        Never overrides a match that is clearly better.
        Returns (boosted_name, boosted_score, match_source).
        """
        if not top_matches or not confirmed_name_set:
            top_score = top_matches[0]["score"] if top_matches else 0
            top_name = top_matches[0]["name"] if top_matches else None
            suggested = top_name if top_score >= threshold else None
            return suggested, top_score, "full_reference"

        top_score = top_matches[0]["score"]
        top_name = top_matches[0]["name"]

        # Check if any top match is from the confirmed lexicon
        confirmed_in_top = [
            m for m in top_matches if m["name"] in confirmed_name_set
        ]
        if not confirmed_in_top:
            suggested = top_name if top_score >= threshold else None
            return suggested, top_score, "full_reference"

        best_confirmed = confirmed_in_top[0]
        bc_score = best_confirmed["score"]
        bc_name = best_confirmed["name"]

        # Boost only if within the window and doesn't displace a clearly better match
        if bc_name == top_name:
            source = "both"
            suggested = top_name if top_score >= threshold else None
            return suggested, top_score, source

        if (top_score - bc_score) <= LEXICON_BOOST_WINDOW and bc_score >= threshold:
            # Tie-break: prefer confirmed name
            return bc_name, bc_score, "confirmed_lexicon"

        suggested = top_name if top_score >= threshold else None
        return suggested, top_score, "full_reference"

    candidates = []
    for item in ocr_results:
        crop_id = item["crop_id"]
        raw_joined = item.get("cleaned_title_guess", "")
        ocr_lines = item.get("ocr_lines", [])

        # Try the full joined text AND each individual OCR line; take the best result.
        texts_to_try = [raw_joined] + ocr_lines
        best_name, best_score, best_top = None, 0, []
        best_source = ""
        for text in texts_to_try:
            if not text.strip():
                continue
            name, score, top = best_match_for_text(text)
            if score > best_score:
                best_name, best_score, best_top = name, score, top
                best_source = text

        if not texts_to_try or all(not t.strip() for t in texts_to_try):
            candidates.append({
                "crop_id": crop_id,
                "title_guess": raw_joined,
                "best_ocr_source": "",
                "top_matches": [],
                "suggested_card_name": None,
                "match_source": "none",
                "needs_review": True,
                "reason": "OCR produced no text",
            })
            print(f"  {crop_id:30s}  (no OCR text)")
            continue

        # Apply confirmed lexicon tie-breaker
        final_name, final_score, match_source = apply_lexicon_boost(best_top, args.threshold)

        needs_review = final_score < args.threshold or final_name is None
        reason = f"Best match score {final_score:.0f} < threshold {args.threshold}" if needs_review else ""

        candidates.append({
            "crop_id": crop_id,
            "title_guess": raw_joined,
            "best_ocr_source": best_source,
            "top_matches": best_top,
            "suggested_card_name": final_name,
            "match_source": match_source,
            "needs_review": needs_review,
            "reason": reason,
        })

        status = (
            f"→ {final_name!r} ({final_score:.0f}) [{match_source}]"
            if final_name
            else f"needs_review (best {final_score:.0f})"
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
