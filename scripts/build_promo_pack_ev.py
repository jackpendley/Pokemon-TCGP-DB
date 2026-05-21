"""
build_promo_pack_ev.py — Compute EV for promo packs using PZ direct drop chances.

Promo packs use Shop Tokens (not Hourglasses), so results are a separate ranking
from the regular pack EV. Output: data/current/promo_pack_ev.json

Reads:
  data/reference/pz_pack_odds.json       — PZ direct drop chances (all 45 packs)
  data/reference/pack_sources.json       — PROMO card name mappings
  data/current/collection_normalized.json

Outputs:
  data/current/promo_pack_ev.json
  review/promo_pack_ev.md
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PZ_PACK_ODDS_JSON  = ROOT / "data" / "reference" / "pz_pack_odds.json"
PACK_SOURCES_JSON  = ROOT / "data" / "reference" / "pack_sources.json"
COLLECTION_JSON    = ROOT / "data" / "current"   / "collection_normalized.json"
OUT_JSON           = ROOT / "data" / "current"   / "promo_pack_ev.json"
OUT_MD             = ROOT / "review"             / "promo_pack_ev.md"

SCORING_WEIGHTS = {
    "new_card":     1.0,
    "copy_up_to_2": 0.4,
    "ex_missing":   1.0,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _norm(name: str) -> str:
    return name.lower().replace("’", "'").replace("‘", "'").strip()


def value_of_next_copy(owned: int, is_ex: bool) -> float:
    if owned >= 2:
        return 0.0
    if owned == 0:
        v = SCORING_WEIGHTS["new_card"]
        if is_ex:
            v += SCORING_WEIGHTS["ex_missing"]
        return v
    # owned == 1: second copy
    v = SCORING_WEIGHTS["copy_up_to_2"]
    if is_ex:
        v += SCORING_WEIGHTS["ex_missing"]
    return v


def load_collection(path: Path) -> dict[str, int]:
    """Returns {normalized_name: owned_count}."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    result: dict[str, int] = {}
    for e in raw.get("collection", []):
        name = _norm(e.get("name", ""))
        result[name] = result.get(name, 0) + e.get("count", 0)
    return result


def load_promo_ps_index(path: Path) -> dict[tuple, dict]:
    """Returns {(SET_CODE_UPPER, card_number): pack_sources_record} for PROMO entries."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    records = raw.get("records", raw) if isinstance(raw, dict) else raw
    idx: dict[tuple, dict] = {}
    for r in records:
        sc = r.get("set_code", "").upper()
        if sc.startswith("PROMO"):
            cn = r.get("card_number")
            if cn is not None:
                idx[(sc, cn)] = r
    return idx


# ---------------------------------------------------------------------------
# Core calculation
# ---------------------------------------------------------------------------

def compute_promo_pack_ev(slug: str, pack_data: dict, collection: dict[str, int],
                          ps_idx: dict[tuple, dict]) -> dict:
    cards = pack_data.get("cards", [])
    pack_name = pack_data.get("pack_name", slug)
    expansion_id = pack_data.get("expansion_id", "")

    new_card_ev  = 0.0
    copy_ev      = 0.0
    ex_ev        = 0.0
    total_ev     = 0.0
    card_details = []

    for card in cards:
        sc  = card.get("set_code", "").upper()
        cn  = card.get("card_number")
        pct = card.get("drop_chance_pct")
        if pct is None:
            continue
        p_pull = pct / 100.0

        # Resolve card name: prefer pack_sources (handles forme disambiguation)
        ps_rec = ps_idx.get((sc, cn))
        if ps_rec:
            card_name = ps_rec.get("card_name", card.get("name", ""))
            is_ex     = bool(ps_rec.get("is_ex", False))
        else:
            card_name = card.get("name", "")
            is_ex     = "ex" in card_name.lower() and not card_name.lower().startswith("exegg")

        # Get owned count from collection
        owned = collection.get(_norm(card_name), 0)

        value = value_of_next_copy(owned, is_ex)
        ev    = p_pull * value

        # Attribute to bucket
        if owned == 0:
            new_card_ev += ev
        else:
            copy_ev += ev
        if is_ex:
            ex_ev += ev
        total_ev += ev

        card_details.append({
            "name":       card_name,
            "set_code":   sc,
            "card_number": cn,
            "is_ex":      is_ex,
            "owned":      owned,
            "drop_chance": round(p_pull, 4),
            "value":      round(value, 2),
            "ev":         round(ev, 5),
        })

    owned_in_pack   = sum(1 for c in card_details if c["owned"] > 0)
    missing_in_pack = len(card_details) - owned_in_pack

    return {
        "pack_name":      pack_name,
        "slug":           slug,
        "expansion_id":   expansion_id,
        "card_count":     len(card_details),
        "owned_in_pack":  owned_in_pack,
        "missing_in_pack": missing_in_pack,
        "new_card_ev":    round(new_card_ev, 5),
        "copy_ev":        round(copy_ev, 5),
        "ex_card_ev":     round(ex_ev, 5),
        "total_ev":       round(total_ev, 5),
        "source_status":  "pz_verified",
        "cards":          card_details,
    }


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------

def write_json(records: list[dict]) -> dict:
    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_by": "build_promo_pack_ev.py",
        "meta": {
            "note": (
                "Promo packs use Shop Tokens (not Hourglasses). "
                "EV is comparable within promo packs only — not directly comparable to regular pack EV."
            ),
            "ev_model": "new_card_ev = Σ(p_pull × value); value=1.0 new card, 0.4 second copy, +1.0 if ex",
            "source": "pz_verified — per-card drop chances from Pokemon Zone",
            "collection_total": None,
        },
        "packs": records,
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


def write_md(records: list[dict]) -> None:
    lines = [
        "# Promo Pack EV Rankings",
        "",
        "> Promo packs use **Shop Tokens** (not Hourglasses) — EVs are not comparable to regular pack rankings.",
        "> Source: Pokemon Zone direct drop chances (`pz_verified`).",
        "> EV model: new card = 1.0, second copy = 0.4, +1.0 bonus for ex cards.",
        "",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}  ",
        "",
        "## Rankings by New Card EV",
        "",
        "| # | Pack | Cards | Owned | Missing | New Card EV | Total EV |",
        "|---|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(records, 1):
        lines.append(
            f"| {i} | {r['pack_name']} | {r['card_count']} "
            f"| {r['owned_in_pack']} | {r['missing_in_pack']} "
            f"| {r['new_card_ev']:.4f} | {r['total_ev']:.4f} |"
        )

    lines += ["", "## Pack Details", ""]
    for r in records:
        if r["missing_in_pack"] == 0:
            continue
        lines += [
            f"### {r['pack_name']}",
            "",
            f"- Missing: {r['missing_in_pack']}/{r['card_count']} cards",
            f"- New card EV: **{r['new_card_ev']:.4f}**",
            "",
            "| Card | Is EX | Owned | Drop % | EV |",
            "|---|---|---|---|---|",
        ]
        for c in sorted(r["cards"], key=lambda x: -x["ev"]):
            lines.append(
                f"| {c['name']} | {'✓' if c['is_ex'] else ''} "
                f"| {c['owned']} | {c['drop_chance']:.1%} | {c['ev']:.4f} |"
            )
        lines.append("")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=== build_promo_pack_ev.py ===")

    pz_raw     = json.loads(PZ_PACK_ODDS_JSON.read_text(encoding="utf-8"))
    collection = load_collection(COLLECTION_JSON)
    ps_idx     = load_promo_ps_index(PACK_SOURCES_JSON)

    promo_slugs = [slug for slug in pz_raw if "promo" in slug]
    print(f"  Promo packs in PZ data: {len(promo_slugs)}")
    print(f"  PROMO entries in pack_sources: {len(ps_idx)}")

    records = []
    for slug in sorted(promo_slugs):
        rec = compute_promo_pack_ev(slug, pz_raw[slug], collection, ps_idx)
        records.append(rec)

    records.sort(key=lambda r: r["new_card_ev"], reverse=True)

    write_json(records)
    write_md(records)

    print(f"\n  Written: {OUT_JSON.relative_to(ROOT)}")
    print(f"  Written: {OUT_MD.relative_to(ROOT)}")

    print("\n=== Promo Pack Rankings (by new card EV) ===")
    print(f"  {'Pack':<38} {'Miss':>4} {'NewEV':>7} {'TotEV':>7}")
    for r in records:
        print(f"  {r['pack_name']:<38} {r['missing_in_pack']:>4} {r['new_card_ev']:>7.4f} {r['total_ev']:>7.4f}")


if __name__ == "__main__":
    main()
