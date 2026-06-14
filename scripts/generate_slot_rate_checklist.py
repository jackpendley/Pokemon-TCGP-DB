#!/usr/bin/env python3
"""
Generates review/slot_rate_verification_checklist.md — a per-pack checklist for confirming
the INFERRED slot rates against the Pokémon TCG Pocket in-app "Offering Rates" screen.

WHY: pull_probability_model.json slot rates come from third-party sources (Game8, ONE
Esports, …) and carry a 0.85x confidence haircut (INFERRED_CONFIDENCE_WEIGHT in
build_pack_ev.py) until verified in-app. This checklist lists the exact branch split and
per-slot rarity rates to tick against the app, and the field to flip once they match.

To clear the haircut for a verified pack: add its "<pack_name> (<set_code>)" to
pull_probability_model.json -> meta.user_in_app_verified_packs (and set the pack's
slot_rates.confidence to "user_in_app_verified").

Usage:
    python3 scripts/generate_slot_rate_checklist.py
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _collection_io import ROOT, PULL_MODEL_JSON

OUT_MD = ROOT / "review" / "slot_rate_verification_checklist.md"

SLOT_KEYS = ["slots_1_3", "slot_4", "slot_5", "slot_6", "rare_pack_all_5_slots"]


def _pct(x) -> str:
    return f"{x * 100:.3f}%" if isinstance(x, (int, float)) else str(x)


def _slot_line(label: str, rates: dict | None) -> str | None:
    if not rates:
        return None
    # A slot dict maps rarity -> probability; skip any non-numeric metadata keys.
    inner = ", ".join(f"{r} {_pct(p)}" for r, p in rates.items()
                      if isinstance(p, (int, float)))
    if not inner:
        return None
    return f"- [ ] `{label}`: {inner}"


def main() -> int:
    model = json.loads(PULL_MODEL_JSON.read_text(encoding="utf-8"))
    verified = set(model.get("meta", {}).get("user_in_app_verified_packs", []))

    lines: list[str] = []
    lines.append("# Slot-rate in-app verification checklist")
    lines.append("")
    lines.append(f"_Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d')} from "
                 f"`data/reference/pull_probability_model.json` (model "
                 f"{model.get('meta', {}).get('model_version', '?')})._")
    lines.append("")
    lines.append("Open each pack's **Offering Rates** screen in the app and tick the rows that "
                 "match. When every row for a pack is ticked, add `\"<pack> (<set_code>)\"` to "
                 "`meta.user_in_app_verified_packs` and set that pack's `slot_rates.confidence` "
                 "to `user_in_app_verified` — this removes the 0.85x EV haircut "
                 "(`INFERRED_CONFIDENCE_WEIGHT`).")
    lines.append("")

    packs = [p for p in model["packs"] if p.get("hourglass_purchasable")]
    packs.sort(key=lambda p: (p.get("set_code", ""), p.get("pack_name", "")))

    for p in packs:
        name, sc = p.get("pack_name", "?"), p.get("set_code", "?")
        already = f"{name} ({sc})" in verified
        sr = p.get("slot_rates") or {}
        badge = "  ✅ already in-app verified" if already else ""
        lines.append(f"## {name} ({sc}){badge}")
        lines.append(f"_source: {sr.get('source_name', '?')} · confidence: "
                     f"{sr.get('confidence', '?')} · branch: "
                     f"{p.get('slot_model', {}).get('branch_model', '?')}_")
        lines.append("")

        reg = sr.get("regular_pack_probability")
        rare = sr.get("rare_pack_probability")
        plus1 = sr.get("regular_pack_plus_one_probability")
        branch = f"- [ ] Branch split: regular {_pct(reg)} / rare {_pct(rare)}"
        if plus1:
            branch += f" / regular+1 {_pct(plus1)}"
        lines.append(branch)

        for key in SLOT_KEYS:
            line = _slot_line(key, sr.get(key))
            if line:
                lines.append(line)
        lines.append("")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {len(packs)} packs → {OUT_MD.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
