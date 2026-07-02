#!/usr/bin/env python3
"""
Ingest Pokémon Zone reference data — pack odds and card identity.

Automates the reference refresh that used to require hand-editing pz_pack_odds.json.
The same parser runs over two interchangeable data SOURCES:

  * Live fetch (default) — reuses the stored sync auth (pokemon_zone_client) to GET
    game-data and the pack-odds pages directly. No manual HAR export.
  * HAR capture (--har) — parses a browser DevTools export; useful offline or when
    stored auth is unavailable.

Two layers are extracted from whichever source is used:

  1. PACK ODDS — from pack-odds pages
       /sets/<exp>/packs/<slug>/?show_pack_odds=1&show_pack_slot_odds=1
     Each card cell has a slot-odds table (card-grid__pack_odds_slots) and a
     "Drop Chance: N%" total (card-grid__pack_odds). Parsed into pz_pack_odds.json
     entries: {pack_name, expansion_id, expansion_slug, pack_slug, card_count,
     cards:[{card_url, name, set_code, card_number, drop_chance_pct, slot_odds_pct}]}.

  2. PACK COMPOSITION / IDENTITY — from /api/game/game-data (packs + packCardIds)
     and /api/cards/search (catalog). Drives the report of which packs/cards are new
     and, with --write-pack-sources, the generation of pack_sources records.

Usage:
    python3 scripts/ingest_pz.py                       # live: dry-run report of new packs
    python3 scripts/ingest_pz.py --apply --write-pack-sources --rebuild-refs
                                                       # live: full refresh + close the loop
    python3 scripts/ingest_pz.py --har CAPTURE.har --apply        # ingest a HAR instead
    python3 scripts/ingest_pz.py --har CAPTURE.har --verify-only  # parse + diff, no write

Exit codes:
    0  success
    1  fatal (no usable data / fetch or rebuild failure)
    2  parsed odds disagree with existing pz_pack_odds.json under --verify-only
"""

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _collection_io import (canonical_set_code, is_ex_from_name, normalize_rarity,
                            load_records,
                            PZ_PACK_ODDS_JSON, PACK_SOURCES_JSON, SOURCES_DIR)

_PZ_BASE = "https://www.pokemon-zone.com"

NUM_SLOTS = 5  # PZ packs have 5 card slots; promo packs leave 2–4 at 0%.

# A single card cell on a pack-odds page. We slice the page on card links and parse
# each window independently — robust to the nested-div markup.
_CARD_LINK_RE = re.compile(r'href="(/cards/([a-z0-9-]+)/(\d+)/[^"]*)"')
_FIGCAPTION_RE = re.compile(r'card-grid__cell-card-caption">([^<]+)</figcaption>')
_SLOT_ROW_RE = re.compile(r'<td>Card #(\d+)</td>\s*<td>([\d.]+)%</td>')
_DROP_CHANCE_RE = re.compile(r'Drop Chance:\s*([\d.]+)%')
_TITLE_RE = re.compile(r'<title>([^<]+)</title>')
# Titles take two shapes:
#   regular: "Pulsing Aura Card List - Pulsing Aura (B3) - Pokémon TCG Pocket"
#   promo:   "Promo Pack B Series Vol. 9 Card List - Promo B - Pokémon TCG Pocket"
# The pack name is always the text before " Card List"; the expansion code only
# appears parenthesised on regular packs (promos fall back to the cards' set_code).
# The readable expansion name sits between " Card List - " and the " (CODE)" on
# regular packs (e.g. "… Card List - Everyday Wonders (B3b) …"); promos have no
# parenthesised code so there's nothing to capture and we fall back to the code.
_PACK_NAME_RE = re.compile(r'^(.+?)\s+Card List')
_EXPANSION_RE = re.compile(r'\(([A-Za-z0-9-]+)\)')
_EXPANSION_NAME_RE = re.compile(r'Card List\s*[-–]\s*(.+?)\s*\([A-Za-z0-9-]+\)')


# ---------------------------------------------------------------------------
# HAR access
# ---------------------------------------------------------------------------

def iter_har_responses(har_path: Path):
    """Yield (url, mimeType, body_text|None) for every entry in a HAR."""
    data = json.loads(har_path.read_text(encoding="utf-8"))
    for e in data.get("log", {}).get("entries", []):
        url = e.get("request", {}).get("url", "")
        content = e.get("response", {}).get("content", {})
        yield url, content.get("mimeType", ""), content.get("text")


def _json_body(body: str | None):
    if not body:
        return None
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return None


def responses_from_har(har_path: Path) -> list[tuple[str, str, str | None]]:
    """Materialise a HAR into the common (url, mimeType, body) response list."""
    return list(iter_har_responses(har_path))


# ---------------------------------------------------------------------------
# Live fetch — same data the HAR carries, pulled directly via the stored PZ
# auth (shared with sync_collection's pokemon_zone_client). Removes the manual
# HAR-export step: discover packs from game-data, then fetch each odds page.
# ---------------------------------------------------------------------------

_GAME_DATA_URL = "https://www.pokemon-zone.com/api/game/game-data/"
_CATALOG_URL = "https://www.pokemon-zone.com/api/cards/search/"
_ODDS_QUERY = "?show_pack_odds=1&show_pack_slot_odds=1"


def _load_auth() -> tuple[dict, dict]:
    """Load stored PZ cookies + auth headers (written by sync_collection's
    --curl-import). Raises a friendly error if absent."""
    import pokemon_zone_client as pz
    if not pz.AUTH_CACHE.exists():
        raise FileNotFoundError(
            f"No stored auth at {pz.AUTH_CACHE.relative_to(pz.ROOT)}. Run a sync first "
            "(python3 scripts/sync_collection.py --curl-import) to store credentials, "
            "or pass a HAR with --har.")
    auth = json.loads(pz.AUTH_CACHE.read_text(encoding="utf-8"))
    return auth.get("cookies", {}), auth.get("auth_headers", {})


def responses_from_live(fetch_all: bool = False, delay: float = 0.5,
                        existing_odds: dict | None = None) -> list[tuple[str, str, str | None]]:
    """Fetch game-data, the catalog, and the needed pack-odds pages live.

    By default only packs missing from pz_pack_odds.json are fetched (the
    "new pack appeared" case); --all refetches every pack.
    """
    import time
    import pokemon_zone_client as pz

    cookies, headers = _load_auth()
    req_headers = {**headers, "Accept": "application/json, text/html, */*"}

    def get(url: str) -> str | None:
        r = pz._get(url, headers=req_headers, cookies=cookies, timeout=30)
        if r.status_code != 200:
            print(f"  WARN: {url} → HTTP {r.status_code}", file=sys.stderr)
            return None
        return r.text

    responses: list[tuple[str, str, str | None]] = []
    game_text = get(_GAME_DATA_URL)
    responses.append((_GAME_DATA_URL, "application/json", game_text))
    catalog_text = get(_CATALOG_URL)
    responses.append((_CATALOG_URL, "application/json", catalog_text))

    game = _json_body(game_text)
    if not isinstance(game, dict):
        print("  WARN: game-data unavailable; cannot discover packs.", file=sys.stderr)
        return responses

    have = set(existing_odds or {})
    fetched = 0
    for p in game.get("packs", []):
        slug, url = p.get("slug"), p.get("url")
        if not slug or not url:
            continue
        if not fetch_all and slug in have:
            continue
        odds_url = _PZ_BASE + url + _ODDS_QUERY
        print(f"  fetching odds: {slug}", file=sys.stderr)
        responses.append((odds_url, "text/html", get(odds_url)))
        fetched += 1
        if fetched > 0:
            time.sleep(delay)
    if not fetched:
        print("  (no new packs to fetch — pz_pack_odds.json is up to date)", file=sys.stderr)
    return responses


# ---------------------------------------------------------------------------
# Layer 1 — pack-odds page parsing
# ---------------------------------------------------------------------------

def parse_pack_odds_page(html: str, pack_slug: str) -> dict | None:
    """Parse a pack-odds page HTML into a pz_pack_odds.json entry, or None if it
    is not a recognisable odds page."""
    title = (_TITLE_RE.search(html) or [None, ""])[1]
    name_m = _PACK_NAME_RE.search(title)
    pack_name = name_m.group(1).strip() if name_m else pack_slug
    exp_m = _EXPANSION_RE.search(title)
    expansion_id = canonical_set_code(exp_m.group(1).upper()) if exp_m else ""
    expname_m = _EXPANSION_NAME_RE.search(title)
    expansion_name = expname_m.group(1).strip() if expname_m else ""

    cards = []
    links = list(_CARD_LINK_RE.finditer(html))
    for idx, m in enumerate(links):
        start = m.end()
        end = links[idx + 1].start() if idx + 1 < len(links) else len(html)
        window = html[start:end]

        drop_m = _DROP_CHANCE_RE.search(window)
        if not drop_m:
            continue  # link without an odds block (e.g. a "related card" link)

        card_url = m.group(1)
        set_code = canonical_set_code(m.group(2).upper())
        card_number = int(m.group(3))

        cap = _FIGCAPTION_RE.search(window)
        name = cap.group(1).strip() if cap else ""

        slot_odds: dict[str, float] = {str(s): 0.0 for s in range(1, NUM_SLOTS + 1)}
        for sm in _SLOT_ROW_RE.finditer(window):
            slot_odds[sm.group(1)] = float(sm.group(2))

        cards.append({
            "card_url": card_url,
            "name": name,
            "set_code": set_code,
            "card_number": card_number,
            "drop_chance_pct": float(drop_m.group(1)),
            "slot_odds_pct": slot_odds,
        })

    if not cards:
        return None
    if not expansion_id:
        expansion_id = cards[0]["set_code"]
    # Regular packs carry a readable expansion name; promos (no parenthesised code)
    # keep the set code, matching the existing source=pokemon_zone promo records.
    if not expansion_name:
        expansion_name = expansion_id

    return {
        "pack_name": pack_name,
        "expansion_id": expansion_id,
        "expansion_name": expansion_name,
        "expansion_slug": expansion_id.lower(),
        "pack_slug": pack_slug,
        "card_count": len(cards),
        "cards": cards,
    }


def extract_pack_odds(responses) -> dict[str, dict]:
    """Return {pack_slug: entry} for every pack-odds page in a sequence of
    (url, mimeType, body) responses (from a HAR or a live fetch)."""
    out: dict[str, dict] = {}
    for url, mime, body in responses:
        p = urlparse(url)
        if "/packs/" not in p.path or "show_pack_odds" not in p.query:
            continue
        if not body or "text/html" not in mime:
            continue
        slug = p.path.rstrip("/").split("/packs/")[-1].split("/")[0]
        entry = parse_pack_odds_page(body, slug)
        if entry:
            out[slug] = entry
    return out


# ---------------------------------------------------------------------------
# Layer 2 — identity / pack composition (report-only)
# ---------------------------------------------------------------------------

def extract_pack_composition(responses) -> dict | None:
    """From /api/game/game-data return {pack_slug: {pack_name, expansion_id,
    card_count}} and a {cardDefKey: (set_code, card_number, name)} catalog if
    /api/cards/search is also present. Returns None if neither is available."""
    game = catalog = None
    for url, _mime, body in responses:
        path = urlparse(url).path.rstrip("/")
        if path.endswith("/api/game/game-data"):
            game = _json_body(body)
        elif path.endswith("/api/cards/search"):
            catalog = _json_body(body)
    if game is None and catalog is None:
        return None

    cat_by_key: dict[str, dict] = {}
    if isinstance(catalog, dict):
        data = catalog.get("data")
        items = data.get("results", []) if isinstance(data, dict) else (data or [])
        for it in items:
            if not isinstance(it, dict):
                continue
            url = it.get("url", "")
            mm = re.match(r"/cards/([a-z0-9-]+)/(\d+)/", url)
            if mm:
                cat_by_key[it.get("cardDefKey")] = {
                    "set_code": canonical_set_code(mm.group(1).upper()),
                    "card_number": int(mm.group(2)),
                    "name": it.get("name"),
                }

    packs: dict[str, dict] = {}
    if isinstance(game, dict):
        by_id = {p.get("packId"): p for p in game.get("packs", [])}
        comp = {pc.get("packId"): pc.get("cardIds", []) for pc in game.get("packCardIds", [])}
        for pid, p in by_id.items():
            slug = p.get("slug")
            card_ids = comp.get(pid, [])
            packs[slug] = {
                "pack_name": p.get("name"),
                "expansion_id": canonical_set_code(
                    (p.get("sku", {}).get("expansion", {}) or {}).get("expansionId", "")),
                "card_count": len(card_ids),
                "cards": [cat_by_key[c] for c in card_ids if c in cat_by_key],
            }
    return {"packs": packs, "catalog": cat_by_key}


# ---------------------------------------------------------------------------
# Reporting / merge
# ---------------------------------------------------------------------------

def _load_snapshot_meta(set_code: str) -> dict[int, dict]:
    """Return {card_number: {rarity, pokemon_type}} from the independent snapshots
    (bulbapedia preferred, serebii fallback) for a set. Used to supply the rarity
    and type that the odds page does not carry."""
    out: dict[int, dict] = {}
    for src in ("bulbapedia", "serebii"):
        path = SOURCES_DIR / src / f"{set_code}.json"
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        cards = data.get("cards", data) if isinstance(data, dict) else data
        items = cards if isinstance(cards, list) else [
            {"card_number": int(k), **v} for k, v in cards.items() if str(k).isdigit()]
        for c in items:
            cn = c.get("card_number")
            if cn is None:
                continue
            slot = out.setdefault(int(cn), {})
            if not slot.get("rarity") and c.get("rarity"):
                slot["rarity"] = c["rarity"]
            if not slot.get("pokemon_type") and c.get("pokemon_type"):
                slot["pokemon_type"] = c["pokemon_type"]
    return out


def build_pack_sources_records(odds: dict[str, dict],
                               existing_coords: set[tuple[str, int]]) -> list[dict]:
    """Generate pack_sources records for cards in the ingested odds packs that are
    not already in pack_sources. Mirrors the existing source=pokemon_zone promo
    schema; rarity/type come from the independent snapshots."""
    snap_cache: dict[str, dict] = {}
    new_records: list[dict] = []
    seen: set[tuple[str, int]] = set()
    for entry in odds.values():
        exp = entry["expansion_id"]
        exp_name = entry.get("expansion_name") or exp
        snap = snap_cache.setdefault(exp, _load_snapshot_meta(exp))
        for c in entry["cards"]:
            key = (c["set_code"], c["card_number"])
            if key in existing_coords or key in seen:
                continue
            seen.add(key)
            meta = snap.get(c["card_number"], {})
            new_records.append({
                "set_code": c["set_code"],
                "card_number": c["card_number"],
                "card_name": c["name"],
                "pack_name": entry["pack_name"],
                "expansion": exp_name,
                "rarity": normalize_rarity(meta.get("rarity")) or "promo",
                "card_category": None,
                "pokemon_type": meta.get("pokemon_type"),
                "is_ex": is_ex_from_name(c["name"]),
                "source_url": _PZ_BASE + c["card_url"],
                "source": "pokemon_zone",
                "confidence": "high",
                "notes": (f"{exp} card from {entry['pack_name']}; "
                          f"PZ drop_chance={c['drop_chance_pct']}% (PZ-ingested)"),
            })
    return new_records


def load_existing_odds() -> dict:
    if PZ_PACK_ODDS_JSON.exists():
        return json.loads(PZ_PACK_ODDS_JSON.read_text(encoding="utf-8"))
    return {}


def pack_sources_coords() -> set[tuple[str, int]]:
    if not PACK_SOURCES_JSON.exists():
        return set()
    recs = load_records(PACK_SOURCES_JSON)
    out = set()
    for r in recs:
        sc = canonical_set_code(str(r.get("set_code", "")).upper())
        cn = r.get("card_number")
        if sc and cn is not None:
            try:
                out.add((sc, int(cn)))
            except (TypeError, ValueError):
                pass
    return out


def diff_against_existing(slug: str, parsed: dict, existing: dict) -> list[str]:
    """Return human-readable mismatch lines for a pack already in pz_pack_odds."""
    cur = existing.get(slug)
    if not cur:
        return []
    diffs = []
    cur_by = {c["card_number"]: c for c in cur.get("cards", [])}
    for c in parsed["cards"]:
        o = cur_by.get(c["card_number"])
        if not o:
            diffs.append(f"  + new card {c['set_code']}/{c['card_number']} {c['name']}")
            continue
        if abs(o.get("drop_chance_pct", 0) - c["drop_chance_pct"]) > 1e-9:
            diffs.append(f"  ~ {c['set_code']}/{c['card_number']} drop {o.get('drop_chance_pct')}→{c['drop_chance_pct']}")
        if o.get("slot_odds_pct") != c["slot_odds_pct"]:
            diffs.append(f"  ~ {c['set_code']}/{c['card_number']} slot_odds {o.get('slot_odds_pct')}→{c['slot_odds_pct']}")
    return diffs


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Ingest Pokémon Zone reference data. Live fetch by default "
                    "(uses stored sync auth — no manual HAR needed); pass --har to "
                    "ingest browser captures instead.")
    ap.add_argument("--har", nargs="+", type=Path, metavar="FILE",
                    help="Ingest from HAR capture(s) instead of fetching live")
    ap.add_argument("--all", action="store_true",
                    help="Live mode: refetch every pack's odds, not just new ones")
    ap.add_argument("--delay", type=float, default=0.5,
                    help="Live mode: seconds between page fetches (default 0.5)")
    ap.add_argument("--apply", action="store_true", help="Write merged odds into pz_pack_odds.json")
    ap.add_argument("--write-pack-sources", action="store_true",
                    help="Also append pack_sources.json records for ingested-pack cards "
                         "missing from it")
    ap.add_argument("--rebuild-refs", action="store_true",
                    help="After --write-pack-sources, run build_card_reference.py to "
                         "incorporate the new cards (closes the loop for validation)")
    ap.add_argument("--verify-only", action="store_true",
                    help="Re-parse and diff against current pz_pack_odds.json; never write")
    args = ap.parse_args()

    existing = load_existing_odds()

    # Gather (url, mime, body) responses from the chosen source.
    responses: list[tuple[str, str, str | None]] = []
    if args.har:
        for har in args.har:
            if not har.exists():
                print(f"ERROR: {har} not found", file=sys.stderr)
                return 1
            responses += responses_from_har(har)
    else:
        try:
            responses = responses_from_live(
                fetch_all=args.all, delay=args.delay, existing_odds=existing)
        except FileNotFoundError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 1

    all_odds = extract_pack_odds(responses)
    composition = extract_pack_composition(responses)

    print(f"Parsed pack-odds pages: {len(all_odds)}")
    mismatch = False
    for slug, entry in sorted(all_odds.items()):
        status = "NEW" if slug not in existing else "update"
        print(f"  [{status}] {slug}: {entry['pack_name']} ({entry['expansion_id']}) — {entry['card_count']} cards")
        diffs = diff_against_existing(slug, entry, existing)
        for line in diffs:
            mismatch = True
            print(line)
        if slug in existing and not diffs:
            print("    ✓ matches existing pz_pack_odds.json exactly")

    # Report-only identity layer: which packs are known to PZ but have no odds yet.
    if composition:
        have = set(existing) | set(all_odds)
        missing = {s: p for s, p in composition["packs"].items() if s not in have}
        if missing:
            print(f"\nPacks known to PZ but missing odds ({len(missing)}):")
            for slug, p in sorted(missing.items()):
                print(f"  - {slug}: {p['pack_name']} ({p['expansion_id']}, {p['card_count']} cards)"
                      " — capture its ?show_pack_odds=1 page")
        ps_coords = pack_sources_coords()
        new_cards = []
        for p in composition["packs"].values():
            for c in p["cards"]:
                if (c["set_code"], c["card_number"]) not in ps_coords:
                    new_cards.append(c)
        if new_cards:
            uniq = {(c["set_code"], c["card_number"]): c for c in new_cards}
            print(f"\nCards in PZ not yet in pack_sources.json ({len(uniq)}):")
            for (sc, cn), c in sorted(uniq.items()):
                print(f"  - {sc}/{cn} {c['name']}")

    if args.verify_only:
        if mismatch:
            print("\nVERIFY FAILED: parsed odds disagree with pz_pack_odds.json", file=sys.stderr)
            return 2
        print("\nVERIFY OK: parsed odds reproduce pz_pack_odds.json")
        return 0

    if args.apply:
        if not all_odds:
            print("Nothing to write (no pack-odds pages parsed).", file=sys.stderr)
            return 1
        merged = dict(existing)
        merged.update(all_odds)
        PZ_PACK_ODDS_JSON.write_text(
            json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nWrote {PZ_PACK_ODDS_JSON} ({len(merged)} packs)")

        if args.write_pack_sources:
            ps = json.loads(PACK_SOURCES_JSON.read_text(encoding="utf-8"))
            recs = ps["records"] if isinstance(ps, dict) and "records" in ps else ps
            new_recs = build_pack_sources_records(all_odds, pack_sources_coords())
            if new_recs:
                recs.extend(new_recs)
                recs.sort(key=lambda r: (str(r.get("set_code", "")), r.get("card_number") or 0))
                PACK_SOURCES_JSON.write_text(
                    json.dumps(ps, indent=2, ensure_ascii=False), encoding="utf-8")
                print(f"Added {len(new_recs)} pack_sources record(s): "
                      + ", ".join(f"{r['set_code']}/{r['card_number']}" for r in new_recs))
                if args.rebuild_refs:
                    import subprocess
                    print("Rebuilding card_reference.json…")
                    rc = subprocess.run(
                        [sys.executable, str(Path(__file__).with_name("build_card_reference.py"))]
                    ).returncode
                    # build_card_reference exits 2 on pre-existing data conflicts but
                    # still writes; only a hard failure (1) should propagate.
                    if rc == 1:
                        print("  ERROR: build_card_reference.py failed", file=sys.stderr)
                        return 1
                    # Rebuild the pull-probability model too: EV/recommendations only
                    # score packs present in it, so a newly-ingested pack would stay
                    # invisible in EV until this runs. Doing it here closes that loop.
                    print("Rebuilding pull_probability_model.json…")
                    rc = subprocess.run(
                        [sys.executable, str(Path(__file__).with_name("build_pull_probability_model.py"))]
                    ).returncode
                    if rc != 0:
                        print("  ERROR: build_pull_probability_model.py failed", file=sys.stderr)
                        return 1
                    print("Done. Re-run run_recommendations.py to pick up the new cards.")
                else:
                    print("Next: python3 scripts/build_card_reference.py   "
                          "(or pass --rebuild-refs to do it automatically)")
            else:
                print("No new pack_sources records needed.")
    else:
        print("\n(dry-run — pass --apply to write pz_pack_odds.json)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
