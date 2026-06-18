import { env } from "@/lib/env";
import { localJsonSource } from "@/lib/data/local-json";
import type { DataSource } from "@/lib/data/source";

/**
 * Selects the active data source from env. Swapping to Supabase later is a
 * one-line change here plus a new implementation — no UI/domain changes.
 */
function selectSource(): DataSource {
  switch (env.DATA_SOURCE) {
    case "local-json":
      return localJsonSource;
    case "supabase":
      throw new Error(
        "DATA_SOURCE=supabase is not implemented yet (deferred to the hosted phase).",
      );
  }
}

export const dataSource = selectSource();
export type { DataSource } from "@/lib/data/source";
