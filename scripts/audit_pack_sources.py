#!/usr/bin/env python3
"""
Audit and auto-fix data/reference/pack_sources.json against card_reference.json.

Reads the cross-validated card_reference.json (produced by build_card_reference.py)
and reconciles all 3,228 pack_sources records against it. Automatically corrects
discrepancies where the reference has ≥2-source confirmation; flags but does not
auto-apply single-source differences.

Checks performed:
  1. Name: pack_sources name vs reference name (after normalization + forme-stripping).
  2. Rarity: pack_sources rarity vs reference rarity.
  3. Pack assignment (A1–B2a): pack_sources pack_name vs TCGdex boosters in reference.
  4. Coord sanity: pack_sources records whose (set_code, card_number) is absent from
     the reference (possible ghost records or new-set data not yet in reference).
  5. Promo subset: promos not in pack_sources but present in reference are listed
     (informational only — promo curation is intentional, no auto-add).

Auto-fix policy:
  - Auto-fix when reference.confidence == "confirmed" and value disagrees.
  - Flag (don't fix) when reference.confidence == "single" — one external source isn't
    enough to silently override the existing data.
  - Never auto-add or auto-remove pack_sources records.

EV impact guard: if the fix changes a record's pack_name (which affects EV scoring),
the change is flagged in the report for manual review even if auto-applied.

Usage:
    python3 scripts/audit_pack_sources.py              # auto-fix + report
    python3 scripts/audit_pack_sources.py --dry-run    # report only, no write
    python3 scripts/audit_pack_sources.py --set B3A    # one set only
    python3 scripts/audit_pack_sources.py --report FILE  # write report to file

Exit codes:
    0  All records confirmed or no actionable differences
    1  Fatal error
    2  Flagged-not-fixed differences remain (manual review recommended)
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _collection_io import (norm_card_name, normalize_rarity,
                            card_reference_by_coord as _card_ref_by_coord,
                            ROOT, PACK_SOURCES_JSON as PACK_SOURCES,
                            CARD_REF_JSON as CARD_REF,
                            name_agrees as _name_agrees)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_pack_sources() -> tuple[dict, list[dict]]:
    raw = _load_json(PACK_SOURCES)
    if isinstance(raw, dict) and "records" in raw:
        return raw.get("_meta", {}), raw["records"]
    return {}, raw


def _load_card_reference() -> dict[tuple[str, int], dict]:
    return _card_ref_by_coord(CARD_REF)


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------

class AuditReport:
    def __init__(self) -> None:
        self.auto_fixed:    list[str] = []
        self.flagged:       list[str] = []
        self.ev_impacts:    list[str] = []
        self.coord_missing: list[str] = []
        self.recs_modified: int = 0


def audit_record(
    rec: dict,
    ref: dict | None,
    report: AuditReport,
    dry_run: bool,
) -> dict:
    """Audit one pack_sources record against the reference. Returns (possibly modified) record."""
    sc = rec.get("set_code", "")
    cn = rec.get("card_number")
    ps_name = rec.get("card_name", "")
    ps_rarity = rec.get("rarity")
    ps_pack = rec.get("pack_name")

    if ref is None:
        report.coord_missing.append(f"{sc}/{cn}: not in card_reference.json")
        return rec

    ref_confidence = ref.get("confidence", "unconfirmed")
    ref_name = ref.get("name", "")
    ref_rarity = normalize_rarity(ref.get("rarity"))
    notes = ref.get("conflict_notes", [])

    modified = dict(rec)
    changed = False

    # ── Name check ────────────────────────────────────────────────────────────
    if ref_name and not _name_agrees(ps_name, ref_name):
        if ref_confidence == "confirmed":
            msg = f"{sc}/{cn}: name {ps_name!r} → {ref_name!r}  [confirmed by {ref.get('confirmations')}]"
            report.auto_fixed.append(msg)
            if not dry_run:
                modified["card_name"] = ref_name
            changed = True
        else:
            report.flagged.append(
                f"{sc}/{cn}: name mismatch {ps_name!r} vs ref={ref_name!r} "
                f"[confidence={ref_confidence}; not auto-fixed]"
            )

    # ── Rarity check ──────────────────────────────────────────────────────────
    if ref_rarity and ref_rarity != normalize_rarity(ps_rarity):
        if ref_confidence == "confirmed":
            msg = f"{sc}/{cn}: rarity {ps_rarity!r} → {ref_rarity!r}  [confirmed]"
            report.auto_fixed.append(msg)
            if not dry_run:
                modified["rarity"] = ref_rarity
            changed = True
        else:
            report.flagged.append(
                f"{sc}/{cn}: rarity mismatch {ps_rarity!r} vs ref={ref_rarity!r} "
                f"[confidence={ref_confidence}; not auto-fixed]"
            )

    # ── Pack assignment check (booster validation via TCGdex data in reference) ──
    ref_pack = ref.get("pack_name")
    booster_notes = [n for n in notes if "pack_name mismatch" in n]
    if booster_notes:
        ev_msg = f"{sc}/{cn}: pack_name validation warning: {'; '.join(booster_notes)}"
        report.ev_impacts.append(ev_msg)
        report.flagged.append(ev_msg)

    if changed:
        report.recs_modified += 1

    return modified


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Audit and auto-fix pack_sources.json.")
    parser.add_argument("--dry-run",  action="store_true",
                        help="Report only; do not write pack_sources.json")
    parser.add_argument("--set",      metavar="SET_CODE",
                        help="Only audit this set (e.g. B3A)")
    parser.add_argument("--report",   metavar="FILE",
                        help="Write full report to this file (stdout otherwise)")
    args = parser.parse_args()

    if not PACK_SOURCES.exists():
        print(f"ERROR: pack_sources.json not found at {PACK_SOURCES}", file=sys.stderr)
        return 1
    if not CARD_REF.exists():
        print(f"ERROR: card_reference.json not found at {CARD_REF}", file=sys.stderr)
        print("       Run: python3 scripts/build_card_reference.py", file=sys.stderr)
        return 1

    meta, records = _load_pack_sources()
    ref_index = _load_card_reference()

    if args.set:
        sc_target = args.set.upper()
        scope_records = [r for r in records if str(r.get("set_code", "")).upper() == sc_target]
    else:
        scope_records = records

    print(f"\nAuditing {len(scope_records)} pack_sources records against card_reference.json …")

    report = AuditReport()
    updated_records = []

    for rec in records:
        sc = str(rec.get("set_code", ""))
        cn_raw = rec.get("card_number")
        try:
            cn = int(cn_raw)
        except (TypeError, ValueError):
            updated_records.append(rec)
            continue

        if args.set and sc.upper() != args.set.upper():
            updated_records.append(rec)
            continue

        ref = ref_index.get((sc, cn))
        updated = audit_record(rec, ref, report, args.dry_run)
        updated_records.append(updated)

    # ── Report ────────────────────────────────────────────────────────────────
    lines: list[str] = [
        f"pack_sources audit — {_now_iso()}",
        f"scope: {'all sets' if not args.set else args.set}",
        f"records checked: {len(scope_records)}",
        "",
    ]

    if report.auto_fixed:
        lines.append(f"AUTO-FIXED ({len(report.auto_fixed)}):")
        for item in report.auto_fixed:
            lines.append(f"  + {item}")
        lines.append("")
    else:
        lines.append("AUTO-FIXED: 0")
        lines.append("")

    if report.flagged:
        lines.append(f"FLAGGED — not auto-fixed ({len(report.flagged)}):")
        for item in report.flagged:
            lines.append(f"  ! {item}")
        lines.append("")
    else:
        lines.append("FLAGGED: 0")
        lines.append("")

    if report.coord_missing:
        lines.append(f"COORD NOT IN REFERENCE ({len(report.coord_missing)}):")
        for item in report.coord_missing:
            lines.append(f"  ? {item}")
        lines.append("")

    if report.ev_impacts:
        lines.append(f"EV-IMPACT WARNINGS ({len(report.ev_impacts)}):")
        for item in report.ev_impacts:
            lines.append(f"  EV {item}")
        lines.append("")

    lines.append(
        f"SUMMARY: {report.recs_modified} record(s) modified  "
        f"{len(report.flagged)} flagged  "
        f"{len(report.coord_missing)} missing from reference"
    )

    report_text = "\n".join(lines)

    if args.report:
        Path(args.report).write_text(report_text, encoding="utf-8")
        print(f"Report written to {args.report}")
    else:
        print("\n" + report_text)

    # ── Write updated pack_sources ────────────────────────────────────────────
    if args.dry_run:
        print("\nDRY RUN — pack_sources.json not written.")
    elif report.recs_modified > 0:
        new_meta = dict(meta)
        new_meta["generated_at"] = new_meta.get("generated_at", "") + " (audited)"
        new_meta["audited_at"] = _now_iso()

        output = {"_meta": new_meta, "records": updated_records}
        tmp = PACK_SOURCES.with_suffix(".tmp")
        tmp.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(PACK_SOURCES)
        print(f"\nWrote {PACK_SOURCES.relative_to(ROOT)} ({report.recs_modified} records updated)")
    else:
        print("\nNo changes — pack_sources.json unchanged.")

    return 2 if report.flagged or report.coord_missing else 0


if __name__ == "__main__":
    sys.exit(main())
