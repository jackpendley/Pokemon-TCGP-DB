import { NextResponse, type NextRequest } from "next/server";
import { createServerClient } from "@supabase/ssr";

/**
 * Next 16 renamed Middleware to Proxy (same mechanics). This refreshes the
 * Supabase auth session cookie on each request so Server Components see a
 * current session — the standard @supabase/ssr pattern.
 *
 * In local-json mode the Supabase env vars are unset; we no-op so dev without a
 * Supabase project still works.
 */
export async function proxy(request: NextRequest) {
  const url = process.env.SUPABASE_URL;
  const anon = process.env.SUPABASE_ANON_KEY;

  let response = NextResponse.next({ request });
  if (!url || !anon) return response;

  const supabase = createServerClient(url, anon, {
    cookies: {
      getAll() {
        return request.cookies.getAll();
      },
      setAll(cookiesToSet) {
        for (const { name, value } of cookiesToSet) {
          request.cookies.set(name, value);
        }
        response = NextResponse.next({ request });
        for (const { name, value, options } of cookiesToSet) {
          response.cookies.set(name, value, options);
        }
      },
    },
  });

  // Touching getUser() triggers the token refresh + Set-Cookie when needed.
  await supabase.auth.getUser();

  return response;
}

export const config = {
  // Run on pages, skip static assets and images (nothing to refresh there).
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico)$).*)",
  ],
};
