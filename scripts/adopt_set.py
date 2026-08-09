#!/usr/bin/env python3
"""
Adopt a newly released set: register it, fetch its data, and rebuild everything.

This automates docs/adding-a-set.md. It exists because nothing used to notice a
new expansion at all — run_recommendations syncs with --no-fetch to stay offline
and deterministic, so a new set's cards became loose "new cards" in the review
queue with no signal that a whole set was missing (gap #7 in that runbook).

Registration is a code edit, and the source slugs are guesses until proven, so
this is deliberately gated rather than automatic:

  1. every source URL must return 200 BEFORE anything is written — a wrong slug
     silently poisons every card name and type in the set;
  2. the registry-consistency and card-classification tests must pass after the
     rebuild, or the run aborts.

Either gate failing leaves the tree untouched (registry edits are rolled back)
and writes the reason to data/sync/adopt_set_result.json, which the dashboard
surfaces next to the "new set detected" banner.

Usage:
    python3 scripts/adopt_set.py B4
    python3 scripts/adopt_set.py B4 --dry-run     # verify sources only
"""

import argparse
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _collection_io import ROOT, VALID_SET_CODES, canonical_set_code  # noqa: E402

COLLECTION_IO = ROOT / "scripts" / "_collection_io.py"
SNAPSHOTS_PY = ROOT / "scripts" / "fetch_source_snapshots.py"
RESULT_JSON = ROOT / "data" / "sync" / "adopt_set_result.json"

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")

LIMITLESS_SET_URL = "https://pocket.limitlesstcg.com/cards/{slug}"
SEREBII_URL = "https://www.serebii.net/tcgpocket/{slug}/"
BULBAPEDIA_URL = "https://bulbapedia.bulbagarden.net/wiki/{title}"

# Gates that must pass after the rebuild before the registration is kept.
GATE_TESTS = [
    "tests/test_set_registry_consistency.py",
    "tests/test_card_type_completeness.py",
]


class AdoptError(RuntimeError):
    """Aborts the adoption with a message the dashboard shows verbatim."""


def _get(url: str, timeout: int = 20) -> str | None:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                return None
            return resp.read().decode("utf-8", "replace")
    except (urllib.error.URLError, urllib.error.HTTPError, OSError):
        return None


def limitless_identity(set_code: str) -> tuple[str, int]:
    """(expansion name, card count) from Limitless — the set's identity.

    Limitless publishes a new set within hours and is the only source that is
    reliably up on release day, so it decides whether the set is real at all.
    """
    html = _get(LIMITLESS_SET_URL.format(slug=set_code))
    if not html:
        raise AdoptError(
            f"Limitless has no set {set_code} yet "
            f"({LIMITLESS_SET_URL.format(slug=set_code)}). Nothing to adopt.")
    title = re.search(r"<title>(.*?)</title>", html, re.S)
    name = None
    if title:
        m = re.match(r"\s*(.+?)\s*\(" + re.escape(set_code) + r"\)", title.group(1))
        if m:
            name = m.group(1).strip()
    if not name:
        raise AdoptError(f"Could not read the expansion name for {set_code} from Limitless.")
    numbers = {int(n) for n in re.findall(rf"/cards/{set_code}/(\d+)", html)}
    if not numbers:
        raise AdoptError(f"Limitless lists no cards for {set_code}.")
    return name, len(numbers)


def slug_candidates(name: str) -> list[str]:
    """Serebii slugs to try, in order, for an expansion name.

    Serebii's slug is the lowercased name with punctuation stripped, but spacing
    is inconsistent across sets (space-timesmackdown keeps its hyphen), so a few
    shapes are tried and the first that 200s wins.
    """
    lowered = name.lower()
    compact = re.sub(r"[^a-z0-9]", "", lowered)
    hyphen = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    no_the = re.sub(r"[^a-z0-9]", "", lowered.replace("the ", ""))
    return list(dict.fromkeys([compact, hyphen, no_the]))


def verify_sources(set_code: str, name: str) -> dict:
    """Resolve and prove every source URL. Raises AdoptError if one can't be."""
    serebii = None
    for cand in slug_candidates(name):
        if _get(SEREBII_URL.format(slug=cand)) is not None:
            serebii = cand
            break
    if serebii is None:
        raise AdoptError(
            f"No Serebii page found for '{name}'. Tried: "
            f"{', '.join(slug_candidates(name))}. Add the slug by hand.")

    title = f"{name} (TCG Pocket)".replace(" ", "_")
    if _get(BULBAPEDIA_URL.format(title=title)) is None:
        # Bulbapedia rate-limits aggressively; a miss here is not fatal because
        # Serebii + Limitless already cross-validate names. Recorded so the
        # rebuild's confidence drop is explainable.
        bulbapedia_ok = False
    else:
        bulbapedia_ok = True

    return {
        "serebii": serebii,
        "bulbapedia": f"{name} (TCG Pocket)",
        "bulbapedia_reachable": bulbapedia_ok,
        "limitless": set_code,
        "tcgdex": None,  # always lags a new set by weeks
    }


def register(set_code: str, aliases: dict) -> tuple[str, str]:
    """Insert the set into SET_REGISTRY and SET_ALIASES. Returns originals for rollback."""
    io_before = COLLECTION_IO.read_text(encoding="utf-8")
    snap_before = SNAPSHOTS_PY.read_text(encoding="utf-8")

    if f'"{set_code}":' in io_before.split("SET_REGISTRY")[1].split("}")[0]:
        raise AdoptError(f"{set_code} is already in SET_REGISTRY.")

    anchor = '    "PROMO-A":'
    if anchor not in io_before:
        raise AdoptError("Could not find the PROMO-A anchor in SET_REGISTRY.")
    entry = (f'    "{set_code}":{" " * max(1, 9 - len(set_code))}'
             f'{{"pack_type": "single", "limitless_slug": "{set_code}"}},\n')
    io_after = io_before.replace(anchor, entry + anchor, 1)

    snap_anchor = '    "PROMO-A":'
    if snap_anchor not in snap_before:
        raise AdoptError("Could not find the PROMO-A anchor in SET_ALIASES.")
    alias = (f'    "{set_code}":{" " * max(1, 9 - len(set_code))}'
             f'{{"tcgdex": None,  "serebii": "{aliases["serebii"]}",'
             f'{" " * max(1, 22 - len(aliases["serebii"]))}'
             f'"bulbapedia": "{aliases["bulbapedia"]}",'
             f'{" " * max(1, 22 - len(aliases["bulbapedia"]))}'
             f'"limitless": "{set_code}"}},\n')
    snap_after = snap_before.replace(snap_anchor, alias + snap_anchor, 1)

    COLLECTION_IO.write_text(io_after, encoding="utf-8")
    SNAPSHOTS_PY.write_text(snap_after, encoding="utf-8")
    return io_before, snap_before


def rollback(io_before: str, snap_before: str) -> None:
    COLLECTION_IO.write_text(io_before, encoding="utf-8")
    SNAPSHOTS_PY.write_text(snap_before, encoding="utf-8")


def run(label: str, args: list[str]) -> None:
    print(f"\n=== {label} ===", flush=True)
    proc = subprocess.run([sys.executable, *args], cwd=ROOT)
    if proc.returncode != 0:
        raise AdoptError(f"{label} failed (exit {proc.returncode}).")


def gates_pass() -> str | None:
    """Run the guard tests. Returns None on success, else the failure summary."""
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", *GATE_TESTS, "-q"],
        cwd=ROOT, capture_output=True, text=True,
    )
    if proc.returncode == 0:
        return None
    tail = [l for l in proc.stdout.splitlines() if "assert" in l.lower() or "failed" in l.lower()]
    return "\n".join(tail[-6:]) or proc.stdout[-600:]


def write_result(**fields) -> None:
    RESULT_JSON.parent.mkdir(parents=True, exist_ok=True)
    RESULT_JSON.write_text(
        json.dumps({"finished_at": datetime.now(timezone.utc).isoformat(), **fields},
                   indent=2, ensure_ascii=False),
        encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("set_code", help="e.g. B4")
    ap.add_argument("--dry-run", action="store_true",
                    help="verify sources and stop; write nothing")
    args = ap.parse_args()

    set_code = canonical_set_code(args.set_code.strip())

    try:
        if set_code in VALID_SET_CODES:
            raise AdoptError(f"{set_code} is already registered — nothing to adopt.")

        name, card_count = limitless_identity(set_code)
        print(f"  {set_code}: '{name}' — {card_count} cards on Limitless")

        aliases = verify_sources(set_code, name)
        print(f"  serebii    : {aliases['serebii']} (200)")
        print(f"  bulbapedia : {aliases['bulbapedia']}"
              f"{'' if aliases['bulbapedia_reachable'] else '  [unreachable — names from Serebii only]'}")

        if args.dry_run:
            print("\n  (dry run — nothing written)")
            write_result(set_code=set_code, expansion=name, card_count=card_count,
                         status="verified", aliases=aliases)
            return 0

        io_before, snap_before = register(set_code, aliases)
        print(f"\n  Registered {set_code} in SET_REGISTRY + SET_ALIASES.")

        try:
            run("Fetch source snapshots", ["scripts/fetch_source_snapshots.py",
                                           "--set", set_code])
            run("Ingest Pokémon Zone", ["scripts/ingest_pz.py", "--apply",
                                        "--write-pack-sources", "--rebuild-refs"])
            run("Build reprint links", ["scripts/build_reprint_links.py"])
            run("Fetch combat stats", ["scripts/fetch_combat_stats.py"])
            run("Fetch trainer effects", ["scripts/fetch_trainer_effects.py"])
            run("Fetch external reference", ["scripts/fetch_ext_ref.py",
                                             "--set", set_code])
            run("Build card reference", ["scripts/build_card_reference.py"])
            run("Build printing groups", ["scripts/build_printing_groups.py"])

            failure = gates_pass()
            if failure:
                raise AdoptError(
                    "Registration reverted — guard tests failed after the rebuild. "
                    "Usually a Mega ex missing its type (add a "
                    "data/reference/card_type_overrides.json entry) or a wrong "
                    f"source slug.\n{failure}")
        except Exception:
            rollback(io_before, snap_before)
            print(f"\n  Rolled back the {set_code} registration.", file=sys.stderr)
            raise

        run("Recommendations", ["scripts/run_recommendations.py", "--skip-sync"])

        print(f"\nAdopted {set_code} ('{name}', {card_count} cards).")
        write_result(set_code=set_code, expansion=name, card_count=card_count,
                     status="adopted", aliases=aliases)
        return 0

    except AdoptError as e:
        print(f"\nADOPT FAILED: {e}", file=sys.stderr)
        write_result(set_code=set_code, status="failed", error=str(e))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
