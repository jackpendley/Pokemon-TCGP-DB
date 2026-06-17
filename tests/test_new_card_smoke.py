"""New-card-addition tests — smoke group.

Split from the former monolithic test_new_card_additions.py; shared setup
lives in _new_card_helpers.py.
"""

from _new_card_helpers import (  # noqa: F401
    sc, PZCard, MatchResult, match_pz_cards, build_auto_entry,
    _normalize, _PROMO_A_OVERRIDES, _PROMO_B_OVERRIDES, _ALT_RARITIES,
    PACK_SOURCES, EXT_REF, check, pz, entry, run,
    ROOT, Path, json, re,
)


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
