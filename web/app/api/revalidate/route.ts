import { revalidateTag } from "next/cache";

import { DATA_TAG } from "@/lib/data/cached";
import { env } from "@/lib/env";

/**
 * Invalidate the cached app data after a publish. The sync workflow
 * (.github/workflows/sync.yml) POSTs here with the REVALIDATE_SECRET once the
 * publisher has written fresh data, so the next request re-reads Supabase
 * instead of serving a stale `use cache` hit.
 */
export async function POST(request: Request): Promise<Response> {
  const provided = request.headers
    .get("authorization")
    ?.replace(/^Bearer\s+/i, "");
  if (!env.REVALIDATE_SECRET || provided !== env.REVALIDATE_SECRET) {
    return new Response("Unauthorized", { status: 401 });
  }

  // "max" = mark stale with stale-while-revalidate; the next visit re-reads
  // Supabase and refreshes in the background (the recommended signature).
  revalidateTag(DATA_TAG, "max");
  return Response.json({ revalidated: true, tag: DATA_TAG });
}
