#!/usr/bin/env python3
"""
Sync collection.json from Pokemon Zone (pokemon-zone.com).

The user must have linked their Nintendo Account to Pokemon Zone first.

EASIEST — Browser bookmarklet (always works, no auth to manage):
    1. Add the bookmarklet from CLAUDE.md section 4 to your bookmarks bar.
    2. Open pokemon-zone.com/collection-tracker/ (must be logged in).
    3. Click the bookmarklet → pz_collection.json downloads automatically.
    4. Run:  python3 scripts/sync_collection.py --json-import pz_collection.json

FIRST-TIME SETUP (Cloudflare-safe, enables headless syncs):
    python3 scripts/sync_collection.py --curl-import
    # Opens instructions; paste a cURL from browser DevTools once.
    # Auth is stored in data/sync/.auth.json (gitignored).

SUBSEQUENT SYNCS (headless, no browser):
    python3 scripts/sync_collection.py            # uses stored auth
    python3 scripts/sync_collection.py --dry-run  # show diff, no writes

WHEN AUTH EXPIRES (re-run curl import):
    python3 scripts/sync_collection.py --curl-import

ONE-SHOT HAR IMPORT (no persistent auth):
    python3 scripts/sync_collection.py --har-import www.pokemon-zone.com.har

OTHER:
    python3 scripts/sync_collection.py --discover # inspect API responses (Playwright)
    python3 scripts/sync_collection.py --login    # headed Playwright login (may hit Cloudflare)

Exit codes:
    0  Success — collection.json updated and validated
    1  Fatal error (auth missing/expired, API failure, validation failure)
    2  Partial — review queue has items (new/ambiguous cards); matched cards updated
    3  Blocked — unresolved review queue; run --force or resolve queue first
"""

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from rapidfuzz import process as fuzz_process

ROOT            = Path(__file__).resolve().parent.parent
COLLECTION_JSON = ROOT / "collection.json"
PACK_SOURCES    = ROOT / "data" / "reference" / "pack_sources.json"
EXT_REF         = ROOT / "data" / "reference" / "external" / "external_card_reference.json"
REVIEW_QUEUE    = ROOT / "data" / "sync" / "sync_review_queue.json"
SYNC_DIR        = ROOT / "data" / "sync"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class PZCard:
    set_code:    str | None
    card_number: int | None
    raw_name:    str
    count:       int
    raw_record:  dict = field(default_factory=dict, repr=False)


@dataclass
class MatchResult:
    status:        str   # MATCHED | NEW_CARD | UNMATCHED | AMBIGUOUS
    pz_card:       PZCard
    entry:         dict | None = None          # the collection.json entry (MATCHED only)
    entry_index:   int | None = None
    canonical_name: str | None = None
    candidates:    list = field(default_factory=list)  # AMBIGUOUS


@dataclass
class CountChange:
    entry:       dict
    entry_index: int
    old_count:   int
    new_count:   int


# ---------------------------------------------------------------------------
# JSON / reference loaders
# ---------------------------------------------------------------------------

def _strip_comments(text: str) -> str:
    return re.sub(r"//[^\n]*", "", text)


def load_collection() -> tuple[str, dict]:
    """Return (raw_text, parsed_dict) for collection.json."""
    raw = COLLECTION_JSON.read_text(encoding="utf-8")
    data = json.loads(_strip_comments(raw))
    return raw, data


def load_pack_sources() -> dict[tuple[str, int], dict]:
    """Return {(set_code, card_number) → record}."""
    data = json.loads(PACK_SOURCES.read_text(encoding="utf-8"))
    records = data.get("records", data) if isinstance(data, dict) else data
    result: dict[tuple[str, int], dict] = {}
    for r in records:
        sc = str(r.get("set_code", "")).upper().strip()
        cn_raw = r.get("card_number")
        try:
            cn = int(cn_raw)
        except (TypeError, ValueError):
            continue
        result[(sc, cn)] = r
    return result


def load_ext_ref() -> dict[str, list[dict]]:
    """Return {normalized_name → [records with hp/set_code/number]}."""
    records = json.loads(EXT_REF.read_text(encoding="utf-8"))
    result: dict[str, list[dict]] = {}
    for r in records:
        nn = r.get("normalized_name") or _normalize(r.get("name", ""))
        result.setdefault(nn, []).append(r)
    return result


# ---------------------------------------------------------------------------
# Name normalization
# ---------------------------------------------------------------------------

def _normalize(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "_", name.lower().strip()).strip("_")


# ---------------------------------------------------------------------------
# Pokemon Zone record → PZCard
# ---------------------------------------------------------------------------

def _guess_field(record: dict, *candidates: str):
    """Return first value found among candidate field names (case-insensitive)."""
    lower = {k.lower(): v for k, v in record.items()}
    for c in candidates:
        v = lower.get(c.lower())
        if v is not None:
            return v
    return None


def normalize_pz_record(raw: dict) -> PZCard | None:
    """Convert a raw Pokemon Zone API record to a PZCard."""
    # Card name
    name = _guess_field(raw, "cardName", "name", "card_name", "pokemonName", "title")
    if not name:
        return None
    name = str(name).strip()

    # Count / quantity owned
    count_raw = _guess_field(raw, "ownedCount", "count", "quantity", "owned",
                              "amount", "copies", "cardCount")
    try:
        count = int(count_raw)
    except (TypeError, ValueError):
        count = 0
    if count <= 0:
        return None

    # Set code
    sc_raw = _guess_field(raw, "setCode", "set_code", "expansionCode", "set",
                           "expansion", "series")
    set_code = str(sc_raw).upper().strip() if sc_raw else None

    # Card number
    cn_raw = _guess_field(raw, "cardNumber", "card_number", "number", "cardId",
                           "collectorNumber")
    # Pokemon Zone may encode as "A1-004" or just 4 or "4"
    card_number: int | None = None
    if cn_raw is not None:
        # Try stripping set prefix if present (e.g. "A1-004" → 4)
        cn_str = str(cn_raw).strip()
        m = re.search(r"(\d+)$", cn_str.split("-")[-1])
        if m:
            try:
                card_number = int(m.group(1))
            except ValueError:
                card_number = None

    return PZCard(
        set_code=set_code,
        card_number=card_number,
        raw_name=name,
        count=count,
        raw_record=raw,
    )


# ---------------------------------------------------------------------------
# Matching logic
# ---------------------------------------------------------------------------

# Known PROMO-B card-number → canonical collection.json name overrides.
# PZ's catalog returns "Zygarde" for these slots; the correct names use form suffixes.
_PROMO_B_OVERRIDES: dict[int, str] = {
    51: "Zygarde 10% Forme",
    52: "Zygarde 50% Forme",
}


def _build_name_index(collection: list[dict]) -> dict[str, list[int]]:
    """Return {normalized_name → [entry_indices]}."""
    idx: dict[str, list[int]] = {}
    for i, entry in enumerate(collection):
        nn = _normalize(entry.get("name", ""))
        idx.setdefault(nn, []).append(i)
    return idx


def _build_pack_name_list(pack_sources: dict) -> list[str]:
    return list({r["card_name"] for r in pack_sources.values()})


def match_pz_cards(
    pz_cards: list[PZCard],
    collection: list[dict],
    pack_sources: dict[tuple[str, int], dict],
    ext_ref: dict[str, list[dict]],
) -> list[MatchResult]:
    name_index = _build_name_index(collection)
    pack_name_list = _build_name_list(pack_sources)
    results: list[MatchResult] = []

    for pz in pz_cards:
        result = _match_one(pz, collection, name_index, pack_sources, pack_name_list, ext_ref)
        results.append(result)

    return results


def _build_name_list(pack_sources: dict) -> list[str]:
    seen: dict[str, None] = {}
    for r in pack_sources.values():
        seen[r["card_name"]] = None
    return list(seen)


def _match_one(
    pz: PZCard,
    collection: list[dict],
    name_index: dict[str, list[int]],
    pack_sources: dict,
    pack_name_list: list[str],
    ext_ref: dict[str, list[dict]],
) -> MatchResult:
    # Pre-step: PROMO-B overrides (PZ catalog returns wrong names for these slots)
    canonical_name: str | None = None
    if pz.set_code == "PROMO-B" and pz.card_number in _PROMO_B_OVERRIDES:
        canonical_name = _PROMO_B_OVERRIDES[pz.card_number]

    # Step 1: resolve canonical name via (set_code, card_number) → pack_sources
    if canonical_name is None and pz.set_code and pz.card_number is not None:
        key = (pz.set_code, pz.card_number)
        ref = pack_sources.get(key)
        if ref:
            canonical_name = ref["card_name"]

    # Step 2: fuzzy match raw name against pack_sources card_name list
    if not canonical_name:
        hit = fuzz_process.extractOne(pz.raw_name, pack_name_list, score_cutoff=85)
        if hit:
            canonical_name = hit[0]

    # Step 3: direct normalized-name match against collection.json
    # (catches trainers and cards from sets not in pack_sources)
    if not canonical_name:
        nn_direct = _normalize(pz.raw_name)
        if nn_direct in name_index:
            canonical_name = pz.raw_name

    if not canonical_name:
        return MatchResult(status="UNMATCHED", pz_card=pz, canonical_name=None)

    nn = _normalize(canonical_name)
    indices = name_index.get(nn, [])

    if not indices:
        return MatchResult(status="NEW_CARD", pz_card=pz, canonical_name=canonical_name)

    if len(indices) == 1:
        return MatchResult(
            status="MATCHED",
            pz_card=pz,
            entry=collection[indices[0]],
            entry_index=indices[0],
            canonical_name=canonical_name,
        )

    # Multiple variants — try to disambiguate via HP from external_card_reference
    if pz.set_code and pz.card_number is not None:
        ext_records = ext_ref.get(nn, [])
        # Find the ext_ref record for this specific card_number in this set
        target_hp: int | None = None
        for er in ext_records:
            if (str(er.get("set_code", "")).upper() == pz.set_code
                    and er.get("number") == pz.card_number):
                target_hp = er.get("hp")
                break

        if target_hp is not None:
            for idx in indices:
                entry = collection[idx]
                if entry.get("hp") == target_hp:
                    return MatchResult(
                        status="MATCHED",
                        pz_card=pz,
                        entry=entry,
                        entry_index=idx,
                        canonical_name=canonical_name,
                    )

    # Disambiguation failed
    return MatchResult(
        status="AMBIGUOUS",
        pz_card=pz,
        canonical_name=canonical_name,
        candidates=[collection[i] for i in indices],
    )


# ---------------------------------------------------------------------------
# Collection.json in-place editor
# ---------------------------------------------------------------------------

def _find_count_lines(raw: str, collection: list[dict]) -> dict[int, int]:
    """
    Return {entry_index → line_number_of_count_field} (0-based line numbers).

    Walks the raw JSONC text, tracking object boundaries and matching each
    "name" field to the corresponding collection entry to locate its "count" line.
    """
    lines = raw.split("\n")
    # Build a lookup: normalized_name + hp (to distinguish variants) → entry_index
    # Use a list because we match in order of appearance in the file
    entry_signatures: list[tuple[str, int | None, int]] = []
    for i, e in enumerate(collection):
        nn = _normalize(e.get("name", ""))
        hp = e.get("hp")
        entry_signatures.append((nn, hp, i))

    count_line: dict[int, int] = {}  # entry_index → line number

    depth = 0
    in_obj = False
    current_name: str | None = None
    current_hp: int | None = None
    # Track which signatures have been matched (in order) to handle duplicates
    matched_set: set[int] = set()

    for lineno, line in enumerate(lines):
        stripped = re.sub(r"//[^\n]*", "", line)  # strip inline comment
        depth += stripped.count("{") - stripped.count("}")

        # Detect "name": "..." on this line
        m_name = re.search(r'"name"\s*:\s*"([^"]+)"', stripped)
        if m_name:
            current_name = m_name.group(1).strip()

        m_hp = re.search(r'"hp"\s*:\s*(\d+)', stripped)
        if m_hp:
            current_hp = int(m_hp.group(1))

        # Detect "count": N on this line
        m_count = re.search(r'"count"\s*:\s*(\d+)', stripped)
        if m_count and current_name is not None:
            nn = _normalize(current_name)
            # Find the matching signature (in-order, first unmatched)
            for sig_nn, sig_hp, sig_idx in entry_signatures:
                if sig_idx in matched_set:
                    continue
                if sig_nn != nn:
                    continue
                # If both have HP, require match; otherwise accept
                if sig_hp is not None and current_hp is not None and sig_hp != current_hp:
                    continue
                count_line[sig_idx] = lineno
                matched_set.add(sig_idx)
                break
            # Reset HP after binding to avoid bleeding into next object
            if depth == 1:
                current_name = None
                current_hp = None

    return count_line


def apply_count_changes(raw: str, changes: list[CountChange], collection: list[dict]) -> str:
    """
    Apply count changes to the raw JSONC text in-place.
    Replacements are made from bottom to top so line numbers stay valid.
    """
    count_lines = _find_count_lines(raw, collection)
    lines = raw.split("\n")

    # Sort changes by line number descending (bottom to top)
    indexed_changes = []
    for ch in changes:
        lineno = count_lines.get(ch.entry_index)
        if lineno is None:
            print(f"  WARNING: could not locate count line for '{ch.entry.get('name')}' — skipping",
                  file=sys.stderr)
            continue
        indexed_changes.append((lineno, ch))

    indexed_changes.sort(key=lambda x: x[0], reverse=True)

    for lineno, ch in indexed_changes:
        line = lines[lineno]
        new_line = re.sub(
            r'("count"\s*:\s*)(\d+)',
            lambda m: f"{m.group(1)}{ch.new_count}",
            line,
            count=1,
        )
        lines[lineno] = new_line

    return "\n".join(lines)


def update_meta(raw: str, new_total: int) -> str:
    """Update meta.total_cards and meta.last_updated in the raw text."""
    today = date.today().isoformat()
    # Update total_cards (in meta block — first occurrence)
    raw = re.sub(
        r'("total_cards"\s*:\s*)(\d+)',
        lambda m: f"{m.group(1)}{new_total}",
        raw,
        count=1,
    )
    # Update last_updated
    raw = re.sub(
        r'("last_updated"\s*:\s*)"[^"]+"',
        lambda m: f'{m.group(1)}"{today}"',
        raw,
        count=1,
    )
    return raw


# ---------------------------------------------------------------------------
# Review queue
# ---------------------------------------------------------------------------

def write_review_queue(
    new_cards: list[MatchResult],
    ambiguous: list[MatchResult],
    missing_from_pz: list[dict],
) -> None:
    SYNC_DIR.mkdir(parents=True, exist_ok=True)
    queue = {
        "generated_at": date.today().isoformat(),
        "resolved": False,
        "new_cards": [
            {
                "set_code": r.pz_card.set_code,
                "card_number": r.pz_card.card_number,
                "raw_name": r.pz_card.raw_name,
                "canonical_name": r.canonical_name,
                "count": r.pz_card.count,
                "action_needed": "Add this card to collection.json manually",
            }
            for r in new_cards
        ],
        "ambiguous_matches": [
            {
                "raw_name": r.pz_card.raw_name,
                "canonical_name": r.canonical_name,
                "pz_count": r.pz_card.count,
                "candidate_names": [
                    f"{c.get('name')} (hp={c.get('hp')}, variant={c.get('variant', '')})"
                    for c in r.candidates
                ],
                "action_needed": "Resolve variant manually, then re-run sync",
            }
            for r in ambiguous
        ],
        "missing_from_pz": [
            {
                "name": e.get("name"),
                "current_count": e.get("count"),
                "note": "Not found in Pokemon Zone response — count NOT zeroed",
            }
            for e in missing_from_pz
        ],
    }
    REVIEW_QUEUE.write_text(json.dumps(queue, indent=2, ensure_ascii=False), encoding="utf-8")


def load_review_queue() -> dict:
    if not REVIEW_QUEUE.exists():
        return {"resolved": True}
    try:
        return json.loads(REVIEW_QUEUE.read_text(encoding="utf-8"))
    except Exception:
        return {"resolved": True}


def review_queue_is_unresolved(q: dict) -> bool:
    if q.get("resolved", True):
        return False
    return bool(q.get("new_cards") or q.get("ambiguous_matches"))


# ---------------------------------------------------------------------------
# Validation subprocess
# ---------------------------------------------------------------------------

def run_validation() -> bool:
    r1 = subprocess.run(
        [sys.executable, "scripts/validate_current_collection.py"],
        capture_output=True, text=True, cwd=ROOT
    )
    if r1.returncode != 0:
        print("  VALIDATION FAILED:", file=sys.stderr)
        print(r1.stdout, file=sys.stderr)
        print(r1.stderr, file=sys.stderr)
        return False

    r2 = subprocess.run(
        [sys.executable, "scripts/normalize_current_collection.py"],
        capture_output=True, text=True, cwd=ROOT
    )
    if r2.returncode != 0:
        print("  NORMALIZE FAILED:", file=sys.stderr)
        print(r2.stdout, file=sys.stderr)
        print(r2.stderr, file=sys.stderr)
        return False

    return True


# ---------------------------------------------------------------------------
# Diff printer
# ---------------------------------------------------------------------------

def print_diff(
    changes: list[CountChange],
    new_cards: list[MatchResult],
    ambiguous: list[MatchResult],
    missing: list[dict],
) -> None:
    today = date.today().isoformat()
    print(f"\nSYNC DIFF — {today}")
    print("-" * 50)

    if changes:
        print(f"  Count updates ({len(changes)}):")
        for ch in changes:
            name = ch.entry.get("name", "?")
            variant = ch.entry.get("variant", "")
            tag = f" [{variant}]" if variant else ""
            print(f"    {name}{tag}: {ch.old_count} → {ch.new_count}")
    else:
        print("  Count updates: none")

    if new_cards:
        print(f"\n  New cards — not in collection.json ({len(new_cards)}) [review required]:")
        for r in new_cards:
            sc = r.pz_card.set_code or "?"
            cn = r.pz_card.card_number or "?"
            print(f"    [{sc}/{cn}] {r.canonical_name or r.pz_card.raw_name}  ×{r.pz_card.count}")

    if ambiguous:
        print(f"\n  Ambiguous matches ({len(ambiguous)}) [review required]:")
        for r in ambiguous:
            variants = ", ".join(
                f"hp={c.get('hp')}" for c in r.candidates
            )
            print(f"    {r.canonical_name} — {len(r.candidates)} variants ({variants})")

    if missing:
        print(f"\n  Missing from Pokemon Zone ({len(missing)}) [counts NOT changed]:")
        for e in missing:
            print(f"    {e.get('name')}  (current count: {e.get('count')})")

    print("-" * 50)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _load_pz_client():
    """Load pokemon_zone_client as a sibling module (avoids package import issues)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "pokemon_zone_client",
        Path(__file__).parent / "pokemon_zone_client.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _read_curl_from_stdin() -> str:
    """Print instructions and read a multi-line cURL paste from stdin."""
    print()
    print("=" * 65)
    print("  CURL IMPORT — paste your cURL command, then press Ctrl+D")
    print("=" * 65)
    print()
    print("Steps:")
    print("  1. Open  https://www.pokemon-zone.com/collection-tracker/")
    print("     in your browser (must be logged in)")
    print("  2. Open DevTools: F12  or  Cmd+Option+I")
    print("  3. Click the 'Network' tab, then 'Fetch/XHR'")
    print("  4. Reload the page (Cmd+R or F5)")
    print("  5. Wait for your cards to appear")
    print("  6. In the Network tab, look for a large request")
    print("     (50 KB+, URL contains 'card', 'collection', or 'inventory')")
    print("  7. Right-click that request → 'Copy' → 'Copy as cURL'")
    print("  8. Paste below, then press Ctrl+D (Mac/Linux) or Ctrl+Z+Enter (Windows):")
    print()
    try:
        curl_str = sys.stdin.read()
    except KeyboardInterrupt:
        print("\nCancelled.")
        return ""
    return curl_str.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync collection.json from Pokemon Zone.")
    parser.add_argument("--har-import",  metavar="FILE",
                        help="Import collection from a browser HAR file (no auth stored; run --curl-import afterwards for ongoing syncs)")
    parser.add_argument("--json-import", metavar="FILE",
                        help="Import pre-normalized JSON from the browser bookmarklet (fastest; no auth stored)")
    parser.add_argument("--curl-import", action="store_true",
                        help="Paste a browser DevTools cURL to set up / refresh auth (Cloudflare-safe)")
    parser.add_argument("--curl-file",   metavar="FILE",
                        help="Read cURL from a file instead of stdin (alternative to --curl-import)")
    parser.add_argument("--login",       action="store_true",
                        help="Headed Playwright browser login (fallback; may hit Cloudflare)")
    parser.add_argument("--discover",    action="store_true",
                        help="Print all Playwright-intercepted network responses and exit")
    parser.add_argument("--dry-run",     action="store_true",
                        help="Show diff only, no writes")
    parser.add_argument("--force",       action="store_true",
                        help="Apply updates even if review queue has items")
    args = parser.parse_args()

    # ── Load sibling client module ────────────────────────────────────────
    pz = _load_pz_client()
    AUTH_CACHE          = pz.AUTH_CACHE
    browser_session     = ROOT / ".browser_session"

    # ── Phase 0: Pre-flight ───────────────────────────────────────────────

    # --json-import: read pre-normalized JSON from the browser bookmarklet
    if args.json_import:
        json_path = Path(args.json_import)
        if not json_path.exists():
            print(f"ERROR: file not found: {json_path}", file=sys.stderr)
            return 1
        print(f"Importing collection from bookmarklet JSON: {json_path.name}")
        try:
            raw_cards = json.loads(json_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            print(f"ERROR: could not read {json_path}: {e}", file=sys.stderr)
            return 1
        if not isinstance(raw_cards, list) or not raw_cards:
            print("ERROR: JSON file must contain a non-empty array of card objects.", file=sys.stderr)
            return 1
        print(f"  Loaded {len(raw_cards)} card records.")

    # --har-import: parse a HAR file directly (one-shot; no auth stored)
    elif args.har_import:
        print(f"Importing collection from HAR file: {args.har_import}")
        try:
            raw_cards, _cache = pz.import_har(args.har_import)
        except (ValueError, FileNotFoundError) as e:
            print(f"\nERROR: {e}", file=sys.stderr)
            return 1
        print()
        print("NOTE: HAR import does not save auth credentials (browser cookies are")
        print("      not included in HAR exports). For automatic future syncs, run:")
        print("       python3 scripts/sync_collection.py --curl-import")
        print("      Go to pokemon-zone.com/collection-tracker/ → DevTools → Network →")
        print("      right-click the /api/players/mine/ request → Copy as cURL.")
        print()

    # --curl-file: read cURL from a file (alternative to --curl-import + paste)
    elif args.curl_file:
        curl_path = Path(args.curl_file)
        if not curl_path.exists():
            print(f"ERROR: file not found: {curl_path}", file=sys.stderr)
            return 1
        curl_str = curl_path.read_text(encoding="utf-8").strip()
        if not curl_str:
            print("ERROR: curl file is empty.", file=sys.stderr)
            return 1
        print(f"Reading cURL from {curl_path} ...")
        print("Parsing cURL and fetching collection...")
        try:
            raw_cards, _cache = pz.import_curl_auth(curl_str)
        except (ValueError, pz.APIDiscoveryFailedError) as e:
            print(f"\nERROR: {e}", file=sys.stderr)
            return 1

    # --curl-import: read a pasted cURL, discover API, save auth, then sync
    elif args.curl_import:
        curl_str = _read_curl_from_stdin()
        if not curl_str:
            return 1
        print("\nParsing cURL and fetching collection...")
        try:
            raw_cards, _cache = pz.import_curl_auth(curl_str)
        except (ValueError, pz.APIDiscoveryFailedError) as e:
            print(f"\nERROR: {e}", file=sys.stderr)
            return 1

    # Normal headless sync using stored auth or Playwright session
    else:
        # Check auth availability before doing anything else
        has_stored_auth  = AUTH_CACHE.exists()
        has_browser_sess = browser_session.exists()

        if not has_stored_auth and not has_browser_sess and not args.login and not args.discover:
            print("ERROR: No stored auth and no browser session found.", file=sys.stderr)
            print()
            print("First-time setup (recommended — avoids Cloudflare):")
            print("  python3 scripts/sync_collection.py --curl-import")
            print()
            print("Alternative (may hit Cloudflare CAPTCHA loop):")
            print("  python3 scripts/sync_collection.py --login")
            return 1

        # ── Phase 1: Fetch from Pokemon Zone ─────────────────────────────
        print("Fetching collection from Pokemon Zone...")
        try:
            raw_cards, _cache = pz.fetch_collection(login=args.login, discover=args.discover)
        except (pz.AuthNotFoundError, pz.SessionNotFoundError) as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 1
        except pz.AuthExpiredError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 1
        except (pz.SessionExpiredError, pz.APIDiscoveryFailedError) as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 1

        if args.discover:
            return 0  # already printed by fetch_collection

    if not raw_cards:
        print("ERROR: No card records returned from Pokemon Zone.", file=sys.stderr)
        return 1

    # ── Review queue gate (all modes except discover/dry-run/force) ───────
    if not args.force and not args.discover and not args.dry_run:
        q = load_review_queue()
        if review_queue_is_unresolved(q):
            n_new = len(q.get("new_cards", []))
            n_amb = len(q.get("ambiguous_matches", []))
            print(f"BLOCKED: Review queue has {n_new} new card(s) and {n_amb} ambiguous match(es).")
            print(f"  File: {REVIEW_QUEUE}")
            print("  Resolve the items or run with --force to skip this check.")
            return 3

    print(f"  Fetched {len(raw_cards)} card records from Pokemon Zone.")

    # ── Load collection.json and reference data ───────────────────────────
    raw_text, collection_data = load_collection()
    collection_entries: list[dict] = collection_data.get("collection", [])
    print("Loading reference data...")
    pack_sources = load_pack_sources()
    ext_ref      = load_ext_ref()

    # ── Phase 2: Normalize PZ records ────────────────────────────────────
    pz_cards: list[PZCard] = []
    skipped = 0
    for rec in raw_cards:
        pzc = normalize_pz_record(rec)
        if pzc is None:
            skipped += 1
            continue
        pz_cards.append(pzc)

    if skipped:
        print(f"  Skipped {skipped} records with count=0 or missing name.")

    # ── Phase 3: Match ────────────────────────────────────────────────────
    print(f"  Matching {len(pz_cards)} PZ cards to {len(collection_entries)} collection entries...")
    results = match_pz_cards(pz_cards, collection_entries, pack_sources, ext_ref)

    matched   = [r for r in results if r.status == "MATCHED"]
    new_cards = [r for r in results if r.status in ("NEW_CARD", "UNMATCHED")]
    ambiguous = [r for r in results if r.status == "AMBIGUOUS"]

    # Entries in collection.json with no corresponding PZ record
    matched_indices = {r.entry_index for r in matched if r.entry_index is not None}
    missing_from_pz = [
        e for i, e in enumerate(collection_entries) if i not in matched_indices
    ]

    # ── Phase 4: Compute diff ─────────────────────────────────────────────
    # Aggregate counts: the same card may appear in multiple sets in PZ
    # (e.g. Shroomish in B2 + B3); sum all copies into one collection entry.
    entry_pz_total: dict[int, int] = {}
    for r in matched:
        idx = r.entry_index
        entry_pz_total[idx] = entry_pz_total.get(idx, 0) + r.pz_card.count

    changes: list[CountChange] = []
    for idx, new_count in entry_pz_total.items():
        entry = collection_entries[idx]
        old_count = entry.get("count", 0)
        if old_count != new_count:
            changes.append(CountChange(
                entry=entry,
                entry_index=idx,
                old_count=old_count,
                new_count=new_count,
            ))

    print_diff(changes, new_cards, ambiguous, missing_from_pz)

    if args.dry_run:
        print("DRY RUN — no changes written.")
        return 0

    # ── Phase 4b: Write review queue ─────────────────────────────────────
    has_review_items = bool(new_cards or ambiguous)
    write_review_queue(new_cards, ambiguous, missing_from_pz)

    if has_review_items and not args.force:
        n_new = len(new_cards)
        n_amb = len(ambiguous)
        print(f"\nReview queue written: {REVIEW_QUEUE}")
        print(f"  {n_new} new card(s) require manual addition to collection.json")
        print(f"  {n_amb} ambiguous match(es) require manual disambiguation")
        print("Continuing to apply count updates for matched cards...")

    # ── Phase 5: Apply in-place edits ────────────────────────────────────
    if not changes:
        print("No count changes to apply.")
        # Still write review queue — exit 2 if review items exist
        return 2 if has_review_items else 0

    print(f"Applying {len(changes)} count update(s) to collection.json...")
    counts = [e.get("count", 0) for e in collection_entries]
    for ch in changes:
        counts[ch.entry_index] = ch.new_count
    new_total = sum(counts)

    edited = apply_count_changes(raw_text, changes, collection_entries)
    edited = update_meta(edited, new_total)

    COLLECTION_JSON.write_text(edited, encoding="utf-8")
    print(f"  collection.json updated. New total: {new_total}")

    # ── Phase 6: Validate ─────────────────────────────────────────────────
    print("Validating...")
    if not run_validation():
        print("ROLLBACK: restoring original collection.json", file=sys.stderr)
        COLLECTION_JSON.write_text(raw_text, encoding="utf-8")
        return 1

    print("  PASS — collection.json valid and normalized.")

    if has_review_items:
        print(f"\nExit 2: review queue has items. See {REVIEW_QUEUE}")
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
