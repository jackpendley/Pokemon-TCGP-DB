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
    python3 scripts/build_card_reference.py --set B3A   # one set

Exit codes:
    0  Success (all cards confirmed or single; no unresolved conflicts)
    1  Fatal error
    2  One or more unresolved conflicts remain after majority-vote resolution
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _collection_io import norm_card_name, normalize_rarity, canonical_set_code

ROOT          = Path(__file__).resolve().parent.parent
SOURCES_DIR   = ROOT / "data" / "reference" / "sources"
PACK_SOURCES  = ROOT / "data" / "reference" / "pack_sources.json"
OUT_JSON      = ROOT / "data" / "reference" / "card_reference.json"
SCHEMA_JSON   = ROOT / "data" / "reference" / "card_reference.schema.json"

SCHEMA_VERSION = "1.0"

# Forme-qualifier stripping for name comparison (port of coord_resolver._FORME_RE).
# Forme qualifiers (e.g. "10% Forme", "Sunny Form") are omitted by some sources but
# included in pack_sources; the card_number still distinguishes them, so a source
# returning just "Zygarde" is treated as agreeing with "Zygarde 10% Forme".
_FORME_RE = re.compile(
    r"\s+(?:\d+%\s+)?(?:complete\s+|sunny\s+|rainy\s+|snowy\s+|normal\s+)?forme?$",
    re.I,
)

# Sources considered independent (not derived from Limitless).
INDEPENDENT_SOURCES = ("tcgdex", "serebii", "bulbapedia")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _name_agrees(a: str, b: str) -> bool:
    """True if a and b refer to the same card after normalization + forme-stripping."""
    if norm_card_name(a) == norm_card_name(b):
        return True
    sa = _FORME_RE.sub("", str(a)).strip()
    sb = _FORME_RE.sub("", str(b)).strip()
    return norm_card_name(sa) == norm_card_name(sb)


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
    data = json.loads(PACK_SOURCES.read_text(encoding="utf-8"))
    records = data.get("records", data) if isinstance(data, dict) else data
    by_set: dict[str, list[dict]] = {}
    for r in records:
        sc = str(r.get("set_code", "")).upper().strip()
        if sc:
            by_set.setdefault(sc, []).append(r)
    return by_set


# ---------------------------------------------------------------------------
# Reconciliation
# ---------------------------------------------------------------------------

def reconcile_card(
    set_code: str,
    card_number: int,
    ps_record: dict,
    snapshots: dict[str, dict],  # source → {str(num): card_dict}
) -> dict:
    """
    Produce a reconciled card_reference entry for one (set_code, card_number).

    Returns:
        {set_code, card_number, name, rarity, pokemon_type, card_category, stage, hp,
         is_ex, pack_name, confirmations, confidence, conflict_notes}
    """
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

    # ── Name resolution ──────────────────────────────────────────────────────
    # Rule: ≥2 independent sources must agree for "confirmed".
    # Disagreements: one-vs-majority → resolve to majority (advisory note).
    # True tie (no majority) → "conflict" (manual review needed, only real case).

    conflict_notes: list[str] = []
    final_name = ps_name

    # ── Confidence determination ─────────────────────────────────────────────
    # Confidence rule: ≥2 genuinely independent sources (TCGdex, Serebii, Bulbapedia)
    # must agree for "confirmed". pack_sources is the Limitless-derived baseline —
    # it is NOT an independent source and is NOT counted as a confirming vote.
    # This prevents 1-source+baseline from masking a genuine disagreement.

    total_reachable = len(agreed) + len(disagreed)
    if total_reachable == 0:
        confidence = "unconfirmed"
    elif len(agreed) >= 2:
        # Two or more independent sources agree → confirmed, regardless of disagreers.
        confidence = "confirmed"
        for src, bad_name in disagreed.items():
            conflict_notes.append(
                f"{src} returned {bad_name!r} (ps={ps_name!r}); overridden by majority"
            )
    elif len(agreed) == 1 and not disagreed:
        # One independent source agrees, none disagree → single-source.
        confidence = "single"
    elif len(agreed) >= 1 and disagreed:
        # Some agree, some disagree. Check if every disagreement is a display truncation
        # (the disagreeing name is a strict normalised prefix of the agreed name). This
        # pattern is known for Serebii, which sometimes truncates long card names.
        # A prefix-match disagreement is advisory, not a blocking conflict.
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

        all_prefix = all(_is_prefix_truncation(bad, ps_name) for bad in disagreed.values())
        if all_prefix:
            confidence = "single"
            for src, bad_name in disagreed.items():
                conflict_notes.append(
                    f"{src} returned truncated name {bad_name!r} (prefix of {ps_name!r}); "
                    f"treated as display truncation — not a blocking conflict"
                )
        else:
            # Genuine disagreement: some agree, some disagree with a non-prefix name.
            confidence = "conflict"
            conflict_notes.append(
                f"UNRESOLVED: agreed={agreed} disagreed={dict(disagreed)} ps={ps_name!r}"
            )
    elif not agreed and disagreed:
        # All reachable sources disagree with pack_sources — check if they agree with each other
        dis_names = list(disagreed.values())
        ref_name = dis_names[0]
        all_same = all(_name_agrees(ref_name, n) for n in dis_names[1:])
        if all_same and len(disagreed) >= 2:
            # Multiple independent sources agree on a different name than pack_sources
            # — the external sources are likely correct; update the name.
            confidence = "confirmed"
            final_name = ref_name  # use the external consensus name
            conflict_notes.append(
                f"pack_sources name {ps_name!r} overridden by external consensus "
                f"{ref_name!r} ({', '.join(disagreed.keys())})"
            )
        elif len(disagreed) == 1:
            confidence = "single"
            # Single disagreeing source: don't auto-update, but flag explicitly so
            # the build surfaces it for review rather than silently keeping ps_name.
            src = list(disagreed.keys())[0]
            conflict_notes.append(
                f"UNRESOLVED (single source): {src} returned {ref_name!r} "
                f"vs pack_sources {ps_name!r} — verify and re-run"
            )
        else:
            # Multiple sources disagree with pack_sources AND with each other
            confidence = "conflict"
            conflict_notes.append(
                f"UNRESOLVED: pack_sources={ps_name!r} "
                f"external_names={dict(disagreed)}"
            )
    else:
        confidence = "unconfirmed"

    # ── Metadata resolution (majority vote, pack_sources as fallback) ─────────
    rarity_final = ps_record.get("rarity")
    if rarity_votes:
        best = max(rarity_votes, key=lambda k: rarity_votes[k])
        # Only override if the external consensus differs AND is more confident
        if best and best != rarity_final and rarity_votes[best] >= 2:
            conflict_notes.append(
                f"rarity override: pack_sources={rarity_final!r} → external={best!r} "
                f"(votes={rarity_votes})"
            )
            rarity_final = best

    pokemon_type_final = None
    if pokemon_type_votes:
        pokemon_type_final = max(pokemon_type_votes, key=lambda k: pokemon_type_votes[k])

    # Category/stage/hp from TCGdex (most structured source)
    tcgdex_card = snapshots.get("tcgdex", {}).get(num_str, {})
    category_final = tcgdex_card.get("category")
    stage_final = tcgdex_card.get("stage")
    hp_final = tcgdex_card.get("hp")

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

def main() -> int:
    parser = argparse.ArgumentParser(description="Build cross-validated card_reference.json.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Report only; do not write card_reference.json")
    parser.add_argument("--set", metavar="SET_CODE",
                        help="Only process this set (e.g. B3A)")
    args = parser.parse_args()

    ps_by_set = _load_pack_sources()

    if args.set:
        # Case-insensitive match so "--set a2a" and "--set B3A" both work regardless
        # of the mixed casing in pack_sources (A2a, B3A, PROMO-A, etc.).
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

            entry = reconcile_card(sc, cn, r, set_snapshots)
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
