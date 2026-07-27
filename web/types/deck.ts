import { z } from "zod";

/**
 * A saved deck, as stored in supabase/migrations/0006_decks.sql.
 *
 * Cards are held as set coordinates plus a count rather than foreign keys, so a
 * deck survives a card-reference rebuild; the catalog join happens in the app.
 * Deck *legality* is not enforced here — that lives in lib/domain/deck.ts, which
 * is the single owner of the rules.
 */
export const deckCardRefSchema = z.object({
  set_code: z.string(),
  card_number: z.number(),
  count: z.number().int().positive(),
});

export type DeckCardRef = z.infer<typeof deckCardRefSchema>;

export const storedDeckSchema = z.object({
  id: z.string(),
  name: z.string(),
  cards: z.array(deckCardRefSchema),
  energy_types: z.array(z.string()),
  created_at: z.string(),
  updated_at: z.string(),
});

export type StoredDeck = z.infer<typeof storedDeckSchema>;
