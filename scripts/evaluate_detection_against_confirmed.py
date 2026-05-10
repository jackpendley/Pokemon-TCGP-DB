#!/usr/bin/env python3
"""
Evaluate OCR/matching detection accuracy against confirmed batch ground truth.

Reads:   batches/cards_batch_*.json          (confirmed ground truth)
         data/extraction/match_candidates.json
Outputs: data/extraction/detection_validation_report.json
         detection_validation_report.md

Usage:
    python3 scripts/evaluate_detection_against_confirmed.py
"""

import glob
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BATCHES_GLOB = "batches/cards_batch_*.json"
MATCH_FILE = Path("data/extraction/match_candidates.json")
REPORT_JSON = Path("data/extraction/detection_validation_report.json")
REPORT_MD = Path("detection_validation_report.md")

# Score buckets to evaluate as threshold candidates
THRESHOLD_CANDIDATES = [70, 75, 80, 85, 90, 95]


def crop_id_from_entry(entry: dict) -> str:
    stem = entry["source_screenshot"].replace(".PNG", "").replace(".png", "")
    return f"{stem}_r{entry['source_row']}c{entry['source_column']}"


def names_match(confirmed: str, candidate: str) -> bool:
    if not confirmed or not candidate:
        return False
    return confirmed.strip().lower() == candidate.strip().lower()


def name_in_top(confirmed: str, top_matches: list) -> bool:
    norm = confirmed.strip().lower()
    return any(m.get("name", "").strip().lower() == norm for m in top_matches)


def main():
    batch_files = sorted(glob.glob(BATCHES_GLOB))
    if not batch_files:
        print("ERROR: No batch files found. Create at least one confirmed batch first.")
        sys.exit(1)

    if not MATCH_FILE.exists():
        print(f"ERROR: {MATCH_FILE} not found. Run match_ocr_to_reference.py first.")
        sys.exit(1)

    # --- Load confirmed ground truth ---
    confirmed: dict = {}   # crop_id → {card_name, screenshot, row, col}
    confirmed_by_screenshot: dict = {}
    for bf in batch_files:
        batch = json.loads(Path(bf).read_text(encoding="utf-8"))
        for entry in batch:
            cid = crop_id_from_entry(entry)
            confirmed[cid] = entry
            ss = entry["source_screenshot"]
            confirmed_by_screenshot.setdefault(ss, []).append((cid, entry))

    # --- Load match candidates ---
    mc_data = json.loads(MATCH_FILE.read_text(encoding="utf-8"))
    candidates_by_id = {c["crop_id"]: c for c in mc_data.get("candidates", [])}

    total = len(confirmed)
    top1_correct = 0
    top3_correct = 0
    ocr_empty_count = 0
    scores_correct = []
    scores_incorrect = []
    no_candidate = []
    per_screenshot: dict = {}

    per_crop_results = []

    for cid, entry in confirmed.items():
        ss = entry["source_screenshot"]
        confirmed_name = entry["card_name"]
        candidate = candidates_by_id.get(cid)

        per_screenshot.setdefault(ss, {"total": 0, "top1": 0, "top3": 0, "empty": 0})
        per_screenshot[ss]["total"] += 1

        if candidate is None:
            no_candidate.append(cid)
            per_crop_results.append({
                "crop_id": cid, "confirmed_name": confirmed_name,
                "suggested": None, "top1_correct": False, "top3_correct": False,
                "top1_score": 0, "ocr_empty": True, "note": "no candidate record",
            })
            continue

        top_matches = candidate.get("top_matches", [])
        suggested = candidate.get("suggested_card_name")
        top1_score = top_matches[0]["score"] if top_matches else 0
        ocr_empty = not candidate.get("title_guess", "").strip()

        if ocr_empty:
            ocr_empty_count += 1
            per_screenshot[ss]["empty"] += 1

        t1 = names_match(confirmed_name, suggested)
        t3 = name_in_top(confirmed_name, top_matches)

        if t1:
            top1_correct += 1
            per_screenshot[ss]["top1"] += 1
            scores_correct.append(top1_score)
        else:
            if not ocr_empty:
                scores_incorrect.append(top1_score)

        if t3:
            top3_correct += 1
            per_screenshot[ss]["top3"] += 1

        per_crop_results.append({
            "crop_id": cid,
            "confirmed_name": confirmed_name,
            "suggested": suggested,
            "top1_correct": t1,
            "top3_correct": t3,
            "top1_score": round(top1_score, 1),
            "ocr_empty": ocr_empty,
            "top_matches": top_matches,
        })

    # --- Threshold analysis ---
    threshold_analysis = []
    for t in THRESHOLD_CANDIDATES:
        tp = fp = tn = fn = 0
        for cid, entry in confirmed.items():
            candidate = candidates_by_id.get(cid)
            if candidate is None:
                fn += 1
                continue
            top_matches = candidate.get("top_matches", [])
            top_score = top_matches[0]["score"] if top_matches else 0
            suggested = candidate.get("suggested_card_name")
            predicted_name = top_matches[0]["name"] if top_score >= t and top_matches else None
            is_correct = names_match(entry["card_name"], predicted_name)
            if predicted_name and is_correct:
                tp += 1
            elif predicted_name and not is_correct:
                fp += 1
            elif not predicted_name and names_match(entry["card_name"], None):
                tn += 1
            else:
                fn += 1
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        threshold_analysis.append({
            "threshold": t, "tp": tp, "fp": fp, "fn": fn,
            "precision": round(precision, 3), "recall": round(recall, 3),
        })

    avg_score_correct = round(sum(scores_correct) / len(scores_correct), 1) if scores_correct else 0
    avg_score_incorrect = round(sum(scores_incorrect) / len(scores_incorrect), 1) if scores_incorrect else 0

    top1_acc = round(top1_correct / total, 3) if total else 0
    top3_acc = round(top3_correct / total, 3) if total else 0
    ocr_empty_rate = round(ocr_empty_count / total, 3) if total else 0

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "confirmed_screenshots": sorted(confirmed_by_screenshot.keys()),
        "summary": {
            "total_confirmed_positions": total,
            "top1_correct": top1_correct,
            "top1_accuracy": top1_acc,
            "top3_correct": top3_correct,
            "top3_accuracy": top3_acc,
            "ocr_empty_count": ocr_empty_count,
            "ocr_empty_rate": ocr_empty_rate,
            "avg_score_when_correct": avg_score_correct,
            "avg_score_when_incorrect": avg_score_incorrect,
        },
        "threshold_analysis": threshold_analysis,
        "per_screenshot": {
            ss: {
                "total": v["total"],
                "top1_correct": v["top1"],
                "top1_accuracy": round(v["top1"] / v["total"], 3) if v["total"] else 0,
                "top3_correct": v["top3"],
                "top3_accuracy": round(v["top3"] / v["total"], 3) if v["total"] else 0,
                "ocr_empty": v["empty"],
            }
            for ss, v in sorted(per_screenshot.items())
        },
        "per_crop": per_crop_results,
    }

    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    # --- Markdown report ---
    lines = [
        "# Detection Validation Report",
        "",
        f"Generated: {report['generated_at'][:19]}Z",
        f"Confirmed screenshots: {', '.join(report['confirmed_screenshots'])}",
        "",
        "## Summary",
        "",
        f"| Metric | Value |",
        f"|---|---|",
        f"| Confirmed positions | {total} |",
        f"| Top-1 accuracy | {top1_acc:.1%} ({top1_correct}/{total}) |",
        f"| Top-3 accuracy | {top3_acc:.1%} ({top3_correct}/{total}) |",
        f"| OCR empty rate | {ocr_empty_rate:.1%} ({ocr_empty_count}/{total}) |",
        f"| Avg score (correct) | {avg_score_correct} |",
        f"| Avg score (incorrect) | {avg_score_incorrect} |",
        "",
        "## Threshold Analysis",
        "",
        "| Threshold | TP | FP | FN | Precision | Recall |",
        "|---|---|---|---|---|---|",
    ]
    for ta in threshold_analysis:
        lines.append(
            f"| {ta['threshold']} | {ta['tp']} | {ta['fp']} | {ta['fn']} "
            f"| {ta['precision']:.1%} | {ta['recall']:.1%} |"
        )
    lines += ["", "## Per-Screenshot Accuracy", ""]
    lines += ["| Screenshot | Total | Top-1 | Top-3 | OCR Empty |", "|---|---|---|---|---|"]
    for ss, v in sorted(report["per_screenshot"].items()):
        lines.append(
            f"| {ss} | {v['total']} | {v['top1_correct']} ({v['top1_accuracy']:.0%}) "
            f"| {v['top3_correct']} ({v['top3_accuracy']:.0%}) | {v['ocr_empty']} |"
        )

    lines += ["", "## Per-Crop Results", ""]
    lines += ["| Crop ID | Confirmed | Suggested | Top-1 ✓ | Top-3 ✓ | Score |", "|---|---|---|---|---|---|"]
    for r in per_crop_results:
        t1 = "✓" if r["top1_correct"] else "✗"
        t3 = "✓" if r["top3_correct"] else "✗"
        lines.append(
            f"| {r['crop_id']} | {r['confirmed_name']} | {r['suggested'] or '—'} "
            f"| {t1} | {t3} | {r['top1_score']} |"
        )

    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(f"Confirmed positions : {total}")
    print(f"Top-1 accuracy      : {top1_acc:.1%} ({top1_correct}/{total})")
    print(f"Top-3 accuracy      : {top3_acc:.1%} ({top3_correct}/{total})")
    print(f"OCR empty rate      : {ocr_empty_rate:.1%} ({ocr_empty_count}/{total})")
    print(f"Avg score (correct) : {avg_score_correct}")
    print(f"Avg score (incorrect): {avg_score_incorrect}")
    print(f"JSON → {REPORT_JSON}")
    print(f"MD   → {REPORT_MD}")


if __name__ == "__main__":
    main()
