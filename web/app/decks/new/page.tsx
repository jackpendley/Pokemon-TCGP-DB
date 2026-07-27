import { Suspense } from "react";
import Link from "next/link";
import { connection } from "next/server";

import { DeckBuilder } from "@/components/decks/deck-builder";
import { PanelSkeleton } from "@/components/ui/skeletons";
import { getCachedCatalog } from "@/lib/data/cached";
import { canEditDecks } from "@/app/decks/actions";

export const metadata = { title: "New deck · TCGP Optimizer" };

async function NewDeckContent() {
  await connection();
  const [catalog, canEdit] = await Promise.all([
    getCachedCatalog(),
    canEditDecks(),
  ]);
  return <DeckBuilder catalog={catalog} existing={null} canEdit={canEdit} />;
}

export default function NewDeckPage() {
  return (
    <div className="space-y-6">
      <Link
        href="/decks"
        className="text-sm text-muted-foreground hover:underline"
      >
        ← Decks
      </Link>
      <h1 className="text-2xl font-semibold tracking-tight">New deck</h1>
      <Suspense
        fallback={
          <div className="grid gap-6 lg:grid-cols-[1fr_22rem]">
            <PanelSkeleton titleWidth="w-28" bodyClassName="h-64" />
            <PanelSkeleton titleWidth="w-20" bodyClassName="h-72" />
          </div>
        }
      >
        <NewDeckContent />
      </Suspense>
    </div>
  );
}
