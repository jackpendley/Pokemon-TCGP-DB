#!/usr/bin/env python3
"""
Pokemon Zone browser client — auth management and collection API access.

Not run directly. Imported by sync_collection.py.

Two fetch modes:
  1. Stored-auth (preferred): user pastes a cURL from DevTools once; subsequent
     syncs use requests with the stored cookies — no Playwright, no Cloudflare.
  2. Playwright (fallback): headed browser login that may hit Cloudflare.

Handles:
  - cURL import: parse cookies/headers from a browser DevTools cURL command
  - Stored auth: load saved credentials and fetch via requests
  - Playwright: persistent context at .browser_session/ (reused across runs)
  - Network response interception to discover and cache the collection API endpoint
  - Raw collection data fetch and caching
"""

import asyncio
import json
import re
import shlex
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from curl_cffi import requests as _cffi_requests
    _HAS_CURL_CFFI = True
except ImportError:
    import requests as _cffi_requests  # type: ignore[no-redef]
    _HAS_CURL_CFFI = False


def _get(url: str, **kwargs):
    """HTTP GET with Chrome TLS impersonation when curl_cffi is available."""
    if _HAS_CURL_CFFI:
        kwargs.setdefault("impersonate", "chrome136")
    return _cffi_requests.get(url, **kwargs)


def _post(url: str, **kwargs):
    """HTTP POST with Chrome TLS impersonation when curl_cffi is available."""
    if _HAS_CURL_CFFI:
        kwargs.setdefault("impersonate", "chrome136")
    return _cffi_requests.post(url, **kwargs)

ROOT = Path(__file__).resolve().parent.parent
BROWSER_SESSION_DIR = ROOT / ".browser_session"
DISCOVERY_CACHE     = ROOT / "data" / "sync" / "api_discovery_cache.json"
RAW_CACHE           = ROOT / "data" / "sync" / "last_sync_raw.json"
AUTH_CACHE          = ROOT / "data" / "sync" / ".auth.json"
PLAYER_STATS_CACHE  = ROOT / "data" / "sync" / "player_stats.json"

COLLECTION_URL = "https://www.pokemon-zone.com/collection-tracker/"
HOME_URL       = "https://www.pokemon-zone.com/"

# Instructions shown when the copied URL isn't the collection API
CURL_IMPORT_GUIDANCE = """\
Could not find collection data at the provided URL.

Please copy the cURL for the specific XHR request that loads your cards.

Steps (Chrome / Safari):
  1. Go to  https://www.pokemon-zone.com/collection-tracker/  (stay logged in)
  2. Open DevTools: F12  or  Cmd+Option+I
  3. Click the "Network" tab
  4. Click "Fetch/XHR" to filter
  5. Press Cmd+R (or F5) to reload the page
  6. Wait for cards to appear, then look for a large response
     — check the "Size" column; look for something 50 KB+
     — look for URLs containing "card", "collection", or "inventory"
  7. Right-click that request → "Copy" → "Copy as cURL"
  8. Re-run:  python3 scripts/sync_collection.py --curl-import
"""

# Headers from the cURL we want to preserve for auth
_AUTH_HEADER_KEYS = {
    "authorization", "x-auth-token", "x-session-token", "x-access-token",
    "user-agent", "referer", "origin", "x-requested-with", "x-csrf-token",
}

# Extensions / fragments definitively NOT collection data (Playwright discovery)
STATIC_EXTENSIONS = {".js", ".css", ".png", ".jpg", ".jpeg", ".gif", ".webp",
                     ".svg", ".ico", ".woff", ".woff2", ".ttf", ".otf", ".eot",
                     ".mp4", ".mp3", ".pdf", ".xml", ".txt"}
STATIC_URL_FRAGMENTS = ["analytics", "gtm", "hotjar", "sentry", "cdn.cloudflare",
                         "googleapis", "gstatic", "facebook", "twitter",
                         "assets.pokemon-zone.com"]

COLLECTION_KEY_HINTS = {"card", "count", "owned", "quantity", "set", "number",
                        "pokemon", "deck", "collection", "inventory"}
COLLECTION_URL_HINTS = {"card", "collection", "owned", "inventory", "user", "me"}


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class AuthExpiredError(Exception):
    pass

class AuthNotFoundError(Exception):
    pass

class SessionExpiredError(Exception):
    pass

class SessionNotFoundError(Exception):
    pass

class APIDiscoveryFailedError(Exception):
    pass


# ---------------------------------------------------------------------------
# Scoring / array helpers (shared by Playwright and requests paths)
# ---------------------------------------------------------------------------

def _is_static(url: str) -> bool:
    path = url.split("?")[0].lower()
    if any(path.endswith(ext) for ext in STATIC_EXTENSIONS):
        return True
    return any(frag in url.lower() for frag in STATIC_URL_FRAGMENTS)


def _score_response(url: str, body: dict | list) -> int:
    score = 0
    url_lower = url.lower()
    if any(h in url_lower for h in COLLECTION_URL_HINTS):
        score += 1

    arr = None
    if isinstance(body, list):
        arr = body
        score += 1
    elif isinstance(body, dict):
        for v in body.values():
            if isinstance(v, list) and len(v) > 10:
                arr = v
                score += 1
                break

    if arr is None:
        return score

    if 50 <= len(arr) <= 5000:
        score += 3

    if not arr:
        return score

    if isinstance(arr[0], dict):
        keys_lower = {k.lower() for k in arr[0].keys()}
        all_tokens: set[str] = set()
        for k in keys_lower:
            all_tokens.update(re.findall(r"[a-z]+", k))
        score += min(len(COLLECTION_KEY_HINTS & all_tokens), 2)

    return score


def _find_array(body: dict | list) -> tuple[list | None, str | None]:
    """Return (array, key_or_None) where the collection data lives."""
    if isinstance(body, list):
        return body, None
    if isinstance(body, dict):
        best_key, best_arr = None, []
        for k, v in body.items():
            if isinstance(v, list) and len(v) > len(best_arr):
                best_key, best_arr = k, v
        if best_arr:
            return best_arr, best_key
    return None, None


# ---------------------------------------------------------------------------
# cURL import (Cloudflare-safe path)
# ---------------------------------------------------------------------------

def parse_curl(curl_str: str) -> dict:
    """
    Parse a browser DevTools cURL command into {url, cookies, headers}.

    Handles multi-line (backslash continuations), single/double quoted args,
    -H / --header / -b / --cookie flags.
    """
    # Normalize line continuations (Unix and Windows)
    normalized = curl_str.replace("\r\n", "\n").replace("\\\n", " ")

    try:
        tokens = shlex.split(normalized)
    except ValueError as e:
        raise ValueError(f"Could not parse cURL command: {e}") from e

    url: str | None = None
    headers: dict[str, str] = {}
    cookies: dict[str, str] = {}

    # Flags that consume one additional positional argument
    ONE_ARG_FLAGS = {
        "-H", "--header", "-b", "--cookie",
        "-X", "--request",
        "-d", "--data", "--data-raw", "--data-binary", "--data-urlencode",
        "-u", "--user", "--url",
        "-A", "--user-agent",
        "-e", "--referer",
        "-o", "--output",
        "-m", "--max-time", "--connect-timeout",
        "-F", "--form",
        "--cert", "--key",
    }

    i = 0
    while i < len(tokens):
        tok = tokens[i]

        if tok == "curl":
            i += 1
            continue

        if tok in ("-H", "--header") and i + 1 < len(tokens):
            raw = tokens[i + 1]
            if ":" in raw:
                k, _, v = raw.partition(":")
                k, v = k.strip(), v.strip()
                if k.lower() == "cookie":
                    for part in v.split(";"):
                        part = part.strip()
                        if "=" in part:
                            ck, _, cv = part.partition("=")
                            cookies[ck.strip()] = cv.strip()
                else:
                    headers[k] = v
            i += 2
            continue

        if tok in ("-b", "--cookie") and i + 1 < len(tokens):
            for part in tokens[i + 1].split(";"):
                part = part.strip()
                if "=" in part:
                    ck, _, cv = part.partition("=")
                    cookies[ck.strip()] = cv.strip()
            i += 2
            continue

        if tok in ONE_ARG_FLAGS and i + 1 < len(tokens):
            i += 2
            continue

        if tok.startswith("-"):
            i += 1
            continue

        if (tok.startswith("http://") or tok.startswith("https://")) and url is None:
            url = tok

        i += 1

    return {"url": url, "cookies": cookies, "headers": headers}


_CATALOG_URL      = "https://www.pokemon-zone.com/api/cards/search/"
_PLAYER_URL       = "https://www.pokemon-zone.com/api/players/mine/"
_IDENTITY_URL     = "https://www.pokemon-zone.com/api/users/identity/"
_SYNC_URL         = "https://www.pokemon-zone.com/api/players/sync/"
_SYNC_STATUS_URL  = "https://www.pokemon-zone.com/api/players/sync/status/{}/"


def _fetch_catalog(cookies: dict, auth_headers: dict) -> dict[str, dict]:
    """
    Fetch the card catalog from /api/cards/search/ and return
    {cardDefKey → {name, set_code, card_number}}.
    Returns an empty dict on failure (caller decides how to handle).
    """
    req_headers = {**auth_headers, "Accept": "application/json, */*"}
    try:
        r = _get(_CATALOG_URL, headers=req_headers, cookies=cookies, timeout=30)
        if r.status_code != 200:
            return {}
        body = r.json()
        data = body.get("data", [])
        if isinstance(data, dict):
            data = data.get("results", [])
        if not isinstance(data, list):
            return {}
        catalog: dict[str, dict] = {}
        for item in data:
            key  = item.get("cardDefKey", "")
            name = item.get("name", "")
            exp  = item.get("expansionId", "")
            cn   = _parse_cn_from_url(item.get("url", ""))
            if key and name:
                catalog[key] = {"name": name, "set_code": exp, "card_number": cn}
        return catalog
    except Exception:
        return {}


def _save_player_stats(body: dict | list | None, catalog_misses: dict | None = None,
                       player_synced: bool | None = None) -> None:
    """Extract and persist player currency/resource stats from the raw API body.

    catalog_misses (owned cards the PZ catalog could not name) and player_synced
    (whether PZ finished refreshing its snapshot from the game) ride along here
    because this file is published verbatim as sync_status.stats, which is what
    the dashboard reads.
    """
    if not isinstance(body, dict):
        body = {}
    data = body.get("data", {})
    if not isinstance(data, dict):
        data = {}
    rd = data.get("resourceData", {})
    if not isinstance(rd, dict):
        rd = {}

    stats: dict = {}

    # Pack Hourglasses — the main pack-opening currency
    for item in rd.get("packPowerChargers", []):
        stats["pack_hourglasses"] = item.get("value", 0)
        break

    # Wonder Hourglasses — challenge-mode currency
    for item in rd.get("challengePowerChargers", []):
        stats["wonder_hourglasses"] = item.get("value", 0)
        break

    # Event Hourglasses
    for item in rd.get("eventPowerChargers", []):
        stats["event_hourglasses"] = item.get("value", 0)
        break

    # Trade Hourglasses
    for item in rd.get("tradePowerChargers", []):
        stats["trade_hourglasses"] = item.get("value", 0)
        break

    # Shop currencies (Shop Tickets, Shinedust, Premium Tickets)
    for item in rd.get("currencies", []):
        key = item.get("key", "")
        if key == "SHOP_TICKET":
            stats["shop_tickets"] = item.get("value", 0)
        elif key == "BRIGHT_SAND":
            stats["shinedust"] = item.get("value", 0)
        elif key == "SUBSCRIPTION_TICKET":
            stats["premium_tickets"] = item.get("value", 0)

    if catalog_misses:
        stats["catalog_misses"] = catalog_misses
    if player_synced is not None:
        # False means the numbers below are PZ's previous snapshot of the
        # collection, not a fresh read from the game.
        stats["player_synced"] = player_synced

    if stats:
        PLAYER_STATS_CACHE.parent.mkdir(parents=True, exist_ok=True)
        PLAYER_STATS_CACHE.write_text(
            json.dumps({"fetched_at": datetime.now(timezone.utc).isoformat(), **stats},
                       indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


def _fetch_and_normalize_cards(
    api_url: str,
    cookies: dict,
    auth_headers: dict,
    catalog: dict[str, dict],
) -> tuple[list | None, dict | list | None, int, dict]:
    """
    GET api_url and decode the raw card records using the catalog.

    Returns (normalized_card_list, raw_body, http_status, catalog_misses).

    catalog_misses reports owned cards the catalog could not resolve:
    {"count", "copies", "card_ids"}. These used to be dropped silently, which
    is exactly how a whole unreleased-to-PZ set can vanish from a sync with no
    trace — see the 2026-08-03 B4 investigation.

    Returns (None, None, status, {}) on failure.
    """
    req_headers = {**auth_headers, "Accept": "application/json, */*"}
    try:
        r = _get(api_url, headers=req_headers, cookies=cookies, timeout=30)
        status = r.status_code
        if status != 200:
            return None, None, status, {}
        body = r.json()
    except Exception:
        return None, None, 0, {}

    # Known Pokemon Zone format: {data: {cards: [...]}}
    owned_raw: list = []
    data = body.get("data") if isinstance(body, dict) else None
    if isinstance(data, dict):
        owned_raw = data.get("cards") or data.get("card_list") or data.get("items") or []

    # Generic fallback: find any large list in the response
    if not owned_raw:
        arr, _ = _find_array(body)
        if arr and len(arr) > 10:
            owned_raw = arr

    if not owned_raw:
        return None, body, 200, {}

    raw_cards: list[dict] = []
    missed_ids: list[str] = []
    missed_copies = 0
    for card in owned_raw:
        if not isinstance(card, dict):
            continue
        card_id    = card.get("cardId", "")
        amount     = int(card.get("amount") or card.get("amountLang_EN") or 0)
        # PZ reports every expansion a card registers in. The first is its debut
        # printing; the rest matter since the 2026-07-29 update made a card count
        # in the dex under all of them (see build_printing_groups.py).
        player_exps = [e for e in (card.get("expansionIds") or []) if e]
        player_exp  = player_exps[0] if player_exps else ""
        if amount <= 0:
            continue
        info = catalog.get(card_id) if catalog else None
        if info:
            set_code = player_exp if player_exp else info["set_code"]
            raw_cards.append({
                "cardName":     info["name"],
                "setCode":      set_code,
                "cardNumber":   info["card_number"],
                "ownedCount":   amount,
                "expansionIds": player_exps,
            })
        elif not catalog:
            # No catalog available — pass raw record; normalize_pz_record will handle it
            raw_cards.append(card)
        else:
            # Owned, but the catalog can't name it. Never drop this silently: it
            # means PZ has not published the card's definition yet (a set released
            # in-game but not yet ingested by PZ), or the catalog fetch truncated.
            missed_ids.append(card_id)
            missed_copies += amount

    misses: dict = {}
    if missed_ids:
        misses = {
            "count":    len(missed_ids),
            "copies":   missed_copies,
            "card_ids": sorted(missed_ids)[:50],
        }
        print(
            f"  WARNING: {len(missed_ids)} owned card(s) ({missed_copies} copies) are not in "
            f"the PZ catalog and were skipped.\n"
            f"           PZ likely has not published these card definitions yet "
            f"(a newly released set), or the catalog response was truncated.",
            file=sys.stderr,
        )

    return (raw_cards or None), body, 200, misses


def import_curl_auth(curl_str: str) -> tuple[list, dict]:
    """
    Parse a cURL command, fetch the collection (catalog + player data), save
    auth credentials, and return (card_array, discovery_cache).

    The Pokemon Zone API returns internal card IDs; we must also fetch the
    card catalog (/api/cards/search/) to map IDs → names/set/number.

    Raises ValueError for unparseable cURL.
    Raises APIDiscoveryFailedError if the collection cannot be fetched.
    """
    parsed = parse_curl(curl_str)
    url = parsed.get("url")
    if not url:
        raise ValueError(
            "No URL found in the pasted cURL command.\n"
            "Make sure you right-clicked an actual network request and chose 'Copy as cURL'."
        )

    cookies = parsed.get("cookies", {})
    all_headers = parsed.get("headers", {})
    auth_headers = {k: v for k, v in all_headers.items() if k.lower() in _AUTH_HEADER_KEYS}

    if not cookies and not any(k.lower() == "authorization" for k in all_headers):
        raise ValueError(
            "No cookies or Authorization header found in the cURL command.\n"
            "The copied request may not require authentication.\n"
            "Make sure you are logged in to Pokemon Zone and that the request\n"
            "you copied is an authenticated XHR (not a static asset or login page)."
        )

    # Step 1: card catalog (maps internal IDs → names/set/number)
    print("  Fetching card catalog...")
    catalog = _fetch_catalog(cookies, auth_headers)
    if catalog:
        print(f"  Card catalog: {len(catalog):,} entries.")
    else:
        print("  WARNING: card catalog unavailable — card names may not resolve correctly.")
        print(f"  (Attempted: {_CATALOG_URL})")

    # Step 2: owned cards (always use the canonical player URL)
    api_url = _PLAYER_URL
    print(f"  Fetching owned cards from {api_url}...")
    arr, body, status, catalog_misses = _fetch_and_normalize_cards(
        api_url, cookies, auth_headers, catalog)

    if status in (301, 302, 401, 403):
        raise APIDiscoveryFailedError(
            f"Auth rejected (HTTP {status}). Make sure you are still logged in to\n"
            "Pokemon Zone when you copy the cURL, then re-run --curl-import."
        )

    if status == 0:
        raise APIDiscoveryFailedError(
            "Network error — could not reach Pokemon Zone API.\n"
            "Check your internet connection and try again."
        )

    if status != 200:
        raise APIDiscoveryFailedError(
            f"Unexpected HTTP {status} from {api_url}.\n"
            "Re-run --curl-import with a fresh cURL from DevTools."
        )

    if arr is None:
        # Show a snippet of the actual response to help diagnose format issues
        hint = ""
        if isinstance(body, dict):
            top_keys = list(body.keys())[:8]
            hint = f"\n  Response top-level keys: {top_keys}"
            data = body.get("data")
            if isinstance(data, dict):
                hint += f"\n  body['data'] keys: {list(data.keys())[:8]}"
            elif isinstance(data, list):
                hint += f"\n  body['data'] is a list with {len(data)} items"
        raise APIDiscoveryFailedError(CURL_IMPORT_GUIDANCE + hint)

    print(f"  Collection API confirmed: {len(arr)} cards.")

    # Save auth
    auth = {
        "imported_at": datetime.now(timezone.utc).isoformat(),
        "api_url": api_url,
        "cookies": cookies,
        "auth_headers": auth_headers,
    }
    AUTH_CACHE.parent.mkdir(parents=True, exist_ok=True)
    AUTH_CACHE.write_text(json.dumps(auth, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  Auth saved → {AUTH_CACHE.relative_to(ROOT)}")

    cache = {
        "discovered_at": auth["imported_at"],
        "api_url": api_url,
        "collection_array_key": "data.cards",
        "element_count": len(arr),
    }
    DISCOVERY_CACHE.parent.mkdir(parents=True, exist_ok=True)
    DISCOVERY_CACHE.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    RAW_CACHE.write_text(json.dumps(arr, indent=2, ensure_ascii=False), encoding="utf-8")
    _save_player_stats(body, catalog_misses)

    return arr, cache


def trigger_player_sync(cookies: dict, auth_headers: dict, poll_interval: float = 2.0, timeout: int = 90) -> bool:
    """
    Trigger the Pokemon Zone 'Sync Player' button programmatically.

    Flow:
      1. GET /api/users/identity/ → get friendId, check nextSyncPlayerAt rate limit
      2. POST /api/players/sync/ with {"friendId": ...} + x-csrftoken
      3. Poll /api/players/sync/status/{taskId}/ until ready=true or timeout

    Returns True if sync completed successfully, False on any non-fatal failure.
    The caller should proceed with collection fetch regardless of the return value.
    """
    import time

    req_headers = {**auth_headers, "Accept": "application/json, */*"}

    # Step 1: identity — get friendId and check rate limit
    try:
        r = _get(_IDENTITY_URL, headers=req_headers, cookies=cookies, timeout=15)
        if r.status_code != 200:
            print(f"  Player sync: identity fetch returned HTTP {r.status_code} — skipping.")
            return False
        identity = r.json().get("data", {})
    except Exception as exc:
        print(f"  Player sync: identity fetch failed ({exc}) — skipping.")
        return False

    players = identity.get("players", [])
    if not players:
        print("  Player sync: no players in identity response — skipping.")
        return False
    friend_id = players[0].get("friendId", "")
    if not friend_id:
        print("  Player sync: friendId missing — skipping.")
        return False

    # Step 2: trigger sync
    csrftoken = cookies.get("csrftoken", "")
    post_headers = {
        **req_headers,
        "content-type": "application/json",
        "x-csrftoken": csrftoken,
        "origin": "https://www.pokemon-zone.com",
        "referer": f"https://www.pokemon-zone.com/players/{friend_id}/",
        "x-402-status": "1",
    }
    try:
        r = _post(_SYNC_URL, headers=post_headers, cookies=cookies,
                  json={"friendId": friend_id}, timeout=20)
        if r.status_code != 200:
            print(f"  Player sync: trigger returned HTTP {r.status_code} — skipping.")
            return False
        task_id = r.json().get("data", {}).get("taskId")
        if not task_id:
            print("  Player sync: no taskId in response — skipping.")
            return False
    except Exception as exc:
        print(f"  Player sync: trigger failed ({exc}) — skipping.")
        return False

    print(f"  Player sync triggered (taskId={task_id}) — waiting for completion...")

    # Step 3: poll until ready
    status_url = _SYNC_STATUS_URL.format(task_id)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        time.sleep(poll_interval)
        try:
            r = _get(status_url, headers=req_headers, cookies=cookies, timeout=15)
            data = r.json().get("data", {})
            if data.get("ready"):
                result = data.get("result", {})
                print(f"  Player sync complete — {result.get('successCount', '?')} cards synced.")
                return True
            if data.get("status") not in ("PENDING", "IN_PROGRESS", None):
                print(f"  Player sync ended with status={data.get('status')} — proceeding.")
                return False
        except Exception:
            pass  # transient poll error — keep trying

    print(f"  Player sync timed out after {timeout}s — Pokémon Zone has not finished "
          f"pulling your collection from the game, so what follows is its previous "
          f"snapshot and may be missing recent pulls.", file=sys.stderr)
    return False


def fetch_with_stored_auth() -> tuple[list, dict]:
    """
    Fetch the collection using stored auth credentials (no browser automation).

    Performs the same two-step fetch as import_har():
      1. Card catalog (/api/cards/search/) — maps internal IDs → names
      2. Player cards (/api/players/mine/) — owned counts

    Raises AuthNotFoundError if no .auth.json exists.
    Raises AuthExpiredError if credentials are rejected.
    Raises APIDiscoveryFailedError on unexpected errors.
    """
    if not AUTH_CACHE.exists():
        raise AuthNotFoundError(
            "No stored auth found.\n"
            "Run:  python3 scripts/sync_collection.py --curl-import\n"
            "\n"
            "This is a one-time setup: paste a cURL from your browser's DevTools\n"
            "to give the sync script access to your Pokemon Zone session."
        )

    auth = json.loads(AUTH_CACHE.read_text(encoding="utf-8"))
    api_url      = auth.get("api_url", _PLAYER_URL)
    cookies      = auth.get("cookies", {})
    auth_headers = auth.get("auth_headers", {})

    # Step 0: ask PZ to refresh its snapshot of the collection from the game
    # (equivalent to clicking "Sync Player" in the browser). When this does not
    # complete, everything below is PZ's *previous* snapshot — the fetch still
    # succeeds, so the outcome has to travel or the run looks clean while
    # silently republishing stale data.
    player_synced = trigger_player_sync(cookies, auth_headers)

    # Step 1: card catalog
    catalog = _fetch_catalog(cookies, auth_headers)
    if catalog:
        print(f"  Card catalog: {len(catalog):,} entries.")
    else:
        print("  WARNING: card catalog unavailable — card names may not resolve.")

    # Step 2: owned cards
    arr, body, status, catalog_misses = _fetch_and_normalize_cards(
        api_url, cookies, auth_headers, catalog)

    if status in (301, 302, 401, 403):
        raise AuthExpiredError(
            f"Auth credentials expired (HTTP {status}).\n"
            "Re-run:  python3 scripts/sync_collection.py --curl-import\n"
            "\n"
            "Go to pokemon-zone.com/collection-tracker/ in your browser,\n"
            "open DevTools → Network → find the /api/players/mine/ request,\n"
            "right-click → Copy as cURL, then run the command."
        )

    if status != 200:
        raise APIDiscoveryFailedError(
            f"Unexpected HTTP {status} from collection API.\n"
            "Try re-running --curl-import."
        )

    if not arr:
        raise APIDiscoveryFailedError(
            f"API response at {api_url} contains no card data.\n"
            "Try re-running --curl-import."
        )

    cache = {
        "discovered_at": datetime.now(timezone.utc).isoformat(),
        "api_url": api_url,
        "collection_array_key": "data.cards",
        "element_count": len(arr),
        "player_synced": player_synced,
    }
    DISCOVERY_CACHE.parent.mkdir(parents=True, exist_ok=True)
    DISCOVERY_CACHE.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    RAW_CACHE.write_text(json.dumps(arr, indent=2, ensure_ascii=False), encoding="utf-8")
    _save_player_stats(body, catalog_misses, player_synced=player_synced)
    print(f"  Fetched {len(arr)} cards via stored auth.")

    return arr, cache


# ---------------------------------------------------------------------------
# Playwright path (fallback — may hit Cloudflare)
# ---------------------------------------------------------------------------

def print_discovery_table(candidates: list[dict]) -> None:
    print("\nPOKEMON ZONE NETWORK RESPONSE DISCOVERY")
    print("=" * 60)
    print(f"Captured {len(candidates)} JSON response(s)\n")

    scored = sorted(candidates, key=lambda c: c["score"], reverse=True)
    static_count = sum(1 for c in candidates if c.get("static"))

    for i, c in enumerate(scored):
        if c.get("static"):
            continue
        label = "*** TOP CANDIDATE ***" if i == 0 and c["score"] > 2 else ""
        print(f"[Score: {c['score']}] {label}")
        print(f"  URL:    {c['url']}")
        print(f"  Status: {c['status']}")
        size = c.get("size", 0)
        print(f"  Size:   {size:,} bytes")
        arr = c.get("array_preview", [])
        if arr is not None:
            print(f"  Count:  {c.get('array_len', '?')} elements")
        keys = c.get("sample_keys", [])
        if keys:
            print(f"  Keys:   {keys}")
        sample = c.get("sample_element")
        if sample:
            sample_str = json.dumps(sample)
            if len(sample_str) > 120:
                sample_str = sample_str[:117] + "..."
            print(f"  Sample: {sample_str}")
        print()

    if static_count:
        print(f"  ({static_count} static asset responses omitted)")
    print("=" * 60)


async def _run_playwright(login: bool, discover: bool) -> tuple[list, dict]:
    """
    Returns (raw_card_array, discovery_cache_dict) via Playwright.

    NOTE: May be blocked by Cloudflare bot detection on the login page.
    Prefer the --curl-import path when possible.

    Raises SessionNotFoundError, SessionExpiredError, APIDiscoveryFailedError.
    """
    from playwright.async_api import async_playwright, Response

    if not login and not BROWSER_SESSION_DIR.exists():
        raise SessionNotFoundError(
            "No browser session found.\n"
            "Preferred: python3 scripts/sync_collection.py --curl-import\n"
            "Fallback:  python3 scripts/sync_collection.py --login  (may hit Cloudflare)"
        )

    candidates: list[dict] = []
    captured_responses: dict[str, dict | list] = {}

    async with async_playwright() as pw:
        browser = await pw.chromium.launch_persistent_context(
            user_data_dir=str(BROWSER_SESSION_DIR),
            headless=not login,
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )

        page = browser.pages[0] if browser.pages else await browser.new_page()

        async def handle_response(resp: Response) -> None:
            url = resp.url
            status = resp.status
            if status < 200 or status >= 300:
                return
            ct = resp.headers.get("content-type", "")
            if "json" not in ct and not url.endswith(".json"):
                return
            try:
                body = await resp.json()
            except Exception:
                return

            is_static = _is_static(url)
            score = 0 if is_static else _score_response(url, body)

            arr, arr_key = _find_array(body)
            sample = (arr[0] if arr else None) if isinstance(arr, list) else None

            entry = {
                "url": url,
                "status": status,
                "score": score,
                "static": is_static,
                "size": len(json.dumps(body)),
                "array_len": len(arr) if arr is not None else None,
                "array_key": arr_key,
                "sample_keys": list(sample.keys())[:8] if isinstance(sample, dict) else None,
                "sample_element": sample,
            }
            candidates.append(entry)
            if not is_static and arr is not None:
                captured_responses[url] = body

        page.on("response", handle_response)

        if login:
            print("Opening browser for login. Sign in to Pokemon Zone with your Nintendo Account.")
            print("NOTE: If you see a Cloudflare CAPTCHA loop, use --curl-import instead.")
            print("Navigate to your collection page when done.")
            await page.goto(HOME_URL, wait_until="domcontentloaded", timeout=60_000)
            print("Waiting for you to log in and reach the collection tracker...")
            try:
                await page.wait_for_url("**/collection-tracker/**", timeout=300_000)
            except Exception:
                pass
            await page.wait_for_load_state("networkidle", timeout=30_000)
        else:
            await page.goto(COLLECTION_URL, wait_until="domcontentloaded", timeout=60_000)
            if "collection-tracker" not in page.url and "login" in page.url.lower():
                await browser.close()
                raise SessionExpiredError(
                    "Pokemon Zone session has expired.\n"
                    "Run:  python3 scripts/sync_collection.py --curl-import"
                )
            await page.wait_for_load_state("networkidle", timeout=30_000)

        await browser.close()

    if discover:
        print_discovery_table(candidates)
        return [], {}

    non_static = [c for c in candidates if not c["static"] and c["score"] > 0]
    if not non_static:
        raise APIDiscoveryFailedError(
            "No JSON API responses detected on the collection page.\n"
            "Try --curl-import instead of Playwright."
        )

    best = max(non_static, key=lambda c: c["score"])

    if best["score"] < 3:
        print("WARNING: Best API candidate has low confidence score.", file=sys.stderr)
        print_discovery_table(candidates)
        raise APIDiscoveryFailedError(
            f"Could not confidently identify the collection API (best score={best['score']}).\n"
            "Try --curl-import instead."
        )

    raw_body = captured_responses[best["url"]]
    arr, arr_key = _find_array(raw_body)

    if not arr:
        raise APIDiscoveryFailedError(f"Best candidate returned no array: {best['url']}")

    new_cache = {
        "discovered_at": datetime.now(timezone.utc).isoformat(),
        "api_url": best["url"],
        "collection_array_key": arr_key,
        "sample_element_keys": best.get("sample_keys") or [],
        "discovery_score": best["score"],
        "element_count": len(arr),
    }
    DISCOVERY_CACHE.parent.mkdir(parents=True, exist_ok=True)
    DISCOVERY_CACHE.write_text(json.dumps(new_cache, indent=2), encoding="utf-8")
    print(f"  API discovered: {best['url']}  ({len(arr)} cards, score={best['score']})")

    RAW_CACHE.write_text(json.dumps(raw_body, indent=2, ensure_ascii=False), encoding="utf-8")

    return arr, new_cache


# ---------------------------------------------------------------------------
# HAR import (one-shot; no stored auth extracted)
# ---------------------------------------------------------------------------

_PZ_HOST = "pokemon-zone.com"
_PLAYERS_MINE_PATH = "players/mine"
_CARDS_SEARCH_PATH = "cards/search/"
_API_BASE = "https://www.pokemon-zone.com/api/players/mine/"


def _parse_cn_from_url(url: str) -> int | None:
    """Extract card number from a URL like /cards/a1/1/bulbasaur/ → 1."""
    m = re.search(r"/cards/[^/]+/(\d+)/", url)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            pass
    return None


def import_har(har_path: str | Path) -> tuple[list, dict]:
    """
    Parse a browser-exported HAR file and extract the user's collection.

    Looks for two responses inside the HAR:
      - /api/cards/search/   → card catalog: internal ID → name, set, number
      - /api/players/mine/   → owned cards: internal ID + amount

    Returns (normalized_card_list, discovery_cache) where each item in
    card_list is a dict ready for normalize_pz_record():
      {"cardName": str, "setCode": str, "cardNumber": int, "ownedCount": int}

    Raises ValueError if either required endpoint is missing from the HAR.
    """
    har_path = Path(har_path)
    size_kb = har_path.stat().st_size // 1024
    print(f"  Parsing HAR: {har_path.name} ({size_kb:,} KB)")

    with har_path.open(encoding="utf-8") as f:
        har = json.load(f)

    entries = har["log"]["entries"]

    # ── Step 1: card catalog from /api/cards/search/ ─────────────────────
    # Maps internal cardDefKey → {name, set_code, card_number}
    catalog: dict[str, dict] = {}

    for e in entries:
        url = e["request"]["url"]
        if _PZ_HOST not in url or _CARDS_SEARCH_PATH not in url:
            continue
        text = e["response"]["content"].get("text", "")
        if not text:
            continue
        try:
            body = json.loads(text)
        except ValueError:
            continue

        # Unwrap nested structure: body.data.results or body.data (list)
        data = body.get("data", [])
        if isinstance(data, dict):
            data = data.get("results", [])
        if not isinstance(data, list):
            continue

        for item in data:
            if not isinstance(item, dict):
                continue
            key  = item.get("cardDefKey", "")
            name = item.get("name", "")
            exp  = item.get("expansionId", "")
            cn   = _parse_cn_from_url(item.get("url", ""))
            if key and name:
                catalog[key] = {
                    "name":        name,
                    "set_code":    exp,
                    "card_number": cn,
                }

        if catalog:
            break  # Found the real catalog — stop searching

    if not catalog:
        raise ValueError(
            "Card catalog (/api/cards/search/) not found in HAR.\n"
            "Make sure you exported the HAR from the collection-tracker page\n"
            "while all card data had loaded."
        )

    print(f"  Card catalog: {len(catalog):,} entries.")

    # ── Step 2: owned cards from /api/players/mine/ ───────────────────────
    raw_cards: list[dict] = []
    api_url: str = _API_BASE

    for e in entries:
        url = e["request"]["url"]
        if _PZ_HOST not in url or _PLAYERS_MINE_PATH not in url:
            continue
        text = e["response"]["content"].get("text", "")
        if not text:
            continue
        try:
            body = json.loads(text)
        except ValueError:
            continue

        owned = body.get("data", {}).get("cards", [])
        if not owned:
            continue

        api_url = url
        skipped_unknown = 0

        for card in owned:
            card_id    = card.get("cardId", "")
            amount     = int(card.get("amount") or card.get("amountLang_EN") or 0)
            player_exp = (card.get("expansionIds") or [""])[0]

            if amount <= 0:
                continue

            info = catalog.get(card_id)
            if not info:
                skipped_unknown += 1
                continue

            # Prefer the expansion the player data says, fall back to catalog URL
            set_code = player_exp if player_exp else info["set_code"]

            raw_cards.append({
                "cardName":   info["name"],
                "setCode":    set_code,
                "cardNumber": info["card_number"],
                "ownedCount": amount,
            })

        if skipped_unknown:
            print(f"  WARNING: {skipped_unknown} card(s) had unknown internal IDs — skipped.")
        break

    if not raw_cards:
        raise ValueError(
            "Owned card data (/api/players/mine/) not found in HAR.\n"
            "Make sure you were logged in and on the collection-tracker page\n"
            "when the HAR was exported."
        )

    total_count = sum(c["ownedCount"] for c in raw_cards)
    print(f"  Owned: {len(raw_cards)} unique entries, {total_count} total count.")

    # ── Persist discovery cache and raw data ──────────────────────────────
    cache = {
        "discovered_at":        datetime.now(timezone.utc).isoformat(),
        "api_url":              api_url,
        "collection_array_key": "data.cards",
        "import_source":        "har",
        "element_count":        len(raw_cards),
    }
    DISCOVERY_CACHE.parent.mkdir(parents=True, exist_ok=True)
    DISCOVERY_CACHE.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    RAW_CACHE.write_text(json.dumps(raw_cards, indent=2, ensure_ascii=False), encoding="utf-8")

    return raw_cards, cache


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------

def fetch_collection(login: bool = False, discover: bool = False) -> tuple[list, dict]:
    """
    Fetch the card array from Pokemon Zone.

    Tries stored auth (requests) first; falls back to Playwright if no auth stored.

    Returns (card_list, discovery_cache).
    Raises SessionNotFoundError, SessionExpiredError, AuthExpiredError,
           AuthNotFoundError, APIDiscoveryFailedError.
    """
    # Prefer stored-auth path (no Cloudflare risk)
    if AUTH_CACHE.exists() and not login:
        return fetch_with_stored_auth()

    # Playwright path
    return asyncio.run(_run_playwright(login=login, discover=discover))
