import { NextResponse } from "next/server";

import { createSupabaseServerClient } from "@/lib/auth/server";

/**
 * Exchanges a Supabase PKCE code for a session, then forwards on.
 *
 * A Route Handler rather than a Server Component because the exchange has to
 * write session cookies, which a Server Component can't do. Keeping it here
 * means the recovery flow never needs a browser Supabase client, so the anon
 * key stays server-only like the rest of the auth layer.
 */
export async function GET(request: Request): Promise<Response> {
  const url = new URL(request.url);
  const code = url.searchParams.get("code");
  const next = url.searchParams.get("next") ?? "/";

  // Only same-site paths — never redirect to an attacker-supplied origin.
  const destination = next.startsWith("/") && !next.startsWith("//") ? next : "/";

  if (!code) {
    return NextResponse.redirect(new URL("/login?error=missing-code", url.origin));
  }

  const supabase = await createSupabaseServerClient();
  const { error } = await supabase.auth.exchangeCodeForSession(code);
  if (error) {
    return NextResponse.redirect(new URL("/login?error=link-expired", url.origin));
  }
  return NextResponse.redirect(new URL(destination, url.origin));
}
