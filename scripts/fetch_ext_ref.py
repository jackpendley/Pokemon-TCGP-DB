#!/usr/bin/env python3
"""
Fetch and populate data/reference/external/external_card_reference.json for
all sets that are missing from it.

ext_ref provides per-card metadata (card_category, pokemon_type, stage, hp,
is_ex) that sync_collection.py uses for auto-add. It currently covers only
B-sets; A1–A4a and PROMO sets are absent, forcing heuristic inference.

Usage:
    python3 scripts/fetch_ext_ref.py               # fetch all missing
    python3 scripts/fetch_ext_ref.py --set A4       # one set only
    python3 scripts/fetch_ext_ref.py --dry-run      # show what would be fetched
    python3 scripts/fetch_ext_ref.py --delay 1.5    # seconds between requests

This script fetches card pages from pocket.limitlesstcg.com and parses:
  - card_category  (Pokemon | Item | Supporter | Stadium | Tool)
  - pokemon_type   (Grass | Fire | Water | ... | None for Trainers)
  - stage          (Basic | Stage 1 | Stage 2 | None for Trainers)
  - hp             (integer | None for Trainers)
  - is_ex          (bool, inferred from card name)

Output: updates data/reference/external/external_card_reference.json in-place.
After running, also run: python3 scripts/build_pack_sources.py
to propagate the metadata into pack_sources.json.

Exit codes:
    0  All cards fetched (or nothing to fetch)
    1  Fatal error
    2  Some fetches failed (partial success)
"""

import argparse
import json
import re
import subprocess
import sys
import time
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _collection_io import (TRAINER_CATEGORIES, is_ex_from_name, RARITY_SYMBOLS,
                            field_slug as _normalize, load_records,
                            http_get_with_retry, ROOT,
                            CARD_REF_JSON as CARD_REF,
                            EXT_REF_JSON as EXT_REF,
                            PACK_SOURCES_JSON as PACK_SOURCES)

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("ERROR: beautifulsoup4 required. Install: python3 -m pip install beautifulsoup4 lxml")
    sys.exit(1)

_BASE_URL = "https://pocket.limitlesstcg.com/cards"

# ext_ref's parser reads Limitless card-page HTML, so the fetch must hit Limitless —
# build the URL from (set_code, number) rather than trusting a record's stored
# source_url. PZ-ingested pack_sources records carry pokemon-zone.com URLs (a
# different site whose HTML this parser can't read, and which Cloudflare-blocks
# plain requests with 403), so following them fails on every card of a
# newly-ingested set. Promos live under P-A/P-B on Limitless (mirrors
# coord_resolver._EXT_SET_ALIAS).
_LIMITLESS_SET_ALIAS = {"PROMO-A": "P-A", "PROMO-B": "P-B"}


def _limitless_card_url(set_code: str, number: int) -> str:
    slug = _LIMITLESS_SET_ALIAS.get(set_code, set_code)
    return f"{_BASE_URL}/{slug}/{number}"

# A re-fetch that flips more than this fraction of records' card_category is
# treated as a likely parser/site-layout regression and aborts the write
# (override with --allow-category-flips). Single-card flips (genuine fixes)
# stay well under the threshold.
FLIP_ABORT_RATIO = 0.15

# A first-fetch batch of at least this many brand-new records that all parse to a
# single card_category is implausible for a full set (real sets mix Pokemon +
# Trainers) and warrants a sanity warning. Set high enough that small promo drops
# (legitimately single-category) don't trip it.
SINGLE_CATEGORY_WARN_MIN = 40


def _should_abort_flips(category_flips: int, refetched: int, allow_override: bool,
                        distinct_transitions: int | None = None) -> bool:
    """Return True if a re-fetch's category-flip rate warrants aborting the write.

    A flip rate above FLIP_ABORT_RATIO is the parser/site-layout regression signature.
    But direction matters: a genuine bulk *fix* flips coherently in ONE direction
    (e.g. all Fossils Pokemon→Item = a single transition type), whereas a regression
    drains many categories into one (a variety collapse = multiple transition types).
    So when the flips are a single coherent transition we let the write proceed (with
    a warning) instead of aborting — this avoids training operators to reflexively
    pass --allow-category-flips for legitimate bulk re-classifications.

    distinct_transitions: number of distinct "old→new" transition types among the
    flips. When None (callers that don't track it), falls back to rate-only.
    """
    if allow_override or not refetched:
        return False
    if (category_flips / refetched) <= FLIP_ABORT_RATIO:
        return False
    # Above the rate threshold. Abort unless the flips are a single coherent
    # direction (one transition type) — that's a fix, not a collapse.
    if distinct_transitions == 1:
        return False
    return True

# Limitless card page HTML selectors — adjust if the site layout changes.
# These were derived by inspecting existing ext_ref data and the Limitless HTML
# page structure. Test with: python3 scripts/fetch_ext_ref.py --set B1 --dry-run
_ENERGY_TYPE_ICONS: dict[str, str] = {
    "grass":    "Grass",
    "fire":     "Fire",
    "water":    "Water",
    "lightning":"Lightning",
    "psychic":  "Psychic",
    "fighting": "Fighting",
    "darkness": "Darkness",
    "metal":    "Metal",
    "dragon":   "Dragon",
    "colorless":"Colorless",
    "normal":   "Colorless",
}

_STAGE_KEYWORDS = {
    "basic":   "Basic",
    "stage 1": "Stage 1",
    "stage 2": "Stage 2",
}

_TRAINER_KEYWORDS = {
    "item":          "Item",
    "supporter":     "Supporter",
    "stadium":       "Stadium",
    "pokémon tool":  "Tool",
    "pokemon tool":  "Tool",
    "tool":          "Tool",
}


_FETCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
}


def _fetch_page(url: str) -> str | None:
    # Retries transient errors (timeout/5xx) before giving up; a permanent 4xx
    # (e.g. 404) or an exhausted retry returns None so the caller skips the card
    # and a later re-run picks it up again (it stays in the missing set).
    try:
        data = http_get_with_retry(url, headers=_FETCH_HEADERS, timeout=15)
        return data.decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code}: {url}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  Error fetching {url}: {e}", file=sys.stderr)
        return None


def _parse_card_page(html: str, set_code: str, number: int, source_url: str) -> dict | None:
    """Parse a Limitless card detail page for ext_ref metadata."""
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        return None

    # ── Card name ────────────────────────────────────────────────────────
    name_el = (
        soup.select_one("span.card-text-name")
        or soup.select_one(".card-text-title .card-text-name")
        or soup.select_one("h1.card-title")
    )
    if name_el:
        name = name_el.get_text(strip=True)
    else:
        title_el = soup.find("title")
        if title_el:
            raw = title_el.get_text(strip=True)
            name = re.split(r"\s*[•–]\s*", raw)[0].strip()
        else:
            return None
    if not name or len(name) < 2:
        return None

    is_ex = is_ex_from_name(name)

    # ── Gather all text blocks for type/stage/category detection ────────
    # Limitless card pages vary slightly in structure; gather all relevant text.
    all_text_blocks: list[str] = []

    # Primary: card-text sections
    for el in soup.select(".card-text-type, .card-text-section, .card-text-title, .card-text-supertype"):
        t = el.get_text(separator=" ", strip=True).lower()
        if t:
            all_text_blocks.append(t)

    # Fallback: any element that looks like a type line
    for el in soup.select("p, span, div"):
        classes = " ".join(el.get("class", []))
        if any(kw in classes for kw in ("type", "super", "subtype", "stage", "category")):
            t = el.get_text(separator=" ", strip=True).lower()
            if t and len(t) < 80:
                all_text_blocks.append(t)

    joined = " ".join(all_text_blocks)

    # ── HP first — presence of HP unambiguously identifies a Pokemon card ───
    # Parse HP before determining card_category so that Pokemon cards whose
    # attack effects mention "Pokémon Tool" are not misclassified as Trainers.
    # Fallbacks are scoped to the card title element only (not effect/section text),
    # since Tool cards carry HP-amounts in their effect descriptions, not their titles.
    hp: int | None = None
    hp_el = soup.select_one("span.card-text-hp, .card-text-hp")
    if hp_el:
        m = re.search(r"(\d+)", hp_el.get_text())
        if m:
            hp = int(m.group(1))
    if hp is None:
        # Scope to card title only — Pokemon HP lives here; Tool effects do not.
        title_text = " ".join(
            el.get_text(separator=" ", strip=True)
            for el in soup.select(".card-text-title")
        )
        m = re.search(r"\bHP\s+(\d{2,3})\b", title_text, re.IGNORECASE)
        if m:
            hp = int(m.group(1))
        if hp is None:
            m = re.search(r"\b(\d{2,3})\s+HP\b", title_text, re.IGNORECASE)
            if m:
                hp = int(m.group(1))

    # ── Determine card_category from the type-line SUPERTYPE ───────────────
    # The .card-text-type element is authoritative and unambiguous:
    #   Pokemon → "Pokémon - Basic/Stage 1/Stage 2"
    #   Trainer → "Trainer - Item/Supporter/Stadium/Tool"
    # Classifying by supertype (not HP) correctly handles both edge cases:
    #   - Pokemon whose attack effect text mentions "Pokémon Tool"
    #   - Fossil/Tool Trainer cards (Item) whose title carries an HP amount
    card_category: str | None = None
    trainer_subtype: str | None = None

    type_line = " ".join(
        el.get_text(separator=" ", strip=True).lower()
        for el in soup.select(".card-text-type, .card-text-supertype")
    )

    if "pokémon" in type_line or "pokemon" in type_line:
        card_category = "Pokemon"
    elif "trainer" in type_line:
        # Trainer supertype confirmed — resolve the subtype keyword.
        for keyword, subtype in _TRAINER_KEYWORDS.items():
            if keyword in type_line:
                card_category = subtype
                trainer_subtype = subtype
                break
        # "Trainer" with no recognised subtype keyword: leave subtype None.
    else:
        # No usable type line — fall back to weaker signals.
        if hp is not None or is_ex:
            card_category = "Pokemon"
        else:
            for keyword, subtype in _TRAINER_KEYWORDS.items():
                if keyword in joined:
                    card_category = subtype
                    trainer_subtype = subtype
                    break
            if not card_category and any(
                kw in joined for kw in ("basic pokémon", "basic pokemon", "stage 1", "stage 2")
            ):
                card_category = "Pokemon"

    # Trainers do not carry HP in the schema — clear any HP parsed from a
    # Fossil/Tool title so Trainer records stay hp=None.
    if card_category and card_category != "Pokemon":
        hp = None

    # ── Stage (Pokemon only) ───────────────────────────────────────────────
    stage: str | None = None
    if card_category == "Pokemon":
        for kw, label in _STAGE_KEYWORDS.items():
            if kw in joined:
                stage = label
                break

    # ── Pokemon type (energy type) ────────────────────────────────────────
    pokemon_type: str | None = None
    if card_category == "Pokemon":
        # Try energy type icons: <img alt="Grass"> or <img alt="[Grass]">
        for img in soup.select("img[alt]"):
            alt = img.get("alt", "").strip("[]").strip().lower()
            if alt in _ENERGY_TYPE_ICONS:
                pokemon_type = _ENERGY_TYPE_ICONS[alt]
                break
        # Fallback: CSS classes like "icon-grass"
        if pokemon_type is None:
            for el in soup.select("[class]"):
                for cls in el.get("class", []):
                    cls_lower = cls.lower()
                    for key, val in _ENERGY_TYPE_ICONS.items():
                        if key in cls_lower:
                            pokemon_type = val
                            break
                if pokemon_type:
                    break

    # ── Rarity ───────────────────────────────────────────────────────────
    rarity: str | None = None
    details = soup.select_one(".prints-current-details")
    if details:
        raw = details.get_text()
        for sym, label in RARITY_SYMBOLS.items():
            if sym in raw:
                rarity = label
                break

    if not card_category:
        return None  # Could not determine card type — skip

    return {
        "set_code":      set_code,
        "number":        number,
        "name":          name,
        "card_category": card_category,
        "pokemon_type":  pokemon_type,
        "stage":         stage,
        "hp":            hp,
        "is_ex":         is_ex,
        "rarity":        rarity,
        "source_url":    source_url,
        "source":        "limitless",
        "normalized_name": _normalize(name),
    }


def _load_ext_ref() -> tuple[list[dict], dict[tuple[str, int], int]]:
    """Load ext_ref and return (records_list, {(set_code, number) → index})."""
    if not EXT_REF.exists():
        return [], {}
    records = json.loads(EXT_REF.read_text(encoding="utf-8"))
    index = {(r.get("set_code"), r.get("number")): i for i, r in enumerate(records)}
    return records, index


def _coords_from(path: Path, number_field: str) -> list[tuple[str, int]]:
    """(set_code, number) pairs from a records file, skipping unusable rows."""
    if not path.exists():
        return []
    coords = []
    for r in load_records(path):
        sc = str(r.get("set_code", "")).strip()
        try:
            coords.append((sc, int(r.get(number_field))))
        except (TypeError, ValueError):
            continue
    return coords


def _load_missing_coords(ext_index: dict[tuple[str, int], int]) -> list[dict]:
    """Cards with no ext_ref entry, from every catalog that names one.

    pack_sources alone is not enough: 81 promo cards exist only in
    card_reference, which build_card_reference synthesizes from the wiki
    snapshots for sets with no pack data. Those were unreachable here, which is
    why 190 Pokémon still carry stage: null — a scope gap, not a parser gap.
    """
    missing = []
    seen: set[tuple[str, int]] = set()
    for key in [
        *_coords_from(PACK_SOURCES, "card_number"),
        *_coords_from(CARD_REF, "card_number"),
    ]:
        if key in seen or key in ext_index:
            continue
        seen.add(key)
        missing.append({
            "set_code": key[0],
            "number": key[1],
            "source_url": _limitless_card_url(*key),
        })
    return missing


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch and populate ext_ref for missing sets.")
    parser.add_argument("--set",      metavar="SET_CODE",
                        help="Only fetch cards for this set (e.g. A4)")
    parser.add_argument("--dry-run",  action="store_true",
                        help="Print what would be fetched, no writes")
    parser.add_argument("--delay",    type=float, default=0.5,
                        help="Seconds to wait between requests (default: 0.5)")
    parser.add_argument("--limit",    type=int, default=0,
                        help="Max cards to fetch per run (0 = no limit)")
    parser.add_argument("--refetch-null-hp", action="store_true",
                        help="Re-fetch cards already in ext_ref that have hp: null")
    parser.add_argument("--force", action="store_true",
                        help="Re-fetch ALL in-scope cards regardless of existing data "
                             "(use with --set to re-parse a set after a parser fix)")
    parser.add_argument("--propagate", action="store_true",
                        help="After a successful fetch, run build_pack_sources.py so "
                             "pack_sources.json stays in sync with ext_ref")
    parser.add_argument("--allow-category-flips", action="store_true",
                        help="Permit a re-fetch that flips a large fraction of records' "
                             "card_category (otherwise the write is aborted as a likely "
                             "parser regression). Threshold: "
                             f"{int(FLIP_ABORT_RATIO * 100)} percent.")
    args = parser.parse_args()

    ext_records, ext_index = _load_ext_ref()

    # --force: treat every card as needing a fetch (re-parse with current parser).
    # --refetch-null-hp: treat existing records with hp=null as missing, except
    #   Trainers (Item/Supporter/Stadium/Tool) which legitimately have no HP.
    if args.force:
        ext_index_complete = {}
    elif args.refetch_null_hp:
        ext_index_complete = {
            key: idx for key, idx in ext_index.items()
            if ext_records[idx].get("hp") is not None
            or ext_records[idx].get("card_category") in TRAINER_CATEGORIES
        }
    else:
        ext_index_complete = ext_index

    missing = _load_missing_coords(ext_index_complete)

    if args.set:
        missing = [m for m in missing if m["set_code"].upper() == args.set.upper()]
    elif args.force:
        # --force without --set would re-fetch the entire catalog (~3200 requests);
        # require an explicit scope to prevent accidental full re-scrapes.
        print("ERROR: --force requires --set to bound the re-fetch scope.", file=sys.stderr)
        return 1

    if args.limit:
        missing = missing[:args.limit]

    if not missing:
        print("ext_ref is already complete for the requested scope.")
        return 0

    # Group by set for reporting
    by_set: dict[str, int] = {}
    for m in missing:
        by_set[m["set_code"]] = by_set.get(m["set_code"], 0) + 1
    print(f"\nCards to fetch: {len(missing)} across {len(by_set)} set(s)")
    for sc in sorted(by_set):
        print(f"  {sc}: {by_set[sc]}")

    if args.dry_run:
        print("\nDRY RUN — no fetches performed.")
        return 0

    fetched = 0
    failed  = 0
    refetched = 0          # records that already existed (re-fetch denominator)
    category_flips = 0
    flip_transitions: dict[str, int] = {}  # "old→new" → count, shows flip direction
    new_categories: dict[str, int] = {}   # category distribution of brand-new records
    for i, card in enumerate(missing):
        sc, num, url = card["set_code"], card["number"], card["source_url"]
        print(f"  [{i+1}/{len(missing)}] {sc}/{num} … ", end="", flush=True)

        html = _fetch_page(url)
        if not html:
            print("FAILED")
            failed += 1
            time.sleep(args.delay)
            continue

        parsed = _parse_card_page(html, sc, num, url)
        if not parsed:
            print(f"could not parse ({url})")
            failed += 1
            time.sleep(args.delay)
            continue

        print(f"OK — {parsed['name']} ({parsed['card_category']})")
        key = (sc, num)
        if key in ext_index:
            # Guard: flag category flips on re-fetch — the symptom of a parser
            # regression (e.g. a whole set suddenly parsing as the wrong type).
            refetched += 1
            old_cat = ext_records[ext_index[key]].get("card_category")
            new_cat = parsed.get("card_category")
            if old_cat != new_cat:
                print(f"  WARN: {sc}/{num} category changed {old_cat!r} → {new_cat!r}",
                      file=sys.stderr)
                category_flips += 1
                transition = f"{old_cat or 'None'}→{new_cat or 'None'}"
                flip_transitions[transition] = flip_transitions.get(transition, 0) + 1
            ext_records[ext_index[key]] = parsed   # update existing record in-place
        else:
            cat = parsed.get("card_category") or "None"
            new_categories[cat] = new_categories.get(cat, 0) + 1
            ext_records.append(parsed)
        fetched += 1
        time.sleep(args.delay)

    # ── Mass-misclassification guard ───────────────────────────────────────────
    # Abort the write if a re-fetch flipped an implausibly large share of records in
    # a way that looks like a regression. Direction is the discriminator: a single
    # coherent transition (e.g. all "Pokemon→Item" for a Fossil fix) proceeds with a
    # warning; many categories collapsing into one (multiple transition types) aborts.
    distinct_transitions = len(flip_transitions)
    if _should_abort_flips(category_flips, refetched, args.allow_category_flips,
                           distinct_transitions):
        print(f"\n  ABORT: {category_flips}/{refetched} re-fetched records "
              f"({category_flips / refetched:.0%}) changed card_category across "
              f"{distinct_transitions} transition types — likely a parser/site-layout "
              f"regression (category collapse). ext_ref NOT written.", file=sys.stderr)
        for transition, n in sorted(flip_transitions.items(), key=lambda kv: -kv[1]):
            print(f"    {n:4d}× {transition}", file=sys.stderr)
        print(f"  Investigate the transitions above, or re-run with "
              f"--allow-category-flips if the change is intentional.", file=sys.stderr)
        return 1
    # High flip rate but a single coherent direction → treat as a likely bulk fix:
    # proceed, but warn loudly so it's not silent.
    if refetched and (category_flips / refetched) > FLIP_ABORT_RATIO and not args.allow_category_flips:
        only = next(iter(flip_transitions)) if flip_transitions else "?"
        print(f"\n  NOTE: {category_flips}/{refetched} records flipped coherently "
              f"({only}) — proceeding as a likely bulk fix. Verify the result.",
              file=sys.stderr)

    if fetched:
        ext_records.sort(key=lambda r: (r.get("set_code", ""), r.get("number", 0)))
        EXT_REF.write_text(json.dumps(ext_records, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n  Wrote {len(ext_records)} records to {EXT_REF.relative_to(ROOT)}")
        if category_flips:
            print(f"  NOTE: {category_flips} re-fetched record(s) changed card_category — "
                  f"review the WARN lines above.", file=sys.stderr)
        # First-fetch plausibility: a full-set-scale brand-new batch that parses as
        # 100% a single category is implausible for a real set (sets mix Pokemon +
        # Trainers). Threshold is set high (SINGLE_CATEGORY_WARN_MIN) so legitimately
        # single-category promo drops, which are small, don't trip a false warning.
        new_total = sum(new_categories.values())
        if new_total >= SINGLE_CATEGORY_WARN_MIN and len(new_categories) == 1:
            only_cat = next(iter(new_categories))
            print(f"  WARN: all {new_total} newly-fetched records parsed as '{only_cat}' — "
                  f"verify this is correct (a full set with no category variety may "
                  f"indicate a parse problem).", file=sys.stderr)
        if args.propagate:
            print("\n  Propagating to pack_sources.json (build_pack_sources.py)…")
            bps = ROOT / "scripts" / "build_pack_sources.py"
            result = subprocess.run([sys.executable, str(bps)], cwd=ROOT)
            if result.returncode != 0:
                print("  ERROR: build_pack_sources.py failed — pack_sources.json may be "
                      "out of sync with ext_ref.", file=sys.stderr)
                return 2
        else:
            print("  Next: run  python3 scripts/build_pack_sources.py  to propagate metadata "
                  "(or re-run with --propagate).")
    else:
        print("\n  No records added.")

    if failed:
        print(f"\n  {failed} card(s) failed. Re-run to retry.", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
