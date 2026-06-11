#!/usr/bin/env python3
"""
Seed / refresh data/reference/special_illustration_rares.json — the curated authority
for the Special Illustration Rare (SIR) tier.

Super Rare and Special Illustration Rare are BOTH the ★★ "Two Star" tier in Pokémon
TCG Pocket: same symbol, same pull rate. No structured per-card source (TCGdex,
Limitless, Bulbapedia) distinguishes them, so this version-controlled list is the
authority for the super_rare → special_illustration_rare upgrade in
build_card_reference.py.

Source: Game8 "List of Full Art Cards" — the "Rainbow Illustration Rare" sections
enumerate SIR cards per set. Each candidate coord is VALIDATED against the local
source snapshots (TCGdex must say "super_rare", i.e. ★★; or, for sets TCGdex does
not cover, Bulbapedia must say ★★). Candidates that don't validate as ★★ (e.g. the
"Original Card" base printing Game8 lists alongside each SIR) are dropped.

Usage:
    python3 scripts/build_special_illustration_rares.py            # fetch + write
    python3 scripts/build_special_illustration_rares.py --dry-run  # report only

Run after fetch_source_snapshots.py so the validation snapshots are current.
"""

import argparse
import html
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _collection_io import normalize_rarity, canonical_set_code

ROOT        = Path(__file__).resolve().parent.parent
SOURCES_DIR = ROOT / "data" / "reference" / "sources"
OUT_JSON    = ROOT / "data" / "reference" / "special_illustration_rares.json"

GAME8_URL = "https://game8.co/games/Pokemon-TCG-Pocket/archives/483152"
_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

# Section-heading keywords that bound a single rarity section on the Game8 page.
_HEAD_RE = re.compile(
    r"(?:Illustration Rare|CG Full Art|Rainbow Illustration Rare|Deluxe Full Art|"
    r"Immersive Art|Crown Rare Art|Trainer Full Art|Shiny[^<(]*?)\s*Cards?\s*\("
)
# A card coord that is immediately followed by the illustrator line, e.g. "(A1 274) Illust".
_COORD_RE = re.compile(r"\(([A-Za-z0-9]+)\s+0*(\d{1,4})\)\s*Illust")
# Card name that precedes a coord (best-effort, for the human-readable 'name' field).
_NAME_COORD_RE = re.compile(r"([A-Za-z0-9'.:\- ]{2,40}?)\s*\(([A-Za-z0-9]+)\s+0*(\d{1,4})\)\s*Illust")


def _fetch_game8() -> str:
    req = urllib.request.Request(GAME8_URL, headers={"User-Agent": _UA})
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")


def parse_rainbow_ir(raw: str) -> dict[tuple[str, int], str]:
    """Return {(SET_UPPER, number): name} for every coord in a Rainbow IR section."""
    starts = [m.start() for m in re.finditer(r"Rainbow Illustration Rare Cards?\s*\(", raw)
              if m.start() > 100_000]  # skip the table-of-contents links near the top
    found: dict[tuple[str, int], str] = {}
    for s in starts:
        nxt = [m.start() for m in _HEAD_RE.finditer(raw, s + 30)]
        seg = raw[s:(nxt[0] if nxt else s + 6000)]
        text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", seg)))
        for m in _NAME_COORD_RE.finditer(text):
            name = m.group(1).strip(" -:.")
            sc = m.group(2).upper()
            num = int(m.group(3))
            found[(sc, num)] = name
    return found


def _snapshot_rarity(source: str, set_code: str, number: int) -> str | None:
    p = SOURCES_DIR / source / f"{canonical_set_code(set_code)}.json"
    if not p.exists():
        return None
    try:
        cards = json.loads(p.read_text(encoding="utf-8")).get("cards", {})
    except Exception:
        return None
    card = cards.get(str(number))
    return normalize_rarity(card.get("rarity")) if card else None


def validate_is_two_star(set_code: str, number: int) -> bool:
    """A SIR card must be the ★★ tier. TCGdex is authoritative where it covers the set;
    otherwise fall back to Bulbapedia. This drops Game8's 'Original Card' base printings."""
    tc = _snapshot_rarity("tcgdex", set_code, number)
    if tc is not None:
        return tc == "super_rare"
    return _snapshot_rarity("bulbapedia", set_code, number) == "super_rare"


def _snapshot_name(set_code: str, number: int) -> str | None:
    """Clean card name from a source snapshot (Game8 layout text is unreliable)."""
    for src in ("tcgdex", "bulbapedia", "serebii"):
        p = SOURCES_DIR / src / f"{canonical_set_code(set_code)}.json"
        if not p.exists():
            continue
        try:
            card = json.loads(p.read_text(encoding="utf-8")).get("cards", {}).get(str(number))
        except Exception:
            card = None
        if card and card.get("name"):
            return card["name"]
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Seed/refresh special_illustration_rares.json from Game8.")
    ap.add_argument("--dry-run", action="store_true", help="Report only; do not write.")
    args = ap.parse_args()

    try:
        raw = _fetch_game8()
    except Exception as e:
        print(f"ERROR: could not fetch Game8 full-art list: {e}", file=sys.stderr)
        return 1

    candidates = parse_rainbow_ir(raw)
    print(f"Parsed {len(candidates)} Rainbow-IR candidate coords from Game8.")

    records, dropped = [], []
    for (sc, num), name in sorted(candidates.items()):
        if validate_is_two_star(sc, num):
            records.append({
                "set_code": canonical_set_code(sc),
                "card_number": num,
                "name": _snapshot_name(sc, num) or name,
                "source": "game8",
                "source_url": GAME8_URL,
            })
        else:
            dropped.append((sc, num, name))

    by_set: dict[str, int] = {}
    for r in records:
        by_set[r["set_code"]] = by_set.get(r["set_code"], 0) + 1
    print(f"Validated {len(records)} SIR coords (★★ confirmed); dropped {len(dropped)} "
          f"non-★★ candidates (originals / unvalidated).")
    print("Per-set SIR counts:", dict(sorted(by_set.items())))

    if args.dry_run:
        print("--dry-run: not writing.")
        return 0

    payload = {
        "_meta": {
            "description": "Curated Special Illustration Rare (★★ rainbow-border) coords. "
                           "SIR shares the Two Star tier/pull-rate with Super Rare; this list "
                           "is the authority for the super_rare→special_illustration_rare split.",
            "source": "game8 List of Full Art Cards (Rainbow Illustration Rare sections)",
            "source_url": GAME8_URL,
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "validation": "each coord confirmed ★★ (super_rare) in TCGdex, else Bulbapedia",
            "count": len(records),
        },
        "records": sorted(records, key=lambda r: (r["set_code"], r["card_number"])),
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(records)} records → {OUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
