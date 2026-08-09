import { Suspense } from "react";
import { connection } from "next/server";

import { HistoryView } from "@/components/history/history-view";
import { PanelSkeleton } from "@/components/ui/skeletons";
import { getCachedRecommendationHistory } from "@/lib/data/cached";

export const metadata = { title: "History · TCGP Optimizer" };

async function HistoryContent() {
  await connection();
  const entries = await getCachedRecommendationHistory();
  return <HistoryView entries={entries} />;
}

export default function HistoryPage() {
  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">History</h1>
        <p className="text-sm text-muted-foreground">
          How your collection and pack recommendations have drifted over time.
        </p>
      </div>
      <Suspense
        fallback={
          <div className="space-y-6">
            <PanelSkeleton titleWidth="w-40" bodyClassName="h-64" />
            <PanelSkeleton titleWidth="w-48" bodyClassName="h-64" />
          </div>
        }
      >
        <HistoryContent />
      </Suspense>
    </div>
  );
}
