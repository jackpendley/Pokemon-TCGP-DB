"""New-card-addition tests — basic group.

Split from the former monolithic test_new_card_additions.py; shared setup
lives in _new_card_helpers.py.
"""

from _new_card_helpers import (  # noqa: F401
    sc, PZCard, MatchResult, match_pz_cards, build_auto_entry,
    _normalize, _PROMO_A_OVERRIDES, _PROMO_B_OVERRIDES, _ALT_RARITIES,
    PACK_SOURCES, EXT_REF, check, pz, entry, run,
    ROOT, Path, json, re,
)


def test_simple_new_card():
    print("\n--- 1. Simple new card (pack_sources match) ---")
    # Use a real card that IS in pack_sources but NOT in an empty collection
    # Bulbasaur A1#1 → common
    results = run([pz("Bulbasaur", 2, "A1", 1)], [])
    r = results[0]
    check("status=NEW_CARD", r.status == "NEW_CARD", r.status)
    check("canonical_name=Bulbasaur", r.canonical_name == "Bulbasaur", r.canonical_name)
    check("count=2", r.pz_card.count == 2)

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

def test_new_promo_a():
    print("\n--- 9. New PROMO-A card (override, not in collection) ---")
    # PROMO-A#1 → "Potion"; collection is empty for this card
    collection = []
    results = run([pz("SomeWrongName", 1, "PROMO-A", 1)], collection)
    r = results[0]
    check("canonical_name=Potion (override)", r.canonical_name == "Potion", r.canonical_name)
    check("status=NEW_CARD", r.status == "NEW_CARD", r.status)

def test_new_promo_b():
    print("\n--- 10. New PROMO-B card (override, not in collection) ---")
    # PROMO-B#51 → "Zygarde 10% Forme"; collection is empty
    collection = []
    results = run([pz("Zygarde", 1, "PROMO-B", 51)], collection)
    r = results[0]
    check("canonical_name=Zygarde 10% Forme", r.canonical_name == "Zygarde 10% Forme",
          r.canonical_name)
    check("status=NEW_CARD", r.status == "NEW_CARD", r.status)

def test_raw_name_fallback():
    print("\n--- 11. Raw-name fallback (no pack_sources, no collection entry) ---")
    collection = []
    # Use a fake set/number not in pack_sources
    results = run([pz("BrandNewPokemon", 1, "ZSET", 999)], collection)
    r = results[0]
    check("status=NEW_CARD", r.status == "NEW_CARD", r.status)
    check("canonical_name=BrandNewPokemon", r.canonical_name == "BrandNewPokemon",
          r.canonical_name)

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


def test_describe_new_entry():
    print("\n--- 17. _describe_new_entry surfaces assigned metadata for the log ---")
    # Pokémon: resolved coord, rarity, card type, stage label, type, HP all shown so the
    # synced card can be validated against the in-app card straight from pipeline.log.
    poke = {"name": "Duskull", "count": 1, "card_type": "Pokemon", "stage": 0,
            "stage_label": "Basic", "type": "Darkness", "hp": 50, "rarity": "common",
            "set_code": "B1", "card_number": 103}
    desc = sc._describe_new_entry(poke)
    for token in ("B1/103", "common", "Pokemon", "Basic", "Darkness", "HP50"):
        check(f"describe contains {token!r}", token in desc, desc)

    # Trainer: card_type/subtype shown instead of Pokémon attributes.
    trainer = {"name": "Rare Candy", "count": 1, "card_type": "Trainer",
               "trainer_subtype": "Item", "rarity": "uncommon",
               "set_code": "A3", "card_number": 144}
    tdesc = sc._describe_new_entry(trainer)
    for token in ("A3/144", "uncommon", "Trainer/Item"):
        check(f"trainer describe contains {token!r}", token in tdesc, tdesc)

    # Alt-art variant is surfaced.
    alt = {"name": "Bulbasaur", "count": 1, "card_type": "Pokemon", "rarity": "illustration_rare",
           "set_code": "A1", "card_number": 227, "variant": "alt art"}
    check("variant shown", "alt art" in sc._describe_new_entry(alt), sc._describe_new_entry(alt))
