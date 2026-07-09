import path from "node:path";

import { z } from "zod";

/**
 * Validated environment config. Imported by server-side code only.
 * Fails loudly at startup if a required variable is malformed.
 */
const envSchema = z.object({
  // Which data backend the app reads from. Only local-json is implemented today;
  // "supabase" is reserved for the deferred hosted phase.
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
  SUPABASE_ANON_KEY: z.string().min(1).optional(),
  // Service-role key: server-side writes only (publisher / future sync
  // trigger). Never used by the web read path.
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
});

export const env = envSchema
  .superRefine((cfg, ctx) => {
    if (cfg.DATA_SOURCE === "supabase") {
      for (const key of ["SUPABASE_URL", "SUPABASE_ANON_KEY"] as const) {
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
