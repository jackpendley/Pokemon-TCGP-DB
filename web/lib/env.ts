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
  // Gate for the dev-only sync trigger; never enabled in production.
  ENABLE_LOCAL_SYNC: z
    .enum(["true", "false"])
    .default("false")
    .transform((v) => v === "true"),
});

export const env = envSchema.parse(process.env);
