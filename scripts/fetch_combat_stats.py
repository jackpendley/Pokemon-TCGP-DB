#!/usr/bin/env python3
"""
Fetch per-card combat stats (per-attack damage + energy cost + drawback flags, HP,
ability presence) and cache them for the card power/value model.

Two sources, one cache (data/reference/card_combat_stats.json, keyed "SET|name"):
  - TCGdex (https://api.tcgdex.net/v2/en/cards/{SET}-{NNN}) for the sets it covers
    (A1–B2a + PROMO-A). Structured JSON with attacks[].cost / attacks[].damage /
    attacks[].effect.
  - Limitless (https://pocket.limitlesstcg.com/cards/{SET}/{n}) for the newer sets
    TCGdex hasn't published yet (A4b/B2b/B3/B3a/B3b + PROMO-B). Attack cost is the
    energy-symbol letters in .ptcg-symbol; damage is the trailing number in
    .card-text-attack-info; effect text is .card-text-attack-effect.

Each cached attack carries {damage, cost, discards_energy, self_damage,
self_damage_amount} so build_card_power_score can pick a card's best *effective*
attack (cost = one-time ramp; energy-discard attacks aren't repeatable;
self-damage shortens the Pokémon's life).

Alt-art reprints are the same card, so we fetch one printing per (set_code, name).
Resumable + idempotent: entries already carrying the per-attack `attacks` field are
skipped, and the cache is flushed periodically so an interrupted run loses nothing.

Usage:
    python3 scripts/fetch_combat_stats.py            # fetch missing / stale entries
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
TCGDEX_API = "https://api.tcgdex.net/v2/en/cards/{sid}-{num:03d}"

# Newer sets TCGdex hasn't published yet — scraped from Limitless instead.
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

# Drawbacks parsed from an attack's effect text. Kept conservative — only clear
# self-directed matches trip a flag (opponent-directed effects must not).
_RE_DISCARD_SELF = re.compile(
    r"discard\b.{0,40}\benergy\b.{0,40}\b(this pok[eé]mon|itself)\b", re.I | re.S
)
_RE_SELF_DAMAGE = re.compile(
    r"(\d+)\s+damage\s+to\s+(itself|this pok[eé]mon)", re.I
)


def _norm(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


def _leading_int(s) -> int:
    """Damage like '60', '20+', '30×' → the leading integer (0 for status moves)."""
    m = re.match(r"\s*(\d+)", str(s or ""))
    return int(m.group(1)) if m else 0


def _attack_entry(damage: int, cost: int, effect: str) -> dict:
    """One attack's power-relevant fields, incl. self-directed drawbacks."""
    sd = _RE_SELF_DAMAGE.search(effect or "")
    return {
        "damage": damage,
        "cost": cost,
        "discards_energy": bool(_RE_DISCARD_SELF.search(effect or "")),
        "self_damage": bool(sd),
        "self_damage_amount": int(sd.group(1)) if sd else 0,
    }


def _combat_record(hp, attacks: list[dict], ability_count: int, retreat,
                   evolve_from=None) -> dict:
    """Shared cache shape. Keeps max_damage/attack_count for quick inspection.
    `evolve_from` is the predecessor's name (None for Basics), used to build the
    evolution families the web dialog shows."""
    return {
        "hp": hp,
        "attacks": attacks,
        "attack_count": len(attacks),
        "max_damage": max((a["damage"] for a in attacks), default=0),
        "ability_count": ability_count,
        "retreat": retreat,
        "evolve_from": evolve_from,
    }


# ── TCGdex (structured JSON) ────────────────────────────────────────────────
def _extract_tcgdex(card: dict) -> dict:
    attacks = [
        _attack_entry(
            _leading_int(a.get("damage")),
            len(a.get("cost") or []),
            a.get("effect") or "",
        )
        for a in (card.get("attacks") or [])
    ]
    return _combat_record(
        card.get("hp"), attacks, len(card.get("abilities") or []), card.get("retreat"),
        card.get("evolveFrom") or None,
    )


# ── Limitless (HTML scrape) ─────────────────────────────────────────────────
def _extract_limitless(html: str) -> dict | None:
    """Parse a Limitless card page. Returns None (retryable) when it isn't a
    Pokémon card / HP couldn't be read."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        print("ERROR: beautifulsoup4 required (pip install beautifulsoup4 lxml)",
              file=sys.stderr)
        raise
    soup = BeautifulSoup(html, "lxml")

    title = " ".join(
        el.get_text(" ", strip=True) for el in soup.select(".card-text-title")
    )
    m = re.search(r"(\d{2,3})\s*HP", title, re.I)
    hp = int(m.group(1)) if m else None
    if hp is None:
        return None  # Trainer or parse miss — skip so a re-run retries.

    # Evolution predecessor: ".card-text-type" reads e.g. "Pokémon - Stage 2 -
    # Evolves from Ivysaur" (None for Basics).
    type_el = soup.select_one(".card-text-type")
    evo = re.search(r"Evolves from\s+(.+)$",
                    type_el.get_text(" ", strip=True)) if type_el else None
    evolve_from = evo.group(1).strip() if evo else None

    attacks: list[dict] = []
    for att in soup.select(".card-text-attack"):
        info = att.select_one(".card-text-attack-info")
        if not info:
            continue
        sym = info.select_one(".ptcg-symbol")
        cost = len(re.sub(r"\s+", "", sym.get_text() if sym else ""))
        if sym:
            sym.extract()  # leave just "<name> <damage>"
        rest = info.get_text(" ", strip=True)
        dm = re.search(r"(\d+)\s*[+×x]?\s*$", rest)
        damage = int(dm.group(1)) if dm else 0
        eff_el = att.select_one(".card-text-attack-effect")
        attacks.append(
            _attack_entry(damage, cost, eff_el.get_text(" ", strip=True) if eff_el else "")
        )

    ability_count = len(soup.select(".card-text-ability"))
    return _combat_record(hp, attacks, ability_count, None, evolve_from)


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

    # One representative printing (lowest card_number) per (set_code, name), tagged
    # with its fetcher. Limitless-covered sets are Pokémon-only (Trainers have no
    # attacks/HP to score); TCGdex returns Pokémon data regardless.
    reps: dict[str, dict] = {}
    for r in ref:
        sc = r["set_code"]
        if sc in TCGDEX_COVERED:
            fetch = _fetch_tcgdex
        elif sc in LIMITLESS_COVERED and r.get("card_category") == "Pokemon":
            fetch = _fetch_limitless
        else:
            continue
        key = f"{sc}|{_norm(r['name'])}"
        if key not in reps or r["card_number"] < reps[key]["rec"]["card_number"]:
            reps[key] = {"rec": r, "fetch": fetch}

    # Re-fetch when the cache is missing the per-attack `attacks` field (older
    # format) or, for evolving Pokémon (Stage 1/2), the `evolve_from` field. Basics
    # never evolve from anything, so they don't need a refetch for evolve_from.
    def _needs(rec: dict, entry: dict | None) -> bool:
        if entry is None or "attacks" not in entry:
            return True
        return rec.get("stage") in ("Stage1", "Stage2") and "evolve_from" not in entry

    todo = [(k, v) for k, v in reps.items() if _needs(v["rec"], cache.get(k))]
    print(f"  {len(reps)} unique cards; {len(cache)} cached; {len(todo)} to fetch.")

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
        if (i + 1) % 100 == 0:
            CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
            print(f"    …{fetched} fetched, {failed} failed, {len(cache)} cached",
                  file=sys.stderr)
        time.sleep(args.delay)

    CACHE.write_text(json.dumps(cache, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"  Done: +{fetched} fetched, {failed} failed, {len(cache)} total cached.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
