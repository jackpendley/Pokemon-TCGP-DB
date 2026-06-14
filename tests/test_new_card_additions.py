#!/usr/bin/env python3
"""
Simulation: new card additions from all packs.

Tests that every category of card the sync pipeline will encounter
is handled correctly when the card doesn't yet exist in the collection.

Scenarios:
  1.  Simple new card — pack_sources match, not in collection
  2.  Multi-set new card — same card from two different sets, dedup to one entry
  3.  New alt-art (illustration_rare rarity) — base already owned, alt art is new
  4.  New super_rare alt art — same as above, super_rare rarity is_alt path
  5.  New immersive — another star-tier new card
  6.  Both variants new — neither base nor alt yet owned; PZ returns both
  7.  A1 numbering mismatch, card NOT owned — must use PZ raw_name, not pack_sources
  8.  A1 numbering mismatch, card OWNED — existing behavior preserved
  9.  New PROMO-A card (override)
 10.  New PROMO-B card (override)
 11.  New card not in pack_sources or collection (raw-name fallback)
 12.  New Trainer card — direct normalized-name match (not in pack_sources)
 13.  Multi-variant: base owned, PZ returns base + alt art simultaneously
 14.  New card whose name collides with known card after normalization
 15.  Cross-set parallel: card owned, PZ returns it from three set codes
 16.  All known A1/A4 numbering mismatches (not owned)
 17.  Smoke test: first unowned card from every set code
 18.  All super_rare/immersive → is_alt=True
 19.  Nidoran♀ + Nidoran♂ both new — dedup must produce 2 entries, not 1
 20.  build_auto_entry blank card_category — hp/stage/type populated from ext_ref
 21.  Nidoran♀ + Nidoran♂ both owned — exact-name shortcut routes each correctly
 22.  Mismatch slot with alt-art rarity, card OWNED → MATCHED (not NEW_CARD)
 23.  Mismatch slot with alt-art rarity, card NOT owned → NEW_CARD with correct name
 24.  All illustration_rare + crown rarities → alt art routing (extends scenario 18)
 25.  Comprehensive: every unowned non-mismatch card across all packs → NEW_CARD
 26.  Phase 4b alt-art tagging — build_auto_entry + name guard tags all alt rarities
 27.  Phase 4c Case A simulation — alt art added marks base entry stale
 28.  Phase 4c Case B — fixed threshold fires at 3rd consecutive miss (not 4th)
 29.  Phase 4e — stale entry names excluded from write_review_queue call
 30.  Phase 4c Case A regression — Nidoran♀ alt-art does NOT mark Nidoran♂ base stale
 31.  Phase 4c Case A — pre-existing MATCHED alt-art triggers Case A for missing base

Usage:
    python3 -m pytest tests/test_new_card_additions.py
    python3 tests/test_new_card_additions.py
"""

import importlib.util
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Load sync_collection without running main()
# ---------------------------------------------------------------------------

spec = importlib.util.spec_from_file_location(
    "sync_collection", ROOT / "scripts" / "sync_collection.py"
)
sc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sc)

PZCard             = sc.PZCard
MatchResult        = sc.MatchResult
match_pz_cards     = sc.match_pz_cards
build_auto_entry   = sc.build_auto_entry
_normalize         = sc._normalize
_PROMO_A_OVERRIDES = sc._PROMO_A_OVERRIDES
_PROMO_B_OVERRIDES = sc._PROMO_B_OVERRIDES
# Use the production alt-rarity vocabulary so the test tracks the real constant
# (a change to RARE_PLUS_RARITIES propagates here instead of silently diverging).
_ALT_RARITIES = sc.RARE_PLUS_RARITIES

# ---------------------------------------------------------------------------
# Load real reference data — via the production loaders, so the tests exercise
# the exact parsing the sync pipeline uses (no private copies to drift).
# ---------------------------------------------------------------------------

PACK_SOURCES = sc.load_pack_sources()
EXT_REF      = sc.load_ext_ref()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PASS = "  ✓"
FAIL = "  ✗"
_failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"{PASS}  {name}")
    else:
        msg = f"{name}" + (f": {detail}" if detail else "")
        print(f"{FAIL}  {msg}")
        _failures.append(msg)
        # Raise so pytest registers a real failure (script mode exits 1 via main).
        assert cond, msg


def pz(raw_name, count=1, set_code=None, card_number=None) -> PZCard:
    return PZCard(set_code=set_code, card_number=card_number,
                  raw_name=raw_name, count=count)


def entry(name, count=1, hp=None, variant=None, card_type="Pokemon") -> dict:
    e = {"name": name, "count": count, "card_type": card_type, "is_ex": False}
    if hp is not None:
        e["hp"] = hp
    if variant is not None:
        e["variant"] = variant
    return e


def run(pz_cards, collection, label=""):
    """Convenience: run match_pz_cards with real reference data."""
    return match_pz_cards(pz_cards, collection, PACK_SOURCES, EXT_REF)


# ---------------------------------------------------------------------------
# 1. Simple new card — pack_sources match, not in collection
# ---------------------------------------------------------------------------
def test_simple_new_card():
    print("\n--- 1. Simple new card (pack_sources match) ---")
    # Use a real card that IS in pack_sources but NOT in an empty collection
    # Bulbasaur A1#1 → common
    results = run([pz("Bulbasaur", 2, "A1", 1)], [])
    r = results[0]
    check("status=NEW_CARD", r.status == "NEW_CARD", r.status)
    check("canonical_name=Bulbasaur", r.canonical_name == "Bulbasaur", r.canonical_name)
    check("count=2", r.pz_card.count == 2)


# ---------------------------------------------------------------------------
# 2. Multi-set new card — same card from two different set codes
# ---------------------------------------------------------------------------
def test_multi_set_new_card():
    print("\n--- 2. Multi-set new card (same card, two sets) ---")
    # Bulbasaur appears in A1#1 and A4b#1; both NEW_CARD, dedup logic sums them
    collection = []
    pz_cards = [
        pz("Bulbasaur", 2, "A1", 1),
        pz("Bulbasaur", 3, "A4b", 1),
    ]
    results = run(pz_cards, collection)
    check("both NEW_CARD", all(r.status == "NEW_CARD" for r in results))
    check("same canonical_name", results[0].canonical_name == results[1].canonical_name == "Bulbasaur")

    # Simulate Phase 4b dedup (as in main()) — key is canonical_name.lower() + "|base"|"|alt"
    _ALT_RARITIES_S2 = _ALT_RARITIES

    def _is_alt_s2(mr):
        pz_c = mr.pz_card
        if not (pz_c.set_code and pz_c.card_number is not None):
            return False
        ps_r = PACK_SOURCES.get((pz_c.set_code, pz_c.card_number))
        return bool(
            ps_r
            and _normalize(ps_r.get("card_name", "")) == _normalize(mr.canonical_name or "")
            and ps_r.get("rarity") in _ALT_RARITIES_S2
        )

    merged = {}
    for mr in results:
        key = mr.canonical_name.lower() + ("|alt" if _is_alt_s2(mr) else "|base")
        if key in merged:
            prev = merged[key]
            merged[key] = MatchResult(
                status=prev.status,
                pz_card=PZCard(prev.pz_card.set_code, prev.pz_card.card_number,
                               prev.pz_card.raw_name,
                               prev.pz_card.count + mr.pz_card.count),
                canonical_name=prev.canonical_name,
            )
        else:
            merged[key] = mr

    check("dedup to 1 entry", len(merged) == 1, str(len(merged)))
    check("merged count = 5", merged["bulbasaur|base"].pz_card.count == 5, str(merged["bulbasaur|base"].pz_card.count))


# ---------------------------------------------------------------------------
# 3. New illustration_rare alt-art — base owned, alt art is new
# ---------------------------------------------------------------------------
def test_new_alt_art_one_star():
    print("\n--- 3. New illustration_rare alt-art (base owned, alt is new) ---")
    # Bulbasaur A1#227 is illustration_rare (alt art); only base Bulbasaur is in collection.
    # The rarity cross-check should detect: PZ card is alt-art, collection entry is base
    # → this is a NEW variant, not a match to the base entry.
    collection = [entry("Bulbasaur", 2, hp=70)]
    results = run([pz("Bulbasaur", 1, "A1", 227)], collection)
    r = results[0]
    check("status=NEW_CARD (alt art, base entry doesn't match)", r.status == "NEW_CARD", r.status)
    check("canonical_name=Bulbasaur", r.canonical_name == "Bulbasaur")


# ---------------------------------------------------------------------------
# 4. New super_rare alt-art — confirm is_alt includes super_rare
# ---------------------------------------------------------------------------
def test_new_two_star():
    print("\n--- 4. New super_rare alt-art (is_alt check) ---")
    # Venusaur ex A1#251 is super_rare; collection has base Venusaur ex (double_rare, hp=340)
    # and alt-art Venusaur ex entry
    collection = [
        entry("Venusaur ex", 1, hp=190),                    # base (double_rare)
        entry("Venusaur ex", 1, hp=190, variant="alt art"),  # alt art
    ]
    results = run([pz("Venusaur ex", 1, "A1", 251)], collection)
    r = results[0]
    # A1#251 = super_rare → is_alt=True
    # alt_idx should = [1] (the alt art entry) → MATCHED to alt art
    check("status=MATCHED", r.status == "MATCHED", r.status)
    check("matched to alt art entry", r.entry.get("variant") == "alt art",
          str(r.entry.get("variant")))


# ---------------------------------------------------------------------------
# 5. New immersive — is_alt=True for immersive rarity
# ---------------------------------------------------------------------------
def test_new_three_star():
    print("\n--- 5. New immersive (is_alt check) ---")
    # Find a real immersive card in pack_sources
    triple = next((r for r in PACK_SOURCES.values() if r.get("rarity") == "immersive"), None)
    if triple is None:
        print("  SKIP: no immersive card found in pack_sources")
        return
    sc_code = triple["set_code"]
    cn = triple["card_number"]
    name = triple["card_name"]
    print(f"  Using: {sc_code}#{cn} {name} [immersive]")

    collection = [
        entry(name, 1, hp=100),
        entry(name, 1, hp=100, variant="alt art"),
    ]
    results = run([pz(name, 1, sc_code, cn)], collection)
    r = results[0]
    check("status=MATCHED", r.status == "MATCHED", r.status)
    check("immersive matched to alt art",
          r.entry.get("variant") == "alt art", str(r.entry.get("variant")))


# ---------------------------------------------------------------------------
# 6. Both variants new — neither in collection, PZ returns base + alt
# ---------------------------------------------------------------------------
def test_both_variants_new():
    print("\n--- 6. Both variants new (base + alt, neither owned) ---")
    # Grovyle: neither variant in collection; PZ returns both
    # Find base and illustration_rare entries
    base_r = PACK_SOURCES.get(("A2b", 5))   # Grovyle base (if exists)
    # Let's just use a card we know has both
    # Use Bulbasaur: A1#1 (common base) and A1#227 (illustration_rare alt)
    collection = []
    pz_cards = [
        pz("Bulbasaur", 2, "A1", 1),    # common → base
        pz("Bulbasaur", 1, "A1", 227),  # illustration_rare → alt art
    ]
    results = run(pz_cards, collection)
    # Both should be NEW_CARD since collection is empty
    check("both NEW_CARD", all(r.status == "NEW_CARD" for r in results))
    check("same canonical Bulbasaur", all(r.canonical_name == "Bulbasaur" for r in results))
    check("count preserved: 2+1", sum(r.pz_card.count for r in results) == 3)


# ---------------------------------------------------------------------------
# 7. A1 numbering mismatch, card NOT owned — must use PZ raw_name
# ---------------------------------------------------------------------------
def test_a1_mismatch_not_owned():
    print("\n--- 7. A1 numbering mismatch — card not owned ---")
    import io, contextlib
    # A1#67: pack_sources has "Cloyster"; PZ returns "Moltres ex" (real data mismatch)
    # The card is NOT in the collection (empty)
    collection = []
    stderr_buf = io.StringIO()
    with contextlib.redirect_stderr(stderr_buf):
        results = run([pz("Moltres ex", 1, "A1", 67)], collection)
    r = results[0]
    # Should NOT be "Cloyster" — must use raw_name "Moltres ex"
    check("canonical_name=Moltres ex (not Cloyster)",
          r.canonical_name == "Moltres ex", r.canonical_name)
    check("status=NEW_CARD", r.status == "NEW_CARD", r.status)
    _s = stderr_buf.getvalue().lower()
    check("mismatch surfaced (INFO summary or WARN)", "re-resolved" in _s or "mismatch" in _s,
          repr(stderr_buf.getvalue()[:120]))


# ---------------------------------------------------------------------------
# 8. A1 numbering mismatch, card OWNED — existing behavior preserved
# ---------------------------------------------------------------------------
def test_a1_mismatch_owned():
    print("\n--- 8. A1 numbering mismatch — card owned ---")
    import io, contextlib
    # A1#67: pack_sources "Cloyster" vs PZ "Moltres ex"; Moltres ex IS in collection
    collection = [entry("Moltres ex", 1, hp=130)]
    stderr_buf = io.StringIO()
    with contextlib.redirect_stderr(stderr_buf):
        results = run([pz("Moltres ex", 1, "A1", 67)], collection)
    r = results[0]
    check("status=MATCHED to Moltres ex", r.status == "MATCHED" and r.entry.get("name") == "Moltres ex",
          f"{r.status} / {r.entry.get('name') if r.entry else None}")
    _s = stderr_buf.getvalue().lower()
    check("mismatch surfaced (INFO summary or WARN)", "re-resolved" in _s or "mismatch" in _s)


# ---------------------------------------------------------------------------
# 9. New PROMO-A card (override)
# ---------------------------------------------------------------------------
def test_new_promo_a():
    print("\n--- 9. New PROMO-A card (override, not in collection) ---")
    # PROMO-A#1 → "Potion"; collection is empty for this card
    collection = []
    results = run([pz("SomeWrongName", 1, "PROMO-A", 1)], collection)
    r = results[0]
    check("canonical_name=Potion (override)", r.canonical_name == "Potion", r.canonical_name)
    check("status=NEW_CARD", r.status == "NEW_CARD", r.status)


# ---------------------------------------------------------------------------
# 10. New PROMO-B card (override)
# ---------------------------------------------------------------------------
def test_new_promo_b():
    print("\n--- 10. New PROMO-B card (override, not in collection) ---")
    # PROMO-B#51 → "Zygarde 10% Forme"; collection is empty
    collection = []
    results = run([pz("Zygarde", 1, "PROMO-B", 51)], collection)
    r = results[0]
    check("canonical_name=Zygarde 10% Forme", r.canonical_name == "Zygarde 10% Forme",
          r.canonical_name)
    check("status=NEW_CARD", r.status == "NEW_CARD", r.status)


# ---------------------------------------------------------------------------
# 11. New card not in pack_sources or collection (raw-name fallback)
# ---------------------------------------------------------------------------
def test_raw_name_fallback():
    print("\n--- 11. Raw-name fallback (no pack_sources, no collection entry) ---")
    collection = []
    # Use a fake set/number not in pack_sources
    results = run([pz("BrandNewPokemon", 1, "ZSET", 999)], collection)
    r = results[0]
    check("status=NEW_CARD", r.status == "NEW_CARD", r.status)
    check("canonical_name=BrandNewPokemon", r.canonical_name == "BrandNewPokemon",
          r.canonical_name)


# ---------------------------------------------------------------------------
# 12. New Trainer card (direct normalized-name match, pack_sources may differ)
# ---------------------------------------------------------------------------
def test_new_trainer_direct_match():
    print("\n--- 12. New Trainer (direct name match, not yet owned) ---")
    # "Professor's Research" not in collection, but in real pack_sources
    # PZ returns it with a set code that IS in pack_sources
    collection = []
    # pack_sources has Professor's Research in multiple sets; use one
    prof_entry = next(
        (r for r in PACK_SOURCES.values() if r.get("card_name") == "Professor's Research"),
        None
    )
    if prof_entry is None:
        print("  SKIP: Professor's Research not in pack_sources")
        return
    sc_code = prof_entry["set_code"]
    cn      = prof_entry["card_number"]
    results = run([pz("Professor's Research", 2, sc_code, cn)], collection)
    r = results[0]
    check("status=NEW_CARD", r.status == "NEW_CARD", r.status)
    check("canonical_name correct", r.canonical_name == "Professor's Research",
          r.canonical_name)


# ---------------------------------------------------------------------------
# 13. Multi-variant: base owned, PZ returns base + new alt simultaneously
# ---------------------------------------------------------------------------
def test_base_owned_alt_new():
    print("\n--- 13. Base owned, alt art new (Bulbasaur common + illustration_rare) ---")
    # Collection has only the base Bulbasaur
    collection = [entry("Bulbasaur", 3, hp=70)]
    pz_cards = [
        pz("Bulbasaur", 3, "A1", 1),    # common → base (owned)
        pz("Bulbasaur", 1, "A1", 227),  # illustration_rare → alt art (not owned)
    ]
    results = run(pz_cards, collection)
    matched_r  = [r for r in results if r.status == "MATCHED"]
    new_r      = [r for r in results if r.status == "NEW_CARD"]
    check("one MATCHED (base)", len(matched_r) == 1, str(len(matched_r)))
    check("one NEW_CARD (alt)", len(new_r) == 1, str(len(new_r)))
    if matched_r:
        check("MATCHED entry is base", matched_r[0].entry.get("variant", "") == "",
              str(matched_r[0].entry.get("variant")))
    if new_r:
        check("NEW_CARD canonical=Bulbasaur", new_r[0].canonical_name == "Bulbasaur")


# ---------------------------------------------------------------------------
# 14. Normalized name collision — different card names that normalize the same
# ---------------------------------------------------------------------------
def test_normalized_name_collision():
    print("\n--- 14. Normalized-name near-collision ---")
    # "Mr. Mime" normalizes to "mr_mime"; "Mr Mime" also → "mr_mime"
    # Make sure a PZ card with "Mr. Mime" matches collection "Mr. Mime" exactly
    collection = [entry("Mr. Mime", 1)]
    results = run([pz("Mr. Mime", 1, "ZSET", 1)], collection)
    r = results[0]
    # No pack_sources for ZSET → Step 2 direct match: normalize("Mr. Mime") == normalize("Mr. Mime")
    check("status=MATCHED", r.status == "MATCHED", r.status)
    check("matched entry name", r.entry.get("name") == "Mr. Mime")


# ---------------------------------------------------------------------------
# 15. Cross-set parallel: card owned, PZ returns it from three set codes
# ---------------------------------------------------------------------------
def test_cross_set_parallel():
    print("\n--- 15. Cross-set parallel (same card, 3 PZ sets, all owned) ---")
    # Bulbasaur in A1#1, A4b#1, A4b#2 → all point to same collection entry
    collection = [entry("Bulbasaur", 5, hp=70)]
    pz_cards = [
        pz("Bulbasaur", 2, "A1",  1),
        pz("Bulbasaur", 1, "A4b", 1),
        pz("Bulbasaur", 2, "A4b", 2),
    ]
    results = run(pz_cards, collection)
    matched = [r for r in results if r.status == "MATCHED"]
    check("all 3 MATCHED", len(matched) == 3, str(len(matched)))
    # entry_pz_total aggregation (Phase 4 in main): counts should sum to 2+1+2=5
    from collections import defaultdict
    totals = defaultdict(int)
    for r in matched:
        totals[r.entry_index] += r.pz_card.count
    check("total count = 5 (sum of 3 sets)", totals[0] == 5, str(dict(totals)))


# ---------------------------------------------------------------------------
# 16. All unowned A1 mismatch numbers — none should produce wrong canonical
# ---------------------------------------------------------------------------
def test_all_a1_mismatches():
    print("\n--- 16. All known A1/A4 numbering mismatches (not owned) ---")
    # Known mismatched numbers from pipeline log history
    mismatches = [
        ("A1",  67, "Moltres ex",   "Cloyster"),
        ("A1", 194, "Cubone",       "Wigglytuff"),
        ("A1", 196, "Marowak ex",   "Meowth"),
        ("A1", 277, "Jigglypuff",   "Gengar ex"),
        ("A1", 280, "Farfetch'd",   "Charizard ex"),
        ("A4", 140, "Chinchou",     "Hoothoot"),
        ("A4", 142, "Lanturn ex",   "Aipom"),
    ]
    import io, contextlib
    all_pass = True
    for sc_code, cn, pz_name, ps_wrong in mismatches:
        collection = []  # not owned
        stderr_buf = io.StringIO()
        with contextlib.redirect_stderr(stderr_buf):
            results = run([pz(pz_name, 1, sc_code, cn)], collection)
        r = results[0]
        correct = (r.canonical_name == pz_name and r.status == "NEW_CARD")
        check(f"{sc_code}#{cn} {pz_name!r} → NEW_CARD, NOT {ps_wrong!r}",
              correct,
              f"got canonical={r.canonical_name!r} status={r.status}")
        if not correct:
            all_pass = False


# ---------------------------------------------------------------------------
# 17. Real unowned card from every set code — smoke test
# ---------------------------------------------------------------------------
def test_smoke_all_sets():
    print("\n--- 17. Smoke test: first unowned card from every set code ---")
    import json, re
    raw = open(ROOT / "collection.json").read()
    owned = {e["name"] for e in json.loads(re.sub(r"//[^\n]*", "", raw))["collection"]}

    # Group pack_sources by set_code, find first unowned card per set
    by_set: dict[str, list] = {}
    for r in PACK_SOURCES.values():
        by_set.setdefault(r["set_code"], []).append(r)

    sets_checked = 0
    for sc_code in sorted(by_set.keys()):
        candidate = next((r for r in by_set[sc_code] if r["card_name"] not in owned), None)
        if candidate is None:
            continue
        name = candidate["card_name"]
        cn   = candidate["card_number"]
        rar  = candidate.get("rarity", "?")

        collection = []
        results = run([pz(name, 1, sc_code, cn)], collection)
        r = results[0]
        ok = (r.canonical_name == name and r.status == "NEW_CARD")
        check(f"{sc_code} [{rar}] {name!r} → NEW_CARD", ok,
              f"canonical={r.canonical_name!r} status={r.status}")
        sets_checked += 1

    print(f"  ({sets_checked} sets checked)")


# ---------------------------------------------------------------------------
# 18. All super_rare + immersive cards — verify is_alt resolves correctly
# ---------------------------------------------------------------------------
def test_all_rare_star_is_alt():
    print("\n--- 18. All super_rare/immersive → is_alt=True path ---")
    from collections import Counter
    ok_count = 0
    fail_count = 0

    for (sc_code, cn), ref in PACK_SOURCES.items():
        rarity = ref.get("rarity", "")
        if rarity not in ("super_rare", "immersive"):
            continue
        name = ref["card_name"]

        # Simulate: collection has base entry + alt entry; PZ returns this alt card
        col = [
            entry(name, 1, hp=100),
            entry(name, 1, hp=100, variant="alt art"),
        ]
        results = run([pz(name, 1, sc_code, cn)], col)
        r = results[0]
        if r.status == "MATCHED" and r.entry.get("variant") == "alt art":
            ok_count += 1
        else:
            fail_count += 1
            if fail_count <= 3:  # show first 3 failures
                print(f"  ✗  {sc_code}#{cn} {name} [{rarity}]: "
                      f"status={r.status} variant={r.entry.get('variant') if r.entry else None}")

    total = ok_count + fail_count
    check(f"all {total} two/immersive cards route to alt art variant",
          fail_count == 0, f"{fail_count} failed out of {total}")


# ---------------------------------------------------------------------------
# 19. Nidoran♀ + Nidoran♂ both new — dedup must keep them as separate entries
# ---------------------------------------------------------------------------
def test_nidoran_dedup_distinct():
    print("\n--- 19. Nidoran♀ + Nidoran♂ both new — dedup produces 2 entries ---")
    # Both cards are new (empty collection).
    # _normalize("Nidoran♀") == _normalize("Nidoran♂") == "nidoran".
    # The old _normalize-based dedup key would merge them; the new .lower() key keeps them separate.
    collection = []
    pz_cards = [
        pz("Nidoran♀", 2, "A1", 166),
        pz("Nidoran♂", 3, "A1", 169),
    ]
    results = run(pz_cards, collection)
    check("both NEW_CARD", all(r.status == "NEW_CARD" for r in results), str([r.status for r in results]))
    check("different canonical names", results[0].canonical_name != results[1].canonical_name,
          f"{results[0].canonical_name!r} vs {results[1].canonical_name!r}")

    # Simulate Phase 4b dedup using canonical_name.lower() as key (matches production)
    merged = {}
    for mr in results:
        key = mr.canonical_name.lower()
        if key in merged:
            prev = merged[key]
            merged[key] = MatchResult(
                status=prev.status,
                pz_card=PZCard(prev.pz_card.set_code, prev.pz_card.card_number,
                               prev.pz_card.raw_name,
                               prev.pz_card.count + mr.pz_card.count),
                canonical_name=prev.canonical_name,
            )
        else:
            merged[key] = mr

    check("dedup produces 2 entries (not merged to 1)", len(merged) == 2, str(len(merged)))
    names_added = {mr.canonical_name for mr in merged.values()}
    check("both Nidoran♀ and Nidoran♂ preserved", names_added == {"Nidoran♀", "Nidoran♂"},
          str(names_added))
    check("Nidoran♀ count=2", merged["nidoran♀"].pz_card.count == 2)
    check("Nidoran♂ count=3", merged["nidoran♂"].pz_card.count == 3)


# ---------------------------------------------------------------------------
# 20. build_auto_entry: blank card_category → hp/stage/type populated
# ---------------------------------------------------------------------------
def test_build_auto_entry_blank_category():
    print("\n--- 20. build_auto_entry blank card_category — hp/stage/type populated ---")
    # Construct a synthetic ext_ref with card_category=None (blank — triggers elif not cat: branch)
    ext_ref_blank = {
        "testpokemon": [{
            "set_code": "A1",
            "number": 999,
            "card_category": None,
            "pokemon_type": "Fire",
            "stage": "Basic",
            "hp": 60,
            "is_ex": False,
        }]
    }
    mr = MatchResult(
        status="NEW_CARD",
        pz_card=PZCard(set_code="A1", card_number=999, raw_name="TestPokemon", count=1),
        canonical_name="TestPokemon",
    )
    built = build_auto_entry(mr, ext_ref_blank, None)
    check("card_type=Pokemon", built.get("card_type") == "Pokemon", str(built.get("card_type")))
    check("hp=60 populated", built.get("hp") == 60, str(built.get("hp")))
    check("type=Fire populated", built.get("type") == "Fire", str(built.get("type")))
    check("stage key present", "stage" in built, str(built))


# ---------------------------------------------------------------------------
# 21. Nidoran♀ + Nidoran♂ both owned — exact-name shortcut routes each correctly
# ---------------------------------------------------------------------------
def test_nidoran_both_owned():
    print("\n--- 21. Nidoran♀ + Nidoran♂ both owned — exact-name match routes correctly ---")
    # Both in collection; PZ returns both. The exact-name shortcut in _match_one
    # should match "Nidoran♀" PZ card to the "Nidoran♀" collection entry,
    # and "Nidoran♂" PZ card to the "Nidoran♂" collection entry —
    # even though both normalize to "nidoran" and have the same rarity/hp.
    collection = [
        entry("Nidoran♀", 2),
        entry("Nidoran♂", 1),
    ]
    pz_cards = [
        pz("Nidoran♀", 2, "A1", 166),
        pz("Nidoran♂", 3, "A1", 169),
    ]
    results = run(pz_cards, collection)
    matched = [r for r in results if r.status == "MATCHED"]
    check("both MATCHED", len(matched) == 2, str([r.status for r in results]))

    by_pz_name = {r.pz_card.raw_name: r for r in matched}
    female_result = by_pz_name.get("Nidoran♀")
    male_result   = by_pz_name.get("Nidoran♂")
    check("Nidoran♀ PZ → Nidoran♀ entry",
          female_result is not None and female_result.entry.get("name") == "Nidoran♀",
          str(female_result.entry.get("name") if female_result else None))
    check("Nidoran♂ PZ → Nidoran♂ entry",
          male_result is not None and male_result.entry.get("name") == "Nidoran♂",
          str(male_result.entry.get("name") if male_result else None))


# ---------------------------------------------------------------------------
# 22. Mismatch slot with alt-art rarity — card OWNED (regression for bug)
# ---------------------------------------------------------------------------
def test_mismatch_slot_altart_rarity_owned():
    print("\n--- 22. Mismatch slot alt-art rarity, card owned → MATCHED ---")
    import io, contextlib
    # A1#277: pack_sources = "Gengar ex" (super_rare), but PZ returns "Jigglypuff"
    # at that slot (set-numbering mismatch). Collection has Jigglypuff (base).
    # Before fix: rarity cross-check saw super_rare → is_pz_alt=True, entry_is_alt=False
    #             → incorrectly returned NEW_CARD instead of MATCHED.
    # After fix:  name guard skips rarity check when ps_ref card ≠ canonical_name.
    mismatch_ps = PACK_SOURCES.get(("A1", 277))
    if mismatch_ps is None or _normalize(mismatch_ps.get("card_name", "")) == _normalize("Jigglypuff"):
        print("  SKIP: A1#277 not in pack_sources or name changed — can't test mismatch")
        return
    print(f"  A1#277 pack_sources = {mismatch_ps['card_name']!r} ({mismatch_ps.get('rarity')})")

    collection = [entry("Jigglypuff", 1, hp=60)]
    stderr_buf = io.StringIO()
    with contextlib.redirect_stderr(stderr_buf):
        results = run([pz("Jigglypuff", 1, "A1", 277)], collection)
    r = results[0]
    check("status=MATCHED (not NEW_CARD)", r.status == "MATCHED", r.status)
    check("matched to Jigglypuff entry", r.entry and r.entry.get("name") == "Jigglypuff",
          str(r.entry.get("name") if r.entry else None))
    _s = stderr_buf.getvalue().lower()
    check("mismatch surfaced (INFO summary or WARN)", "re-resolved" in _s or "mismatch" in _s)


# ---------------------------------------------------------------------------
# 23. Mismatch slot with alt-art rarity — card NOT owned → NEW_CARD
# ---------------------------------------------------------------------------
def test_mismatch_slot_altart_rarity_not_owned():
    print("\n--- 23. Mismatch slot alt-art rarity, card not owned → NEW_CARD ---")
    import io, contextlib
    # Same A1#277 mismatch scenario, but Jigglypuff is NOT in the collection.
    # Should still produce NEW_CARD with canonical_name=Jigglypuff (from PZ raw_name),
    # not from the mismatch slot's pack_sources name.
    mismatch_ps = PACK_SOURCES.get(("A1", 277))
    if mismatch_ps is None or _normalize(mismatch_ps.get("card_name", "")) == _normalize("Jigglypuff"):
        print("  SKIP: A1#277 not in pack_sources or name changed")
        return

    collection = []
    stderr_buf = io.StringIO()
    with contextlib.redirect_stderr(stderr_buf):
        results = run([pz("Jigglypuff", 1, "A1", 277)], collection)
    r = results[0]
    check("status=NEW_CARD", r.status == "NEW_CARD", r.status)
    check("canonical_name=Jigglypuff (not mismatch card)",
          r.canonical_name == "Jigglypuff", r.canonical_name)
    _s = stderr_buf.getvalue().lower()
    check("mismatch surfaced (INFO summary or WARN)", "re-resolved" in _s or "mismatch" in _s)


# ---------------------------------------------------------------------------
# 24. All illustration_rare + crown rarities → alt art routing
# ---------------------------------------------------------------------------
def test_all_one_star_crown_is_alt():
    print("\n--- 24. All illustration_rare + crown → is_alt=True path ---")
    fail_count = 0
    ok_count   = 0

    for (sc_code, cn), ref in PACK_SOURCES.items():
        rarity = ref.get("rarity", "")
        if rarity not in ("illustration_rare", "ultra_rare"):
            continue
        name = ref["card_name"]
        col = [
            entry(name, 1, hp=100),
            entry(name, 1, hp=100, variant="alt art"),
        ]
        results = run([pz(name, 1, sc_code, cn)], col)
        r = results[0]
        if r.status == "MATCHED" and r.entry.get("variant") == "alt art":
            ok_count += 1
        else:
            fail_count += 1
            if fail_count <= 3:
                print(f"  ✗  {sc_code}#{cn} {name} [{rarity}]: "
                      f"status={r.status} variant={r.entry.get('variant') if r.entry else None}")

    total = ok_count + fail_count
    check(f"all {total} illustration_rare/crown cards route to alt art variant",
          fail_count == 0, f"{fail_count} failed out of {total}")


# ---------------------------------------------------------------------------
# 25. Comprehensive routing: every unowned non-mismatch card → NEW_CARD
# ---------------------------------------------------------------------------
def test_comprehensive_all_packs():
    print("\n--- 25. Comprehensive: every unowned non-mismatch card → NEW_CARD ---")
    import json, re as _re
    raw = open(ROOT / "collection.json").read()
    owned = {e["name"] for e in json.loads(_re.sub(r"//[^\n]*", "", raw))["collection"]}

    KNOWN_MISMATCHES = {
        ("A1",  67), ("A1", 194), ("A1", 196),
        ("A1", 277), ("A1", 280),
        ("A4", 140), ("A4", 142),
    }

    fail_count = 0
    ok_count   = 0
    for (sc_code, cn), ref in PACK_SOURCES.items():
        if (sc_code, cn) in KNOWN_MISMATCHES:
            continue
        name = ref["card_name"]
        if name in owned:
            continue  # skip owned — not a new addition scenario

        results = run([pz(name, 1, sc_code, cn)], [])
        r = results[0]
        if r.status == "NEW_CARD" and r.canonical_name == name:
            ok_count += 1
        else:
            fail_count += 1
            if fail_count <= 5:
                print(f"  ✗  {sc_code}#{cn} {name!r}: "
                      f"status={r.status} canonical={r.canonical_name!r}")

    total = ok_count + fail_count
    check(f"all {total} unowned cards route to NEW_CARD with correct canonical name",
          fail_count == 0, f"{fail_count} failed out of {total}")


# ---------------------------------------------------------------------------
# 26. Phase 4b alt-art tagging: build_auto_entry + name guard
# ---------------------------------------------------------------------------
def test_phase4b_alt_art_tagging():
    print("\n--- 26. Phase 4b alt-art tagging via build_auto_entry + name guard ---")
    # _ALT_RARITIES: use the module-level shared alias (defined at import)

    # Replicate Phase 4b logic inline: for a NEW_CARD result, call build_auto_entry
    # then apply the pack_sources name guard to set variant="alt art".
    def phase4b_tag(mr):
        e = build_auto_entry(mr, EXT_REF, None)
        pz_c = mr.pz_card
        if pz_c.set_code and pz_c.card_number is not None:
            ps_r = PACK_SOURCES.get((pz_c.set_code, pz_c.card_number))
            if (ps_r
                    and _normalize(ps_r["card_name"]) == _normalize(mr.canonical_name)
                    and ps_r.get("rarity") in _ALT_RARITIES):
                e["variant"] = "alt art"
        return e

    fail_alt   = 0
    fail_base  = 0
    ok_count   = 0
    KNOWN_MISMATCHES = {
        ("A1",  67), ("A1", 194), ("A1", 196),
        ("A1", 277), ("A1", 280),
        ("A4", 140), ("A4", 142),
    }

    for (sc_code, cn), ref in PACK_SOURCES.items():
        if (sc_code, cn) in KNOWN_MISMATCHES:
            continue
        rarity = ref.get("rarity", "")
        name   = ref["card_name"]
        results = run([pz(name, 1, sc_code, cn)], [])
        r = results[0]
        if r.status != "NEW_CARD":
            continue

        tagged = phase4b_tag(r)
        is_alt_rarity = rarity in _ALT_RARITIES
        has_variant   = tagged.get("variant") == "alt art"

        if is_alt_rarity and not has_variant:
            fail_alt += 1
            if fail_alt <= 3:
                print(f"  ✗  {sc_code}#{cn} {name} [{rarity}]: expected variant='alt art', got {tagged.get('variant')!r}")
        elif not is_alt_rarity and has_variant:
            fail_base += 1
            if fail_base <= 3:
                print(f"  ✗  {sc_code}#{cn} {name} [{rarity}]: unexpected variant='alt art' on base rarity")
        else:
            ok_count += 1

    check(f"alt-rarity NEW_CARDs get variant='alt art' (0 missed)",
          fail_alt == 0, f"{fail_alt} alt cards not tagged")
    check("base-rarity NEW_CARDs do NOT get variant='alt art'",
          fail_base == 0, f"{fail_base} base cards incorrectly tagged")


# ---------------------------------------------------------------------------
# 27. Phase 4c Case A: alt art added marks base entry stale
# ---------------------------------------------------------------------------
def test_phase4c_case_a_stale_base():
    print("\n--- 27. Phase 4c Case A — alt art added marks base entry stale ---")
    # Simulate the Phase 4c logic inline.
    # Setup: base Bulbasaur is in missing_from_pz; an alt-art Bulbasaur was just auto-added.
    auto_added = [{"name": "Bulbasaur", "variant": "alt art", "count": 1}]
    missing_from_pz = [{"name": "Bulbasaur", "count": 2}]
    collection_entries = [
        {"name": "Bulbasaur", "count": 2, "card_type": "Pokemon"},  # index 0 — base
        {"name": "Squirtle",  "count": 1, "card_type": "Pokemon"},  # index 1 — keep
    ]
    matched_indices: set = set()  # nothing matched this run

    # Fixed: use .lower() (not _normalize) so Nidoran♀/♂ stay distinct
    alt_art_nns = {e["name"].lower() for e in auto_added if e.get("variant") == "alt art"}
    missing_nns = {_normalize(e.get("name", "")) for e in missing_from_pz}

    stale_base_indices: set = set()
    for i, e in enumerate(collection_entries):
        if i in matched_indices:
            continue
        nn = _normalize(e.get("name", ""))
        if nn not in missing_nns:
            continue
        name = e.get("name", "")
        if not e.get("variant") and name.lower() in alt_art_nns:
            stale_base_indices.add(i)

    check("base Bulbasaur (index 0) marked stale", 0 in stale_base_indices,
          str(stale_base_indices))
    check("Squirtle (index 1) NOT marked stale", 1 not in stale_base_indices,
          str(stale_base_indices))
    check("stale set has exactly 1 entry", len(stale_base_indices) == 1,
          str(len(stale_base_indices)))


# ---------------------------------------------------------------------------
# 28. Phase 4c Case B: fixed threshold fires at 3rd consecutive miss
# ---------------------------------------------------------------------------
def test_phase4c_case_b_threshold():
    print("\n--- 28. Phase 4c Case B — threshold fires at 3rd miss (not 4th) ---")
    import json, tempfile

    write_review_queue = sc.write_review_queue
    orig_queue = sc.REVIEW_QUEUE

    with tempfile.TemporaryDirectory() as tmp:
        queue_path = Path(tmp) / "sync_review_queue.json"
        sc.REVIEW_QUEUE = queue_path

        try:
            _STALE_THRESHOLD = sc._STALE_THRESHOLD

            # Sync 1: Misdreavus first seen missing; stored consecutive=1
            write_review_queue([], [{"name": "Misdreavus", "count": 2}])
            # Sync 2: still missing; stored consecutive=2
            write_review_queue([], [{"name": "Misdreavus", "count": 2}])

            prev_q = json.loads(queue_path.read_text())
            prev_consecutive = {e["name"]: e["consecutive_missing"]
                                for e in prev_q.get("missing_from_pz", [])}
            stored = prev_consecutive.get("Misdreavus", 0)
            check("after 2 misses: stored consecutive=2", stored == 2, str(stored))

            # Simulate Phase 4c Case B check at start of sync 3
            # With fix: >= _STALE_THRESHOLD - 1 (>= 2) fires when stored=2
            fires_at_sync3 = stored >= _STALE_THRESHOLD - 1
            check("Case B fires at 3rd miss (stored=2 >= threshold-1=2)", fires_at_sync3,
                  f"stored={stored} threshold-1={_STALE_THRESHOLD - 1}")

            # Confirm OLD (unfixed) check would NOT have fired
            old_fires = stored >= _STALE_THRESHOLD
            check("old check (>= threshold) would NOT fire at sync 3", not old_fires,
                  f"stored={stored} old_threshold={_STALE_THRESHOLD}")

            # Confirm fix fires BEFORE the consecutive count is incremented to 3
            check("fix fires on exactly the 3rd miss (not delayed to 4th)",
                  fires_at_sync3 and not old_fires)

        finally:
            sc.REVIEW_QUEUE = orig_queue


# ---------------------------------------------------------------------------
# 29. Phase 4e: stale entry names excluded from write_review_queue
# ---------------------------------------------------------------------------
def test_phase4e_stale_queue_exclusion():
    print("\n--- 29. Phase 4e — stale names excluded from review queue ---")
    import json, tempfile

    write_review_queue = sc.write_review_queue
    orig_queue = sc.REVIEW_QUEUE

    with tempfile.TemporaryDirectory() as tmp:
        queue_path = Path(tmp) / "sync_review_queue.json"
        sc.REVIEW_QUEUE = queue_path

        try:
            collection_entries = [
                {"name": "Drifloon", "count": 1},  # index 0 — going stale
                {"name": "Gengar",   "count": 2},  # index 1 — genuinely missing
            ]
            stale_base_indices = {0}
            missing_from_pz = [
                {"name": "Drifloon", "count": 1},
                {"name": "Gengar",   "count": 2},
            ]

            # Replicate Phase 4e filter logic (with fix 6: guard against empty names)
            stale_names = {
                collection_entries[i]["name"]
                for i in stale_base_indices
                if collection_entries[i].get("name")
            }
            queue_missing = [e for e in missing_from_pz if e.get("name") not in stale_names]

            write_review_queue([], queue_missing)
            q = json.loads(queue_path.read_text())
            missing_names = [e["name"] for e in q.get("missing_from_pz", [])]

            check("Drifloon excluded from queue (stale)", "Drifloon" not in missing_names,
                  str(missing_names))
            check("Gengar still in queue (genuinely missing)", "Gengar" in missing_names,
                  str(missing_names))
            check("queue has exactly 1 missing entry", len(missing_names) == 1,
                  str(missing_names))

        finally:
            sc.REVIEW_QUEUE = orig_queue


# ---------------------------------------------------------------------------
# 31. Phase 4c Case A: pre-existing MATCHED alt-art does NOT trigger Case A
# ---------------------------------------------------------------------------
def test_phase4c_case_a_matched_alt_art():
    print("\n--- 31. Phase 4c Case A — pre-existing matched alt-art does NOT mark base stale (by design) ---")
    # Production code builds alt_art_nns ONLY from auto_added (newly added this sync).
    # A user who already owns Bulbasaur alt-art (matched this sync) + Bulbasaur base (missing)
    # does NOT trigger Case A — the base must wait for Case B (_STALE_THRESHOLD consecutive misses).
    # Rationale: extending to pre-existing matched alt-art would delete the base on ANY single
    # transient PZ failure, with no threshold protection. Deliberately not implemented.
    collection_entries = [
        {"name": "Bulbasaur", "count": 2, "card_type": "Pokemon"},               # index 0 — base (missing)
        {"name": "Bulbasaur", "count": 1, "card_type": "Pokemon", "variant": "alt art"},  # index 1 — alt art (matched)
        {"name": "Squirtle",  "count": 1, "card_type": "Pokemon"},               # index 2 — keep
    ]
    matched_indices = {1}  # alt-art entry was matched this run
    auto_added: list = []  # nothing newly added this sync
    missing_from_pz = [{"name": "Bulbasaur", "count": 2}]  # base is missing from PZ

    # Production logic: alt_art_nns comes ONLY from auto_added, never from matched_indices
    alt_art_nns = {e["name"].lower() for e in auto_added if e.get("variant") == "alt art"}
    missing_nns = {_normalize(e.get("name", "")) for e in missing_from_pz}

    stale_base_indices: set = set()
    for i, e in enumerate(collection_entries):
        if i in matched_indices:
            continue
        nn = _normalize(e.get("name", ""))
        if nn not in missing_nns:
            continue
        name = e.get("name", "")
        if not e.get("variant") and name.lower() in alt_art_nns:
            stale_base_indices.add(i)

    # Production: Case A does NOT fire — alt_art_nns is empty (no new alt-art was added)
    check("base Bulbasaur (index 0) NOT stale (pre-existing alt-art never triggers Case A)",
          0 not in stale_base_indices, str(stale_base_indices))
    check("alt-art Bulbasaur (index 1) NOT stale (was matched)", 1 not in stale_base_indices,
          str(stale_base_indices))
    check("Squirtle (index 2) NOT stale", 2 not in stale_base_indices,
          str(stale_base_indices))
    check("stale_base_indices is empty (no Case A without newly-added alt-art)",
          len(stale_base_indices) == 0, str(stale_base_indices))

    # Show what the REVERTED (unsafe) logic WOULD have done — for documentation
    unsafe_alt_art_nns = {e["name"].lower() for e in auto_added if e.get("variant") == "alt art"}
    for idx in matched_indices:
        if idx < len(collection_entries) and collection_entries[idx].get("variant") == "alt art":
            unsafe_alt_art_nns.add(collection_entries[idx]["name"].lower())
    unsafe_stale: set = set()
    for i, e in enumerate(collection_entries):
        if i in matched_indices:
            continue
        nn = _normalize(e.get("name", ""))
        if nn not in missing_nns:
            continue
        name = e.get("name", "")
        if not e.get("variant") and name.lower() in unsafe_alt_art_nns:
            unsafe_stale.add(i)
    check("(reference) unsafe matched_indices extension WOULD mark base stale",
          0 in unsafe_stale, str(unsafe_stale))


# ---------------------------------------------------------------------------
# 30. Phase 4c Case A: Nidoran♀ alt-art does NOT mark Nidoran♂ base stale
# ---------------------------------------------------------------------------
def test_phase4c_nidoran_cross_contamination():
    print("\n--- 30. Phase 4c Case A — Nidoran♀ alt-art does not mark Nidoran♂ base stale ---")
    # Regression for: _normalize("Nidoran♀") == _normalize("Nidoran♂") == "nidoran".
    # Before fix: alt_art_nns = {"nidoran"}, nn for Nidoran♂ base = "nidoran" → incorrectly marked stale.
    # After fix:  alt_art_nns = {"nidoran♀"}, name.lower() for Nidoran♂ base = "nidoran♂" → not in set → kept.
    auto_added       = [{"name": "Nidoran♀", "variant": "alt art", "count": 1}]
    missing_from_pz  = [{"name": "Nidoran♀", "count": 1}, {"name": "Nidoran♂", "count": 1}]
    collection_entries = [
        {"name": "Nidoran♀", "count": 1, "card_type": "Pokemon"},  # index 0 — base ♀ (missing)
        {"name": "Nidoran♂", "count": 2, "card_type": "Pokemon"},  # index 1 — base ♂ (missing)
        {"name": "Squirtle",  "count": 1, "card_type": "Pokemon"},  # index 2 — keep
    ]
    matched_indices: set = set()

    # Fixed logic: .lower() for alt_art_nns, name.lower() for Case A check
    alt_art_nns = {e["name"].lower() for e in auto_added if e.get("variant") == "alt art"}
    missing_nns = {_normalize(e.get("name", "")) for e in missing_from_pz}

    stale_base_indices: set = set()
    for i, e in enumerate(collection_entries):
        if i in matched_indices:
            continue
        nn = _normalize(e.get("name", ""))
        if nn not in missing_nns:
            continue
        name = e.get("name", "")
        if not e.get("variant") and name.lower() in alt_art_nns:
            stale_base_indices.add(i)

    check("Nidoran♀ base (index 0) marked stale (alt-art added)", 0 in stale_base_indices,
          str(stale_base_indices))
    check("Nidoran♂ base (index 1) NOT marked stale (different card)", 1 not in stale_base_indices,
          str(stale_base_indices))
    check("Squirtle (index 2) NOT marked stale", 2 not in stale_base_indices,
          str(stale_base_indices))

    # Confirm the OLD _normalize-based logic WOULD have incorrectly marked ♂ stale
    old_alt_art_nns = {_normalize(e["name"]) for e in auto_added if e.get("variant") == "alt art"}
    old_stale: set = set()
    for i, e in enumerate(collection_entries):
        if i in matched_indices:
            continue
        nn = _normalize(e.get("name", ""))
        if nn not in missing_nns:
            continue
        if nn in old_alt_art_nns:
            old_stale.add(i)
    check("old _normalize logic WOULD have marked ♂ stale (regression reference)",
          1 in old_stale, str(old_stale))


# ---------------------------------------------------------------------------
# 32. Phase 4c Case B — named-art variants immune to Case B deletion
# ---------------------------------------------------------------------------
def test_phase4c_case_b_named_art_immune():
    print("\n--- 32. Phase 4c Case B — named-art variants immune (never returned by PZ) ---")
    # PZ never returns named-art entries ("Tackle art", "Flame Tail art", etc.) as standalone
    # records. Without protection they'd accumulate consecutive_missing counts and be deleted
    # after _STALE_THRESHOLD syncs. Case B must skip non-"alt art" variant entries.
    _STALE_THRESHOLD = sc._STALE_THRESHOLD

    collection_entries = [
        {"name": "Pikachu",          "count": 1, "card_type": "Pokemon"},                           # index 0 — base, missing → should be removed
        {"name": "Pikachu",          "count": 1, "card_type": "Pokemon", "variant": "alt art"},     # index 1 — alt art, missing → should be removed
        {"name": "Pikachu",          "count": 1, "card_type": "Pokemon", "variant": "Tackle art"},  # index 2 — named-art, never in PZ → must survive
        {"name": "Pikachu",          "count": 1, "card_type": "Pokemon", "variant": "Spark art"},   # index 3 — named-art, never in PZ → must survive
        {"name": "Charmander",       "count": 2, "card_type": "Pokemon"},                           # index 4 — matched this run → keep
    ]
    matched_indices = {4}
    auto_added: list = []
    # All Pikachu entries appear in missing_from_pz (base, alt art, and named-art variants)
    missing_from_pz = [
        {"name": "Pikachu",          "count": 1},
    ]
    # Pikachu base + alt-art have been consecutively missing >= _STALE_THRESHOLD - 1 runs
    prev_consecutive = {
        "Pikachu": _STALE_THRESHOLD - 1,
    }

    alt_art_nns: set = set()
    missing_nns = {_normalize(e.get("name", "")) for e in missing_from_pz}

    stale_base_indices: set = set()
    for i, e in enumerate(collection_entries):
        if i in matched_indices:
            continue
        nn = _normalize(e.get("name", ""))
        if nn not in missing_nns:
            continue
        name = e.get("name", "")
        if not e.get("variant") and name.lower() in alt_art_nns:
            stale_base_indices.add(i)
        elif (e.get("variant") in (None, "alt art")
              and prev_consecutive.get(name, 0) >= _STALE_THRESHOLD - 1):
            stale_base_indices.add(i)

    check("Pikachu base (index 0) marked stale by Case B", 0 in stale_base_indices,
          str(stale_base_indices))
    check("Pikachu alt art (index 1) marked stale by Case B", 1 in stale_base_indices,
          str(stale_base_indices))
    check("Pikachu 'Tackle art' (index 2) NOT stale (named-art immune)", 2 not in stale_base_indices,
          str(stale_base_indices))
    check("Pikachu 'Spark art' (index 3) NOT stale (named-art immune)", 3 not in stale_base_indices,
          str(stale_base_indices))
    check("Charmander (index 4) NOT stale (matched)", 4 not in stale_base_indices,
          str(stale_base_indices))


# ---------------------------------------------------------------------------
# 33. Phase 4b dedup — base + alt-art for same card stay separate
# ---------------------------------------------------------------------------
def test_phase4b_dedup_base_vs_altart():
    print("\n--- 33. Phase 4b dedup — base + alt-art NEW_CARDs kept separate ---")
    # Bug: old key was canonical_name.lower() → base and alt-art Bulbasaur both keyed
    # as "bulbasaur" → alt-art slot lost, doubled count, no variant tag.
    # Fix: key includes "|alt" or "|base" suffix based on pack_sources rarity lookup.
    collection: list = []  # nothing owned
    pz_cards = [
        pz("Bulbasaur", 2, "A1", 1),    # A1#1 = common (base)
        pz("Bulbasaur", 1, "A1", 227),  # A1#227 = illustration_rare (alt art)
    ]
    results = run(pz_cards, collection)
    check("both NEW_CARD", all(r.status == "NEW_CARD" for r in results))

    _ALT_RARITIES_S33 = _ALT_RARITIES

    def _is_alt_s33(mr):
        pz_c = mr.pz_card
        if not (pz_c.set_code and pz_c.card_number is not None):
            return False
        ps_r = PACK_SOURCES.get((pz_c.set_code, pz_c.card_number))
        return bool(
            ps_r
            and _normalize(ps_r.get("card_name", "")) == _normalize(mr.canonical_name or "")
            and ps_r.get("rarity") in _ALT_RARITIES_S33
        )

    merged = {}
    for mr in results:
        key = mr.canonical_name.lower() + ("|alt" if _is_alt_s33(mr) else "|base")
        if key in merged:
            prev = merged[key]
            merged[key] = MatchResult(
                status=prev.status,
                pz_card=PZCard(prev.pz_card.set_code, prev.pz_card.card_number,
                               prev.pz_card.raw_name,
                               prev.pz_card.count + mr.pz_card.count),
                canonical_name=prev.canonical_name,
            )
        else:
            merged[key] = mr

    check("dedup produces 2 entries (base and alt separate)", len(merged) == 2, str(list(merged.keys())))
    check("'bulbasaur|base' entry exists", "bulbasaur|base" in merged, str(list(merged.keys())))
    check("'bulbasaur|alt' entry exists", "bulbasaur|alt" in merged, str(list(merged.keys())))
    check("base count=2", merged["bulbasaur|base"].pz_card.count == 2,
          str(merged["bulbasaur|base"].pz_card.count))
    check("alt count=1", merged["bulbasaur|alt"].pz_card.count == 1,
          str(merged["bulbasaur|alt"].pz_card.count))
    check("base slot = A1#1", merged["bulbasaur|base"].pz_card.card_number == 1,
          str(merged["bulbasaur|base"].pz_card.card_number))
    check("alt slot = A1#227", merged["bulbasaur|alt"].pz_card.card_number == 227,
          str(merged["bulbasaur|alt"].pz_card.card_number))

    # OLD key (just .lower()) would have collapsed both into one entry
    old_merged = {}
    for mr in results:
        key = mr.canonical_name.lower()
        if key in old_merged:
            prev = old_merged[key]
            old_merged[key] = MatchResult(
                status=prev.status,
                pz_card=PZCard(prev.pz_card.set_code, prev.pz_card.card_number,
                               prev.pz_card.raw_name,
                               prev.pz_card.count + mr.pz_card.count),
                canonical_name=prev.canonical_name,
            )
        else:
            old_merged[key] = mr
    check("old key (canonical_name.lower()) would collapse to 1 entry (regression ref)",
          len(old_merged) == 1, str(len(old_merged)))


# ---------------------------------------------------------------------------
# Run all
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 65)
    print("  New card additions simulation — all packs")
    print("=" * 65)

    test_simple_new_card()
    test_multi_set_new_card()
    test_new_alt_art_one_star()
    test_new_two_star()
    test_new_three_star()
    test_both_variants_new()
    test_a1_mismatch_not_owned()
    test_a1_mismatch_owned()
    test_new_promo_a()
    test_new_promo_b()
    test_raw_name_fallback()
    test_new_trainer_direct_match()
    test_base_owned_alt_new()
    test_normalized_name_collision()
    test_cross_set_parallel()
    test_all_a1_mismatches()
    test_smoke_all_sets()
    test_all_rare_star_is_alt()
    test_nidoran_dedup_distinct()
    test_build_auto_entry_blank_category()
    test_nidoran_both_owned()
    test_mismatch_slot_altart_rarity_owned()
    test_mismatch_slot_altart_rarity_not_owned()
    test_all_one_star_crown_is_alt()
    test_comprehensive_all_packs()
    test_phase4b_alt_art_tagging()
    test_phase4c_case_a_stale_base()
    test_phase4c_case_b_threshold()
    test_phase4e_stale_queue_exclusion()
    test_phase4c_case_a_matched_alt_art()
    test_phase4c_nidoran_cross_contamination()
    test_phase4c_case_b_named_art_immune()
    test_phase4b_dedup_base_vs_altart()

    print()
    if _failures:
        print(f"FAILED: {len(_failures)} check(s)")
        for f in _failures:
            print(f"  - {f}")
        sys.exit(1)
    else:
        print(f"ALL PASSED — {33} scenarios, 0 failures")
        sys.exit(0)
