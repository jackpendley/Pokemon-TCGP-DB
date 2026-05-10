#!/usr/bin/env python3
"""
Build a known-good card name lexicon from all confirmed batch files.

Reads:   batches/cards_batch_*.json
Outputs: data/reference/confirmed_lexicon.json
         data/reference/confirmed_card_names.txt

Usage:
    python3 scripts/build_confirmed_lexicon.py
"""

import glob
import json
from datetime import datetime, timezone
from pathlib import Path

BATCHES_GLOB = "batches/cards_batch_*.json"
LEXICON_JSON = Path("data/reference/confirmed_lexicon.json")
LEXICON_NAMES = Path("data/reference/confirmed_card_names.txt")


def main():
    batch_files = sorted(glob.glob(BATCHES_GLOB))
    if not batch_files:
        print("No batch files found. Nothing to build.")
        return

    lexicon: dict = {}   # card_name → aggregated data

    for bf in batch_files:
        batch = json.loads(Path(bf).read_text(encoding="utf-8"))
        for entry in batch:
            name = entry.get("card_name", "").strip()
            if not name or name.lower() == "unknown":
                continue
            ss = entry.get("source_screenshot", "")
            qty = entry.get("quantity", 0)
            is_ex = entry.get("is_ex", False)
            special_type = entry.get("special_type", "unknown")

            if name not in lexicon:
                lexicon[name] = {
                    "card_name": name,
                    "count_seen": 0,
                    "total_quantity": 0,
                    "screenshots_seen": [],
                    "is_ex_values": [],
                    "special_type_values": [],
                }

            rec = lexicon[name]
            rec["count_seen"] += 1
            rec["total_quantity"] += qty
            if ss and ss not in rec["screenshots_seen"]:
                rec["screenshots_seen"].append(ss)
            if is_ex not in rec["is_ex_values"]:
                rec["is_ex_values"].append(is_ex)
            if special_type not in rec["special_type_values"]:
                rec["special_type_values"].append(special_type)

    entries = sorted(lexicon.values(), key=lambda x: x["card_name"])

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_unique_names": len(entries),
        "source_batches": batch_files,
        "entries": entries,
    }

    LEXICON_JSON.parent.mkdir(parents=True, exist_ok=True)
    LEXICON_JSON.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    names_txt = "\n".join(e["card_name"] for e in entries) + "\n"
    LEXICON_NAMES.write_text(names_txt, encoding="utf-8")

    print(f"Confirmed lexicon: {len(entries)} unique card names")
    print(f"JSON  → {LEXICON_JSON}")
    print(f"Names → {LEXICON_NAMES}")


if __name__ == "__main__":
    main()
