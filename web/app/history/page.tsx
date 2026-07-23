import { HistoryView } from "@/components/history/history-view";
import { fetchRecommendationHistory } from "@/lib/data/supabase";
import { env } from "@/lib/env";

// Reads recommendation_snapshots via the service role (public, like the other
// pages). Force-dynamic for the same reason as the rest of the app until the
// Phase 5 caching pass (docs/hosting-roadmap.md).
export const dynamic = "force-dynamic";
export const metadata = { title: "History · TCGP Optimizer" };

export default async function HistoryPage() {
  // Snapshots live only in Supabase; local-json dev has none.
  const entries =
    env.DATA_SOURCE === "supabase" ? await fetchRecommendationHistory() : [];

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">History</h1>
        <p className="text-sm text-muted-foreground">
          How your collection and pack recommendations have drifted over time.
        </p>
      </div>
      <HistoryView entries={entries} />
    </div>
  );
}
