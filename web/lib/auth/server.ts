import "server-only";

import { cookies } from "next/headers";
import { createServerClient } from "@supabase/ssr";
import type { SupabaseClient } from "@supabase/supabase-js";

import { env } from "@/lib/env";

/**
 * Cookie-bound Supabase client for Server Components and Server Actions. Reads
 * and writes the auth session via Next's cookie store, so sign-in/out and
 * `getUser()` share the same session the proxy refreshes on each request.
 *
 * Login/logout run as server actions, so the anon key never needs a
 * NEXT_PUBLIC_ prefix — it stays server-side. Reads of collection data still go
 * through the service-role source (lib/data/supabase.ts); this client exists
 * only for authentication.
 */
export async function createSupabaseServerClient(): Promise<SupabaseClient> {
  if (!env.SUPABASE_URL || !env.SUPABASE_ANON_KEY) {
    throw new Error("SUPABASE_URL and SUPABASE_ANON_KEY are required for auth.");
  }
  const cookieStore = await cookies();
  return createServerClient(env.SUPABASE_URL, env.SUPABASE_ANON_KEY, {
    cookies: {
      getAll() {
        return cookieStore.getAll();
      },
      setAll(cookiesToSet) {
        try {
          for (const { name, value, options } of cookiesToSet) {
            cookieStore.set(name, value, options);
          }
        } catch {
          // Called from a Server Component, where the cookie store is
          // read-only. Safe to ignore: the proxy refreshes session cookies.
        }
      },
    },
  });
}

/** The authenticated user for this request, or null. */
export async function getSessionUser() {
  const supabase = await createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  return user;
}

/**
 * True only when the request is authenticated as the configured owner. Fails
 * closed: if OWNER_USER_ID is unset (e.g. local-json mode), nobody is the owner.
 */
export async function isOwner(): Promise<boolean> {
  if (!env.OWNER_USER_ID) return false;
  const user = await getSessionUser();
  return user?.id === env.OWNER_USER_ID;
}
