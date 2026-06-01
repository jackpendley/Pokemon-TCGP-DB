"""
Shared collection I/O and derivation helpers.

Small utilities that must behave identically across the collection-handling
scripts (sync, normalize, validate, assign, EV). Kept here as the single
source of truth so fixes don't have to be copied into every script.
"""

import html
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path


# Cached external lookups (TCGdex/Limitless) older than this are re-fetched, so
# upstream corrections and newly-added sets propagate. Shared by coord_resolver
# and validate_collection_coords so the TTL is defined once.
CACHE_MAX_AGE_DAYS = 30


def norm_card_name(name) -> str:
    """Normalize a card name for cross-source matching.

    Pipeline: html.unescape (handles &eacute; etc from Serebii) → gender symbols to
    ASCII markers BEFORE stripping (♀→f, ♂→m, so Nidoran♀/♂ don't collapse) →
    NFKD accent-fold to ASCII (Flabébé/Flabebe both → flabebe) → lowercase →
    strip non-alphanumerics. The ' ex' suffix is NOT stripped — base vs EX are
    distinct cards. Single source so all scripts and new ingestion layer normalize
    identically.
    """
    s = html.unescape(str(name or ""))
    s = s.replace("♀", "f").replace("♂", "m")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = s.lower()
    return re.sub(r"[^a-z0-9]", "", s)


def is_cache_fresh(entry: dict, max_age_days: int = CACHE_MAX_AGE_DAYS) -> bool:
    """True if a cache entry's cached_at ISO timestamp is within max_age_days.

    A missing timestamp (legacy entry) or an unparseable one is treated as stale
    so it gets re-fetched. Naive timestamps are coerced to UTC.
    """
    ts = entry.get("cached_at")
    if not ts:
        return False
    try:
        cached = datetime.fromisoformat(ts)
        if cached.tzinfo is None:
            cached = cached.replace(tzinfo=timezone.utc)
        age_days = (datetime.now(timezone.utc) - cached).total_seconds() / 86400
    except (ValueError, TypeError):
        return False
    return age_days < max_age_days


# Maps an ext_ref/TCGdex card_category to the collection.json trainer_subtype.
# Single source of truth — sync, assign, and fetch all derive their trainer
# vocabulary from this so a new subtype can't be added to one and missed elsewhere.
TRAINER_SUBTYPE_MAP: dict[str, str] = {
    "Supporter": "Supporter",
    "Item":      "Item",
    "Stadium":   "Stadium",
    "Tool":      "Pokemon Tool",
}
# The set of ext_ref card_category values that denote a Trainer card.
TRAINER_CATEGORIES = frozenset(TRAINER_SUBTYPE_MAP)

# "Rare+" / alt-art rarity tiers — cards at these rarities are full-art / alt-art
# printings (vs base 1–4 diamond). Single source for: rare-plus EV metrics
# (build_pack_ev), alt-art disambiguation (assign, sync), and the test harnesses.
# NOTE: validate_pack_sources / build_pull_probability_model use a deliberate
# superset (adding "promo"/None) and intentionally do NOT import this.
RARE_PLUS_RARITIES = frozenset({"one_star", "two_star", "three_star", "crown"})

# Legacy rarity-name aliases → canonical names (two_star/three_star, matching the
# one_star/one_diamond pattern). Single source for the normalization.
RARITY_ALIASES = {"double_star": "two_star", "triple_star": "three_star"}


def normalize_rarity(rarity: str | None) -> str | None:
    """Map a legacy rarity alias to its canonical name; pass through otherwise."""
    if rarity is None:
        return None
    return RARITY_ALIASES.get(rarity, rarity)


def ext_ref_by_coord(ext_ref_path: Path) -> dict[tuple[str, int], dict]:
    """Load external_card_reference.json indexed by (set_code_upper, card_number).

    Shared by the coord-assignment and coord-validation scripts so the index
    shape and the malformed-number handling stay identical.
    """
    records = json.loads(Path(ext_ref_path).read_text(encoding="utf-8"))
    index: dict[tuple[str, int], dict] = {}
    for r in records:
        sc = str(r.get("set_code") or "").upper().strip()
        num = r.get("number")
        if sc and num is not None:
            try:
                index[(sc, int(num))] = r
            except (TypeError, ValueError):
                pass
    return index


def strip_comments(text: str) -> str:
    """Strip JSONC-style line comments from text.

    Only removes lines whose first non-whitespace chars are '//', so string
    values containing '//' (e.g. a URL field) are preserved.
    """
    return re.sub(r"(?m)^\s*//[^\n]*\n?", "", text)


def is_ex_from_name(name: str | None) -> bool:
    """Return True if a card is a Pokémon ex, derived from its name.

    In TCG Pocket the ' ex' suffix is the canonical, unambiguous EX marker
    (e.g. 'Charizard ex', 'Mega Charizard Y ex'). This mirrors how
    fetch_ext_ref.py derives is_ex; the is_ex field is no longer stored on
    collection entries, so all EX accounting derives from the name.
    """
    return (name or "").lower().endswith(" ex")
