/**
 * Pokémon energy-type → color, approximating the in-game energy colors.
 * Shared by the dashboard pie chart and (later) type badges. Hex so it can feed
 * recharts fills and inline styles directly.
 */
export const TYPE_COLORS: Record<string, string> = {
  Grass: "#5fb35a",
  Fire: "#e2553f",
  Water: "#4f92d6",
  Lightning: "#f2c44d",
  Psychic: "#b163b1",
  Fighting: "#ce5a2e",
  Darkness: "#4a5066",
  Metal: "#8a93a3",
  Dragon: "#c9a227",
  Colorless: "#b3a690",
};

const FALLBACK = "#9aa0aa";

export function typeColor(type: string | null | undefined): string {
  if (!type) return FALLBACK;
  return TYPE_COLORS[type] ?? FALLBACK;
}
