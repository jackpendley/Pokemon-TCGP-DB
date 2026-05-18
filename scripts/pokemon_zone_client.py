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

import requests as _requests

ROOT = Path(__file__).resolve().parent.parent
BROWSER_SESSION_DIR = ROOT / ".browser_session"
DISCOVERY_CACHE     = ROOT / "data" / "sync" / "api_discovery_cache.json"
RAW_CACHE           = ROOT / "data" / "sync" / "last_sync_raw.json"
AUTH_CACHE          = ROOT / "data" / "sync" / ".auth.json"

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


def _try_fetch(url: str, cookies: dict, auth_headers: dict) -> tuple[list | None, dict | list | None]:
    """Try a GET request and return (card_array, raw_body) or (None, None)."""
    req_headers = {**auth_headers, "Accept": "application/json, */*"}
    try:
        r = _requests.get(url, headers=req_headers, cookies=cookies, timeout=30)
        if r.status_code != 200:
            return None, None
        body = r.json()
        score = _score_response(url, body)
        arr, _ = _find_array(body)
        if arr and score >= 3:
            return arr, body
    except Exception:
        pass
    return None, None


def import_curl_auth(curl_str: str) -> tuple[list, dict]:
    """
    Parse a cURL command, discover the collection API, save auth, and
    return (card_array, discovery_cache).

    Raises ValueError for unparseable cURL.
    Raises APIDiscoveryFailedError if the collection API cannot be found.
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

    # Try the URL from the pasted cURL first
    print(f"  Trying URL from cURL: {url[:80]}...")
    arr, body = _try_fetch(url, cookies, auth_headers)
    api_url = url

    if arr is None:
        print("  That URL doesn't appear to be the collection API.")
        # Try the cached API URL with the new credentials
        if DISCOVERY_CACHE.exists():
            try:
                cached = json.loads(DISCOVERY_CACHE.read_text(encoding="utf-8"))
                cached_url = cached.get("api_url", "")
                if cached_url and cached_url != url:
                    print(f"  Trying cached API URL: {cached_url[:80]}...")
                    arr, body = _try_fetch(cached_url, cookies, auth_headers)
                    if arr:
                        api_url = cached_url
                        print(f"  Cached URL works with new credentials: {len(arr)} cards.")
            except Exception:
                pass

    if arr is None or body is None:
        raise APIDiscoveryFailedError(CURL_IMPORT_GUIDANCE)

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

    # Update discovery cache and raw cache
    _, arr_key = _find_array(body)
    cache = {
        "discovered_at": auth["imported_at"],
        "api_url": api_url,
        "collection_array_key": arr_key,
        "sample_element_keys": list(arr[0].keys())[:8] if isinstance(arr[0], dict) else [],
        "element_count": len(arr),
    }
    DISCOVERY_CACHE.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    RAW_CACHE.write_text(json.dumps(body, indent=2, ensure_ascii=False), encoding="utf-8")

    return arr, cache


def fetch_with_stored_auth() -> tuple[list, dict]:
    """
    Fetch the collection using stored auth credentials (no browser automation).

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
    api_url     = auth.get("api_url", "")
    cookies     = auth.get("cookies", {})
    auth_headers = auth.get("auth_headers", {})

    if not api_url:
        raise APIDiscoveryFailedError(
            "Stored auth is missing api_url. Re-run --curl-import."
        )

    req_headers = {**auth_headers, "Accept": "application/json, */*"}

    try:
        resp = _requests.get(api_url, headers=req_headers, cookies=cookies, timeout=30)
    except _requests.RequestException as e:
        raise APIDiscoveryFailedError(f"Network request failed: {e}") from e

    if resp.status_code in (301, 302, 401, 403):
        raise AuthExpiredError(
            f"Auth credentials expired (HTTP {resp.status_code}).\n"
            "Re-run:  python3 scripts/sync_collection.py --curl-import\n"
            "\n"
            "Go to pokemon-zone.com/collection-tracker/ in your browser,\n"
            "open DevTools → Network → find the collection API request,\n"
            "right-click → Copy as cURL, then paste when prompted."
        )

    if resp.status_code != 200:
        raise APIDiscoveryFailedError(
            f"Unexpected HTTP {resp.status_code} from collection API.\n"
            "Try re-running --curl-import."
        )

    try:
        body = resp.json()
    except ValueError as e:
        raise AuthExpiredError(
            "API returned non-JSON (possible login redirect).\n"
            "Re-run:  python3 scripts/sync_collection.py --curl-import"
        ) from e

    arr, arr_key = _find_array(body)
    if not arr:
        raise APIDiscoveryFailedError(
            f"API response at {api_url} contains no array data."
        )

    # Update caches
    cache = {
        "discovered_at": datetime.now(timezone.utc).isoformat(),
        "api_url": api_url,
        "collection_array_key": arr_key,
        "sample_element_keys": list(arr[0].keys())[:8] if isinstance(arr[0], dict) else [],
        "element_count": len(arr),
    }
    DISCOVERY_CACHE.parent.mkdir(parents=True, exist_ok=True)
    DISCOVERY_CACHE.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    RAW_CACHE.write_text(json.dumps(body, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  Fetched {len(arr)} cards via stored auth.")

    return arr, cache


# ---------------------------------------------------------------------------
# Playwright path (fallback — may hit Cloudflare)
# ---------------------------------------------------------------------------

def _is_static_playwright(url: str) -> bool:
    return _is_static(url)


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
