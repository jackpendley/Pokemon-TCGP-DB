import { Suspense } from "react";
import Link from "next/link";
import { connection } from "next/server";
import { Plus } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { PanelSkeleton } from "@/components/ui/skeletons";
import { getCachedDecks } from "@/lib/data/cached";
import { canEditDecks } from "@/app/decks/actions";

export const metadata = { title: "Decks · TCGP Optimizer" };

async function DecksContent() {
  // Runtime-only, before any cached read — see web/AGENTS.md.
  await connection();
  const [decks, canEdit] = await Promise.all([getCachedDecks(), canEditDecks()]);

  if (decks.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-sm text-muted-foreground">
          No decks yet.
          {canEdit ? " Build one to check it against the game's rules." : null}
        </CardContent>
      </Card>
    );
  }

  return (
    <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {decks.map((deck) => {
        const cards = deck.cards.reduce((n, c) => n + c.count, 0);
        return (
          <li key={deck.id}>
            <Link href={`/decks/${deck.id}`} className="block">
              <Card className="h-full transition-colors hover:border-primary/50">
                <CardContent className="space-y-2">
                  <div className="flex items-start justify-between gap-2">
                    <span className="font-heading font-semibold">{deck.name}</span>
                    <Badge variant={cards === 20 ? "secondary" : "outline"}>
                      {cards}/20
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {deck.energy_types.length > 0
                      ? deck.energy_types.join(" · ")
                      : "No energy selected"}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Updated {new Date(deck.updated_at).toLocaleDateString()}
                  </p>
                </CardContent>
              </Card>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}

async function NewDeckButton() {
  await connection();
  if (!(await canEditDecks())) return null;
  return (
    <Button render={<Link href="/decks/new" />}>
      <Plus className="size-4" />
      New deck
    </Button>
  );
}

export default function DecksPage() {
  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">Decks</h1>
          <p className="text-sm text-muted-foreground">
            20-card decks checked against the game&rsquo;s construction rules.
          </p>
        </div>
        <Suspense fallback={null}>
          <NewDeckButton />
        </Suspense>
      </header>
      <Suspense
        fallback={
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[0, 1, 2].map((i) => (
              <PanelSkeleton key={i} titleWidth="w-32" bodyClassName="h-12" />
            ))}
          </div>
        }
      >
        <DecksContent />
      </Suspense>
    </div>
  );
}
