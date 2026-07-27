import path from "node:path";

import { z } from "zod";

/**
 * Validated environment config. Imported by server-side code only.
 * Fails loudly at startup if a required variable is malformed.
 */
const envSchema = z.object({
  // Which data backend the app reads from: local pipeline artifacts or the
  // hosted Supabase project (web/lib/data/index.ts switches on this).
  DATA_SOURCE: z.enum(["local-json", "supabase"]).default("local-json"),
  // Absolute or relative path to the Python pipeline's repo root (the dir that
  // contains data/current + data/reference). Defaults to the monorepo parent.
  PIPELINE_ROOT: z.string().default(path.resolve(process.cwd(), "..")),
  // Dev-only sync trigger. On by default in local dev; always force-disabled in
  // production regardless of this value. Set to "false" to disable it locally.
  ENABLE_LOCAL_SYNC: z
    .enum(["true", "false"])
    .default("true")
    .transform((v) => v === "true"),
  // Supabase connection (hosted phase). Optional so local-json mode needs no
  // config; required together when DATA_SOURCE=supabase (checked below). None
  // are NEXT_PUBLIC_, so Next.js can never inline them into the client bundle.
  SUPABASE_URL: z.url().optional(),
  // Anon key: used by the auth layer (@supabase/ssr) for owner sign-in and the
  // session-refresh proxy. Safe to expose by design, but kept server-side here
  // since login/logout run as server actions. Required in supabase mode.
  SUPABASE_ANON_KEY: z.string().min(1).optional(),
  // Service-role key: used server-side only — by the publisher and, since
  // Phase 6 dropped the anon RLS policies, by the web read path
  // (web/lib/data/supabase.ts, a server-only module).
  SUPABASE_SERVICE_ROLE_KEY: z.string().min(1).optional(),
  // Hosted sync trigger (Phase 5): a fine-grained GitHub token with Contents
  // read/write on the repo below, used to fire repository_dispatch. When both
  // are set, the sync button dispatches .github/workflows/sync.yml instead of
  // spawning the local pipeline. Server-only.
  GITHUB_SYNC_TOKEN: z.string().min(1).optional(),
  GITHUB_SYNC_REPO: z
    .string()
    .regex(/^[\w.-]+\/[\w.-]+$/, "expected owner/repo")
    .optional(),
  // Auth (Phase 1): the single owner's auth.users UUID. Writes (sync) are gated
  // to this user; reads stay public. Required in supabase mode. Server-only.
  OWNER_USER_ID: z.uuid().optional(),
  // Canonical public origin, used to build auth email links. Must not come from
  // the request's Origin header — that is attacker-controlled, and a recovery
  // link is exactly the thing you never want pointed at someone else's domain.
  // Falls back to Vercel's injected production hostname.
  SITE_URL: z.url().optional(),
  // Phase 5: shared secret guarding POST /api/revalidate, which the sync
  // workflow calls after a publish to invalidate the cached data (revalidateTag).
  // When unset the route is disabled (returns 401). Server-only.
  REVALIDATE_SECRET: z.string().min(1).optional(),
});

export const env = envSchema
  .superRefine((cfg, ctx) => {
    if (cfg.DATA_SOURCE === "supabase") {
      for (const key of [
        "SUPABASE_URL",
        "SUPABASE_SERVICE_ROLE_KEY",
        "SUPABASE_ANON_KEY",
        "OWNER_USER_ID",
      ] as const) {
        if (!cfg[key]) {
          ctx.addIssue({
            code: "custom",
            path: [key],
            message: `${key} is required when DATA_SOURCE=supabase`,
          });
        }
      }
    }
  })
  .parse(process.env);
