#!/usr/bin/env python3
"""
One-time admin tool: create the single owner auth user (Phase 6 of the
hosting roadmap). Run locally before applying
supabase/migrations/0002_auth_owner.sql, which resolves this user by email
and backfills the placeholder user_id onto its UUID.

No password is set — one gets created via a recovery link if/when the login
UI ships. Idempotent: if the user already exists, prints its UUID and exits 0.

Env (service-role, server-side only — never expose to a browser bundle):
    SUPABASE_URL                 https://<project-ref>.supabase.co
    SUPABASE_SERVICE_ROLE_KEY    service_role API key

Usage:
    pip install supabase   # optional dep, not needed by the pipeline or CI
    SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... \
        python3 scripts/create_owner_user.py
"""

import os
import sys

OWNER_EMAIL = "jackpendley9@gmail.com"


def main() -> None:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        sys.exit("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (service role).")

    # Lazy import: the pipeline and CI never need the supabase package.
    try:
        from supabase import create_client
    except ImportError:
        sys.exit("The `supabase` package is required: pip install supabase")

    client = create_client(url, key)

    existing = [
        u for u in client.auth.admin.list_users() if u.email == OWNER_EMAIL
    ]
    if existing:
        user = existing[0]
        print(f"Owner auth user already exists: {user.id}")
    else:
        user = client.auth.admin.create_user(
            {"email": OWNER_EMAIL, "email_confirm": True}
        ).user
        print(f"Owner auth user created: {user.id}")

    print("Next steps:")
    print("  1. Apply supabase/migrations/0002_auth_owner.sql (dashboard SQL editor).")
    print(f"  2. Set the GitHub Actions secret OWNER_USER_ID to {user.id}.")


if __name__ == "__main__":
    main()
