#!/usr/bin/env python3
"""
Simulation / unit tests for the sync matching pipeline.

Tests every reliability-critical scenario:
  1. Exact (set_code, card_number) → pack_sources match
  2. PROMO-A override match
  3. PROMO-B override match
  4. Direct normalized-name match (trainers / sets not in pack_sources)
  5. NEW_CARD auto-add (card not in collection)
  6. Duplicate NEW_CARD dedup — same canonical name from two PZ set records
  7. Multi-variant disambiguation — Pass 2 (exclusion resolves AMBIGUOUS)
  8. Multi-variant disambiguation — Pass 3 (rarity rank assignment)
  9. AMBIGUOUS force-match with WARN (no disambiguation data)
 10. consecutive_missing counter increments correctly from 0

Usage:
    python3 -m pytest tests/test_sync_matching.py
    python3 tests/test_sync_matching.py
"""

import importlib.util
import json
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Load sync_collection functions without executing main()
# ---------------------------------------------------------------------------

spec = importlib.util.spec_from_file_location(
    "sync_collection",
    ROOT / "scripts" / "sync_collection.py",
)
sc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sc)

PZCard       = sc.PZCard
MatchResult  = sc.MatchResult
match_pz_cards  = sc.match_pz_cards
write_review_queue = sc.write_review_queue
_normalize   = sc._normalize


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


def make_pz(raw_name, count=1, set_code=None, card_number=None) -> PZCard:
    return PZCard(
        set_code=set_code,
        card_number=card_number,
        raw_name=raw_name,
        count=count,
    )


def make_entry(name, count=1, hp=None, variant=None, card_type="Pokemon") -> dict:
    e = {"name": name, "count": count, "card_type": card_type, "is_ex": False}
    if hp is not None:
        e["hp"] = hp
    if variant is not None:
        e["variant"] = variant
    return e


# ---------------------------------------------------------------------------
# Scenario 1: Exact (set_code, card_number) match
# ---------------------------------------------------------------------------
def test_exact_set_number_match():
    print("\n--- 1. Exact set+number match ---")
    collection = [make_entry("Charmander", count=2)]
    pack_sources = {("A1", 4): {"card_name": "Charmander", "rarity": "common"}}
    pz_cards = [make_pz("Charmander", count=3, set_code="A1", card_number=4)]

    results = match_pz_cards(pz_cards, collection, pack_sources, {})
    r = results[0]
    check("status=MATCHED", r.status == "MATCHED", r.status)
    check("entry name correct", r.entry.get("name") == "Charmander")
    check("canonical_name correct", r.canonical_name == "Charmander")
    check("pz count preserved", r.pz_card.count == 3)


# ---------------------------------------------------------------------------
# Scenario 2: PROMO-A override
# ---------------------------------------------------------------------------
def test_promo_a_override():
    print("\n--- 2. PROMO-A override ---")
    collection = [make_entry("Potion", count=1, card_type="Trainer")]
    pack_sources = {}  # PROMO-A not in pack_sources
    pz_cards = [make_pz("PotionXXXWrongName", count=1, set_code="PROMO-A", card_number=1)]

    results = match_pz_cards(pz_cards, collection, pack_sources, {})
    r = results[0]
    check("status=MATCHED", r.status == "MATCHED", r.status)
    check("override maps to 'Potion'", r.entry.get("name") == "Potion")


# ---------------------------------------------------------------------------
# Scenario 3: PROMO-B override
# ---------------------------------------------------------------------------
def test_promo_b_override():
    print("\n--- 3. PROMO-B override ---")
    collection = [make_entry("Zygarde 10% Forme", count=1)]
    pack_sources = {}
    pz_cards = [make_pz("Zygarde", count=1, set_code="PROMO-B", card_number=51)]

    results = match_pz_cards(pz_cards, collection, pack_sources, {})
    r = results[0]
    check("status=MATCHED", r.status == "MATCHED", r.status)
    check("override maps to 'Zygarde 10% Forme'", r.entry.get("name") == "Zygarde 10% Forme")


# ---------------------------------------------------------------------------
# Scenario 4: Direct normalized-name match (trainer not in pack_sources)
# ---------------------------------------------------------------------------
def test_direct_name_match():
    print("\n--- 4. Direct normalized-name match ---")
    collection = [make_entry("Professor's Research", count=2, card_type="Trainer")]
    pack_sources = {}
    pz_cards = [make_pz("Professor's Research", count=3, set_code="A1", card_number=999)]

    results = match_pz_cards(pz_cards, collection, pack_sources, {})
    r = results[0]
    check("status=MATCHED", r.status == "MATCHED", r.status)
    check("entry name correct", r.entry.get("name") == "Professor's Research")


# ---------------------------------------------------------------------------
# Scenario 5: NEW_CARD — card exists in PZ but not in collection
# ---------------------------------------------------------------------------
def test_new_card():
    print("\n--- 5. NEW_CARD auto-add ---")
    collection = [make_entry("Charmander", count=2)]
    pack_sources = {("B1", 7): {"card_name": "Bulbasaur", "rarity": "common"}}
    pz_cards = [make_pz("Bulbasaur", count=1, set_code="B1", card_number=7)]

    results = match_pz_cards(pz_cards, collection, pack_sources, {})
    r = results[0]
    check("status=NEW_CARD", r.status == "NEW_CARD", r.status)
    check("canonical_name set", r.canonical_name == "Bulbasaur")


# ---------------------------------------------------------------------------
# Scenario 6: Duplicate NEW_CARD dedup — same canonical from two PZ set records
# ---------------------------------------------------------------------------
def test_new_card_dedup():
    print("\n--- 6. Duplicate NEW_CARD dedup (same card, two PZ sets) ---")
    collection: list[dict] = []
    pack_sources = {
        ("A1", 1): {"card_name": "Bulbasaur", "rarity": "common"},
        ("B1", 1): {"card_name": "Bulbasaur", "rarity": "common"},
    }
    pz_cards = [
        make_pz("Bulbasaur", count=2, set_code="A1", card_number=1),
        make_pz("Bulbasaur", count=3, set_code="B1", card_number=1),
    ]

    results = match_pz_cards(pz_cards, collection, pack_sources, {})
    new_results = [r for r in results if r.status == "NEW_CARD"]
    check("both results are NEW_CARD", len(new_results) == 2, str(len(new_results)))
    check("both have canonical_name=Bulbasaur", all(r.canonical_name == "Bulbasaur" for r in new_results))

    # Simulate Phase 4b dedup logic from main():
    # Key = canonical_name.lower() + "|alt"|"|base" to keep base and alt-art separate.
    # .lower() (not _normalize) preserves Nidoran♀ vs Nidoran♂ distinction.
    _ALT_RARITIES = sc.RARE_PLUS_RARITIES  # shared production vocabulary

    def _mr_is_alt(mr: MatchResult, ps: dict) -> bool:
        pz_c = mr.pz_card
        if not (pz_c.set_code and pz_c.card_number is not None):
            return False
        ps_r = ps.get((pz_c.set_code, pz_c.card_number))
        return bool(
            ps_r
            and _normalize(ps_r.get("card_name", "")) == _normalize(mr.canonical_name or "")
            and ps_r.get("rarity") in _ALT_RARITIES
        )

    merged: dict[str, MatchResult] = {}
    for mr in new_results:
        key = mr.canonical_name.lower() + ("|alt" if _mr_is_alt(mr, pack_sources) else "|base")
        if key in merged:
            prev = merged[key]
            merged[key] = MatchResult(
                status=prev.status,
                pz_card=PZCard(
                    set_code=prev.pz_card.set_code,
                    card_number=prev.pz_card.card_number,
                    raw_name=prev.pz_card.raw_name,
                    count=prev.pz_card.count + mr.pz_card.count,
                ),
                canonical_name=prev.canonical_name,
            )
        else:
            merged[key] = mr

    check("dedup produces 1 entry", len(merged) == 1, str(len(merged)))
    merged_mr = merged["bulbasaur|base"]
    check("merged count = 5 (2+3)", merged_mr.pz_card.count == 5, str(merged_mr.pz_card.count))


# ---------------------------------------------------------------------------
# Scenario 7: Pass 2 AMBIGUOUS resolution (sibling match frees last candidate)
# ---------------------------------------------------------------------------
def test_pass2_ambiguous_resolution():
    print("\n--- 7. Pass 2: sibling match resolves AMBIGUOUS ---")
    # Two Riolu entries (hp=70 and hp=80). Two PZ records for Riolu.
    # Pass 1 can't distinguish (both unresolvable by HP if HP data is absent).
    # But: the first PZ record gets MATCHED by HP (70), leaving only one
    # candidate for the second — Pass 2 resolves it.
    collection = [
        make_entry("Riolu", count=1, hp=70),
        make_entry("Riolu", count=1, hp=80),
    ]
    ext_ref = {
        "riolu": [
            {"set_code": "A1", "number": 10, "hp": 70, "card_category": "Pokemon"},
            {"set_code": "A1", "number": 11, "hp": 80, "card_category": "Pokemon"},
        ]
    }
    pack_sources = {
        ("A1", 10): {"card_name": "Riolu", "rarity": "common"},
        ("A1", 11): {"card_name": "Riolu", "rarity": "common"},
    }
    pz_cards = [
        make_pz("Riolu", count=2, set_code="A1", card_number=10),
        make_pz("Riolu", count=3, set_code="A1", card_number=11),
    ]

    results = match_pz_cards(pz_cards, collection, pack_sources, ext_ref)
    matched = [r for r in results if r.status == "MATCHED"]
    check("both results MATCHED", len(matched) == 2, str(len(matched)))
    # hp=70 should match the pz card with card_number=10, hp=80 with card_number=11
    hp_map = {r.pz_card.card_number: r.entry.get("hp") for r in matched}
    check("card_number 10 → hp=70", hp_map.get(10) == 70, str(hp_map))
    check("card_number 11 → hp=80", hp_map.get(11) == 80, str(hp_map))


# ---------------------------------------------------------------------------
# Scenario 8: Pass 3 rarity-rank assignment (N PZ records, N collection entries)
# ---------------------------------------------------------------------------
def test_pass3_rarity_assignment():
    print("\n--- 8. Pass 3: rarity-rank assignment ---")
    # Pikachu has two variants: base (no variant) and alt art.
    # PZ returns common (base) and illustration_rare (alt).
    collection = [
        make_entry("Pikachu", count=1),                            # base
        make_entry("Pikachu", count=1, variant="alt art"),         # alt
    ]
    pack_sources = {
        ("A1", 35): {"card_name": "Pikachu", "rarity": "common"},
        ("A1", 36): {"card_name": "Pikachu", "rarity": "illustration_rare"},
    }
    pz_cards = [
        make_pz("Pikachu", count=2, set_code="A1", card_number=35),  # common → base
        make_pz("Pikachu", count=1, set_code="A1", card_number=36),  # illustration_rare → alt
    ]

    results = match_pz_cards(pz_cards, collection, pack_sources, {})
    matched = [r for r in results if r.status == "MATCHED"]
    check("both results MATCHED", len(matched) == 2, str(len(matched)))

    by_cn = {r.pz_card.card_number: r.entry for r in matched}
    base_entry = by_cn.get(35)
    alt_entry  = by_cn.get(36)
    check("common (35) → base variant", base_entry and not base_entry.get("variant"), str(base_entry))
    check("illustration_rare (36) → alt variant", alt_entry and alt_entry.get("variant") == "alt art", str(alt_entry))


# ---------------------------------------------------------------------------
# Scenario 9: AMBIGUOUS force-match WARN (more PZ records than collection entries)
# ---------------------------------------------------------------------------
def test_ambiguous_force_match():
    print("\n--- 9. AMBIGUOUS force-match with WARN ---")
    import io
    import contextlib

    # Three PZ records for a card, but only 2 collection entries.
    # Pass 3 skips the group (len(res_idxs)=3 != len(remaining)=2),
    # so the force-match loop fires for the overflow record.
    collection = [
        make_entry("Charmander", count=1, hp=60),
        make_entry("Charmander", count=1, hp=80),
    ]
    pack_sources: dict = {}  # no pack_sources for disambiguation
    pz_cards = [
        make_pz("Charmander", count=2, set_code="X1", card_number=1),
        make_pz("Charmander", count=3, set_code="X1", card_number=2),
        make_pz("Charmander", count=1, set_code="X1", card_number=3),  # no collection entry left
    ]

    stderr_capture = io.StringIO()
    with contextlib.redirect_stderr(stderr_capture):
        results = match_pz_cards(pz_cards, collection, pack_sources, {})

    # All 3 should be MATCHED: first two force-matched to available entries,
    # the overflow merged back into the first already-matched entry.
    matched = [r for r in results if r.status == "MATCHED"]
    check("all 3 results MATCHED (overflow merged into existing)", len(matched) == 3, str(len(matched)))

    warn_output = stderr_capture.getvalue()
    check("WARN printed for force-match or overflow", "WARN:" in warn_output, repr(warn_output[:200]))


# ---------------------------------------------------------------------------
# Scenario 10: consecutive_missing counter starts at 1, increments correctly
# ---------------------------------------------------------------------------
def test_consecutive_missing_counter():
    print("\n--- 10. consecutive_missing counter ---")
    import io

    with tempfile.TemporaryDirectory() as tmp:
        queue_path = Path(tmp) / "sync_review_queue.json"

        # Simulate: first run writes queue with no previous queue
        orig_review_queue = sc.REVIEW_QUEUE
        sc.REVIEW_QUEUE = queue_path

        try:
            write_review_queue([], [{"name": "Misdreavus", "count": 2}])
            q1 = json.loads(queue_path.read_text())
            missing1 = q1["missing_from_pz"][0]
            check("first missing run: consecutive=1", missing1["consecutive_missing"] == 1,
                  str(missing1["consecutive_missing"]))

            # Second run: Misdreavus still missing
            write_review_queue([], [{"name": "Misdreavus", "count": 2}])
            q2 = json.loads(queue_path.read_text())
            missing2 = q2["missing_from_pz"][0]
            check("second missing run: consecutive=2", missing2["consecutive_missing"] == 2,
                  str(missing2["consecutive_missing"]))

            # Third run: Misdreavus reappears (no longer missing)
            write_review_queue([], [])
            q3 = json.loads(queue_path.read_text())
            check("after reappear: missing_from_pz empty", q3["missing_from_pz"] == [], str(q3["missing_from_pz"]))

            # Fourth run: Misdreavus goes missing again — counter should reset to 1
            write_review_queue([], [{"name": "Misdreavus", "count": 2}])
            q4 = json.loads(queue_path.read_text())
            missing4 = q4["missing_from_pz"][0]
            check("after reset: consecutive=1 again", missing4["consecutive_missing"] == 1,
                  str(missing4["consecutive_missing"]))

        finally:
            sc.REVIEW_QUEUE = orig_review_queue


# ---------------------------------------------------------------------------
# Scenario 11: a corrupt review queue is recovered, not fatal
# ---------------------------------------------------------------------------
def test_corrupt_review_queue_recovers():
    print("\n--- 11. corrupt review queue recovery ---")
    import io
    import contextlib

    with tempfile.TemporaryDirectory() as tmp:
        queue_path = Path(tmp) / "sync_review_queue.json"
        queue_path.write_text("{ this is not valid json ", encoding="utf-8")

        orig_review_queue = sc.REVIEW_QUEUE
        sc.REVIEW_QUEUE = queue_path
        try:
            # load_review_queue must not raise; warns and falls back to resolved.
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                q = sc.load_review_queue()
            check("load_review_queue falls back to resolved", q.get("resolved") is True, str(q))
            check("load_review_queue warns on corrupt file", "WARN" in err.getvalue(),
                  err.getvalue().strip())

            # write_review_queue must complete despite the corrupt prior file,
            # resetting consecutive_missing to 1 (history unreadable).
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                write_review_queue([], [{"name": "Misdreavus", "count": 2}])
            q = json.loads(queue_path.read_text())
            missing = q["missing_from_pz"][0]
            check("write_review_queue recovers, consecutive=1",
                  missing["consecutive_missing"] == 1, str(missing["consecutive_missing"]))
            check("write_review_queue warns on corrupt prior", "WARN" in err.getvalue(),
                  err.getvalue().strip())
        finally:
            sc.REVIEW_QUEUE = orig_review_queue


# ---------------------------------------------------------------------------
# Scenario 12: overflow/force matches surface via extract_ambiguous_matches
# ---------------------------------------------------------------------------
def test_extract_ambiguous_matches():
    print("\n--- 12. extract_ambiguous_matches surfaces fallback matches ---")
    import io
    import contextlib

    # Same setup as scenario 9: 3 PZ records, 2 collection entries → one overflow.
    collection = [
        make_entry("Charmander", count=1, hp=60),
        make_entry("Charmander", count=1, hp=80),
    ]
    pz_cards = [
        make_pz("Charmander", count=2, set_code="X1", card_number=1),
        make_pz("Charmander", count=3, set_code="X1", card_number=2),
        make_pz("Charmander", count=1, set_code="X1", card_number=3),  # overflow
    ]

    with contextlib.redirect_stderr(io.StringIO()):
        results = match_pz_cards(pz_cards, collection, {}, {})

    # Existing merge behavior unchanged: still 3 MATCHED.
    matched = [r for r in results if r.status == "MATCHED"]
    check("merge behavior unchanged (3 MATCHED)", len(matched) == 3, str(len(matched)))

    ambiguous = sc.extract_ambiguous_matches(results)
    reasons = {a["reason"] for a in ambiguous}
    check("at least one ambiguous match surfaced", len(ambiguous) >= 1, str(ambiguous))
    check("overflow_merged reason present", "overflow_merged" in reasons, str(reasons))
    overflow = next(a for a in ambiguous if a["reason"] == "overflow_merged")
    check("overflow carries coords", overflow["set_code"] == "X1" and overflow["card_number"] == 3,
          str(overflow))
    check("overflow carries count", overflow["count"] == 1, str(overflow["count"]))


# ---------------------------------------------------------------------------
# Scenario 13: ambiguous_matches written to queue with consecutive_unresolved
# ---------------------------------------------------------------------------
def test_ambiguous_queue_counter():
    print("\n--- 13. ambiguous_matches queue + consecutive_unresolved ---")
    with tempfile.TemporaryDirectory() as tmp:
        queue_path = Path(tmp) / "sync_review_queue.json"
        orig_review_queue = sc.REVIEW_QUEUE
        sc.REVIEW_QUEUE = queue_path
        try:
            amb = [{"set_code": "B1", "card_number": 208, "canonical_name": "Furfrou",
                    "count": 1, "reason": "overflow_merged"}]

            write_review_queue([], [], amb)
            q1 = json.loads(queue_path.read_text())
            check("ambiguous_matches populated", len(q1["ambiguous_matches"]) == 1,
                  str(q1["ambiguous_matches"]))
            check("first run: consecutive_unresolved=1",
                  q1["ambiguous_matches"][0]["consecutive_unresolved"] == 1,
                  str(q1["ambiguous_matches"][0]))
            # Guardrail: overflow/force-match alone (no new cards) must gate the
            # next run, so run_recommendations surfaces it instead of burying in stderr.
            check("ambiguous-only queue is unresolved", q1["resolved"] is False, str(q1))

            write_review_queue([], [], amb)
            q2 = json.loads(queue_path.read_text())
            check("second run: consecutive_unresolved=2",
                  q2["ambiguous_matches"][0]["consecutive_unresolved"] == 2,
                  str(q2["ambiguous_matches"][0]))

            # Resolved (no longer ambiguous) → counter clears.
            write_review_queue([], [], [])
            q3 = json.loads(queue_path.read_text())
            check("after resolve: ambiguous_matches empty", q3["ambiguous_matches"] == [],
                  str(q3["ambiguous_matches"]))
            check("clean queue is resolved", q3["resolved"] is True, str(q3))
        finally:
            sc.REVIEW_QUEUE = orig_review_queue


# ---------------------------------------------------------------------------
# Scenario 14: a new printing of an owned card (coord-bearing entries) becomes a
# NEW_CARD, not an overflow-merge onto a sibling printing.
# ---------------------------------------------------------------------------
def test_new_printing_of_owned_card_is_new_not_overflow():
    print("\n--- 14. New printing of owned card → NEW_CARD ---")
    import io
    import contextlib

    # Own two Sableye printings (with coords); PZ also reports a third (A3:70).
    collection = [
        {**make_entry("Sableye", count=2), "set_code": "B3a", "card_number": 40},
        {**make_entry("Sableye", count=5), "set_code": "PROMO-B", "card_number": 70},
    ]
    pack_sources = {
        ("A3", 70): {"card_name": "Sableye", "rarity": "uncommon"},
        ("B3A", 40): {"card_name": "Sableye", "rarity": "uncommon"},
        ("PROMO-B", 70): {"card_name": "Sableye", "rarity": "promo"},
    }
    pz_cards = [
        make_pz("Sableye", count=2, set_code="B3A", card_number=40),
        make_pz("Sableye", count=5, set_code="PROMO-B", card_number=70),
        make_pz("Sableye", count=1, set_code="A3", card_number=70),  # new printing
    ]

    with contextlib.redirect_stderr(io.StringIO()):
        results = match_pz_cards(pz_cards, collection, pack_sources, {})

    by_coord = {(r.pz_card.set_code, r.pz_card.card_number): r for r in results}
    a3 = by_coord[("A3", 70)]
    check("A3:70 is NEW_CARD (not overflow)", a3.status == "NEW_CARD", a3.status)
    check("A3:70 not overflow_merged", a3.match_note != "overflow_merged", str(a3.match_note))
    check("B3a:40 matched its own entry", by_coord[("B3A", 40)].status == "MATCHED")
    check("PROMO-B:70 matched its own entry", by_coord[("PROMO-B", 70)].status == "MATCHED")


# ---------------------------------------------------------------------------
# Run all scenarios
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("  Sync matching simulation")
    print("=" * 60)

    test_exact_set_number_match()
    test_promo_a_override()
    test_promo_b_override()
    test_direct_name_match()
    test_new_card()
    test_new_card_dedup()
    test_pass2_ambiguous_resolution()
    test_pass3_rarity_assignment()
    test_ambiguous_force_match()
    test_consecutive_missing_counter()
    test_corrupt_review_queue_recovers()
    test_extract_ambiguous_matches()
    test_ambiguous_queue_counter()
    test_new_printing_of_owned_card_is_new_not_overflow()

    print()
    if _failures:
        print(f"FAILED: {len(_failures)} scenario(s)")
        for f in _failures:
            print(f"  - {f}")
        sys.exit(1)
    else:
        print(f"ALL PASSED — {14 - len(_failures)} / 14 scenarios")
        sys.exit(0)
