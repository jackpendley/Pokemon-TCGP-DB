#!/usr/bin/env python3
"""
Publish the pipeline's JSON artifacts to Supabase (Phase 4 of the hosting
roadmap). Reads data/current/ + data/reference/ + data/sync/ and upserts them
into the Postgres schema defined in supabase/migrations/0001_init.sql.

Pipeline logic is untouched — this only reads what the pipeline already emits.
Derived per-user artifacts (collection summary, pack EV, recommendations) are
published as whole JSONB documents so they round-trip byte-identically through
the web/types Zod contract.

Idempotent: rows are upserted on their natural primary keys, so re-running is
a no-op when the artifacts haven't changed. `collections` is delete-then-insert
per user so cards removed from the collection don't linger.

Env (service-role, server-side only — never expose to a browser bundle):
    SUPABASE_URL                 https://<project-ref>.supabase.co
    SUPABASE_SERVICE_ROLE_KEY    service_role API key
    OWNER_USER_ID                auth owner UUID (scripts/create_owner_user.py)
    SYNC_OUTCOME                 optional: ok|review|auth_expired (CI sync marker)
    SYNC_MODE                    optional: live|skip (CI sync marker)

Usage:
    pip install supabase   # optional dep, not needed by the pipeline or CI
    SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... OWNER_USER_ID=... \
        python3 scripts/publish_to_supabase.py

The row-builder functions below are pure (no I/O, no supabase import) so
tests/test_publish_to_supabase.py can verify payload shapes against the
web/types/__fixtures__ contract without the supabase package installed.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CURRENT_DIR = ROOT / "data" / "current"
REFERENCE_DIR = ROOT / "data" / "reference"
SYNC_DIR = ROOT / "data" / "sync"

# Single-tenant placeholder owner from Phase 4; kept as the row-builder
# default for tests. Since Phase 6, main() requires the real auth owner UUID
# via the OWNER_USER_ID env var (see scripts/create_owner_user.py).
OWNER_USER_ID = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"

UPSERT_CHUNK_SIZE = 500

# Natural PK per table (PostgREST on_conflict target). None => insert-only
# (the table is cleared for the user first).
TABLE_CONFLICT_KEYS = {
    "cards": "set_code,card_number",
    "packs": "pack_name",
    "pack_cards": "pack_name,set_code,card_number",
    "pack_top_cards": "pack_name",
    "pull_probability_model": "id",
    "collections": None,
    "collection_summaries": "user_id",
    "pack_ev": "user_id",
    "recommendations": "user_id",
    "sync_status": "user_id",
    "sync_history": "user_id,synced_at",
}


def is_mega(record: dict) -> bool:
    """Mega flag derived the same way as web/lib/domain/card.ts."""
    return bool(record.get("is_ex")) and str(record.get("name", "")).startswith(
        "Mega "
    )


def build_card_rows(card_reference: dict, power_scores: dict | None) -> list[dict]:
    """cards rows from card_reference.json + card_power_scores.json."""
    scores = (power_scores or {}).get("scores", {})
    rows = []
    for r in card_reference["records"]:
        coord = f"{r['set_code']}:{r['card_number']}"
        score = scores.get(coord)
        rows.append(
            {
                "set_code": r["set_code"],
                "card_number": r["card_number"],
                "name": r["name"],
                "rarity": r.get("rarity"),
                "pokemon_type": r.get("pokemon_type"),
                "card_category": r.get("card_category"),
                "trainer_subtype": r.get("trainer_subtype"),
                "stage": r.get("stage"),
                "expansion": r.get("expansion") or r["set_code"],
                "is_ex": r.get("is_ex"),
                "is_mega": is_mega(r),
                "evolves_from": r.get("evolves_from"),
                "hp": r.get("hp"),
                "pack_name": r.get("pack_name"),
                "power_score": score["power_score"] if score else None,
                # Which model produced the score — Pokémon and Trainer scores
                # are not comparable, so the kind travels with the number.
                "power_score_kind": score.get("score_kind") if score else None,
            }
        )
    return rows


def build_pack_rows(pack_ev: dict) -> list[dict]:
    """packs rows from pack_ev.json packs[] (one row per pack)."""
    return [
        {
            "pack_name": p["pack_name"],
            "expansion": p["expansion"],
            "set_code": p["set_code"],
        }
        for p in pack_ev["packs"]
    ]


def build_pack_card_rows(card_reference: dict) -> list[dict]:
    """pack_cards membership rows from card_reference records' pack_name.

    A record's pack_name can name several packs ("Mewtwo pack, Pikachu pack")
    or be a shared-pool marker; each comma-separated name becomes one row.
    """
    rows = {}
    for r in card_reference["records"]:
        for pack_name in (r.get("pack_name") or "").split(","):
            pack_name = pack_name.strip()
            if not pack_name:
                continue
            key = (pack_name, r["set_code"], r["card_number"])
            rows[key] = {
                "pack_name": pack_name,
                "set_code": r["set_code"],
                "card_number": r["card_number"],
            }
    return list(rows.values())


def build_pack_top_card_rows(pack_ev: dict) -> list[dict]:
    """pack_top_cards rows (both top_ev_cards and top_power_cards) per pack."""
    return [
        {
            "pack_name": p["pack_name"],
            "top_ev_cards": p.get("top_ev_cards", []),
            "top_power_cards": p.get("top_power_cards", []),
        }
        for p in pack_ev["packs"]
    ]


def build_pull_probability_row(model: dict) -> list[dict]:
    """Singleton pull_probability_model document row."""
    return [
        {
            "id": "current",
            "payload": model,
            "generated_at": model.get("generated_at"),
        }
    ]


def build_collection_rows(collection: dict, user_id: str) -> list[dict]:
    """collections rows from collection_normalized.json (per-user, counts).

    Entries are per-variant (entry_id), so the same set_code+card_number can
    appear more than once; counts are summed to match the web catalog merge
    (web/lib/data/local-json.ts loadCatalog).
    """
    counts: dict[tuple, int] = {}
    for entry in collection["collection"]:
        key = (entry["set_code"], entry["card_number"])
        counts[key] = counts.get(key, 0) + entry["count"]
    return [
        {
            "user_id": user_id,
            "set_code": set_code,
            "card_number": card_number,
            "count": count,
        }
        for (set_code, card_number), count in counts.items()
    ]


def build_document_row(artifact: dict, user_id: str) -> list[dict]:
    """Whole-artifact JSONB row for collection_summaries/pack_ev/recommendations."""
    return [{"user_id": user_id, "payload": artifact}]


def build_sync_status_row(
    stats: dict | None,
    review_queue: dict | None,
    delta: dict | None,
    user_id: str,
    last_run: dict | None = None,
) -> list[dict]:
    """sync_status snapshot row; absent local files publish as nulls.

    published_at is set explicitly so it advances on every publish — the web
    remote sync runner uses it as the completion baseline.
    """
    return [
        {
            "user_id": user_id,
            "stats": stats,
            "review_queue": review_queue,
            "delta": delta,
            "last_run": last_run,
            "published_at": datetime.now(timezone.utc).isoformat(),
        }
    ]


def build_sync_history_rows(history: dict | None, user_id: str) -> list[dict]:
    """sync_history rows, one per entry of sync_history.json."""
    return [
        {
            "user_id": user_id,
            "synced_at": e["synced_at"],
            "added_count": e["added_count"],
            "added": e.get("added", []),
        }
        for e in (history or {}).get("entries", [])
    ]


def build_last_run() -> dict | None:
    """Sync outcome marker from CI env (SYNC_OUTCOME/SYNC_MODE), or None.

    The web remote sync runner reads sync_status.last_run to distinguish a
    finished live sync (ok/review), an expired PZ auth (auth_expired), and a
    plain republish. Set by .github/workflows/sync.yml.
    """
    outcome = os.environ.get("SYNC_OUTCOME")
    if not outcome:
        return None
    return {
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "outcome": outcome,
        "mode": os.environ.get("SYNC_MODE"),
    }


def build_recommendation_snapshot_rows(
    recommendations: dict, pack_ev: dict, user_id: str = OWNER_USER_ID
) -> list[dict]:
    """Append-only snapshot of the current recommendation + pack-EV state.

    One row per real sync (captured_at defaults to now() in Postgres), feeding
    the /history drift view (Phase 7). Kept out of build_all_rows/publish because
    those tables are idempotent upserts, whereas this is a pure append.
    """
    return [
        {
            "user_id": user_id,
            "payload": {"recommendations": recommendations, "pack_ev": pack_ev},
        }
    ]


def should_snapshot() -> bool:
    """Snapshot on real syncs, not pure republishes.

    push-to-main runs the workflow in --skip-sync republish mode (SYNC_MODE=skip)
    on every commit; appending a snapshot there would flood the history with
    identical rows. A live sync (SYNC_MODE=live) or a local manual publish
    (SYNC_MODE unset) does append one.
    """
    return os.environ.get("SYNC_MODE") != "skip"


def publish_recommendation_snapshot(client, rows: list[dict]) -> None:
    """Append snapshot rows (no delete, no upsert) — history is append-only."""
    if not rows:
        return
    client.table("recommendation_snapshots").insert(rows).execute()
    print(f"  recommendation_snapshots: +{len(rows)} row")


def build_all_rows(
    artifacts: dict, user_id: str = OWNER_USER_ID, last_run: dict | None = None
) -> dict:
    """Map every table to its rows from the loaded artifacts dict."""
    return {
        "cards": build_card_rows(
            artifacts["card_reference"], artifacts.get("card_power_scores")
        ),
        "packs": build_pack_rows(artifacts["pack_ev"]),
        "pack_cards": build_pack_card_rows(artifacts["card_reference"]),
        "pack_top_cards": build_pack_top_card_rows(artifacts["pack_ev"]),
        "pull_probability_model": build_pull_probability_row(
            artifacts["pull_probability_model"]
        ),
        "collections": build_collection_rows(
            artifacts["collection_normalized"], user_id
        ),
        "collection_summaries": build_document_row(
            artifacts["collection_summary"], user_id
        ),
        "pack_ev": build_document_row(artifacts["pack_ev"], user_id),
        "recommendations": build_document_row(
            artifacts["recommendations"], user_id
        ),
        "sync_status": build_sync_status_row(
            artifacts.get("player_stats"),
            artifacts.get("sync_review_queue"),
            artifacts.get("last_sync_delta"),
            user_id,
            last_run,
        ),
        "sync_history": build_sync_history_rows(
            artifacts.get("sync_history"), user_id
        ),
    }


def publish(client, rows_by_table: dict, user_id: str = OWNER_USER_ID) -> None:
    """Push rows through a supabase-py style client (injectable for tests)."""
    for table, rows in rows_by_table.items():
        conflict_key = TABLE_CONFLICT_KEYS[table]
        if conflict_key is None:
            # Full replace: cards removed from the source must not linger.
            client.table(table).delete().eq("user_id", user_id).execute()
        for start in range(0, len(rows), UPSERT_CHUNK_SIZE):
            chunk = rows[start : start + UPSERT_CHUNK_SIZE]
            query = client.table(table)
            if conflict_key is None:
                query.insert(chunk).execute()
            else:
                query.upsert(chunk, on_conflict=conflict_key).execute()
        print(f"  {table}: {len(rows)} rows")


def load_json(path: Path, required: bool = True) -> dict | None:
    if not path.exists():
        if required:
            sys.exit(
                f"Missing artifact {path}. Run `python3 scripts/run_recommendations.py"
                " --skip-sync` (and build_card_power_score.py) first."
            )
        return None
    with open(path) as f:
        return json.load(f)


def load_artifacts() -> dict:
    return {
        "card_reference": load_json(REFERENCE_DIR / "card_reference.json"),
        "card_power_scores": load_json(
            REFERENCE_DIR / "card_power_scores.json", required=False
        ),
        "pull_probability_model": load_json(
            REFERENCE_DIR / "pull_probability_model.json"
        ),
        "collection_normalized": load_json(CURRENT_DIR / "collection_normalized.json"),
        "collection_summary": load_json(CURRENT_DIR / "collection_summary.json"),
        "pack_ev": load_json(CURRENT_DIR / "pack_ev.json"),
        "recommendations": load_json(
            CURRENT_DIR / "inferred_pack_recommendations.json"
        ),
        # Sync snapshots are optional (gitignored, absent until a sync runs).
        "player_stats": load_json(SYNC_DIR / "player_stats.json", required=False),
        "sync_review_queue": load_json(
            SYNC_DIR / "sync_review_queue.json", required=False
        ),
        "last_sync_delta": load_json(
            SYNC_DIR / "last_sync_delta.json", required=False
        ),
        "sync_history": load_json(SYNC_DIR / "sync_history.json", required=False),
    }


def main() -> None:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        sys.exit("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (service role).")
    owner = os.environ.get("OWNER_USER_ID")
    if not owner:
        sys.exit(
            "Set OWNER_USER_ID to the auth owner UUID printed by "
            "scripts/create_owner_user.py (Phase 6)."
        )

    # Lazy import: the pipeline and CI never need the supabase package.
    try:
        from supabase import create_client
    except ImportError:
        sys.exit("The `supabase` package is required: pip install supabase")

    print("Loading artifacts...")
    artifacts = load_artifacts()
    rows_by_table = build_all_rows(
        artifacts, user_id=owner, last_run=build_last_run()
    )
    print(f"Publishing to {url} as owner {owner}:")
    client = create_client(url, key)
    publish(client, rows_by_table, user_id=owner)
    if should_snapshot():
        publish_recommendation_snapshot(
            client,
            build_recommendation_snapshot_rows(
                artifacts["recommendations"], artifacts["pack_ev"], owner
            ),
        )
    print("Done.")


if __name__ == "__main__":
    main()
