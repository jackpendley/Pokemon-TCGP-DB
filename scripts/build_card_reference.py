#!/usr/bin/env python3
"""
Build data/reference/card_reference.json — the cross-validated frozen truth.

Reads per-source snapshots (data/reference/sources/<source>/<SET>.json) produced
by fetch_source_snapshots.py and reconciles them into a single authoritative card
list for all 20 TCG Pocket sets.

Independent sources:
  tcgdex    — A1–B2a (15 sets). Provides name, rarity, boosters (pack assignment),
               hp, stage, category, types.
  serebii   — All 20 sets. Provides name only.
  bulbapedia — All 20 sets. Provides name, rarity, pokemon_type.

Limitless is pack_sources' origin — NOT counted as independent. Pack_sources provides
the baseline card pool (set_code, card_number, card_name, rarity, pack_name).

Unanimity policy (a single flaky scrape must never force manual review):
  confirmed — ≥2 independent sources agree on the name (after forme-stripping).
  single    — Exactly 1 independent source confirms; others unreachable.
  conflict  — Sources disagree. Majority wins when one-vs-many; true tie surfaces
               for manual resolution. Genuine conflicts are the ONLY manual-review case.

Usage:
    python3 scripts/build_card_reference.py             # build/update
    python3 scripts/build_card_reference.py --dry-run   # report only, no write
    python3 scripts/build_card_reference.py --set B3a   # one set

Exit codes:
    0  Success (all cards confirmed or single; no unresolved conflicts)
    1  Fatal error
    2  One or more unresolved conflicts remain after majority-vote resolution
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _collection_io import (norm_card_name, normalize_rarity, canonical_set_code,
                            ext_ref_by_coord, load_records, PROMO_SET_CODES,
                            ROOT, SOURCES_DIR, REFERENCE_DIR,
                            PACK_SOURCES_JSON as PACK_SOURCES,
                            CARD_REF_JSON as OUT_JSON, EXT_REF_JSON,
                            FORME_RE as _FORME_RE, name_agrees as _name_agrees)

SCHEMA_JSON   = REFERENCE_DIR / "card_reference.schema.json"
COMBAT_JSON   = REFERENCE_DIR / "card_combat_stats.json"
SIR_JSON      = REFERENCE_DIR / "special_illustration_rares.json"
RARITY_OVR_JSON = REFERENCE_DIR / "rarity_overrides.json"
TYPE_OVR_JSON = REFERENCE_DIR / "card_type_overrides.json"

SCHEMA_VERSION = "1.0"

# Canonical Pokémon energy types. Used to tell a real type apart from a trainer
# subtype token: some wiki sources put the trainer kind (Item/Supporter/…) in the
# "type" column, so a non-energy "type" actually identifies a Trainer.
ENERGY_TYPES = frozenset({
    "Grass", "Fire", "Water", "Lightning", "Psychic", "Fighting",
    "Darkness", "Metal", "Dragon", "Colorless",
})
# Trainer subtype tokens as they appear in external_card_reference / wiki type cells.
# Bulbapedia writes the accented "Pokémon Tool"; include it so tool cards in sets
# where Bulbapedia is the only classifier (TCGdex-uncovered, e.g. B3b) are still
# recognised as Trainers. _norm_trainer_subtype folds it to "Pokemon Tool".
TRAINER_SUBTYPE_TOKENS = frozenset({"Supporter", "Item", "Stadium", "Tool", "Pokemon Tool", "Pokémon Tool"})


def _norm_trainer_subtype(tok: str | None) -> str | None:
    """Normalize a trainer-subtype token to the collection.json vocabulary."""
    if not tok:
        return None
    return "Pokemon Tool" if tok in ("Tool", "Pokémon Tool") else tok

# TCGdex is the only structured stage source, but it covers only A1–B2a (A4b/B2b/B3/B3a and
# the promo sets are tcgdex:None). For those sets, fall back to the Limitless-derived
# external_card_reference stage. Limitless writes "Stage 1"/"Stage 2"; map to TCGdex's
# spaceless "Stage1"/"Stage2" so card_reference stays single-format.
_EXT_STAGE_TO_TCGDEX = {"Basic": "Basic", "Stage 1": "Stage1", "Stage 2": "Stage2"}

# Curated Special Illustration Rare coords. Super Rare and Special Illustration Rare
# are BOTH the ★★ "Two Star" tier (same symbol, same pull rate); no structured source
# distinguishes them per-card, so this version-controlled list is the authority for the
# super_rare→special_illustration_rare upgrade. Populated by load_sir_coords() in main().
SIR_COORDS: set[tuple[str, int]] = set()

# Curated rarity corrections (B-series shiny regions). The wiki sources lump 8-point-star
# shiny tiers into one_star/two_star, so source voting converges on the wrong tier; this
# list (derived from PZ drop-chance clusters + user in-app verification) wins over all
# votes. Populated by load_rarity_overrides() in main(): (set_code, card_number) -> rarity.
RARITY_OVERRIDES: dict[tuple[str, int], str] = {}

# Curated Pokémon-type corrections for cards no structured source types (e.g.
# Mega cards in sets TCGdex doesn't cover whose wiki "type" cell is blank).
# Populated by load_type_overrides() in main(): (set_code, card_number) -> type.
TYPE_OVERRIDES: dict[tuple[str, int], str] = {}


def load_type_overrides() -> dict[tuple[str, int], str]:
    """Load curated per-coord Pokémon-type overrides. Empty if absent."""
    if not TYPE_OVR_JSON.exists():
        return {}
    raw = json.loads(TYPE_OVR_JSON.read_text(encoding="utf-8"))
    out: dict[tuple[str, int], str] = {}
    for r in raw.get("records", []):
        sc = canonical_set_code(str(r.get("set_code", "")).strip())
        cn = r.get("card_number")
        if sc and cn is not None and r.get("pokemon_type"):
            out[(sc, int(cn))] = r["pokemon_type"]
    return out


def load_rarity_overrides() -> dict[tuple[str, int], str]:
    """Load curated per-coord rarity overrides (range records). Empty if absent."""
    if not RARITY_OVR_JSON.exists():
        return {}
    raw = json.loads(RARITY_OVR_JSON.read_text(encoding="utf-8"))
    out: dict[tuple[str, int], str] = {}
    for r in raw.get("records", []):
        sc = canonical_set_code(str(r.get("set_code", "")).strip())
        for cn in range(int(r["from"]), int(r["to"]) + 1):
            out[(sc, cn)] = r["rarity"]
    return out


def load_sir_coords() -> set[tuple[str, int]]:
    """Load curated SIR coords keyed by canonical set-code casing. Empty if absent.

    Uses canonical_set_code so the key matches the override's lookup (mixed-case
    mini-sets like A1a/B2a must not be flattened to A1A/B2A)."""
    if not SIR_JSON.exists():
        return set()
    records = load_records(SIR_JSON)
    coords: set[tuple[str, int]] = set()
    for r in records:
        sc = canonical_set_code(str(r.get("set_code", "")).strip())
        cn = r.get("card_number")
        if sc and cn is not None:
            coords.add((sc, int(cn)))
    return coords

# Sources considered independent (not derived from Limitless).
INDEPENDENT_SOURCES = ("tcgdex", "serebii", "bulbapedia")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_snapshot(source: str, set_code: str) -> dict:
    """Load a source snapshot; return empty dict if missing."""
    p = SOURCES_DIR / source / f"{set_code}.json"
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data.get("cards", {})
    except Exception:
        return {}


def _load_pack_sources() -> dict[str, list[dict]]:
    """Return {set_code: [record, ...]} from pack_sources.json, set_code uppercased."""
    records = load_records(PACK_SOURCES)
    by_set: dict[str, list[dict]] = {}
    for r in records:
        sc = str(r.get("set_code", "")).upper().strip()
        if sc:
            by_set.setdefault(sc, []).append(r)
    return by_set


# ---------------------------------------------------------------------------
# Reconciliation
# ---------------------------------------------------------------------------

def _is_prefix_truncation(bad: str, good: str) -> bool:
    """True when one name is a normalised prefix of the other (either direction).

    Covers two known Serebii patterns:
      - Truncation: Serebii omits trailing words ('Mega Charizard' for 'Mega Charizard X')
      - Appended junk: Serebii adds stray chars ('Professor Turoa' for 'Professor Turo')
    Require at least 4 chars to avoid spurious matches on short names.
    """
    nb, ng = norm_card_name(bad), norm_card_name(good)
    if nb == ng:
        return False
    min_len = min(len(nb), len(ng))
    return min_len >= 4 and (ng.startswith(nb) or nb.startswith(ng))


def _resolve_confidence(agreed: list[str], disagreed: dict[str, str],
                        ps_name: str) -> tuple[str, str, list[str]]:
    """Return (confidence, final_name, conflict_notes) from per-source name agreement.

    Confidence rule: ≥2 genuinely independent sources (TCGdex, Serebii, Bulbapedia) must
    agree for "confirmed". pack_sources is the Limitless-derived baseline — NOT an
    independent vote — so 1-source+baseline never masks a genuine disagreement.
    """
    notes: list[str] = []
    final_name = ps_name
    total_reachable = len(agreed) + len(disagreed)

    if total_reachable == 0:
        return "unconfirmed", final_name, notes
    if len(agreed) >= 2:
        # Two or more independent sources agree → confirmed, regardless of disagreers.
        for src, bad_name in disagreed.items():
            notes.append(f"{src} returned {bad_name!r} (ps={ps_name!r}); overridden by majority")
        return "confirmed", final_name, notes
    if len(agreed) == 1 and not disagreed:
        return "single", final_name, notes
    if len(agreed) >= 1 and disagreed:
        # Some agree, some disagree. A disagreement that is purely a display truncation
        # (normalised prefix of ps_name) is advisory, not a blocking conflict.
        if all(_is_prefix_truncation(bad, ps_name) for bad in disagreed.values()):
            for src, bad_name in disagreed.items():
                notes.append(
                    f"{src} returned truncated name {bad_name!r} (prefix of {ps_name!r}); "
                    f"treated as display truncation — not a blocking conflict")
            return "single", final_name, notes
        notes.append(f"UNRESOLVED: agreed={agreed} disagreed={dict(disagreed)} ps={ps_name!r}")
        return "conflict", final_name, notes
    # not agreed and disagreed: all reachable sources disagree with pack_sources —
    # check whether they agree with each other.
    dis_names = list(disagreed.values())
    ref_name = dis_names[0]
    all_same = all(_name_agrees(ref_name, n) for n in dis_names[1:])
    if all_same and len(disagreed) >= 2:
        # Multiple independent sources agree on a different name → trust them.
        notes.append(
            f"pack_sources name {ps_name!r} overridden by external consensus "
            f"{ref_name!r} ({', '.join(disagreed.keys())})")
        return "confirmed", ref_name, notes
    if len(disagreed) == 1:
        src = list(disagreed.keys())[0]
        notes.append(
            f"UNRESOLVED (single source): {src} returned {ref_name!r} "
            f"vs pack_sources {ps_name!r} — verify and re-run")
        return "single", final_name, notes
    notes.append(f"UNRESOLVED: pack_sources={ps_name!r} external_names={dict(disagreed)}")
    return "conflict", final_name, notes


def _resolve_rarity(set_code: str, card_number: int, ps_record: dict,
                    tcgdex_card: dict, rarity_votes: dict[str, int]) -> tuple[str | None, list[str]]:
    """Return (rarity, conflict_notes) from the rarity authority chain:
    TCGdex (per-card authority) → ≥2-source external vote → pack_sources baseline,
    then the curated SIR upgrade, the curated shiny-region overrides, and the promo
    sentinel for symbol-less promo cards."""
    notes: list[str] = []
    tcgdex_rarity = normalize_rarity(tcgdex_card.get("rarity"))
    rarity_final = normalize_rarity(ps_record.get("rarity"))
    if tcgdex_rarity:
        if rarity_final and rarity_final != tcgdex_rarity:
            notes.append(f"rarity: pack_sources={rarity_final!r} → tcgdex(authority)={tcgdex_rarity!r}")
        rarity_final = tcgdex_rarity
    elif rarity_votes:
        best = max(rarity_votes, key=lambda k: rarity_votes[k])
        # Override the baseline on a ≥2-source consensus, or whenever the baseline is
        # empty (any single external vote beats an unknown rarity).
        if best and best != rarity_final and (rarity_votes[best] >= 2 or not rarity_final):
            notes.append(f"rarity override: pack_sources={rarity_final!r} → external={best!r} "
                         f"(votes={rarity_votes})")
            rarity_final = best

    # Super Rare and Special Illustration Rare share the ★★ tier; the curated SIR list is
    # the authority for the super_rare→special_illustration_rare upgrade.
    if rarity_final == "super_rare" and (canonical_set_code(set_code), card_number) in SIR_COORDS:
        rarity_final = "special_illustration_rare"
        notes.append("rarity: super_rare → special_illustration_rare (curated SIR list)")

    # Curated shiny-region corrections win over every source vote (wiki sources lump the
    # 8-point-star tiers into one_star/two_star).
    ovr = RARITY_OVERRIDES.get((canonical_set_code(set_code), card_number))
    if ovr and ovr != rarity_final:
        notes.append(f"rarity: {rarity_final!r} → {ovr!r} (curated rarity_overrides)")
        rarity_final = ovr

    # Promo-set cards carry no rarity symbol; keep the 'promo' sentinel when unresolved.
    if not rarity_final and canonical_set_code(set_code) in PROMO_SET_CODES:
        rarity_final = "promo"
    return rarity_final, notes


def reconcile_card(
    set_code: str,
    card_number: int,
    ps_record: dict,
    snapshots: dict[str, dict],  # source → {str(num): card_dict}
    ext_rec: dict | None = None,  # external_card_reference record (Limitless gap-filler)
    type_override: str | None = None,  # curated pokemon_type for typeless cards
) -> dict:
    """
    Produce a reconciled card_reference entry for one (set_code, card_number).

    Returns:
        {set_code, card_number, name, rarity, pokemon_type, card_category, trainer_subtype,
         stage, hp, is_ex, pack_name, confirmations, confidence, conflict_notes}
    """
    ext_rec = ext_rec or {}
    ext_stage = ext_rec.get("stage")  # Limitless stage fallback (sets TCGdex doesn't cover)
    num_str = str(card_number)
    ps_name = ps_record.get("card_name") or ""

    # Collect independent-source names and rich metadata
    source_names: dict[str, str] = {}    # source → name (for this card)
    agreed: list[str] = []              # sources whose name agrees with ps_name
    disagreed: dict[str, str] = {}     # source → name (disagreeing)

    # Rich metadata buckets (first confirmed value wins)
    rarity_votes: dict[str, int] = {}
    pokemon_type_votes: dict[str, int] = {}
    boosters: list[str] = []

    for source in INDEPENDENT_SOURCES:
        cards = snapshots.get(source, {})
        card = cards.get(num_str)
        if not card:
            continue

        src_name = card.get("name") or ""
        if not src_name:
            continue

        source_names[source] = src_name

        if _name_agrees(ps_name, src_name):
            agreed.append(source)
        else:
            disagreed[source] = src_name

        # Rarity
        r = card.get("rarity")
        if r:
            r = normalize_rarity(r) or r
            rarity_votes[r] = rarity_votes.get(r, 0) + 1

        # Type (Bulbapedia / TCGdex)
        t = card.get("pokemon_type") or (card.get("types") or [None])[0] if card.get("types") else card.get("pokemon_type")
        if t and source in ("bulbapedia", "tcgdex"):
            pokemon_type_votes[t] = pokemon_type_votes.get(t, 0) + 1

        # Boosters (TCGdex only, most reliable for pack assignment)
        if source == "tcgdex" and card.get("boosters"):
            boosters = card["boosters"]

    # ── Name + confidence resolution ─────────────────────────────────────────
    confidence, final_name, conflict_notes = _resolve_confidence(agreed, disagreed, ps_name)

    # ── Rarity resolution ─────────────────────────────────────────────────────
    tcgdex_card = snapshots.get("tcgdex", {}).get(num_str, {})
    rarity_final, rarity_notes = _resolve_rarity(
        set_code, card_number, ps_record, tcgdex_card, rarity_votes)
    conflict_notes.extend(rarity_notes)

    pokemon_type_final = None
    if pokemon_type_votes:
        pokemon_type_final = max(pokemon_type_votes, key=lambda k: pokemon_type_votes[k])

    # Category/stage/hp from TCGdex (most structured source). For sets TCGdex doesn't cover
    # (A4b/B2b/B3/B3a/promos), fall back to the Limitless stage so card_reference stays
    # complete — used by validators and the collection stage backfill.
    category_final = tcgdex_card.get("category")
    stage_final = tcgdex_card.get("stage") or _EXT_STAGE_TO_TCGDEX.get(ext_stage)
    hp_final = tcgdex_card.get("hp")

    # ── Type / category / trainer-subtype completion ─────────────────────────
    # external_card_reference (Limitless) is a *gap-filler only*: it has known
    # errors (it mislabels some Pokémon as "Supporter"), so it never overrides a
    # cross-validated value — it only fills nulls, and its trainer subtype is
    # trusted only once we've otherwise concluded the card is a Trainer.
    ext_type = ext_rec.get("pokemon_type")
    ext_cat = ext_rec.get("card_category")  # Pokemon | Supporter | Item | Stadium | Tool

    # Some wiki sources put the trainer kind in the "type" cell, so a non-energy
    # pokemon_type is really a subtype token, not a Pokémon type.
    subtype_candidate = None
    if pokemon_type_final and pokemon_type_final not in ENERGY_TYPES:
        if pokemon_type_final in TRAINER_SUBTYPE_TOKENS:
            subtype_candidate = pokemon_type_final
        pokemon_type_final = None
    if subtype_candidate is None and ext_cat in TRAINER_SUBTYPE_TOKENS:
        subtype_candidate = ext_cat

    # Fill a missing energy type: curated override first, then Limitless (covers
    # Mega cards in sets TCGdex doesn't cover). A real energy type ⇒ Pokémon.
    if pokemon_type_final is None and type_override in ENERGY_TYPES:
        pokemon_type_final = type_override
    if pokemon_type_final is None and ext_type in ENERGY_TYPES:
        pokemon_type_final = ext_type

    if category_final is None:
        if pokemon_type_final is not None or ext_cat == "Pokemon":
            category_final = "Pokemon"
        elif subtype_candidate is not None:
            category_final = "Trainer"

    trainer_subtype = None
    if category_final == "Trainer":
        trainer_subtype = _norm_trainer_subtype(subtype_candidate)
        pokemon_type_final = None  # Trainers carry no energy type

    # pack_name: trust pack_sources; TCGdex boosters validate for A1–B2a
    pack_name = ps_record.get("pack_name")
    if boosters and pack_name:
        booster_norms = [norm_card_name(b) for b in boosters]
        ps_norm = norm_card_name(pack_name)
        if booster_norms and not any(norm_card_name(b) == ps_norm for b in boosters):
            conflict_notes.append(
                f"pack_name mismatch: pack_sources={pack_name!r} "
                f"tcgdex_boosters={boosters}"
            )

    return {
        "set_code":       canonical_set_code(set_code),
        "card_number":    card_number,
        "name":           final_name,
        "rarity":         normalize_rarity(rarity_final),
        "pokemon_type":   pokemon_type_final,
        "card_category":  category_final,
        "trainer_subtype": trainer_subtype,
        "stage":          stage_final,
        "hp":             hp_final,
        "is_ex":          final_name.lower().endswith(" ex"),
        "pack_name":      pack_name,
        "expansion":      ps_record.get("expansion"),
        "confirmations":  agreed,
        "confidence":     confidence,
        "conflict_notes": conflict_notes,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _attach_evolves_from(records: list[dict]) -> int:
    """Attach `evolves_from` (predecessor Pokémon name, or None) to each record from
    card_combat_stats.json — keyed by `SET|normalized-name`, exactly as
    fetch_combat_stats writes it. Every printing of a species shares one entry."""
    combat = json.loads(COMBAT_JSON.read_text(encoding="utf-8")) if COMBAT_JSON.exists() else {}
    n = 0
    for rec in records:
        key = f"{rec['set_code']}|{' '.join(rec['name'].lower().split())}"
        evo = (combat.get(key) or {}).get("evolve_from")
        rec["evolves_from"] = evo
        if evo:
            n += 1
    return n


def main() -> int:
    parser = argparse.ArgumentParser(description="Build cross-validated card_reference.json.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Report only; do not write card_reference.json")
    parser.add_argument("--set", metavar="SET_CODE",
                        help="Only process this set (e.g. B3A)")
    args = parser.parse_args()

    global SIR_COORDS
    SIR_COORDS = load_sir_coords()
    print(f"Loaded {len(SIR_COORDS)} curated Special Illustration Rare coords.")
    global RARITY_OVERRIDES
    RARITY_OVERRIDES = load_rarity_overrides()
    print(f"Loaded {len(RARITY_OVERRIDES)} curated rarity-override coords.")
    global TYPE_OVERRIDES
    TYPE_OVERRIDES = load_type_overrides()
    print(f"Loaded {len(TYPE_OVERRIDES)} curated type-override coords.")

    ps_by_set = _load_pack_sources()

    # Limitless stage fallback for sets TCGdex doesn't cover (keyed by upper-cased coord).
    ext_ref = ext_ref_by_coord(EXT_REF_JSON) if EXT_REF_JSON.exists() else {}

    if args.set:
        # Case-insensitive match so "--set a2a" and "--set B3a" both work regardless
        # of the mixed casing in pack_sources (A2a, B3a, PROMO-A, etc.).
        sc_upper = args.set.upper()
        canonical = next((k for k in ps_by_set if k.upper() == sc_upper), None)
        if canonical is None:
            print(f"ERROR: set {args.set!r} not found in pack_sources. "
                  f"Known sets: {sorted(ps_by_set)}", file=sys.stderr)
            return 1
        target_sets = [canonical]
    else:
        target_sets = sorted(ps_by_set.keys())

    # Load all source snapshots (once per set, shared across cards)
    # snapshots[source][set_code] = {str(num): card_dict}
    snapshots_cache: dict[str, dict[str, dict]] = {}
    for source in INDEPENDENT_SOURCES:
        snapshots_cache[source] = {}
        for sc in target_sets:
            snapshots_cache[source][sc] = _load_snapshot(source, sc)

    results: list[dict] = []
    stats = {
        "confirmed": 0, "single": 0, "conflict": 0, "unconfirmed": 0,
        "sets": {}, "unresolved_conflicts": [],
    }

    for sc in target_sets:
        records = ps_by_set.get(sc, [])
        sc_stats = {"confirmed": 0, "single": 0, "conflict": 0, "unconfirmed": 0}
        set_snapshots = {src: snapshots_cache[src].get(sc, {}) for src in INDEPENDENT_SOURCES}

        for r in records:
            cn_raw = r.get("card_number")
            try:
                cn = int(cn_raw)
            except (TypeError, ValueError):
                continue

            ext_r = ext_ref.get((sc.upper(), cn))
            t_ovr = TYPE_OVERRIDES.get((canonical_set_code(sc), cn))
            entry = reconcile_card(sc, cn, r, set_snapshots, ext_r, t_ovr)
            results.append(entry)

            conf = entry["confidence"]
            stats[conf] = stats.get(conf, 0) + 1
            sc_stats[conf] = sc_stats.get(conf, 0) + 1
            if conf == "conflict" and any("UNRESOLVED" in n for n in entry["conflict_notes"]):
                stats["unresolved_conflicts"].append(
                    f"{sc}/{cn}: {'; '.join(entry['conflict_notes'])}"
                )

        # Cards present in the independent snapshots but absent from pack_sources (e.g.
        # newer promos Limitless hasn't catalogued yet). Without these, owned copies have
        # no card_reference record and can't be type-validated. Synthesize a baseline from
        # the snapshot name so the normal cross-source reconciliation runs unchanged.
        ps_nums = {int(r["card_number"]) for r in records
                   if str(r.get("card_number", "")).strip().lstrip("-").isdigit()}
        snap_nums: set[int] = set()
        for src in INDEPENDENT_SOURCES:
            for k in set_snapshots[src]:
                try:
                    snap_nums.add(int(k))
                except (TypeError, ValueError):
                    pass
        for cn in sorted(snap_nums - ps_nums):
            name = next((set_snapshots[src].get(str(cn), {}).get("name")
                         for src in INDEPENDENT_SOURCES
                         if set_snapshots[src].get(str(cn), {}).get("name")), None)
            if not name:
                continue
            synth = {"card_number": cn, "card_name": name,
                     "rarity": None, "pack_name": None, "expansion": None}
            ext_r = ext_ref.get((sc.upper(), cn))
            t_ovr = TYPE_OVERRIDES.get((canonical_set_code(sc), cn))
            entry = reconcile_card(sc, cn, synth, set_snapshots, ext_r, t_ovr)
            results.append(entry)
            conf = entry["confidence"]
            stats[conf] = stats.get(conf, 0) + 1
            sc_stats[conf] = sc_stats.get(conf, 0) + 1
            if conf == "conflict" and any("UNRESOLVED" in n for n in entry["conflict_notes"]):
                stats["unresolved_conflicts"].append(
                    f"{sc}/{cn}: {'; '.join(entry['conflict_notes'])}"
                )

        stats["sets"][sc] = sc_stats
        conf_count = sc_stats["confirmed"]
        total = sum(sc_stats.values())
        print(f"  {sc:8s}: {conf_count:3d}/{total:3d} confirmed  "
              f"single={sc_stats['single']}  conflict={sc_stats['conflict']}  "
              f"unconfirmed={sc_stats['unconfirmed']}")

    evo_count = _attach_evolves_from(results)
    print(f"\n  evolves_from attached: {evo_count} cards have a predecessor")

    total_cards = len(results)
    print(f"\n  Total: {total_cards} cards")
    print(f"  confirmed={stats['confirmed']}  single={stats['single']}  "
          f"conflict={stats['conflict']}  unconfirmed={stats['unconfirmed']}")

    if stats["unresolved_conflicts"]:
        print(f"\n  UNRESOLVED CONFLICTS ({len(stats['unresolved_conflicts'])}):")
        for item in stats["unresolved_conflicts"][:20]:
            print(f"    {item}")

    if args.dry_run:
        print("\nDRY RUN — card_reference.json not written.")
        return 2 if stats["unresolved_conflicts"] else 0

    # Write output (sorted by set_code then card_number for diffability)
    results.sort(key=lambda r: (r["set_code"], r["card_number"]))
    output = {
        "_meta": {
            "schema_version": SCHEMA_VERSION,
            "generated_at": _now_iso(),
            "total_cards": total_cards,
            "stats": {
                "confirmed": stats["confirmed"],
                "single": stats["single"],
                "conflict": stats["conflict"],
                "unconfirmed": stats["unconfirmed"],
            },
            "sources": list(INDEPENDENT_SOURCES),
        },
        "records": results,
    }

    tmp = OUT_JSON.with_suffix(".tmp")
    tmp.write_text(json.dumps(output, indent=2, ensure_ascii=False, sort_keys=True),
                   encoding="utf-8")
    tmp.replace(OUT_JSON)
    print(f"\n  Written: {OUT_JSON.relative_to(ROOT)}")

    return 2 if stats["unresolved_conflicts"] else 0


if __name__ == "__main__":
    sys.exit(main())
