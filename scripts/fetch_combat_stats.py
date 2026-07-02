#!/usr/bin/env python3
"""
Fetch per-card combat stats (attack damage, ability presence, HP) from TCGdex and
cache them for the card power/value model.

The local TCGdex snapshots only kept HP, so attack data must be fetched once from
the card endpoint (https://api.tcgdex.net/v2/en/cards/{SET}-{NNN}). Alt-art
reprints are the same card, so we fetch one printing per (set_code, card name) and
key the cache by that — cutting ~2,500 covered-set records to ~1,940 requests.

Resumable + idempotent: already-cached keys are skipped, and the cache is flushed
periodically so an interrupted run loses nothing. Uncovered sets (no TCGdex data)
are left out; the power builder falls back to HP + rarity there.

Usage:
    python3 scripts/fetch_combat_stats.py            # fetch missing entries
    python3 scripts/fetch_combat_stats.py --limit 50 # cap requests (testing)
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
CARD_REF = ROOT / "data" / "reference" / "card_reference.json"
CACHE = ROOT / "data" / "reference" / "card_combat_stats.json"

# Sets TCGdex covers (mirrors card-image.ts). PROMO-A maps to the P-A set id.
TCGDEX_COVERED = {
    "A1", "A1a", "A2", "A2a", "A2b", "A3", "A3a", "A3b", "A4", "A4a",
    "B1", "B1a", "B2", "B2a", "PROMO-A",
}
TCGDEX_SET_ID = {"PROMO-A": "P-A"}
API = "https://api.tcgdex.net/v2/en/cards/{sid}-{num:03d}"
HEADERS = {"User-Agent": "Mozilla/5.0 (TCGP-optimizer combat-stats fetch)"}


def _norm(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


def _leading_int(s) -> int:
    """Damage like '60', '20+', '30×' → the leading integer (0 for status moves)."""
    m = re.match(r"\s*(\d+)", str(s or ""))
    return int(m.group(1)) if m else 0


def _extract(card: dict) -> dict:
    attacks = card.get("attacks") or []
    damages = [_leading_int(a.get("damage")) for a in attacks]
    return {
        "hp": card.get("hp"),
        "attack_count": len(attacks),
        "max_damage": max(damages, default=0),
        "total_damage": sum(damages),
        "ability_count": len(card.get("abilities") or []),
        "retreat": card.get("retreat"),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="max requests this run")
    ap.add_argument("--delay", type=float, default=0.2, help="seconds between requests")
    args = ap.parse_args()

    ref = json.loads(CARD_REF.read_text(encoding="utf-8"))["records"]
    cache: dict = {}
    if CACHE.exists():
        cache = json.loads(CACHE.read_text(encoding="utf-8"))

    # One representative printing (lowest card_number) per (set_code, name).
    reps: dict[str, dict] = {}
    for r in ref:
        sc = r["set_code"]
        if sc not in TCGDEX_COVERED:
            continue
        key = f"{sc}|{_norm(r['name'])}"
        if key not in reps or r["card_number"] < reps[key]["card_number"]:
            reps[key] = r

    todo = [(k, r) for k, r in reps.items() if k not in cache]
    print(f"  {len(reps)} unique cards; {len(cache)} cached; {len(todo)} to fetch.")

    fetched = failed = 0
    for i, (key, r) in enumerate(todo):
        if args.limit and fetched >= args.limit:
            break
        sid = TCGDEX_SET_ID.get(r["set_code"], r["set_code"])
        url = API.format(sid=sid, num=r["card_number"])
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                cache[key] = _extract(resp.json())
                fetched += 1
            else:
                failed += 1
        except requests.RequestException:
            failed += 1
        if (i + 1) % 100 == 0:
            CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
            print(f"    …{fetched} fetched, {failed} failed, {len(cache)} cached", file=sys.stderr)
        time.sleep(args.delay)

    CACHE.write_text(
        json.dumps(cache, indent=1, ensure_ascii=False), encoding="utf-8"
    )
    print(f"  Done: +{fetched} fetched, {failed} failed, {len(cache)} total cached.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
