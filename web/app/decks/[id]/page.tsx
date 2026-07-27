import { Suspense } from "react";
import Link from "next/link";
import { notFound } from "next/navigation";

import { DeckBuilder } from "@/components/decks/deck-builder";
import { DeleteDeckButton } from "@/components/decks/delete-deck-button";
import { PanelSkeleton } from "@/components/ui/skeletons";
import { getCachedCatalog, getCachedDeck } from "@/lib/data/cached";
import { canEditDecks } from "@/app/decks/actions";

async function DeckContent({ params }: { params: Promise<{ id: string }> }) {
  // Awaiting params first is the runtime bail that keeps prerender out of the
  // cached reads below — see web/AGENTS.md.
  const { id } = await params;
  const [deck, catalog, canEdit] = await Promise.all([
    getCachedDeck(id),
    getCachedCatalog(),
    canEditDecks(),
  ]);
  if (!deck) notFound();

  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">{deck.name}</h1>
        {canEdit ? <DeleteDeckButton id={deck.id} name={deck.name} /> : null}
      </div>
      <DeckBuilder
        key={deck.id}
        catalog={catalog}
        existing={deck}
        canEdit={canEdit}
      />
    </>
  );
}

export default function DeckPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  return (
    <div className="space-y-6">
      <Link
        href="/decks"
        className="text-sm text-muted-foreground hover:underline"
      >
        ← Decks
      </Link>
      <Suspense
        fallback={
          <div className="grid gap-6 lg:grid-cols-[1fr_22rem]">
            <PanelSkeleton titleWidth="w-28" bodyClassName="h-64" />
            <PanelSkeleton titleWidth="w-20" bodyClassName="h-72" />
          </div>
        }
      >
        <DeckContent params={params} />
      </Suspense>
    </div>
  );
}
