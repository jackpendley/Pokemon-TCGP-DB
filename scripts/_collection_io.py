"""
Shared collection I/O and derivation helpers.

Small utilities that must behave identically across the collection-handling
scripts (sync, normalize, validate, assign, EV). Kept here as the single
source of truth so fixes don't have to be copied into every script.
"""

import html
import json
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# Canonical repo paths. Every multi-script data file is named once here so a
# data/ reorganisation is a one-file change; scripts import these (aliasing to
# their historical local name where it differs). Single-script outputs (review
# markdown, per-script caches, schemas) stay local to their script.
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
REFERENCE_DIR = ROOT / "data" / "reference"
CURRENT_DIR   = ROOT / "data" / "current"
EXPORTS_DIR   = ROOT / "data" / "exports"
SOURCES_DIR   = REFERENCE_DIR / "sources"

COLLECTION_JSON            = ROOT / "collection.json"   # canonical JSONC source of truth
COLLECTION_NORMALIZED_JSON = CURRENT_DIR / "collection_normalized.json"
PACK_SOURCES_JSON          = REFERENCE_DIR / "pack_sources.json"
CARD_REF_JSON              = REFERENCE_DIR / "card_reference.json"
EXT_REF_JSON               = REFERENCE_DIR / "external" / "external_card_reference.json"
PZ_PACK_ODDS_JSON          = REFERENCE_DIR / "pz_pack_odds.json"
PULL_MODEL_JSON            = REFERENCE_DIR / "pull_probability_model.json"
REPRINT_LINKS_JSON         = REFERENCE_DIR / "reprint_links.json"
TCGDEX_CACHE_JSON          = REFERENCE_DIR / "tcgdex_card_cache.json"
PACK_EV_JSON               = CURRENT_DIR / "pack_ev.json"
PROMO_EV_JSON              = CURRENT_DIR / "promo_pack_ev.json"
DECK_VALIDATION_JSON       = EXPORTS_DIR / "deck_recommendation_validation.json"


# Cached external lookups (TCGdex/Limitless) older than this are re-fetched, so
# upstream corrections and newly-added sets propagate. Shared by coord_resolver
# and validate_collection_coords so the TTL is defined once.
CACHE_MAX_AGE_DAYS = 30


# HTTP request tuning, centralised so the network-timing knobs live in one place
# instead of drifting per script. Two pairs by workload:
#   * REQUEST_* — lightweight JSON-API / single-card page fetches
#     (coord_resolver, validate_collection_coords).
#   * SNAPSHOT_REQUEST_* — full-set HTML scrapes (Bulbapedia/Serebii) in
#     fetch_source_snapshots, which are heavier so they get a longer timeout and
#     a politer delay.
REQUEST_TIMEOUT = 12            # seconds per request
REQUEST_DELAY = 0.35           # seconds between requests
SNAPSHOT_REQUEST_TIMEOUT = 15   # seconds per request
SNAPSHOT_REQUEST_DELAY = 0.4   # seconds between requests


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
    "B3b":    {"pack_type": "single", "limitless_slug": "B3b"},
    "B4":     {"pack_type": "single", "limitless_slug": "B4"},
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

# A4b ("Deluxe Pack: ex") is a reprint set. Pokemon Zone mislabels its cards as
# the original multi-pack they reprint from (A1–A4), keeping the card number, so
# every script that reconciles that relationship needs the same two facts. Single
# source of truth here (upper-cased; A4B_ORIGINAL_SETS is ordered by debut so it
# can drive debut-order tie-breaks as well as membership tests).
A4B_SET_CODE = "A4B"
A4B_ORIGINAL_SETS: tuple[str, ...] = ("A1", "A2", "A3", "A4")

# Promo sets (bought with a different currency, scored separately from the
# hourglass packs).
PROMO_SET_CODES: frozenset[str] = frozenset({"PROMO-A", "PROMO-B"})

# EV scoring weights shared by the regular and promo pack scorers. Each scorer
# spreads this and adds its own term (deck_target for regular, ex_missing for
# promo), so the common weights can't drift between the two models.
EV_BASE_SCORING_WEIGHTS: dict[str, float] = {
    "new_card":     1.0,   # first copy of any unseen unique card
    "copy_up_to_2": 0.4,   # second copy (can use 2 copies per deck)
}

# Case-insensitive → canonical casing lookup (used by build_pack_sources to
# normalise set_codes read from HTML-cache filenames like "card_B3a_N.html"):
_SET_CANONICAL: dict[str, str] = {k.upper(): k for k in SET_REGISTRY}


def canonical_set_code(raw: str) -> str:
    """Return the canonical *display* casing for a set code, or the original if unknown.

    Display/serialization only — e.g. "B3A" → "B3a". Do NOT use this to build keys for
    the by-coord indexes (card_reference/ext_ref/pack_sources): those are keyed by plain
    .upper() (see parse_coord), so canonical_set_code("B3a") == "B3a" would MISS the
    "B3A" key for every mixed-case sub-set. To look up an index, build the key with
    parse_coord(set_code, num); never with canonical_set_code.
    """
    return _SET_CANONICAL.get(raw.upper(), raw)


# ---------------------------------------------------------------------------
# Pack Hourglasses cost (single pack). Single source of truth for build_pack_ev.
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


# Forme qualifiers some sources include and others omit (e.g. Limitless titles both
# "Zygarde 10% Forme" and "Zygarde 50% Forme" simply "Zygarde"). Stripped only for the
# independent NAME-confirmation comparison — the card_number still distinguishes formes,
# and " ex" is intentionally NOT stripped (base vs ex are genuinely different cards).
FORME_RE = re.compile(
    r"\s+(?:\d+%\s+)?(?:complete\s+|sunny\s+|rainy\s+|snowy\s+|normal\s+)?forme?$",
    re.I,
)


def name_agrees(a: str, b: str) -> bool:
    """True if a and b refer to the same card after normalization + forme-stripping."""
    if norm_card_name(a) == norm_card_name(b):
        return True
    sa = FORME_RE.sub("", str(a)).strip()
    sb = FORME_RE.sub("", str(b)).strip()
    return norm_card_name(sa) == norm_card_name(sb)


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

# "◆◆◆◆ or higher" — the tier the 2026-07-29 update made a guaranteed pack
# category ("If certain conditions are fulfilled, the next time a booster pack
# from the same expansion … is opened, a ◆◆◆◆ or higher card will now be
# obtained") and the new trigger for special pack-opening animations.
#
# This is RARE_PLUS_RARITIES plus double_rare, which sits one tier below it.
# Written as an explicit set rather than a rank comparison on RARITIES, because
# 'promo' and 'unknown' are stored *after* ultra_rare there as operational
# sentinels — any ">= double_rare" index test would sweep them in.
DOUBLE_RARE_PLUS_RARITIES = RARE_PLUS_RARITIES | {"double_rare"}


def is_double_rare_plus(rarity: str | None) -> bool:
    """True for ◆◆◆◆ and every tier above it (never for promo/unknown)."""
    return normalize_rarity(rarity) in DOUBLE_RARE_PLUS_RARITIES

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


def load_records(path: Path) -> list:
    """Read a JSON data file and return its list of records.

    Accepts both the flat-array form (``[...]``) and the ``{"records": [...]}``
    envelope form used across the reference/data files, so callers don't each
    re-implement the unwrap. A malformed file raises ValueError naming the path
    instead of a context-free JSONDecodeError.
    """
    p = Path(path)
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"{p}: invalid JSON ({e})") from e
    if isinstance(raw, dict):
        return raw.get("records", raw)
    return raw


def http_get_with_retry(url: str, *, headers: dict | None = None,
                        timeout: float = REQUEST_TIMEOUT, retries: int = 3,
                        backoff: float = 1.0, backoff_factor: float = 2.0,
                        sleep=None) -> bytes:
    """GET ``url`` and return the response body bytes, retrying transient failures.

    Retries timeouts, connection errors and 429/5xx responses with exponential
    backoff (``backoff``, then ×``backoff_factor`` each attempt). Other 4xx
    responses are permanent (e.g. 404 = not found) and re-raised immediately so
    callers can act on them. After the final attempt the last transient error is
    re-raised rather than silently swallowed. ``sleep`` is injectable for tests;
    it defaults to ``time.sleep`` resolved at call time so it stays patchable.
    """
    _sleep = sleep if sleep is not None else time.sleep
    req = urllib.request.Request(url, headers=headers or {})
    delay = backoff
    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            if e.code != 429 and 400 <= e.code < 500:
                raise  # permanent client error — don't retry
            last_exc = e
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last_exc = e
        if attempt < retries:
            _sleep(delay)
            delay *= backoff_factor
    assert last_exc is not None
    raise last_exc


PACK_SOURCES_SCHEMA_JSON = REFERENCE_DIR / "pack_sources.schema.json"


def validate_pack_sources_schema(raw, *, source: str = "") -> bool:
    """Validate a loaded pack_sources structure against pack_sources.schema.json.

    ``raw`` is the parsed JSON (flat array or {'records': [...]} envelope). Raises
    ValueError (naming the failing field path) if the data violates the schema, so
    malformed pack_sources fails loudly at load instead of feeding e.g. a missing
    coord silently into EV. Returns True when validated, False when the check was
    skipped because jsonschema or the schema file is unavailable (the dependency
    is optional, mirroring validate_pack_sources.py).
    """
    try:
        import jsonschema
    except ImportError:
        return False
    if not PACK_SOURCES_SCHEMA_JSON.exists():
        return False
    schema = json.loads(PACK_SOURCES_SCHEMA_JSON.read_text(encoding="utf-8"))
    instance = raw if isinstance(raw, dict) else {"records": raw}
    try:
        jsonschema.validate(instance=instance, schema=schema)
    except jsonschema.ValidationError as e:
        where = f" ({source})" if source else ""
        raise ValueError(
            f"pack_sources{where} failed schema validation: {e.message} "
            f"(path: {list(e.path)})"
        ) from e
    return True


def parse_coord(set_code, card_number,
                *, require_set_code: bool = True) -> tuple[str, int] | None:
    """Parse a (set_code, card_number) pair into a normalised coord tuple.

    Returns (SET_CODE_UPPER, int(card_number)) or None when the input can't form
    a valid coord (blank set_code unless ``require_set_code=False``, missing or
    non-integer number). The single defensive parser so the upper-case + int
    coercion + error handling stay identical across callers.

    Note: callers that must preserve a record's original set_code casing in
    serialized output (e.g. reprint_links) deliberately do not use this.
    """
    sc = str(set_code or "").upper().strip()
    if require_set_code and not sc:
        return None
    if card_number is None:
        return None
    try:
        return (sc, int(card_number))
    except (TypeError, ValueError):
        return None


def _index_by_coord(records: list, num_key: str,
                    *, require_set_code: bool = True) -> dict[tuple[str, int], dict]:
    """Index records by (set_code_upper, int(num_key)).

    Shared core for the by-coord loaders. ``require_set_code`` skips records with
    a blank set_code (pack_sources / ext_ref); card_reference keeps them so
    set_code correction can still find a card by number.
    """
    index: dict[tuple[str, int], dict] = {}
    for r in records:
        coord = parse_coord(r.get("set_code"), r.get(num_key),
                            require_set_code=require_set_code)
        if coord is not None:
            index[coord] = r
    return index


def pack_sources_by_coord(path: Path) -> dict[tuple[str, int], dict]:
    """Load pack_sources.json indexed by (set_code_upper, card_number)."""
    return _index_by_coord(load_records(path), "card_number")


def card_reference_by_coord(path: Path) -> dict[tuple[str, int], dict]:
    """Load card_reference.json indexed by (set_code_upper, card_number).

    Returns {} when the file does not exist (not an error — reference may not
    have been built yet for a brand-new pack). Blank set_codes are kept so a
    card can still be located by number for set_code correction.
    """
    p = Path(path)
    if not p.exists():
        return {}
    return _index_by_coord(load_records(p), "card_number", require_set_code=False)


def ext_ref_by_coord(ext_ref_path: Path) -> dict[tuple[str, int], dict]:
    """Load external_card_reference.json indexed by (set_code_upper, number).

    Shared by the coord-assignment and coord-validation scripts so the index
    shape and the malformed-number handling stay identical.
    """
    return _index_by_coord(load_records(ext_ref_path), "number")


def strip_comments(text: str) -> str:
    """Strip JSONC-style line comments from text.

    Only removes lines whose first non-whitespace chars are '//', so string
    values containing '//' (e.g. a URL field) are preserved.
    """
    return re.sub(r"(?m)^\s*//[^\n]*\n?", "", text)


def load_collection_json(path: Path | None = None) -> tuple[str, dict]:
    """Read collection.json (JSONC) and return (raw_text, parsed_dict).

    The raw text is returned alongside the parse because sync edits counts
    in place with regexes to preserve comments and formatting. Raises
    FileNotFoundError / json.JSONDecodeError; CLI scripts that want a friendly
    exit catch these themselves.
    """
    p = Path(path) if path is not None else COLLECTION_JSON
    raw = p.read_text(encoding="utf-8")
    return raw, json.loads(strip_comments(raw))


def meta_errors(meta: dict) -> list[str]:
    """Validate collection.json's meta block against the web contract.

    Single definition consumed by both normalize_current_collection (hard gate
    before writing collection_summary.json) and validate_current_collection, so
    the two pipeline steps can't disagree about what a valid meta looks like.
    The webapp's Zod schema (web/types/collection-summary.ts) requires these
    fields as non-nullable — a bad hand-edit must fail in the pipeline, not at
    page render. bool is excluded explicitly: isinstance(True, int) is True in
    Python, but the web contract needs a real number.
    """
    errors = []
    total = meta.get("total_cards")
    if not isinstance(total, int) or isinstance(total, bool):
        errors.append("meta.total_cards must be an integer")
    if not isinstance(meta.get("last_updated"), str):
        errors.append("meta.last_updated must be a string")
    if not isinstance(meta.get("format"), str):
        errors.append("meta.format must be a string")
    return errors


def load_collection_or_exit(path: Path | None = None) -> dict:
    """Parse collection.json, exiting(1) with a friendly stderr message on failure.

    For CLI scripts (validate/normalize) that want a clean error instead of a
    traceback. Returns the parsed dict (the raw text is discarded).
    """
    p = Path(path) if path is not None else COLLECTION_JSON
    if not p.exists():
        print(f"ERROR: {p} not found", file=sys.stderr)
        sys.exit(1)
    try:
        _, data = load_collection_json(p)
        return data
    except json.JSONDecodeError as e:
        print(f"ERROR: collection.json is not valid JSON (after stripping comments): {e}",
              file=sys.stderr)
        sys.exit(1)


def load_collection_counts(path: Path | None = None) -> tuple[dict[str, int], dict[tuple[str, int], int]]:
    """Aggregate owned counts from collection.json for EV scoring.

    Returns (by_name, by_coord):
      by_name:  {norm_card_name: total_count}              — name-based fallback
      by_coord: {(set_code_upper, card_number): count}     — preferred, set-exact
    """
    _, data = load_collection_json(path)
    by_name: dict[str, int] = {}
    by_coord: dict[tuple[str, int], int] = {}
    for e in data.get("collection", []):
        cnt = e.get("count", 0)
        nn = norm_card_name(e.get("name", ""))
        by_name[nn] = by_name.get(nn, 0) + cnt
        sc = str(e.get("set_code") or "").upper().strip()
        cn = e.get("card_number")
        if sc and cn is not None:
            try:
                key = (sc, int(cn))
                by_coord[key] = by_coord.get(key, 0) + cnt
            except (TypeError, ValueError):
                pass
    return by_name, by_coord


PRINTING_GROUPS_JSON = REFERENCE_DIR / "printing_groups.json"


def credit_printing_groups(by_coord: dict[tuple[str, int], int],
                           path: Path | None = None) -> dict[tuple[str, int], int]:
    """Credit owned copies across every printing of the same physical card.

    Since the 2026-07-29 update a card obtained from any pack registers in the dex
    under *every* expansion it appears in, so its printings are no longer
    independent: one copy of Cubone fills the Genetic Apex slot AND the Deluxe
    Pack: ex slot, and pulling the A4b printing yields a duplicate rather than a
    new card. EV therefore reads a group's combined count at every coord in it.

    Copies themselves are never duplicated — this returns a *derived* view for
    ownership questions. collection.json stays the record of what is physically
    held, so quantity totals are unaffected.

    Returns by_coord unchanged when printing_groups.json is absent.
    """
    p = path or PRINTING_GROUPS_JSON
    if not p.exists():
        return by_coord
    try:
        groups = json.loads(p.read_text(encoding="utf-8")).get("groups", [])
    except (OSError, json.JSONDecodeError):
        return by_coord

    credited = dict(by_coord)
    for g in groups:
        coords = [(str(sc).upper(), int(cn)) for sc, cn in g.get("coords", [])]
        total = sum(by_coord.get(c, 0) for c in coords)
        if total <= 0:
            continue
        for c in coords:
            credited[c] = total
    return credited


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
