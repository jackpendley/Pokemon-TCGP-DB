"use server";

import { redirect } from "next/navigation";
import { updateTag } from "next/cache";

import { isOwner } from "@/lib/auth/server";
import { DECKS_TAG } from "@/lib/data/cached";
import {
  deleteDeck as deleteDeckRow,
  insertDeck,
  updateDeck as updateDeckRow,
  type DeckWrite,
} from "@/lib/data/decks";
import { deckCardRefSchema } from "@/types";
import { z } from "zod";

/**
 * Deck mutations. Public read, owner-gated write — the same posture as sync.
 *
 * Two layers guard every write and that is deliberate: this owner check gives a
 * clear message and keeps the UI honest, while the RLS policies in
 * 0006_decks.sql are the actual enforcement (writes use the cookie-bound anon
 * client, so a forged request still can't get past Postgres).
 *
 * Each mutation ends in updateTag(DECKS_TAG) rather than revalidateTag: it
 * expires the deck cache immediately so the author sees their own save instead
 * of a stale list.
 */

const deckInputSchema = z.object({
  name: z.string().trim().min(1, "Give the deck a name.").max(80),
  cards: z.array(deckCardRefSchema),
  energyTypes: z.array(z.string()),
});

export type DeckActionResult = { ok: true; id: string } | { ok: false; error: string };

async function guard(): Promise<string | null> {
  return (await isOwner()) ? null : "Sign in as the owner to manage decks.";
}

function parse(input: unknown): DeckWrite | string {
  const parsed = deckInputSchema.safeParse(input);
  if (!parsed.success) {
    return parsed.error.issues[0]?.message ?? "That deck couldn't be saved.";
  }
  return parsed.data;
}

export async function saveDeck(
  id: string | null,
  input: unknown,
): Promise<DeckActionResult> {
  const denied = await guard();
  if (denied) return { ok: false, error: denied };

  const write = parse(input);
  if (typeof write === "string") return { ok: false, error: write };

  try {
    const deckId = id ? (await updateDeckRow(id, write), id) : await insertDeck(write);
    updateTag(DECKS_TAG);
    return { ok: true, id: deckId };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "Save failed." };
  }
}

export async function deleteDeck(id: string): Promise<void> {
  const denied = await guard();
  if (denied) return;
  await deleteDeckRow(id);
  updateTag(DECKS_TAG);
  redirect("/decks");
}

/** Whether the current visitor may create or edit decks. Drives the UI. */
export async function canEditDecks(): Promise<boolean> {
  return isOwner();
}
