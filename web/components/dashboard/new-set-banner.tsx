"use client";

import { useState } from "react";
import { PackagePlus } from "lucide-react";

import { adoptSet } from "@/app/sync/actions";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export interface PendingSet {
  setCode: string;
  cardCount: number;
  copies: number;
}

/**
 * Owner-only prompt for an expansion Pokémon Zone is serving that the pipeline
 * has never registered.
 *
 * Until this existed nothing noticed a new set: the pipeline syncs offline
 * (--no-fetch), so a released expansion's cards became unexplained "new cards"
 * in the review queue and its packs never appeared in EV at all. That is what
 * happened when Ruler of the Skies shipped.
 *
 * Adoption stays a click rather than a consequence of detection, because
 * registering a set edits SET_REGISTRY/SET_ALIASES with source slugs that are
 * guesses until proven. The workflow verifies each source, reverts on a failed
 * guard test, and opens a PR.
 */
export function NewSetBanner({ sets }: { sets: PendingSet[] }) {
  const [pending, setPending] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  if (sets.length === 0) return null;

  async function onAdopt(setCode: string) {
    setPending(setCode);
    setMessage(null);
    const res = await adoptSet(setCode);
    setPending(null);
    if (res.ok) {
      setDone(true);
      setMessage(
        `Adopting ${setCode}. It runs on the self-hosted runner and opens a pull request when it finishes — a few minutes.`,
      );
    } else {
      setMessage(res.reason);
    }
  }

  return (
    <Card className="border-primary/40 bg-primary/5">
      <CardContent className="flex flex-wrap items-center gap-x-4 gap-y-3 py-4">
        <PackagePlus className="size-5 shrink-0 text-primary" />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium">
            New set{sets.length > 1 ? "s" : ""} detected
          </p>
          <p className="text-sm text-muted-foreground">
            {sets.map((s) => `${s.setCode} (${s.cardCount} cards)`).join(", ")}{" "}
            — Pokémon Zone is serving{" "}
            {sets.length > 1 ? "these sets" : "this set"}, but the pipeline
            hasn&apos;t registered {sets.length > 1 ? "them" : "it"} yet, so{" "}
            {sets.length > 1 ? "their" : "its"} cards can&apos;t be classified or
            scored.
          </p>
          {message ? (
            <p className="mt-2 text-sm text-muted-foreground">{message}</p>
          ) : null}
        </div>
        <div className="flex shrink-0 gap-2">
          {sets.map((s) => (
            <Button
              key={s.setCode}
              onClick={() => onAdopt(s.setCode)}
              disabled={pending !== null || done}
            >
              {pending === s.setCode ? "Starting…" : `Adopt ${s.setCode}`}
            </Button>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
