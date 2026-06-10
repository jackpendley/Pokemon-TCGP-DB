#!/usr/bin/env python3
"""
Fetch per-source card-name snapshots for all 20 TCG Pocket sets.

Produces data/reference/sources/<source>/<SET>.json — lightweight caches that
the build_card_reference.py reconciler uses for cross-source name validation.
Each snapshot carries: {<card_number_str>: {"name": ..., "rarity": ..., ...}}.

Sources:
  tcgdex    — REST API, covers A1–B2a (15 sets). Returns name + rarity + boosters
               (pack membership) + hp/type/stage from per-card endpoint.
  serebii   — Per-set index page title scrape. Covers all 20 sets.
  bulbapedia — MediaWiki API wikitext parse. Covers all 20 sets. Returns name +
               rarity + pokemon_type from the card-list rows.

Limitless is NOT a new source here — it's the origin of pack_sources.json and
external_card_reference.json, so it's already the baseline, not an independent check.

Usage:
    python3 scripts/fetch_source_snapshots.py               # all sources, all sets
    python3 scripts/fetch_source_snapshots.py --set B3A     # one set only
    python3 scripts/fetch_source_snapshots.py --source serebii
    python3 scripts/fetch_source_snapshots.py --dry-run     # show what would be fetched
    python3 scripts/fetch_source_snapshots.py --force       # ignore TTL, re-fetch all

Exit codes:
    0  All snapshots written (or nothing to do)
    1  Fatal error
    2  Partial failure (some sets failed; others were written)
"""

import argparse
import html as _html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _collection_io import is_cache_fresh, norm_card_name, normalize_rarity

ROOT         = Path(__file__).resolve().parent.parent
SOURCES_DIR  = ROOT / "data" / "reference" / "sources"
PACK_SOURCES = ROOT / "data" / "reference" / "pack_sources.json"

REQUEST_DELAY   = 0.4   # seconds between HTTP requests
REQUEST_TIMEOUT = 15    # seconds per request
CACHE_MAX_DAYS  = 30

_UA_BROWSER = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
# Descriptive UA for Bulbapedia/MediaWiki (per bot policy)
_UA_BOT = "PokemonTCGP-DB/1.0 (jackpendley9@gmail.com; personal collection validator)"

TCGDEX_BASE    = "https://api.tcgdex.net/v2/en"
SEREBII_BASE   = "https://www.serebii.net/tcgpocket"
BULBAPEDIA_API = "https://bulbapedia.bulbagarden.net/w/api.php"


# ---------------------------------------------------------------------------
# Canonical set-alias table (verified 2026-06-01: all HTTP 200)
# set_code → {tcgdex: str|None, serebii: str, bulbapedia: str, limitless: str}
# ---------------------------------------------------------------------------
SET_ALIASES: dict[str, dict] = {
    "A1":     {"tcgdex": "A1",  "serebii": "geneticapex",             "bulbapedia": "Genetic Apex (TCG Pocket)",           "limitless": "A1"},
    "A1a":    {"tcgdex": "A1a", "serebii": "mythicalisland",           "bulbapedia": "Mythical Island (TCG Pocket)",         "limitless": "A1a"},
    "A2":     {"tcgdex": "A2",  "serebii": "space-timesmackdown",      "bulbapedia": "Space-Time Smackdown (TCG Pocket)",    "limitless": "A2"},
    "A2a":    {"tcgdex": "A2a", "serebii": "triumphantlight",          "bulbapedia": "Triumphant Light (TCG Pocket)",        "limitless": "A2a"},
    "A2b":    {"tcgdex": "A2b", "serebii": "shiningrevelry",           "bulbapedia": "Shining Revelry (TCG Pocket)",         "limitless": "A2b"},
    "A3":     {"tcgdex": "A3",  "serebii": "celestialguardians",       "bulbapedia": "Celestial Guardians (TCG Pocket)",     "limitless": "A3"},
    "A3a":    {"tcgdex": "A3a", "serebii": "extradimensionalcrisis",   "bulbapedia": "Extradimensional Crisis (TCG Pocket)", "limitless": "A3a"},
    "A3b":    {"tcgdex": "A3b", "serebii": "eeveegrove",               "bulbapedia": "Eevee Grove (TCG Pocket)",             "limitless": "A3b"},
    "A4":     {"tcgdex": "A4",  "serebii": "wisdomofseaandsky",        "bulbapedia": "Wisdom of Sea and Sky (TCG Pocket)",   "limitless": "A4"},
    "A4a":    {"tcgdex": "A4a", "serebii": "secludedsprings",          "bulbapedia": "Secluded Springs (TCG Pocket)",        "limitless": "A4a"},
    "A4b":    {"tcgdex": None,  "serebii": "deluxepackex",             "bulbapedia": "Deluxe Pack: ex (TCG Pocket)",         "limitless": "A4b"},
    "B1":     {"tcgdex": "B1",  "serebii": "megarising",               "bulbapedia": "Mega Rising (TCG Pocket)",             "limitless": "B1"},
    "B1a":    {"tcgdex": "B1a", "serebii": "crimsonblaze",             "bulbapedia": "Crimson Blaze (TCG Pocket)",           "limitless": "B1a"},
    "B2":     {"tcgdex": "B2",  "serebii": "fantasticalparade",        "bulbapedia": "Fantastical Parade (TCG Pocket)",      "limitless": "B2"},
    "B2a":    {"tcgdex": "B2a", "serebii": "paldeanwonders",           "bulbapedia": "Paldean Wonders (TCG Pocket)",         "limitless": "B2a"},
    "B2b":    {"tcgdex": None,  "serebii": "megashine",                "bulbapedia": "Mega Shine (TCG Pocket)",              "limitless": "B2b"},
    "B3":     {"tcgdex": None,  "serebii": "pulsingaura",              "bulbapedia": "Pulsing Aura (TCG Pocket)",            "limitless": "B3"},
    "B3A":    {"tcgdex": None,  "serebii": "paradoxdrive",             "bulbapedia": "Paradox Drive (TCG Pocket)",           "limitless": "B3a"},
    "PROMO-A":{"tcgdex": "P-A", "serebii": "promo-a",                  "bulbapedia": "Promo-A (TCG Pocket)",                 "limitless": "PROMO-A"},
    "PROMO-B":{"tcgdex": None,  "serebii": "promo-b",                  "bulbapedia": "Promo-B (TCG Pocket)",                 "limitless": "PROMO-B"},
}

TCGDEX_SETS = frozenset(a["tcgdex"] for a in SET_ALIASES.values() if a["tcgdex"])

# Rarity normalisation: Bulbapedia uses {{Rar/TCGP|Diamond|1}} style. Mapped to the new
# canonical vocabulary. (Bulbapedia is a cross-validator; TCGdex is the per-card authority,
# and the curated SIR list distinguishes super_rare vs special_illustration_rare.)
_BP_RARITY: dict[str, str] = {
    ("Diamond", "1"):  "common",
    ("Diamond", "2"):  "uncommon",
    ("Diamond", "3"):  "rare",
    ("Diamond", "4"):  "double_rare",
    ("Star", "1"):     "illustration_rare",
    ("Star", "2"):     "super_rare",
    ("Star", "3"):     "immersive",
    ("Shiny", "1"):    "shiny_rare",
    ("Shiny", "2"):    "shiny_super_rare",
    ("Crown", "1"):    "ultra_rare",
    ("Promo", ""):     "promo",
    ("Promo", "1"):    "promo",
}

# TCGdex rarity strings → new canonical names. TCGdex is the per-card rarity
# authority — it distinguishes the shiny tiers ("One Shiny"/"Two Shiny") and Crown,
# which the symbol-scraping sources do not. The super_rare→special_illustration_rare
# split (both "Two Star") is applied later from the curated SIR reference
# (build_card_reference). Current API returns "Crown"; older responses used
# "Crown Rare" — both mapped so re-fetches and stale caches agree.
_TCGDEX_RARITY: dict[str, str] = {
    "One Diamond":    "common",
    "Two Diamond":    "uncommon",
    "Three Diamond":  "rare",
    "Four Diamond":   "double_rare",
    "One Star":       "illustration_rare",
    "Two Star":       "super_rare",
    "Three Star":     "immersive",
    "One Shiny":      "shiny_rare",
    "Two Shiny":      "shiny_super_rare",
    "Crown":          "ultra_rare",
    "Crown Rare":     "ultra_rare",
    "Promo":          "promo",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _get(url: str, ua: str = _UA_BROWSER, params: dict | None = None) -> bytes | None:
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": ua})
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        print(f"    HTTP {e.code}: {url}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"    Error fetching {url}: {e}", file=sys.stderr)
        return None


def _snapshot_path(source: str, set_code: str) -> Path:
    return SOURCES_DIR / source / f"{set_code}.json"


def _load_snapshot(source: str, set_code: str) -> dict | None:
    p = _snapshot_path(source, set_code)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_snapshot(source: str, set_code: str, cards: dict, meta_extra: dict | None = None) -> None:
    p = _snapshot_path(source, set_code)
    p.parent.mkdir(parents=True, exist_ok=True)
    meta = {"set_code": set_code, "source": source, "cached_at": _now_iso(), "card_count": len(cards)}
    if meta_extra:
        meta.update(meta_extra)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(
        json.dumps({"_meta": meta, "cards": cards}, indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    tmp.replace(p)


def _is_fresh(source: str, set_code: str, force: bool) -> bool:
    if force:
        return False
    snap = _load_snapshot(source, set_code)
    if not snap:
        return False
    return is_cache_fresh({"cached_at": snap.get("_meta", {}).get("cached_at")}, CACHE_MAX_DAYS)


# ---------------------------------------------------------------------------
# TCGdex fetcher (A1–B2a only; bulk set list + per-card detail)
# ---------------------------------------------------------------------------

def _tcgdex_rarity(raw: str | None) -> str | None:
    if not raw:
        return None
    return normalize_rarity(_TCGDEX_RARITY.get(raw))


def fetch_tcgdex(set_code: str) -> dict | None:
    """Fetch all cards for a set from TCGdex. Returns {str(number): card_dict} or None."""
    alias = SET_ALIASES[set_code]["tcgdex"]
    if not alias:
        return None  # not covered by TCGdex

    # Bulk set list: fast, gets name + localId for every card
    raw = _get(f"{TCGDEX_BASE}/sets/{alias}", ua=_UA_BROWSER)
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except Exception:
        return None

    bulk_cards = data.get("cards", [])
    if not bulk_cards:
        return None

    boosters_by_id: dict[str, list[str]] = {}

    # Per-card fetch for rich metadata (rarity, boosters, hp, type, stage).
    # Rate-limited; delay after each call.
    cards: dict[str, dict] = {}
    for i, c in enumerate(bulk_cards):
        local_id = c.get("localId", "")
        try:
            num = int(local_id)
        except (ValueError, TypeError):
            continue

        card_raw = _get(f"{TCGDEX_BASE}/cards/{alias}-{local_id}", ua=_UA_BROWSER)
        time.sleep(REQUEST_DELAY)

        if not card_raw:
            # Fallback: use bulk-list name only
            cards[str(num)] = {"name": c.get("name", ""), "rarity": None, "boosters": []}
            continue
        try:
            cd = json.loads(card_raw)
        except Exception:
            cards[str(num)] = {"name": c.get("name", ""), "rarity": None, "boosters": []}
            continue

        booster_names = [b.get("name", "") for b in (cd.get("boosters") or [])]
        cards[str(num)] = {
            "name":          cd.get("name") or c.get("name", ""),
            "rarity":        _tcgdex_rarity(cd.get("rarity")),
            "boosters":      booster_names,
            "hp":            cd.get("hp"),
            "stage":         cd.get("stage"),
            "category":      cd.get("category"),
            "types":         cd.get("types", []),
        }

    return cards if cards else None


# ---------------------------------------------------------------------------
# Serebii fetcher (all 20 sets; per-set index page)
# ---------------------------------------------------------------------------

# Serebii index page name-cell pattern:
#   <a href="/tcgpocket/<dir>/<NNN>.shtml">Mega <font size="2">Heracross</font> ex</a>
# Card names may have parts outside the <font> tag, so capture the full <a> text content.
# The img-link and text-link share the same URL; we match the text-link (no <img> child).
_SE_NAME_LINK_RE = re.compile(
    r'<a\s+href="/tcgpocket/([^/]+)/(\d{3})\.shtml"\s*>((?:(?!<img)[^<]|<font[^>]*>[^<]*</font>)*)</a>',
)
_STRIP_TAGS_RE = re.compile(r"<[^>]+>")


def _serebii_parse_name(raw: str) -> str:
    """Strip inner tags, unescape HTML entities, and normalize whitespace."""
    text = _STRIP_TAGS_RE.sub("", raw)
    return " ".join(_html.unescape(text).split())


def fetch_serebii(set_code: str) -> dict | None:
    """Parse card names from the Serebii set index page (1 request per set).

    Each card appears twice on the page (img link + text link); we parse the text links
    which carry the full card name (which may straddle <font> tags for 'Mega X ex' names).
    """
    alias = SET_ALIASES[set_code]
    se_dir = alias["serebii"]

    raw = _get(f"{SEREBII_BASE}/{se_dir}/", ua=_UA_BROWSER)
    time.sleep(REQUEST_DELAY)
    if not raw:
        return None

    # Serebii serves UTF-8 for accented names (Flabébé, etc.). Try UTF-8 first;
    # fall back to latin-1 for pages that aren't valid UTF-8.
    try:
        page = raw.decode("utf-8")
    except UnicodeDecodeError:
        page = raw.decode("latin-1", errors="replace")

    cards: dict[str, dict] = {}
    seen: set[int] = set()
    for m in _SE_NAME_LINK_RE.finditer(page):
        if m.group(1) != se_dir:
            continue
        try:
            num = int(m.group(2))
        except ValueError:
            continue
        if num in seen:
            continue
        seen.add(num)
        name = _serebii_parse_name(m.group(3))
        if name:
            cards[str(num)] = {"name": name}

    if not cards:
        print(f"    Serebii {set_code}: no cards parsed from index page", file=sys.stderr)
        return None

    return cards


# ---------------------------------------------------------------------------
# Bulbapedia fetcher (all 20 sets; MediaWiki API wikitext)
# ---------------------------------------------------------------------------

_BP_CARD_ROW_RE = re.compile(
    r"\|\s*(\d{3})/(\d{3})\s*\|\|\s*\{\{TCG ID\|[^|]+\|([^|}]+)\|(\d+)"
    r"(?:\|[^|}]*)?\}\}"                                  # optional 4th arg (display name for ex cards)
    r"(?:\{\{TCGP Icon\|ex\}\})?"                         # optional {{TCGP Icon|ex}}
    r"(?:[^|]*\|\|\s*\{\{TCG Icon\|([^|}]*)\}\})?"        # optional type column
    r"(?:[^|]*\|\|\s*\{\{Rar/TCGP\|([^|}]*)\|([^|}]*)\}\})?",  # optional rarity column
)

# Promo rows: | NNN/P-A || {{TCG ID|Promo-A|Name|N}} || {{TCG Icon|...}} || ...
# The denominator is non-numeric (P-A, P-B), so the number comes from the TCG ID param.
_BP_PROMO_ROW_RE = re.compile(
    r"\|\s*(\d{3})/[A-Z]+-[A-Z]\s*\|\|\s*\{\{TCG ID\|[^|]+\|([^|}]+)\|(\d+)"
    r"(?:\|[^|}]*)?\}\}"                                  # optional 4th display-name arg
    r"(?:\{\{TCGP Icon\|ex\}\})?"
    r"(?:[^|]*\|\|\s*\{\{TCG Icon\|([^|}]*)\}\})?"        # optional type column
)


def _bp_rarity(kind: str, level: str) -> str | None:
    kind = kind.strip()
    level = level.strip()
    return _BP_RARITY.get((kind, level)) or _BP_RARITY.get((kind, ""))


def fetch_bulbapedia(set_code: str) -> dict | None:
    """Fetch card list from Bulbapedia MediaWiki API. Returns {str(number): card_dict}."""
    alias = SET_ALIASES[set_code]
    bp_title = alias["bulbapedia"]

    params = {
        "action": "parse",
        "page": bp_title,
        "prop": "wikitext",
        "format": "json",
    }
    raw = _get(BULBAPEDIA_API, ua=_UA_BOT, params=params)
    time.sleep(REQUEST_DELAY)
    if not raw:
        return None

    try:
        data = json.loads(raw)
        wikitext = data["parse"]["wikitext"]["*"]
    except (KeyError, json.JSONDecodeError):
        print(f"    Bulbapedia {set_code}: parse error", file=sys.stderr)
        return None

    cards: dict[str, dict] = {}

    # Standard numbered rows: | NNN/DDD || {{TCG ID|Set|Name|N}} ...
    for m in _BP_CARD_ROW_RE.finditer(wikitext):
        num_str, _denom, name, _local_n, type_raw, rar_kind, rar_level = m.groups()
        try:
            num = int(num_str)
        except ValueError:
            continue
        rarity = _bp_rarity(rar_kind or "", rar_level or "") if rar_kind else None
        pokemon_type = type_raw.strip() if type_raw else None
        cards[str(num)] = {
            "name": _html.unescape(name.strip()),
            "rarity": rarity,
            "pokemon_type": pokemon_type,
        }

    # Promo rows: | NNN/P-A || {{TCG ID|Promo-A|Name|N}} ... (non-numeric denominator)
    if not cards:
        for m in _BP_PROMO_ROW_RE.finditer(wikitext):
            num_str, name, local_n, type_raw = m.groups()
            try:
                num = int(num_str)
            except ValueError:
                continue
            pokemon_type = type_raw.strip() if type_raw else None
            cards[str(num)] = {
                "name": _html.unescape(name.strip()),
                "rarity": "promo",
                "pokemon_type": pokemon_type,
            }

    if not cards:
        print(f"    Bulbapedia {set_code}: no card rows found in wikitext", file=sys.stderr)
        return None

    return cards


# ---------------------------------------------------------------------------
# CLI driver
# ---------------------------------------------------------------------------

FETCHERS = {
    "tcgdex":     fetch_tcgdex,
    "serebii":    fetch_serebii,
    "bulbapedia": fetch_bulbapedia,
}


def _sets_from_pack_sources() -> list[str]:
    """Return ordered set list from pack_sources.json (or fall back to SET_ALIASES keys)."""
    if PACK_SOURCES.exists():
        try:
            data = json.loads(PACK_SOURCES.read_text(encoding="utf-8"))
            records = data.get("records", data) if isinstance(data, dict) else data
            seen: list[str] = []
            for r in records:
                sc = str(r.get("set_code", "")).strip()
                if sc and sc not in seen:
                    seen.append(sc)
            return seen
        except Exception:
            pass
    return list(SET_ALIASES.keys())


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch per-source card-name snapshots for cross-validation."
    )
    parser.add_argument("--set",    metavar="SET_CODE",
                        help="Only process this set (e.g. B3A)")
    parser.add_argument("--source", metavar="SOURCE",
                        choices=list(FETCHERS) + ["all"], default="all",
                        help="Source to fetch from (default: all)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be fetched; make no requests")
    parser.add_argument("--force", action="store_true",
                        help="Ignore TTL and re-fetch even fresh snapshots")
    args = parser.parse_args()

    all_sets = _sets_from_pack_sources()
    if args.set:
        sc_up = args.set.upper()
        # Accept 'B3a' → 'B3A' case-insensitively
        matched = next((s for s in SET_ALIASES if s.upper() == sc_up), None)
        if not matched:
            print(f"ERROR: unknown set '{args.set}'. Known: {', '.join(SET_ALIASES)}", file=sys.stderr)
            return 1
        target_sets = [matched]
    else:
        target_sets = [s for s in all_sets if s in SET_ALIASES]

    sources_to_run = list(FETCHERS.keys()) if args.source == "all" else [args.source]

    # Determine what actually needs fetching (respects TTL)
    work: list[tuple[str, str]] = []  # (source, set_code)
    for source in sources_to_run:
        for sc in target_sets:
            if source == "tcgdex" and not SET_ALIASES[sc]["tcgdex"]:
                continue  # TCGdex doesn't cover this set
            if not _is_fresh(source, sc, args.force):
                work.append((source, sc))

    if not work:
        print("All snapshots are fresh. Use --force to re-fetch.")
        return 0

    # Group for reporting
    by_source: dict[str, list[str]] = {}
    for source, sc in work:
        by_source.setdefault(source, []).append(sc)
    print(f"\nSnapshots to fetch: {len(work)}")
    for source, sets in sorted(by_source.items()):
        print(f"  {source}: {', '.join(sets)}")

    if args.dry_run:
        print("\nDRY RUN — no fetches performed.")
        return 0

    failed: list[tuple[str, str]] = []

    for source, sc in work:
        print(f"\n  [{source}] {sc} …", flush=True)
        fetcher = FETCHERS[source]
        try:
            cards = fetcher(sc)
        except Exception as e:
            print(f"    ERROR: {e}", file=sys.stderr)
            failed.append((source, sc))
            continue

        if not cards:
            print(f"    FAILED — no cards returned", file=sys.stderr)
            failed.append((source, sc))
            continue

        _write_snapshot(source, sc, cards)
        print(f"    OK — {len(cards)} cards written to sources/{source}/{sc}.json")

    print()
    if failed:
        print(f"  {len(failed)} snapshot(s) failed:", file=sys.stderr)
        for source, sc in failed:
            print(f"    {source}/{sc}", file=sys.stderr)
        return 2

    print(f"  All snapshots written successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
