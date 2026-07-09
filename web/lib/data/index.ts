import { env } from "@/lib/env";
import { localJsonSource } from "@/lib/data/local-json";
import { createDefaultSupabaseSource } from "@/lib/data/supabase";
import type { DataSource } from "@/lib/data/source";

/** Selects the active data source from env. */
function selectSource(): DataSource {
  switch (env.DATA_SOURCE) {
    case "local-json":
      return localJsonSource;
    case "supabase":
      return createDefaultSupabaseSource();
  }
}

export const dataSource = selectSource();
export type { DataSource } from "@/lib/data/source";
