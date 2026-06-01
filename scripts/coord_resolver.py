#!/usr/bin/env python3
"""
Cross-validated coord resolver: PZ × pack_sources × TCGdex × Limitless.

PZ tells us a card's NAME and a reliable card_NUMBER, but its set_code is sometimes
wrong (it mislabels the "Deluxe Pack: ex" A4b set as A1/A2/A3/A4). The true coord is
recovered from (card_name, card_number) → pack_sources, then CONFIRMED against
independent sources:
  - TCGdex API   (official numbering; covers A1–B2a only)
  - Limitless    (pocket.limitlesstcg.com; covers everything, incl. A4b/B3/B3a/promo)

resolve(name, pz_set, pz_number) → ResolvedCoord with a confidence:
  confirmed     pack_sources + ≥1 independent source agree
  single-source only pack_sources/Limitless backs it (no independent disagreement)
  conflict      an independent source names a DIFFERENT card at that coord
  unconfirmed   nothing reachable confirms it

Caches: TCGdex in data/reference/tcgdex_card_cache.json (shared w/ validate_collection_coords),
Limitless names in data/reference/limitless_name_cache.json. Both with a 30-day TTL.
"""

import json
import re
import sys
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _collection_io import normalize_rarity, norm_card_name as _norm, is_cache_fresh as _fresh

ROOT = Path(__file__).resolve().parent.parent
PACK_SOURCES_JSON = ROOT / "data" / "reference" / "pack_sources.json"
TCGDEX_CACHE      = ROOT / "data" / "reference" / "tcgdex_card_cache.json"
LIMITLESS_CACHE   = ROOT / "data" / "reference" / "limitless_name_cache.json"

TCGDEX_BASE   = "https://api.tcgdex.net/v2/en"
LIMITLESS_BASE = "https://pocket.limitlesstcg.com/cards"
REQUEST_TIMEOUT = 12
REQUEST_DELAY   = 0.35

_UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

# PZ / pack_sources label promos PROMO-A / PROMO-B; TCGdex and Limitless use P-A / P-B.
# The collection keeps the PROMO-* form (matches pack_sources / EV pools); only the
# external-source URLs are translated.
_EXT_SET_ALIAS = {"PROMO-A": "P-A", "PROMO-B": "P-B"}


def _ext_set(s: str) -> str:
    return _EXT_SET_ALIAS.get(s, s)


# Forme qualifiers some sources include and others omit (e.g. Limitless titles both
# "Zygarde 10% Forme" and "Zygarde 50% Forme" simply "Zygarde"). Stripped only for the
# independent NAME-confirmation comparison — the card_number still distinguishes formes,
# and " ex" is intentionally NOT stripped (base vs ex are genuinely different cards).
_FORME_RE = re.compile(r"\s+(?:\d+%\s+)?(?:complete\s+|sunny\s+|rainy\s+|snowy\s+|normal\s+)?forme?$", re.I)


def _name_agrees(a: str, b: str) -> bool:
    if _norm(a) == _norm(b):
        return True
    sa, sb = _FORME_RE.sub("", str(a)), _FORME_RE.sub("", str(b))
    return _norm(sa) == _norm(sb)


@dataclass
class ResolvedCoord:
    name: str
    set_code: str | None
    card_number: int | None
    rarity: str | None
    confidence: str            # confirmed | single-source | conflict | unconfirmed
    sources_agreed: list = field(default_factory=list)   # e.g. ["pack_sources", "tcgdex", "limitless"]
    detail: str = ""


class CoordResolver:
    def __init__(self, *, fetch: bool = True, tcgdex_sets: set | None = None):
        self.fetch = fetch
        # pack_sources indexes
        data = json.loads(PACK_SOURCES_JSON.read_text(encoding="utf-8"))
        records = data.get("records", data) if isinstance(data, dict) else data
        self.ps_by_coord: dict[tuple, dict] = {}
        self.ps_name_num: dict[tuple, list] = {}
        for r in records:
            s = str(r.get("set_code") or "").upper().strip()
            try:
                n = int(r.get("card_number"))
            except (TypeError, ValueError):
                continue
            self.ps_by_coord[(s, n)] = r
            self.ps_name_num.setdefault((_norm(r.get("card_name")), n), []).append(s)
        # caches
        self.tcgdex_cache = json.loads(TCGDEX_CACHE.read_text()) if TCGDEX_CACHE.exists() else {}
        self.limitless_cache = json.loads(LIMITLESS_CACHE.read_text()) if LIMITLESS_CACHE.exists() else {}
        self._dirty_td = False
        self._dirty_ll = False
        # Caller may inject an already-fetched set list (validate_collection_coords
        # fetches it once and passes it in) to avoid a duplicate /series/tcgp request.
        self.tcgdex_sets = tcgdex_sets if tcgdex_sets is not None else self._tcgdex_sets()

    # ── source name lookups (cached) ─────────────────────────────────────────
    def _tcgdex_sets(self) -> set:
        if not self.fetch:
            return {k.rsplit("-", 1)[0].upper() for k in self.tcgdex_cache}
        try:
            req = urllib.request.Request(f"{TCGDEX_BASE}/series/tcgp", headers=_UA)
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                d = json.loads(resp.read())
            return {s["id"].upper() for s in d.get("sets", [])}
        except Exception:
            return {k.rsplit("-", 1)[0].upper() for k in self.tcgdex_cache}

    def _tcgdex_name(self, s: str, n: int) -> str | None:
        """Return the card name TCGdex has at S/N (None if not found / not covered)."""
        s = _ext_set(s)
        if s not in self.tcgdex_sets:
            return None
        key = f"{s}-{n:03d}"
        ent = self.tcgdex_cache.get(key)
        if ent and ent.get("error") != "not_found" and _fresh(ent):
            return ent.get("name")
        if not self.fetch:
            return ent.get("name") if ent and not ent.get("error") else None
        try:
            req = urllib.request.Request(f"{TCGDEX_BASE}/cards/{s}-{n:03d}", headers=_UA)
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                d = json.loads(resp.read())
            rec = {"name": d.get("name"), "hp": d.get("hp"), "source": "tcgdex",
                   "cached_at": datetime.now(timezone.utc).isoformat()}
        except urllib.error.HTTPError as e:
            rec = {"error": "not_found" if e.code == 404 else f"http_{e.code}", "source": "tcgdex",
                   "cached_at": datetime.now(timezone.utc).isoformat()}
        except Exception as e:
            rec = {"error": str(e), "source": "tcgdex"}
        self.tcgdex_cache[key] = rec
        self._dirty_td = True
        time.sleep(REQUEST_DELAY)
        return rec.get("name") if not rec.get("error") else None

    def _limitless_name(self, s: str, n: int) -> str | None:
        """Return the card name on the live Limitless page at S/N."""
        s = _ext_set(s)
        key = f"{s}/{n}"
        ent = self.limitless_cache.get(key)
        if ent and ent.get("name") is not None and _fresh(ent):
            return ent.get("name")
        if not self.fetch:
            return ent.get("name") if ent else None
        name = None
        try:
            req = urllib.request.Request(f"{LIMITLESS_BASE}/{s}/{n}", headers=_UA)
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                html = resp.read().decode("utf-8", errors="replace")
            m = re.search(r'<span class="card-text-name">\s*<a[^>]*>([^<]+)</a>', html) \
                or re.search(r'<span class="card-text-name">([^<]+)</span>', html) \
                or re.search(r"<title>\s*([^<·–|]+)", html)
            if m:
                name = re.sub(r"&#0?39;|&apos;", "'", m.group(1)).strip()
        except urllib.error.HTTPError:
            name = None
        except Exception:
            name = None
        self.limitless_cache[key] = {"name": name, "cached_at": datetime.now(timezone.utc).isoformat()}
        self._dirty_ll = True
        time.sleep(REQUEST_DELAY)
        return name

    def save(self) -> None:
        if self._dirty_td:
            TCGDEX_CACHE.write_text(json.dumps(self.tcgdex_cache, indent=2, ensure_ascii=False, sort_keys=True))
            self._dirty_td = False
        if self._dirty_ll:
            LIMITLESS_CACHE.write_text(json.dumps(self.limitless_cache, indent=2, ensure_ascii=False, sort_keys=True))
            self._dirty_ll = False

    # ── core ─────────────────────────────────────────────────────────────────
    def _confirm(self, name: str, s: str, n: int) -> tuple[list, list]:
        """Return (agreed_sources, disagreed_sources) among the independent sources."""
        agreed, disagreed = [], []
        for src, fn in (("tcgdex", self._tcgdex_name), ("limitless", self._limitless_name)):
            other = fn(s, n)
            if other is None:
                continue
            (agreed if _name_agrees(other, name) else disagreed).append(src)
        return agreed, disagreed

    def resolve(self, name: str, pz_set: str | None, pz_number) -> ResolvedCoord:
        try:
            num = int(pz_number)
        except (TypeError, ValueError):
            return ResolvedCoord(name, None, None, None, "unconfirmed", detail="no card_number")
        pz_s = str(pz_set or "").upper().strip()

        cands = self.ps_name_num.get((_norm(name), num), [])
        # pick candidate set from pack_sources
        if len(cands) == 1:
            S, backed = cands[0], True
        elif pz_s in cands:
            S, backed = pz_s, True
        elif len(cands) > 1:
            # ambiguous: confirm each candidate, prefer the one an independent source agrees with
            confirmed = [c for c in cands if self._confirm(name, c, num)[0]]
            if len(confirmed) == 1:
                S, backed = confirmed[0], True
            else:
                return ResolvedCoord(name, None, num, None, "conflict",
                                     detail=f"ambiguous sets {sorted(cands)}")
        elif pz_s:
            S, backed = pz_s, False  # no pack_sources record (e.g. promo) → trust PZ coord
        else:
            # No pack_sources match AND PZ gave no set → nothing to anchor a coord on.
            return ResolvedCoord(name, None, num, None, "unconfirmed",
                                 detail="no pack_sources match and no PZ set_code")

        rar = normalize_rarity(self.ps_by_coord.get((S, num), {}).get("rarity")) if backed else None
        agreed, disagreed = self._confirm(name, S, num)
        sources = (["pack_sources"] if backed else []) + agreed
        if disagreed:
            conf = "conflict"
            detail = f"{','.join(disagreed)} name a different card at {S}/{num}"
        elif agreed:
            conf = "confirmed"
            detail = f"agreed: {','.join(sources)}"
        elif backed:
            conf = "single-source"   # only the pack_sources scrape backs it
            detail = "pack_sources only (no independent source reachable/covered)"
        else:
            conf = "unconfirmed"     # promo with no pack_sources and no Limitless confirmation
            detail = "no source confirms"
        return ResolvedCoord(name, S, num, rar, conf, sources, detail)
