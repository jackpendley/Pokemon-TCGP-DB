#!/usr/bin/env python3
"""
Validate collection.json set_code/card_number assignments against external sources.

For each entry that has set_code + card_number, confirms:
  - card_name matches card_reference.json (offline, cross-validated across TCGdex,
    Serebii, and Bulbapedia — covers all 20 sets, not just A1–B2a)
  - HP matches (TCGdex cache or ext_ref), for Pokemon entries

Primary source: card_reference.json (frozen, multi-source — covers all 20 sets)
Fallback source: TCGdex API + local ext_ref (for brand-new cards not yet in reference)

Run python3 scripts/fetch_source_snapshots.py && python3 scripts/build_card_reference.py
to refresh the reference when a new pack ships.

Usage:
    python3 scripts/validate_collection_coords.py
    python3 scripts/validate_collection_coords.py --no-fetch   # fully offline
    python3 scripts/validate_collection_coords.py --set A1     # one set only
    python3 scripts/validate_collection_coords.py --fix-cache  # re-fetch TCGdex HP cache

Exit codes:
    0  All entries validated
    1  One or more validation failures found
"""

import argparse
import json
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict, Counter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _collection_io import (ext_ref_by_coord, load_collection_json,
                            norm_card_name as norm_name, is_cache_fresh as _is_cache_fresh,
                            pack_sources_by_coord as _ps_by_coord,
                            card_reference_by_coord as _card_ref_by_coord,
                            ROOT, COLLECTION_JSON as COLLECTION,
                            PACK_SOURCES_JSON as PACK_SOURCES,
                            CARD_REF_JSON as CARD_REF,
                            EXT_REF_JSON as EXT_REF,
                            TCGDEX_CACHE_JSON as TCGDEX_CACHE)
from coord_resolver import _name_agrees

TCGDEX_BASE    = "https://api.tcgdex.net/v2/en"
REQUEST_DELAY  = 0.35   # seconds between API calls
REQUEST_TIMEOUT = 12


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------

def load_collection() -> list[dict]:
    return load_collection_json(COLLECTION)[1]["collection"]


def load_card_reference() -> dict[tuple[str, int], dict]:
    return _card_ref_by_coord(CARD_REF)


def load_pack_sources() -> dict[tuple[str, int], dict]:
    return _ps_by_coord(PACK_SOURCES)


def load_cache() -> dict:
    if TCGDEX_CACHE.exists():
        return json.loads(TCGDEX_CACHE.read_text(encoding="utf-8"))
    return {}


def save_cache(cache: dict) -> None:
    TCGDEX_CACHE.parent.mkdir(parents=True, exist_ok=True)
    TCGDEX_CACHE.write_text(
        json.dumps(cache, indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# TCGdex API
# ---------------------------------------------------------------------------

def _tcgdex_sets_available() -> set[str] | None:
    """Return set of set IDs available in TCGdex Pocket series, or None on failure."""
    url = f"{TCGDEX_BASE}/series/tcgp"
    req = urllib.request.Request(url, headers={"User-Agent": "ptcgp-validator/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            data = json.loads(resp.read())
        return {s["id"].upper() for s in data.get("sets", [])}
    except Exception as e:
        print(f"  WARN: TCGdex set list fetch failed ({e}) — falling back to cache", file=sys.stderr)
        return None


def fetch_tcgdex_card(set_code: str, card_number: int) -> dict | None:
    """
    Fetch card data from TCGdex. Returns a dict with the fields the validator
    actually checks (name, hp) plus source; or an {"error": ...} dict.
    Uses zero-padded 3-digit card number: A1-033.
    """
    url = f"{TCGDEX_BASE}/cards/{set_code}-{card_number:03d}"
    req = urllib.request.Request(url, headers={"User-Agent": "ptcgp-validator/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            data = json.loads(resp.read())
        # Store only what validate_entry consumes — name + hp. (If a future check
        # needs rarity/stage/types, add them here and re-run with --fix-cache.)
        return {
            "name":    data.get("name"),
            "hp":      data.get("hp"),
            "source":  "tcgdex",
        }
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"error": "not_found", "source": "tcgdex"}
        return {"error": f"http_{e.code}", "source": "tcgdex"}
    except Exception as e:
        return {"error": str(e), "source": "tcgdex"}


# ---------------------------------------------------------------------------
# Name normalization
# ---------------------------------------------------------------------------

def names_match(a: str, b: str) -> bool:
    """Loose name match: normalise both strings and compare."""
    return norm_name(a) == norm_name(b)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_entry(
    entry: dict,
    pack_sources: dict,
    ext_ref: dict,
    cache: dict,
    tcgdex_sets: set[str],
    fetch: bool,
    fetch_stats: dict | None = None,
    covered_sets: frozenset[str] | None = None,
    limitless_lookup=None,
    card_ref: dict | None = None,
) -> dict:
    """
    Validate one collection entry. Returns a result dict with:
      status: "ok" | "mismatch" | "not_found" | "no_coords" | "skipped"
      issues: list of human-readable issue strings

    fetch_stats: optional mutable dict; its "count" key is incremented each time
    a live TCGdex fetch is performed (covers both new lookups and stale refreshes).
    """
    sc = str(entry.get("set_code") or "").upper().strip()
    cn_raw = entry.get("card_number")
    name = entry.get("name", "")

    if not sc or cn_raw is None:
        return {"status": "no_coords", "issues": []}

    try:
        cn = int(cn_raw)
    except (TypeError, ValueError):
        return {"status": "mismatch", "issues": [f"invalid card_number: {cn_raw}"],
                "serious": True, "set_code": sc, "card_number": cn_raw, "source": "local"}

    key = (sc, cn)
    # Two severity buckets, kept structurally separate so a serious issue can't be
    # recorded without counting as serious (no hand-maintained flag to forget):
    #   serious  = the coord points at a wrong/nonexistent card → mis-attributes
    #              counts in set-aware EV → fatal.
    #   advisory = an HP data-quality diff (typo / upstream change / wrong variant)
    #              → warn only.
    serious_issues: list[str] = []
    advisory_issues: list[str] = []
    ref_data: dict | None = None

    # ── Source 1: TCGdex ────────────────────────────────────────────────────
    cache_key = f"{sc}-{cn:03d}"
    if sc in tcgdex_sets:
        cached_entry = cache.get(cache_key)
        # Re-fetch when: not cached, a transient error (not None/not_found), or stale.
        needs_fetch = (
            cached_entry is None
            or cached_entry.get("error") not in (None, "not_found")
            or not _is_cache_fresh(cached_entry)
        )
        if needs_fetch:
            if fetch:
                ref_data_raw = fetch_tcgdex_card(sc, cn)
                ref_data_raw["cached_at"] = datetime.now(timezone.utc).isoformat()
                cache[cache_key] = ref_data_raw
                if fetch_stats is not None:
                    fetch_stats["count"] = fetch_stats.get("count", 0) + 1
                time.sleep(REQUEST_DELAY)
            else:
                # Offline: use whatever we have (even if stale) rather than nothing
                ref_data_raw = cached_entry
        else:
            ref_data_raw = cached_entry

        if ref_data_raw and not ref_data_raw.get("error"):
            ref_data = ref_data_raw
        elif ref_data_raw and ref_data_raw.get("error") == "not_found":
            # Card not in TCGdex — fall through to local validation only (no issue raised)
            pass

    # ── Source 2: local pack_sources + ext_ref (fallback or supplement) ────
    ps_rec  = pack_sources.get(key)
    ext_rec = ext_ref.get(key)

    # Name validation — a name mismatch means (set_code, card_number) points at the
    # wrong card. This is serious: build_pack_ev attributes owned counts by coord, so
    # a wrong coord silently skews EV.
    #
    # Priority: card_reference (offline, 3-source validated, covers all 20 sets)
    #   > TCGdex API cache (A1–B2a only, fallback for brand-new cards)
    #   > local pack_sources (same-origin, last resort)
    ind_name = ind_source = None

    # ── Primary: card_reference (offline) ─────────────────────────────────────
    if card_ref is not None:
        ref_rec = card_ref.get(key)
        if ref_rec:
            ind_name = ref_rec.get("name", "")
            ref_confidence = ref_rec.get("confidence", "unconfirmed")
            ind_source = f"card_reference({ref_confidence})"

    # ── Fallback: TCGdex API cache (for cards absent from reference) ──────────
    if ind_name is None and ref_data:
        ind_name, ind_source = ref_data["name"], "tcgdex"

    # ── Fallback: live Limitless (for brand-new cards) ────────────────────────
    if ind_name is None and limitless_lookup is not None:
        ll = limitless_lookup(sc, cn)
        if ll:
            ind_name, ind_source = ll, "limitless"

    if ind_name is not None:
        # card_reference names are pre-reconciled (forme-tolerant) — use _name_agrees.
        # TCGdex names are exact → use strict compare. Limitless is scrape-sourced → forme-tolerant.
        if ind_source and "tcgdex" in ind_source and "card_reference" not in ind_source:
            agrees = names_match(name, ind_name)
        else:
            agrees = _name_agrees(name, ind_name)
        if not agrees:
            sev_source = ind_source or "unknown"
            if ind_source and "limitless" in ind_source:
                advisory_issues.append(f"name mismatch: collection='{name}' vs limitless='{ind_name}'"
                                       f" — verify {sc}/{cn} (scrape-sourced; run reconcile_coords_from_pz)")
            else:
                serious_issues.append(f"name mismatch: collection='{name}' vs {sev_source}='{ind_name}'")
    elif ps_rec:
        ps_name = ps_rec.get("card_name", "")
        if not names_match(name, ps_name):
            serious_issues.append(f"name mismatch: collection='{name}' vs pack_sources='{ps_name}'")
    else:
        # Coord in neither card_reference nor pack_sources — brand-new card.
        set_covered = covered_sets is not None and sc in covered_sets
        if set_covered:
            serious_issues.append(f"coord {sc}/{cn} not found in pack_sources or card_reference "
                                  f"(set {sc} is known — possible wrong coord)")
        else:
            advisory_issues.append(f"coord {sc}/{cn} in uncovered set {sc} — cannot validate "
                                   f"(run fetch_source_snapshots + build_card_reference)")

    # HP validation (Pokemon only) — advisory, NOT fatal. An HP mismatch with a
    # matching name is ambiguous: it can mean (a) the coord points at the WRONG
    # same-name VARIANT (e.g. A1 vs A2a Charmander — the real corruption that skews
    # set-aware EV), or (b) a benign HP typo / an upstream TCGdex HP change. We can't
    # tell (a) from (b) here, and making it fatal would halt the pipeline on every
    # upstream HP edit — so it's surfaced as advisory with a note to investigate.
    entry_hp = entry.get("hp")
    if entry_hp is not None:
        if ref_data and ref_data.get("hp") is not None:
            if entry_hp != ref_data["hp"]:
                advisory_issues.append(f"HP mismatch: collection={entry_hp} vs TCGdex={ref_data['hp']}"
                                       f" — possible wrong-variant coord, verify {sc}/{cn}")
        elif ext_rec and ext_rec.get("hp") is not None:
            if entry_hp != ext_rec["hp"]:
                advisory_issues.append(f"HP mismatch: collection={entry_hp} vs ext_ref={ext_rec['hp']}"
                                       f" — possible wrong-variant coord, verify {sc}/{cn}")

    # Attack names in collection.json were manually entered and use different naming
    # conventions than TCGdex — skip attack validation to avoid false positives.

    # Record how the entry was checked: against an independent source (TCGdex or
    # live Limitless) or only local ext_ref/pack_sources (near-circular — same data
    # that assigned the coord).
    source = ind_source if ind_name else "local"

    # serious is derived from the bucket, not a hand-set flag: serious issues are
    # listed first so the most important ones surface at the top of the report.
    issues = serious_issues + advisory_issues
    if issues:
        return {"status": "mismatch", "issues": issues, "serious": bool(serious_issues),
                "set_code": sc, "card_number": cn, "source": source}
    return {"status": "ok", "issues": [], "serious": False, "source": source}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Validate collection.json coord assignments.")
    parser.add_argument("--no-fetch", action="store_true",
                        help="Use cache only, do not hit TCGdex API")
    parser.add_argument("--fix-cache", action="store_true",
                        help="Re-fetch all TCGdex entries (ignore cache)")
    parser.add_argument("--set", metavar="SET_CODE",
                        help="Validate only this set")
    args = parser.parse_args()

    fetch = not args.no_fetch
    entries      = load_collection()
    pack_sources = load_pack_sources()
    ext_ref      = ext_ref_by_coord(EXT_REF)
    cache        = {} if args.fix_cache else load_cache()
    card_ref_raw = load_card_reference()
    if card_ref_raw:
        print(f"  card_reference: {len(card_ref_raw)} coords (offline, 3-source validated)")
        card_ref: dict | None = card_ref_raw
    else:
        print("  WARN: card_reference.json not found or empty — name validation falls back to "
              "TCGdex+local. Run fetch_source_snapshots + build_card_reference to rebuild.",
              file=sys.stderr)
        card_ref = None

    # Set codes pack_sources actually covers — used to tell a "wrong card number in
    # a known set" (serious) from an "uncovered new set, can't validate yet" (advisory).
    covered_sets = frozenset(sc for (sc, _cn) in pack_sources)

    # TCGdex set list (for HP cache lookups — name check now uses card_reference).
    if fetch:
        tcgdex_sets = _tcgdex_sets_available() or {k.rsplit("-", 1)[0].upper() for k in cache}
    else:
        tcgdex_sets = {k.rsplit("-", 1)[0].upper() for k in cache}

    # Limitless fallback for brand-new cards absent from card_reference.
    # Best-effort: if resolver can't load, those entries fall back to local-only.
    limitless_lookup = resolver = None
    try:
        from coord_resolver import CoordResolver
        resolver = CoordResolver(fetch=fetch, tcgdex_sets=tcgdex_sets)
        limitless_lookup = resolver._limitless_name
    except Exception as e:
        print(f"  WARN: Limitless fallback unavailable ({e})", file=sys.stderr)

    # Filter by --set
    if args.set:
        entries = [e for e in entries if str(e.get("set_code") or "").upper() == args.set.upper()]

    results = defaultdict(list)
    fetch_stats = {"count": 0}

    print(f"\nValidating {len(entries)} entries…")
    for entry in entries:
        sc = str(entry.get("set_code") or "").upper().strip()
        cn_raw = entry.get("card_number")
        if not sc or cn_raw is None:
            results["no_coords"].append(entry)
            continue

        result = validate_entry(entry, pack_sources, ext_ref, cache,
                                tcgdex_sets, fetch, fetch_stats, covered_sets,
                                limitless_lookup, card_ref=card_ref)
        results[result["status"]].append((entry, result))

    # Save updated cache if any live fetch occurred (new lookups or stale refreshes)
    if fetch_stats["count"] > 0:
        save_cache(cache)
        print(f"  Cached {fetch_stats['count']} TCGdex lookups → {TCGDEX_CACHE.relative_to(ROOT)}")
    if resolver is not None:
        resolver.save()   # persist any new Limitless name lookups

    # ── Report ───────────────────────────────────────────────────────────────
    ok_count       = len(results["ok"])
    mismatch_count = len(results["mismatch"])
    no_coords      = len(results["no_coords"])

    # Independent (TCGdex) vs local-only cross-check coverage. A "local" check
    # compares against the same ext_ref/pack_sources that assigned the coord, so
    # it is near-circular and far weaker than a TCGdex cross-check. Surfacing the
    # split prevents a green "PASS" from being mistaken for full verification —
    # especially under --no-fetch, where uncached sets get only local checks.
    checked = results["ok"] + results["mismatch"]
    cardref_checked   = sum(1 for _, r in checked if r.get("source", "").startswith("card_reference"))
    tcgdex_checked    = sum(1 for _, r in checked if r.get("source") == "tcgdex")
    limitless_checked = sum(1 for _, r in checked if r.get("source") == "limitless")
    local_only        = sum(1 for _, r in checked if r.get("source") == "local")
    independent       = cardref_checked + tcgdex_checked + limitless_checked

    # Ownership-confidence breakdown: card_reference's 'confidence' (confirmed/single/conflict)
    # reflects how many independent sources agreed on the card's identity. PZ is the only
    # source of WHAT you own, so surfacing this flags owned cards whose printing isn't fully
    # cross-validated (e.g. a name only one source confirmed, or a cross-set/A4b ambiguity).
    cardref_conf: Counter = Counter()
    low_conf_owned: list[tuple[dict, str]] = []
    for entry, r in checked:
        src = r.get("source", "")
        if src.startswith("card_reference(") and src.endswith(")"):
            conf = src[len("card_reference("):-1]
            cardref_conf[conf] += 1
            if conf != "confirmed":
                low_conf_owned.append((entry, conf))

    print(f"\n── Validation Results ──────────────────────────────────────────")
    print(f"  OK:           {ok_count}")
    print(f"  Mismatches:   {mismatch_count}")
    print(f"  No coords:    {no_coords}")
    print(f"  Cross-checked vs card_reference (offline, 3-source): {cardref_checked} "
          f"(confirmed: {cardref_conf['confirmed']}, single: {cardref_conf['single']}, "
          f"conflict: {cardref_conf['conflict']})")
    print(f"  Cross-checked vs TCGdex (fallback):  {tcgdex_checked}")
    print(f"  Cross-checked vs Limitless (fallback): {limitless_checked}")
    print(f"  Local-only (ext_ref/pack_sources, weaker): {local_only}")

    if low_conf_owned:
        print(f"\n── Owned cards with <confirmed identity ({len(low_conf_owned)}) — verify printing ──")
        for entry, conf in low_conf_owned:
            print(f"  [{conf}] {entry.get('name')} {entry.get('set_code')}/{entry.get('card_number')}")

    serious_count = sum(1 for _, r in results["mismatch"] if r.get("serious"))
    advisory_count = mismatch_count - serious_count

    if mismatch_count:
        print(f"\n── Mismatches ──────────────────────────────────────────────────")
        for entry, result in results["mismatch"]:
            sc   = entry.get("set_code", "?")
            cn   = entry.get("card_number", "?")
            sev  = "SERIOUS" if result.get("serious") else "advisory"
            print(f"  [{entry.get('name')}] {sc}/{cn} (vs {result.get('source')}) [{sev}]")
            for issue in result["issues"]:
                print(f"    ✗ {issue}")

    # Exit-code severity (the pipeline maps these to FATAL vs WARN):
    #   2 = serious (coord points at a wrong/nonexistent card → would skew set-aware EV)
    #   1 = advisory-only (HP data-quality diffs)
    #   0 = clean
    if serious_count:
        print(f"\nFAIL: {serious_count} serious coord error(s) "
              f"({advisory_count} advisory HP diff(s))")
        return 2
    # No serious errors. A cold cache where NOTHING was independently cross-checked
    # is itself an advisory condition — the validator verified nothing against an
    # authoritative source, so it must not report a plain green PASS. Return 1 so the
    # pipeline surfaces a WARN instead of "OK".
    if checked and independent == 0:
        print(f"\nWARN (LOCAL-ONLY): 0 of {len(checked)} entries cross-checked vs an "
              f"independent source (cold cache) — verified only against local data. "
              f"Run with fetch to verify.")
        return 1

    if advisory_count:
        print(f"\nWARN: {advisory_count} advisory diff(s) — no serious coord errors")
        return 1

    print(f"\nPASS: {cardref_checked} cross-checked vs card_reference (offline), "
          f"{tcgdex_checked} vs TCGdex, {limitless_checked} vs Limitless, "
          f"{local_only} local-only")
    return 0


if __name__ == "__main__":
    sys.exit(main())
