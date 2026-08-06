#!/usr/bin/env python3
"""
Fetch Trainer rule text and cache it for the Trainer half of the power model.

Trainers carry no HP or attacks, so build_card_power_score.py could never score
them — all 287 came out null. What a Trainer is worth lives entirely in its
effect text, and nothing in the pipeline persisted that. This fills the gap.

Two sources, one cache (data/reference/card_trainer_effects.json, keyed
"SET|name"), mirroring fetch_combat_stats.py:
  - TCGdex (https://api.tcgdex.net/v2/en/cards/{SET}-{NNN}) for the sets it
    covers. Trainers return `effect` (the rule text) and `trainerType`.
  - Limitless (https://pocket.limitlesstcg.com/cards/{SET}/{n}) for the newer
    sets TCGdex hasn't published. Rule text is the .card-text-section between
    the title section and the artist credit; .card-text-type reads
    "Trainer - Supporter".

Alt-art reprints are the same card, so we fetch one printing per (set_code,
name). Resumable + idempotent: entries already carrying `effect` are skipped and
the cache is flushed periodically, so an interrupted run loses nothing.

Usage:
    python3 scripts/fetch_trainer_effects.py             # fetch missing entries
    python3 scripts/fetch_trainer_effects.py --limit 20  # cap requests (testing)
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
CACHE = ROOT / "data" / "reference" / "card_trainer_effects.json"

# Kept in sync with fetch_combat_stats.py — same source split, same set ids.
TCGDEX_COVERED = {
    "A1", "A1a", "A2", "A2a", "A2b", "A3", "A3a", "A3b", "A4", "A4a",
    "B1", "B1a", "B2", "B2a", "PROMO-A",
}
TCGDEX_SET_ID = {"PROMO-A": "P-A"}
TCGDEX_API = "https://api.tcgdex.net/v2/en/cards/{sid}-{num:03d}"

LIMITLESS_COVERED = {"A4b", "B2b", "B3", "B3a", "B3b", "B4", "PROMO-B"}
LIMITLESS_SET_ID = {"PROMO-A": "P-A", "PROMO-B": "P-B"}
LIMITLESS_URL = "https://pocket.limitlesstcg.com/cards/{sid}/{num}"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/json",
}


def _norm(name: str) -> str:
    return re.sub(r"\s+", " ", (name or "").strip().lower())


def _record(effect: str, subtype: str | None) -> dict | None:
    """Shared cache shape. Returns None when there's no usable rule text, so a
    re-run retries rather than caching a miss."""
    effect = re.sub(r"\s+", " ", (effect or "").strip())
    if not effect:
        return None
    return {"effect": effect, "subtype": subtype}


# ── TCGdex (structured JSON) ────────────────────────────────────────────────
def _extract_tcgdex(card: dict) -> dict | None:
    if card.get("category") != "Trainer":
        return None
    return _record(card.get("effect") or "", card.get("trainerType"))


# ── Limitless (HTML scrape) ─────────────────────────────────────────────────
def _extract_limitless(html: str) -> dict | None:
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        print("ERROR: beautifulsoup4 required (pip install beautifulsoup4 lxml)",
              file=sys.stderr)
        raise
    soup = BeautifulSoup(html, "lxml")

    type_el = soup.select_one(".card-text-type")
    type_text = type_el.get_text(" ", strip=True) if type_el else ""
    if "trainer" not in type_text.lower():
        return None  # Pokémon or parse miss — skip so a re-run retries.
    sub = re.search(r"Trainer\s*-\s*(.+)$", type_text)
    subtype = sub.group(1).strip() if sub else None

    # Sections are: [title + type], [rule text…], [artist credit]. Drop the two
    # we can identify structurally and keep whatever rule text is left. The
    # marker class can sit on the section element itself (the artist credit does
    # exactly that), so check the node as well as its descendants.
    def _tagged(sec, cls: str) -> bool:
        return cls in (sec.get("class") or []) or sec.select_one(f".{cls}") is not None

    parts: list[str] = []
    for sec in soup.select(".card-text-section"):
        if _tagged(sec, "card-text-title") or _tagged(sec, "card-text-artist"):
            continue
        text = sec.get_text(" ", strip=True)
        if text:
            parts.append(text)
    return _record(" ".join(parts), subtype)


def _fetch_tcgdex(set_code: str, number: int) -> dict | None:
    sid = TCGDEX_SET_ID.get(set_code, set_code)
    try:
        resp = requests.get(
            TCGDEX_API.format(sid=sid, num=number), headers=HEADERS, timeout=15
        )
        return _extract_tcgdex(resp.json()) if resp.status_code == 200 else None
    except requests.RequestException:
        return None


def _fetch_limitless(set_code: str, number: int) -> dict | None:
    sid = LIMITLESS_SET_ID.get(set_code, set_code)
    try:
        resp = requests.get(
            LIMITLESS_URL.format(sid=sid, num=number), headers=HEADERS, timeout=15
        )
        return _extract_limitless(resp.text) if resp.status_code == 200 else None
    except requests.RequestException:
        return None


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
        if r.get("card_category") != "Trainer":
            continue
        sc = r["set_code"]
        if sc in TCGDEX_COVERED:
            fetch = _fetch_tcgdex
        elif sc in LIMITLESS_COVERED:
            fetch = _fetch_limitless
        else:
            continue
        key = f"{sc}|{_norm(r['name'])}"
        if key not in reps or r["card_number"] < reps[key]["rec"]["card_number"]:
            reps[key] = {"rec": r, "fetch": fetch}

    todo = [(k, v) for k, v in reps.items() if not (cache.get(k) or {}).get("effect")]
    print(f"  {len(reps)} unique trainers; {len(cache)} cached; {len(todo)} to fetch.")

    fetched = failed = 0
    for i, (key, v) in enumerate(todo):
        if args.limit and fetched >= args.limit:
            break
        rec = v["rec"]
        result = v["fetch"](rec["set_code"], rec["card_number"])
        if result is not None:
            cache[key] = result
            fetched += 1
        else:
            failed += 1
        if (i + 1) % 50 == 0:
            CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
            print(f"    …{fetched} fetched, {failed} failed, {len(cache)} cached",
                  file=sys.stderr)
        time.sleep(args.delay)

    CACHE.write_text(json.dumps(cache, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"  Done: +{fetched} fetched, {failed} failed, {len(cache)} total cached.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
