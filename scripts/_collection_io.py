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


# ---------------------------------------------------------------------------
# Canonical set-code registry.
# Keys are the canonical casing used throughout the pipeline. The value dict
# carries: pack_type ("single"/"multi") and limitless_slug (the slug used in
# Limitless URLs, which may differ in casing — same casing throughout, e.g. B3a).
# ---------------------------------------------------------------------------
SET_REGISTRY: dict[str, dict] = {
    "A1":     {"pack_type": "multi",  "limitless_slug": "A1"},
    "A1a":    {"pack_type": "single", "limitless_slug": "A1a"},
    "A2":     {"pack_type": "multi",  "limitless_slug": "A2"},
    "A2a":    {"pack_type": "single", "limitless_slug": "A2a"},
    "A2b":    {"pack_type": "single", "limitless_slug": "A2b"},
    "A3":     {"pack_type": "multi",  "limitless_slug": "A3"},
    "A3a":    {"pack_type": "single", "limitless_slug": "A3a"},
    "A3b":    {"pack_type": "single", "limitless_slug": "A3b"},
    "A4":     {"pack_type": "multi",  "limitless_slug": "A4"},
    "A4a":    {"pack_type": "single", "limitless_slug": "A4a"},
    "A4b":    {"pack_type": "single", "limitless_slug": "A4b"},
    "B1":     {"pack_type": "multi",  "limitless_slug": "B1"},
    "B1a":    {"pack_type": "single", "limitless_slug": "B1a"},
    "B2":     {"pack_type": "single", "limitless_slug": "B2"},
    "B2a":    {"pack_type": "single", "limitless_slug": "B2a"},
    "B2b":    {"pack_type": "single", "limitless_slug": "B2b"},
    "B3":     {"pack_type": "single", "limitless_slug": "B3"},
    "B3a":    {"pack_type": "single", "limitless_slug": "B3a"},
    "PROMO-A":{"pack_type": "single", "limitless_slug": "PROMO-A"},
    "PROMO-B":{"pack_type": "single", "limitless_slug": "PROMO-B"},
}

# Derived convenience sets for scripts that need them:
SINGLE_PACK_SETS: frozenset[str] = frozenset(
    k for k, v in SET_REGISTRY.items() if v["pack_type"] == "single"
)
MULTI_PACK_SETS: frozenset[str] = frozenset(
    k for k, v in SET_REGISTRY.items() if v["pack_type"] == "multi"
)
# All valid set codes (for validators):
VALID_SET_CODES: frozenset[str] = frozenset(SET_REGISTRY)

# Case-insensitive → canonical casing lookup (used by build_pack_sources to
# normalise set_codes read from HTML-cache filenames like "card_B3a_N.html"):
_SET_CANONICAL: dict[str, str] = {k.upper(): k for k in SET_REGISTRY}


def canonical_set_code(raw: str) -> str:
    """Return the canonical casing for a set code, or the original if unknown."""
    return _SET_CANONICAL.get(raw.upper(), raw)


# ---------------------------------------------------------------------------
# Pack Hourglasses cost (single pack). Single source for build_pack_ev and
# generate_hourglass_spending_plan.
# ---------------------------------------------------------------------------
HOURGLASS_PER_PACK: int = 12


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


def _parse_iso(ts: str | None):
    """Parse an ISO8601 timestamp (accepting a trailing 'Z') to an aware UTC datetime."""
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def card_reference_freshness(card_ref_path: Path, sources_dir: Path,
                             max_age_days: int = CACHE_MAX_AGE_DAYS) -> tuple[str, str]:
    """Assess whether card_reference.json is fresh relative to its source snapshots.

    Returns (level, message):
      'ok'             — up to date
      'missing'        — card_reference.json absent
      'stale_rebuild'  — a source snapshot is newer than card_reference (rebuild needed)
      'stale_age'      — card_reference older than max_age_days (refresh recommended)
    Used by the pipeline as a non-fatal freshness gate so syncs never validate against a
    stale reference (e.g. after a new set's snapshots are fetched but the reference isn't
    rebuilt). Falls back to 'ok' when timestamps can't be parsed (never blocks the pipeline).
    """
    p = Path(card_ref_path)
    if not p.exists():
        return ("missing", "card_reference.json not found — run fetch_source_snapshots.py + build_card_reference.py")
    try:
        meta = json.loads(p.read_text(encoding="utf-8")).get("_meta", {})
    except (OSError, json.JSONDecodeError):
        return ("ok", "")
    gen_dt = _parse_iso(meta.get("generated_at"))
    if gen_dt is None:
        return ("ok", "")

    newest_snap = None
    sd = Path(sources_dir)
    if sd.exists():
        for snap in sd.glob("*/*.json"):
            try:
                ca = json.loads(snap.read_text(encoding="utf-8")).get("_meta", {}).get("cached_at")
            except (OSError, json.JSONDecodeError):
                continue
            dt = _parse_iso(ca)
            if dt and (newest_snap is None or dt > newest_snap):
                newest_snap = dt

    if newest_snap and newest_snap > gen_dt:
        return ("stale_rebuild",
                f"card_reference ({gen_dt.date()}) is older than source snapshots "
                f"({newest_snap.date()}) — run build_card_reference.py")
    age_days = int((datetime.now(timezone.utc) - gen_dt).total_seconds() / 86400)
    if age_days > max_age_days:
        return ("stale_age",
                f"card_reference is {age_days}d old (>{max_age_days}d) — run "
                f"fetch_source_snapshots.py + build_card_reference.py")
    return ("ok", f"fresh ({age_days}d old)")


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

# "Rare+" / alt-art rarity tiers — cards at these tiers are full-art / alt-art
# printings (vs the base common–double_rare diamonds). Single source for: rare-plus
# EV metrics (build_pack_ev), alt-art disambiguation (assign, sync), and the test
# harnesses.
# NOTE: validate_pack_sources / build_pull_probability_model use a deliberate
# superset (adding the base diamonds, "promo"/None) built from this set.
RARE_PLUS_RARITIES = frozenset({
    "illustration_rare", "super_rare", "special_illustration_rare",
    "immersive", "shiny_rare", "shiny_super_rare", "ultra_rare",
})

# Canonical ordered rarity list — the 11 Pokémon TCG Pocket tiers per Bulbapedia
# "Rarity (TCG Pocket)", low→high, plus operational sentinels. Drives RARITY_FIELDS
# in build_pull_probability_model, VALID_RARITIES in validate_pack_sources, and
# RARITY_RANK below.
#   common ◊ · uncommon ◊◊ · rare ◊◊◊ · double_rare ◊◊◊◊ · illustration_rare ☆ ·
#   super_rare ☆☆ · special_illustration_rare ☆☆(rainbow) · immersive ☆☆☆ ·
#   shiny_rare ✷ · shiny_super_rare ✷✷ · ultra_rare 👑
# 'promo' (PROMO-A/-B cards, no rarity symbol) and 'unknown' (unresolved) are kept
# after the 11 named tiers.
RARITIES: tuple[str, ...] = (
    "common", "uncommon", "rare", "double_rare",
    "illustration_rare", "super_rare", "special_illustration_rare", "immersive",
    "shiny_rare", "shiny_super_rare", "ultra_rare",
    "promo", "unknown",
)

# Ordered rank (1-based) over the 11 named tiers, for rarity-based disambiguation
# (sync_collection alt-art matching). Sentinels (promo/unknown) are omitted —
# callers default them to a high "unknown" rank.
RARITY_RANK: dict[str, int] = {
    name: i for i, name in enumerate(RARITIES, start=1)
    if name not in ("promo", "unknown")
}

# Legacy symbol-tier rarity names → new canonical names. Single source for the
# migration; normalize_rarity() applies it so any value still stored under the old
# scheme (e.g. an un-regenerated collection.json entry) reads as the new name.
# 'two_star' maps to the super_rare baseline; the super_rare→special_illustration_rare
# split is applied separately from the curated SIR reference (build_card_reference).
RARITY_ALIASES = {
    "one_diamond":   "common",
    "two_diamond":   "uncommon",
    "three_diamond": "rare",
    "four_diamond":  "double_rare",
    "one_star":      "illustration_rare",
    "two_star":      "super_rare",
    "double_star":   "super_rare",
    "three_star":    "immersive",
    "triple_star":   "immersive",
    "one_shiny":     "shiny_rare",
    "two_shiny":     "shiny_super_rare",
    "crown":         "ultra_rare",
}

# Unicode rarity symbols → canonical names. Used by build_pack_sources and
# fetch_ext_ref to parse rarity from Limitless / ext_ref HTML. Longest glyphs must
# come first (substring matching: '◊◊◊◊' before '◊◊◊'; '✷✷' before '✷').
RARITY_SYMBOLS: dict[str, str] = {
    "◊◊◊◊": "double_rare",
    "◊◊◊":  "rare",
    "◊◊":   "uncommon",
    "◊":    "common",
    "☆☆☆":  "immersive",
    "☆☆":   "super_rare",
    "☆":    "illustration_rare",
    "✷✷":   "shiny_super_rare",
    "✸✸":   "shiny_super_rare",
    "✷":    "shiny_rare",
    "✸":    "shiny_rare",
    "♛":    "ultra_rare",
    "👑":   "ultra_rare",
    "✦":    "promo",
}


def normalize_rarity(rarity: str | None) -> str | None:
    """Map a legacy symbol-tier rarity name to its new canonical name; pass through
    values that are already canonical (or None)."""
    if rarity is None:
        return None
    return RARITY_ALIASES.get(rarity, rarity)


def pack_sources_by_coord(path: Path) -> dict[tuple[str, int], dict]:
    """Load pack_sources.json indexed by (set_code_upper, card_number).

    Handles both the flat-array and {'records': [...]} envelope forms.
    set_code is always uppercased so callers don't need to normalise.
    """
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    records = raw.get("records", raw) if isinstance(raw, dict) else raw
    index: dict[tuple[str, int], dict] = {}
    for r in records:
        sc = str(r.get("set_code") or "").upper().strip()
        cn_raw = r.get("card_number")
        if sc and cn_raw is not None:
            try:
                index[(sc, int(cn_raw))] = r
            except (TypeError, ValueError):
                pass
    return index


def card_reference_by_coord(path: Path) -> dict[tuple[str, int], dict]:
    """Load card_reference.json indexed by (set_code_upper, card_number).

    Returns {} when the file does not exist (not an error — reference may not
    have been built yet for a brand-new pack).
    """
    p = Path(path)
    if not p.exists():
        return {}
    raw = json.loads(p.read_text(encoding="utf-8"))
    records = raw.get("records", []) if isinstance(raw, dict) else raw
    index: dict[tuple[str, int], dict] = {}
    for r in records:
        sc = str(r.get("set_code") or "").upper().strip()
        cn_raw = r.get("card_number")
        if cn_raw is not None:
            try:
                index[(sc, int(cn_raw))] = r
            except (TypeError, ValueError):
                pass
    return index


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


def field_slug(name: str) -> str:
    """Normalize a string to a lower-snake-case field/key slug.

    Used for indexing collection entries and ext_ref records by name where
    exact Unicode matching is not required. Distinct from norm_card_name
    (which is for cross-source card-name matching): this replaces non-alphanumeric
    chars with underscores rather than stripping them.

    ⚠️  Gender symbols (♀, ♂) are stripped to underscore, NOT substituted with f/m.
    Both Nidoran♀ and Nidoran♂ produce 'nidoran', so this function MUST NOT be used
    to build a lookup that must distinguish the two variants. Use norm_card_name
    (which maps ♀→f, ♂→m before stripping) for any gender-sensitive card matching.
    """
    return re.sub(r"[^a-z0-9]", "_", name.lower().strip()).strip("_")


def is_ex_from_name(name: str | None) -> bool:
    """Return True if a card is a Pokémon ex, derived from its name.

    In TCG Pocket the ' ex' suffix is the canonical, unambiguous EX marker
    (e.g. 'Charizard ex', 'Mega Charizard Y ex'). This mirrors how
    fetch_ext_ref.py derives is_ex; the is_ex field is no longer stored on
    collection entries, so all EX accounting derives from the name.
    """
    return (name or "").lower().endswith(" ex")
