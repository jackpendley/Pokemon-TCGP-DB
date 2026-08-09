import "server-only";

import { createClient } from "@supabase/supabase-js";

import { createSupabaseServerClient } from "@/lib/auth/server";
import { env } from "@/lib/env";
import { storedDeckSchema, type DeckCardRef, type StoredDeck } from "@/types";

/**
 * Deck persistence.
 *
 * Deliberately *not* part of the DataSource seam. That interface mirrors the
 * pipeline's published artifacts and has a local-json implementation for parity;
 * decks are authored in the app, exist only in Supabase, and are written at
 * request time. Forcing them through DataSource would mean inventing a
 * meaningless local-json half.
 *
 * Reads use the service-role key (like the rest of lib/data). Writes go through
 * the cookie-bound client so the RLS policies in 0006_decks.sql are what
 * actually enforce ownership — the app never decides on its own that a write is
 * allowed.
 */

const DECK_COLUMNS = "id, name, cards, energy_types, created_at, updated_at";

function serviceClient() {
  if (!env.SUPABASE_URL || !env.SUPABASE_SERVICE_ROLE_KEY) return null;
  return createClient(env.SUPABASE_URL, env.SUPABASE_SERVICE_ROLE_KEY, {
    auth: { persistSession: false },
  });
}

/**
 * Every saved deck, newest first. Returns [] when Supabase isn't configured —
 * that's local-json dev, where decks simply don't exist rather than erroring.
 */
export async function fetchDecks(): Promise<StoredDeck[]> {
  const client = serviceClient();
  if (!client) return [];
  const { data, error } = await client
    .from("decks")
    .select(DECK_COLUMNS)
    .order("updated_at", { ascending: false });
  if (error) throw new Error(`Failed to load decks: ${error.message}`);
  return (data ?? []).map((row) => storedDeckSchema.parse(row));
}

export async function fetchDeck(id: string): Promise<StoredDeck | null> {
  const client = serviceClient();
  if (!client) return null;
  const { data, error } = await client
    .from("decks")
    .select(DECK_COLUMNS)
    .eq("id", id)
    .maybeSingle();
  if (error) throw new Error(`Failed to load deck: ${error.message}`);
  return data ? storedDeckSchema.parse(data) : null;
}

export interface DeckWrite {
  name: string;
  cards: DeckCardRef[];
  energyTypes: string[];
}

/** Creates a deck owned by the signed-in user. RLS rejects an unauthenticated call. */
export async function insertDeck(input: DeckWrite): Promise<string> {
  const supabase = await createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) throw new Error("Sign in to save a deck.");

  const { data, error } = await supabase
    .from("decks")
    .insert({
      user_id: user.id,
      name: input.name,
      cards: input.cards,
      energy_types: input.energyTypes,
    })
    .select("id")
    .single();
  if (error) throw new Error(`Failed to save deck: ${error.message}`);
  return data.id as string;
}

export async function updateDeck(id: string, input: DeckWrite): Promise<void> {
  const supabase = await createSupabaseServerClient();
  const { error } = await supabase
    .from("decks")
    .update({
      name: input.name,
      cards: input.cards,
      energy_types: input.energyTypes,
      updated_at: new Date().toISOString(),
    })
    .eq("id", id);
  if (error) throw new Error(`Failed to update deck: ${error.message}`);
}

export async function deleteDeck(id: string): Promise<void> {
  const supabase = await createSupabaseServerClient();
  const { error } = await supabase.from("decks").delete().eq("id", id);
  if (error) throw new Error(`Failed to delete deck: ${error.message}`);
}
