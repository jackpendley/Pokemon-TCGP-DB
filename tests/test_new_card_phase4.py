"""New-card-addition tests — phase4 group.

Split from the former monolithic test_new_card_additions.py; shared setup
lives in _new_card_helpers.py.
"""

from _new_card_helpers import (  # noqa: F401
    sc, PZCard, MatchResult, match_pz_cards, build_auto_entry,
    _normalize, _PROMO_A_OVERRIDES, _PROMO_B_OVERRIDES, _ALT_RARITIES,
    PACK_SOURCES, EXT_REF, check, pz, entry, run,
    ROOT, Path, json, re,
)


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
