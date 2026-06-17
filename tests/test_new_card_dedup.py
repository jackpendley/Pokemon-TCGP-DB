"""New-card-addition tests — dedup group.

Split from the former monolithic test_new_card_additions.py; shared setup
lives in _new_card_helpers.py.
"""

from _new_card_helpers import (  # noqa: F401
    sc, PZCard, MatchResult, match_pz_cards, build_auto_entry,
    _normalize, _PROMO_A_OVERRIDES, _PROMO_B_OVERRIDES, _ALT_RARITIES,
    PACK_SOURCES, EXT_REF, check, pz, entry, run,
    ROOT, Path, json, re,
)


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
