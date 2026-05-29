#!/usr/bin/env python3
"""
New-pack integration test orchestrator.

Validates that the pipeline handles new packs gracefully by running two gates
against a randomly selected (or explicitly named) victim pack:

  Gate 1 — Delete/Restore: removes victim from all reference data, confirms the
            pipeline still runs cleanly, then restores and verifies byte-identical output.

  Gate 2 — Sync Simulation: removes victim from pack_sources, feeds synthetic
            PZ-format JSON (from simulate_pack_opens.py) through the sync pipeline,
            and confirms correct behavior at each stage.

Once both gates pass with several different seeds, you can safely add a new pack
to the reference data with confidence the system handles it correctly.

Usage:
  python3 scripts/run_new_pack_test.py                        # random victim
  python3 scripts/run_new_pack_test.py --seed 42              # reproducible random victim
  python3 scripts/run_new_pack_test.py --pack triumphant-light  # fixed victim
  python3 scripts/run_new_pack_test.py --gate 1               # Gate 1 only
  python3 scripts/run_new_pack_test.py --gate 2               # Gate 2 only
"""

import argparse
import json
import random
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT             = Path(__file__).resolve().parent.parent
PZ_PACK_ODDS     = ROOT / "data" / "reference" / "pz_pack_odds.json"
PULL_MODEL       = ROOT / "data" / "reference" / "pull_probability_model.json"
PACK_SOURCES     = ROOT / "data" / "reference" / "pack_sources.json"
PACK_EV          = ROOT / "data" / "current" / "pack_ev.json"
COLLECTION       = ROOT / "collection.json"
SIMULATE_SCRIPT  = ROOT / "scripts" / "simulate_pack_opens.py"
RUN_PIPELINE     = ROOT / "scripts" / "run_recommendations.py"
SYNC_SCRIPT      = ROOT / "scripts" / "sync_collection.py"
VALIDATE_SCRIPT  = ROOT / "scripts" / "validate_current_collection.py"


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def _log(msg: str = "") -> None:
    print(msg)


def _section(title: str) -> None:
    _log()
    _log("─" * 64)
    _log(f"  {title}")
    _log("─" * 64)


def _run(cmd: list) -> subprocess.CompletedProcess:
    _log(f"  $ {' '.join(str(c) for c in cmd)}")
    return subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)


def _git_restore(*rel_paths: str) -> None:
    subprocess.run(["git", "checkout", "--", *rel_paths], cwd=ROOT, check=True)


# ---------------------------------------------------------------------------
# Pack helpers
# ---------------------------------------------------------------------------

def _variant(pack_name: str) -> str:
    """'Genetic Apex: Charizard' → 'Charizard'; 'Fantastical Parade' → 'Fantastical Parade'"""
    return pack_name.split(": ", 1)[1] if ": " in pack_name else pack_name


def _sibling_slugs(victim_slug: str, expansion_id: str, pz_data: dict) -> list[str]:
    return [
        s for s, info in pz_data.items()
        if info.get("expansion_id") == expansion_id
        and s != victim_slug
    ]


def _pack_in_ev(ev_path: Path, expansion_id: str, variant_name: str, is_single_pack: bool) -> bool:
    """
    Return True if the victim pack appears in pack_ev.json.

    pz_pack_odds uses expansion names (e.g. "Triumphant Light") while pack_ev / pull_model
    use the legendary Pokémon name (e.g. "Arceus").  For single-pack expansions the set_code
    is the unambiguous identifier, so we skip the pack_name comparison entirely.  For multi-pack
    expansions the variant extracted from "Expansion: Variant" matches the pack_name in pack_ev.
    """
    data  = json.loads(ev_path.read_bytes())
    packs = data.get("packs", [])
    for p in packs:
        if p.get("set_code", "").upper() != expansion_id.upper():
            continue
        if is_single_pack:
            return True   # set_code uniquely identifies a single-pack expansion
        if p.get("pack_name", "") == variant_name:
            return True
    return False


def _ev_packs_equal(ev_path: Path, baseline_data: dict) -> bool:
    """Compare pack EV data ignoring time-varying top-level fields (generated_at etc.)."""
    current = json.loads(ev_path.read_bytes())
    for key in ("packs", "scoring_weights", "confidence_weights", "deck_targets",
                "overall_summary", "blocked_packs", "next_steps"):
        if current.get(key) != baseline_data.get(key):
            return False
    return True


# ---------------------------------------------------------------------------
# Check / failure
# ---------------------------------------------------------------------------

class GateFailure(Exception):
    pass


def _check(condition: bool, label: str) -> None:
    status = "PASS" if condition else "FAIL"
    _log(f"  [{status}] {label}")
    if not condition:
        raise GateFailure(label)


# ---------------------------------------------------------------------------
# Victim selection
# ---------------------------------------------------------------------------

def select_victim(pack_slug: str | None, seed: int | None, pz_data: dict) -> tuple[str, dict]:
    non_promo = sorted(
        s for s, info in pz_data.items()
        if not info.get("expansion_id", "").upper().startswith("PROMO")
    )
    if pack_slug:
        if pack_slug not in pz_data:
            print(f"ERROR: unknown pack slug '{pack_slug}'")
            print(f"  Available: {', '.join(non_promo)}")
            sys.exit(1)
        return pack_slug, pz_data[pack_slug]
    rng = random.Random(seed)
    slug = rng.choice(non_promo)
    return slug, pz_data[slug]


# ---------------------------------------------------------------------------
# Reference-data mutations
# ---------------------------------------------------------------------------

def _remove_from_pz_pack_odds(victim_slug: str) -> None:
    data = json.loads(PZ_PACK_ODDS.read_text(encoding="utf-8"))
    data.pop(victim_slug, None)
    PZ_PACK_ODDS.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    _log(f"  pz_pack_odds: removed slug '{victim_slug}'")


def _remove_from_pull_model(expansion_id: str, variant_name: str, is_single_pack: bool) -> None:
    """
    Remove the victim's entry from pull_probability_model.json.

    Single-pack expansions match by set_code only (naming differs between pz_pack_odds and pull_model).
    Multi-pack expansions match by set_code + pack_name variant (names are consistent).
    """
    raw   = json.loads(PULL_MODEL.read_text(encoding="utf-8"))
    packs = raw.get("packs", raw) if isinstance(raw, dict) else raw

    def _matches(p: dict) -> bool:
        sc = p.get("set_code", "").upper()
        if sc != expansion_id.upper():
            return False
        return True if is_single_pack else p.get("pack_name", "") == variant_name

    filtered = [p for p in packs if not _matches(p)]
    removed  = len(packs) - len(filtered)
    _log(f"  pull_model  : removed {removed} entr{'y' if removed==1 else 'ies'} for {expansion_id}/{variant_name}")

    if isinstance(raw, dict):
        raw["packs"] = filtered
        PULL_MODEL.write_text(json.dumps(raw, indent=2, ensure_ascii=False), encoding="utf-8")
    else:
        PULL_MODEL.write_text(json.dumps(filtered, indent=2, ensure_ascii=False), encoding="utf-8")


def _remove_from_pack_sources(expansion_id: str, variant_name: str, is_single_pack: bool) -> None:
    raw     = json.loads(PACK_SOURCES.read_text(encoding="utf-8"))
    records = raw.get("records", raw) if isinstance(raw, dict) else raw

    def _drop(r: dict) -> bool:
        sc = str(r.get("set_code", "")).upper()
        pn = r.get("pack_name")
        if sc != expansion_id.upper():
            return False
        # Single-pack: drop all records for this set_code.
        # Multi-pack: drop only pack-specific records; keep shared (pack_name=None) and sibling records.
        return True if is_single_pack else pn == variant_name

    kept    = [r for r in records if not _drop(r)]
    removed = len(records) - len(kept)
    _log(f"  pack_sources: removed {removed} record(s) for {expansion_id}/{variant_name}")

    if isinstance(raw, dict):
        raw["records"] = kept
        PACK_SOURCES.write_text(json.dumps(raw, indent=2, ensure_ascii=False), encoding="utf-8")
    else:
        PACK_SOURCES.write_text(json.dumps(kept, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------------------
# Gate 1: Delete / Restore
# ---------------------------------------------------------------------------

def run_gate1(victim_slug: str, pack_info: dict, pz_data: dict) -> None:
    _section("GATE 1: Delete / Restore Cycle")

    expansion_id = pack_info["expansion_id"]
    pack_name    = pack_info["pack_name"]
    variant      = _variant(pack_name)
    siblings     = _sibling_slugs(victim_slug, expansion_id, pz_data)
    is_single    = len(siblings) == 0

    _log(f"  Victim  : {pack_name}  (expansion={expansion_id}, slug={victim_slug})")
    _log(f"  Siblings: {[pz_data[s]['pack_name'] for s in siblings] or '— single-pack expansion'}")

    # Step 1: Baseline
    _log("\n[1/5] Capturing baseline pipeline output...")
    r = _run(["python3", str(RUN_PIPELINE), "--skip-sync"])
    _check(r.returncode == 0, "Baseline pipeline exits 0")
    baseline_ev      = PACK_EV.read_bytes()
    baseline_ev_data = json.loads(baseline_ev)

    try:
        # Step 2: Delete victim from reference files
        _log("\n[2/5] Removing victim from all reference data...")
        _remove_from_pz_pack_odds(victim_slug)
        _remove_from_pull_model(expansion_id, variant, is_single)
        _remove_from_pack_sources(expansion_id, variant, is_single)

        # Step 3: Run pipeline with pack missing
        _log("\n[3/5] Running pipeline with victim pack removed...")
        r = _run(["python3", str(RUN_PIPELINE), "--skip-sync"])
        _check(r.returncode == 0, "Pipeline exits 0 with pack missing (no crash)")

        _check(
            not _pack_in_ev(PACK_EV, expansion_id, variant, is_single),
            f"Victim '{variant}' absent from pack_ev.json after deletion",
        )
        if siblings:
            all_siblings_present = all(
                _pack_in_ev(PACK_EV, expansion_id, _variant(pz_data[s]["pack_name"]), False)
                for s in siblings
            )
            _check(all_siblings_present, "All sibling packs still present in pack_ev.json")

        r2 = _run(["python3", str(VALIDATE_SCRIPT)])
        _check(r2.returncode == 0, "Collection validates correctly while pack is missing")

    finally:
        # Step 4: Restore
        _log("\n[4/5] Restoring reference data via git checkout...")
        _git_restore("data/reference/")

    # Step 5: Verify byte-identical restore
    _log("\n[5/5] Re-running pipeline and verifying byte-identical output...")
    r = _run(["python3", str(RUN_PIPELINE), "--skip-sync"])
    _check(r.returncode == 0, "Pipeline exits 0 after restore")
    _check(
        _ev_packs_equal(PACK_EV, baseline_ev_data),
        "pack_ev.json pack data is identical to pre-deletion baseline (excluding timestamps)",
    )

    _log("\n  ✓ GATE 1 PASSED")


# ---------------------------------------------------------------------------
# Gate 2: Sync Simulation
# ---------------------------------------------------------------------------

def run_gate2(victim_slug: str, pack_info: dict, pz_data: dict, seed: int | None) -> None:
    _section("GATE 2: Pack Opening Simulation + Sync")

    expansion_id = pack_info["expansion_id"]
    pack_name    = pack_info["pack_name"]
    variant      = _variant(pack_name)
    siblings     = _sibling_slugs(victim_slug, expansion_id, pz_data)
    is_single    = len(siblings) == 0

    _log(f"  Victim: {pack_name}  (expansion={expansion_id}, seed={seed})")

    collection_backup   = COLLECTION.read_bytes()
    review_queue_path   = ROOT / "data" / "sync" / "sync_review_queue.json"
    review_queue_backup = review_queue_path.read_bytes()
    sim_path: str | None = None

    try:
        # Step 1: Remove from pack_sources only (simulates "new pack not yet in our reference data")
        _log("\n[1/7] Removing victim from pack_sources (simulating pack not yet in reference data)...")
        _remove_from_pack_sources(expansion_id, variant, is_single)

        # Step 2: Generate synthetic PZ JSON
        _log("\n[2/7] Generating synthetic PZ JSON (5 simulated pack opens)...")
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            sim_path = tf.name

        sim_cmd = ["python3", str(SIMULATE_SCRIPT), "--pack", victim_slug, "--count", "5"]
        if seed is not None:
            sim_cmd += ["--seed", str(seed)]
        sim_cmd += ["--output", sim_path]

        r = _run(sim_cmd)
        _check(r.returncode == 0, "simulate_pack_opens.py exits 0")

        sim_records = json.loads(Path(sim_path).read_text(encoding="utf-8"))
        _check(len(sim_records) > 0, f"Synthetic JSON non-empty ({len(sim_records)} records)")

        # Step 3: Dry-run sync
        _log("\n[3/7] Dry-run sync (preview diff without writing)...")
        r = _run(["python3", str(SYNC_SCRIPT), "--json-import", sim_path, "--dry-run"])
        _check(r.returncode in (0, 1, 2), f"Sync dry-run returns a recognized exit code (got {r.returncode})")
        _log(r.stdout.strip() if r.stdout.strip() else "  (no stdout)")

        # Step 4: Apply sync
        _log("\n[4/7] Applying sync...")
        r = _run(["python3", str(SYNC_SCRIPT), "--json-import", sim_path, "--force"])
        _check(
            r.returncode in (0, 2),
            f"Sync exits 0 (clean) or 2 (partial — review queue with new cards); got {r.returncode}",
        )

        # Step 5: Validate collection after sync
        _log("\n[5/7] Validating collection integrity post-sync...")
        r = _run(["python3", str(VALIDATE_SCRIPT)])
        _check(r.returncode == 0, "Collection validates correctly after sync")

        # Step 6: Run pipeline — pack_sources missing but EV still computed from pz_pack_odds
        # Note: pack_sources only affects sync card-matching, NOT EV computation.
        # The pack should still appear in pack_ev.json because pz_pack_odds was not changed.
        _log("\n[6/7] Running pipeline with pack_sources missing (EV still computes from pz_pack_odds)...")
        r = _run(["python3", str(RUN_PIPELINE), "--skip-sync"])
        _check(r.returncode == 0, "Pipeline exits 0 without victim in pack_sources")
        _check(
            _pack_in_ev(PACK_EV, expansion_id, variant, is_single),
            f"Victim '{variant}' still in pack_ev.json (pack_sources doesn't affect EV — expected)",
        )

    finally:
        # Always restore all three modified resources — runs on success, GateFailure, and any
        # unexpected exception (OSError, KeyboardInterrupt, etc.) so nothing leaks.
        # _git_restore is wrapped so that a git failure doesn't skip the in-memory restores.
        _log("\n  Restoring pack_sources, collection.json, and review queue...")
        try:
            _git_restore("data/reference/pack_sources.json")
        except subprocess.CalledProcessError as e:
            _log(f"  WARNING: git restore failed — pack_sources.json may be dirty: {e}")
        COLLECTION.write_bytes(collection_backup)
        review_queue_path.write_bytes(review_queue_backup)
        if sim_path:
            Path(sim_path).unlink(missing_ok=True)

    # Step 7: Re-run pipeline and final validation (only reached on success path)
    _log("\n[7/7] Regenerating pipeline outputs from restored collection...")

    r = _run(["python3", str(RUN_PIPELINE), "--skip-sync"])
    _check(r.returncode == 0, "Pipeline exits 0 after collection restore")

    r = _run(["python3", str(VALIDATE_SCRIPT)])
    _check(r.returncode == 0, "Collection validates correctly after full restore")

    _log("\n  ✓ GATE 2 PASSED")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="New-pack integration test: verify pipeline handles new packs correctly."
    )
    parser.add_argument("--pack", help="Fixed victim pack slug (skips random selection)")
    parser.add_argument("--seed", type=int, help="Random seed for victim selection and simulation")
    parser.add_argument("--gate", type=int, choices=[1, 2], help="Run only Gate 1 or Gate 2 (default: both)")
    args = parser.parse_args()

    pz_data = json.loads(PZ_PACK_ODDS.read_text(encoding="utf-8"))
    victim_slug, pack_info = select_victim(args.pack, args.seed, pz_data)

    expansion_id = pack_info["expansion_id"]
    variant      = _variant(pack_info["pack_name"])
    siblings     = _sibling_slugs(victim_slug, expansion_id, pz_data)

    _log()
    _log("=" * 64)
    _log("  NEW PACK INTEGRATION TEST")
    _log("=" * 64)
    _log(f"  Victim     : {pack_info['pack_name']}")
    _log(f"  Expansion  : {expansion_id}  ({pack_info['card_count']} cards in pack pool)")
    _log(f"  Pack type  : {'single-pack expansion' if not siblings else f'multi-pack expansion ({len(siblings)+1} packs total)'}")
    _log(f"  Seed       : {args.seed}")

    failures: list[str] = []

    if args.gate in (None, 1):
        try:
            run_gate1(victim_slug, pack_info, pz_data)
        except GateFailure as exc:
            _log(f"\n  ✗ GATE 1 FAILED: {exc}")
            _log("  Attempting reference data restore...")
            try:
                _git_restore("data/reference/")
                _log("  Reference data restored.")
            except Exception as rerr:
                _log(f"  WARNING: restore failed: {rerr}")
            failures.append(f"Gate 1: {exc}")

    if args.gate in (None, 2):
        try:
            run_gate2(victim_slug, pack_info, pz_data, args.seed)
        except GateFailure as exc:
            _log(f"\n  ✗ GATE 2 FAILED: {exc}")
            # run_gate2's finally block already restored pack_sources, collection.json,
            # and sync_review_queue.json before the exception propagated here.
            failures.append(f"Gate 2: {exc}")

    _log()
    _log("=" * 64)
    if failures:
        _log("  RESULT: FAILED")
        for f in failures:
            _log(f"    ✗ {f}")
        _log("=" * 64)
        _log()
        sys.exit(1)
    else:
        _log("  RESULT: ALL GATES PASSED")
        _log(f"  Victim: {pack_info['pack_name']}  (seed={args.seed})")
        _log("=" * 64)
        _log()


if __name__ == "__main__":
    main()
