#!/usr/bin/env python3
"""
Cross-validated coord resolver: PZ × card_reference (offline) with live fallback.

PZ tells us a card's NAME and a reliable card_NUMBER, but its set_code is sometimes
wrong (it mislabels the "Deluxe Pack: ex" A4b set as A1/A2/A3/A4). The true coord is
recovered via card_reference.json — the frozen, cross-validated snapshot built by
fetch_source_snapshots.py + build_card_reference.py from three independent sources:
  - TCGdex    (official numbering; covers A1–B2a: 15 sets)
  - Serebii   (all 20 sets)
  - Bulbapedia (all 20 sets, via MediaWiki API)

resolve(name, pz_set, pz_number) → ResolvedCoord with a confidence:
  confirmed     card_reference has this coord with ≥2-source confirmation
  single-source card_reference has this coord with only 1-source confirmation
  conflict      independent sources disagree at this coord (surfaced, not auto-added)
  unconfirmed   card not in reference — brand-new card; run fetch_source_snapshots +
                build_card_reference to add it, then re-sync

Live-network fallback (TCGdex + Limitless) is retained for cards absent from the
reference, maintaining backward compatibility for new packs before the reference is
refreshed.

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
from _collection_io import (normalize_rarity, norm_card_name as _norm,
                            is_cache_fresh as _fresh, ROOT, REFERENCE_DIR,
                            PACK_SOURCES_JSON, CARD_REF_JSON,
                            TCGDEX_CACHE_JSON as TCGDEX_CACHE,
                            name_agrees as _name_agrees, load_records,
                            REQUEST_TIMEOUT, REQUEST_DELAY)

LIMITLESS_CACHE   = REFERENCE_DIR / "limitless_name_cache.json"

# Pokémon Zone's only known set-code mislabel: it labels "Deluxe Pack: ex" (A4b) cards as
# A1/A2/A3/A4 (keeping the right number). So a cross-set (name, number) collision is only
# genuinely ambiguous when PZ's set_code is one of those mislabel TARGETS *and* an A4b
# printing (the SOURCE) of this (name, number) exists. In every other case PZ's set_code is
# trustworthy. (Sets, upper-cased.)
_PZ_MISLABEL_SOURCE_SETS = frozenset({"A4B"})
_PZ_MISLABEL_TARGET_SETS = frozenset({"A1", "A2", "A3", "A4"})

TCGDEX_BASE   = "https://api.tcgdex.net/v2/en"
LIMITLESS_BASE = "https://pocket.limitlesstcg.com/cards"

_UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

# PZ / pack_sources label promos PROMO-A / PROMO-B; TCGdex and Limitless use P-A / P-B.
# The collection keeps the PROMO-* form (matches pack_sources / EV pools); only the
# external-source URLs are translated.
_EXT_SET_ALIAS = {"PROMO-A": "P-A", "PROMO-B": "P-B"}


def _ext_set(s: str) -> str:
    return _EXT_SET_ALIAS.get(s, s)


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
        # pack_sources indexes (kept for fallback when card_reference doesn't have a card)
        records = load_records(PACK_SOURCES_JSON)
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

        # card_reference.json: frozen, cross-validated (offline primary lookup)
        # Indexed by (set_code, card_number) and by (_norm(name), card_number) for
        # set_code correction (e.g. PZ mislabeling A4b cards as A1).
        self.ref_by_coord: dict[tuple[str, int], dict] = {}
        self.ref_name_num: dict[tuple[str, int], list[tuple[str, int]]] = {}
        if CARD_REF_JSON.exists():
            ref_data = json.loads(CARD_REF_JSON.read_text(encoding="utf-8"))
            for r in ref_data.get("records", []):
                sc = str(r.get("set_code") or "").upper().strip()
                try:
                    cn = int(r.get("card_number"))
                except (TypeError, ValueError):
                    continue
                self.ref_by_coord[(sc, cn)] = r
                self.ref_name_num.setdefault((_norm(r.get("name", "")), cn), []).append((sc, cn))

        # Per-card network caches (used only as fallback for cards absent from the reference)
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

        # ── Fast path: card_reference lookup (offline, no network) ─────────────
        # 1a. Exact coord: (pz_set, number) → reference record. When the name agrees,
        #     PZ's coord is authoritative: for dual-location A4b reprints PZ's set_code
        #     is the ORIGINAL set (the app's dex attribution — user-verified 2026-06-12),
        #     so a (name, number) collision with an A4b printing is not ambiguous; the
        #     original-set slot is the right one either way.
        ref = self.ref_by_coord.get((pz_s, num))
        if ref and _name_agrees(name, ref.get("name", "")):
            return self._coord_from_ref(name, ref)
        elif ref:
            # Reference has a DIFFERENT card at the PZ coord. Before declaring a conflict,
            # try resolving by (name, number): PZ emits HYBRID coords for A4b "Deluxe Pack:
            # ex" reprints — the original set_code + the A4b number — e.g. Greninja as A1/114
            # where A1/114 is really Clefable but (Greninja, 114) uniquely lives at A4b/114.
            # Fall through to the 1b name+number handler when it can resolve; only when the
            # PZ name exists nowhere at this number is it a genuine conflict.
            ref_name = ref.get("name", "")
            if not self.ref_name_num.get((_norm(name), num)):
                return ResolvedCoord(name, pz_s, num, None, "conflict",
                                     sources_agreed=["card_reference"],
                                     detail=f"card_reference says {ref_name!r} at {pz_s}/{num}")
            # else: fall through to 1b — (name, number) resolves the PZ hybrid coord.

        # 1b. Name+number lookup: handles PZ set_code mislabels (e.g. A4b cards as A1)
        ref_cands = self.ref_name_num.get((_norm(name), num), [])
        if len(ref_cands) == 1:
            ref = self.ref_by_coord[ref_cands[0]]
            return self._coord_from_ref(name, ref)
        elif len(ref_cands) > 1:
            # Multiple sets share this (name, number). PZ's set_code is genuinely ambiguous
            # ONLY when it is a mislabel target (A1/A2/A3/A4) AND an A4b printing of this
            # (name, number) exists (the possible mislabel source). In every other case —
            # no A4b candidate, or PZ reports a non-target set like B1a/A1a — PZ's set_code
            # is trustworthy, so resolve to it when it's one of the confirmed candidates.
            cand_sets = {c[0].upper() for c in ref_cands}
            if pz_s in cand_sets:
                a4b_ambiguous = (pz_s in _PZ_MISLABEL_TARGET_SETS
                                 and bool(cand_sets & _PZ_MISLABEL_SOURCE_SETS))
                if not a4b_ambiguous:
                    match = next(c for c in ref_cands if c[0].upper() == pz_s)
                    return self._coord_from_ref(name, self.ref_by_coord[match])
            return ResolvedCoord(name, None, num, None, "conflict",
                                 sources_agreed=["card_reference"],
                                 detail=f"ambiguous sets in reference: {sorted(ref_cands)}")

        # ── Fallback: live network (for brand-new cards not yet in reference) ──
        # A card absent from card_reference is genuinely new — run fetch_source_snapshots
        # then build_card_reference to add it, then re-sync. In the meantime the old
        # pack_sources + TCGdex/Limitless logic applies as a temporary bridge.
        cands = self.ps_name_num.get((_norm(name), num), [])
        if len(cands) == 1:
            S, backed = cands[0], True
        elif pz_s in cands:
            S, backed = pz_s, True
        elif len(cands) > 1:
            confirmed = [c for c in cands if self._confirm(name, c, num)[0]]
            if len(confirmed) == 1:
                S, backed = confirmed[0], True
            else:
                return ResolvedCoord(name, None, num, None, "conflict",
                                     detail=f"ambiguous sets {sorted(cands)}; not in card_reference")
        elif pz_s:
            S, backed = pz_s, False
        else:
            return ResolvedCoord(name, None, num, None, "unconfirmed",
                                 detail="not in card_reference and no pack_sources match")

        rar = normalize_rarity(self.ps_by_coord.get((S, num), {}).get("rarity")) if backed else None
        agreed, disagreed = self._confirm(name, S, num)
        sources = (["pack_sources"] if backed else []) + agreed
        if disagreed:
            conf = "conflict"
            detail = f"{','.join(disagreed)} name a different card at {S}/{num}"
        elif agreed:
            conf = "confirmed"
            detail = f"agreed: {','.join(sources)} (live; not in card_reference)"
        elif backed:
            conf = "single-source"
            detail = "pack_sources only; not in card_reference — run reference refresh"
        else:
            conf = "unconfirmed"
            detail = "not in card_reference; no source confirms"
        return ResolvedCoord(name, S, num, rar, conf, sources, detail)

    def _coord_from_ref(self, pz_name: str, ref: dict) -> ResolvedCoord:
        """Build a ResolvedCoord from a card_reference record."""
        sc = ref["set_code"]
        cn = ref["card_number"]
        rar = normalize_rarity(ref.get("rarity"))
        ref_conf = ref.get("confidence", "unconfirmed")
        # Map card_reference confidence to the resolver's vocabulary
        conf_map = {"confirmed": "confirmed", "single": "single-source", "conflict": "conflict"}
        conf = conf_map.get(ref_conf, "unconfirmed")
        sources_agreed = ["card_reference"] + ref.get("confirmations", [])
        detail = f"card_reference ({ref_conf})"
        if ref.get("conflict_notes"):
            detail += f"; notes: {'; '.join(ref['conflict_notes'][:2])}"
        return ResolvedCoord(pz_name, sc, cn, rar, conf, sources_agreed, detail)
