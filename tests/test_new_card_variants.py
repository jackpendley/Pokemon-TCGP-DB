"""New-card-addition tests — variants group.

Split from the former monolithic test_new_card_additions.py; shared setup
lives in _new_card_helpers.py.
"""

from _new_card_helpers import (  # noqa: F401
    sc, PZCard, MatchResult, match_pz_cards, build_auto_entry,
    _normalize, _PROMO_A_OVERRIDES, _PROMO_B_OVERRIDES, _ALT_RARITIES,
    PACK_SOURCES, EXT_REF, check, pz, entry, run,
    ROOT, Path, json, re,
)


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
