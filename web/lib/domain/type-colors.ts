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

/**
 * Ink color that stays readable on a given type color.
 *
 * The palette spans a wide lightness range — Lightning (#f2c44d) needs dark text
 * while Darkness (#4a5066) needs light — so the card viewer's type-tinted back
 * face picks per card rather than committing to one.
 *
 * sRGB relative luminance (WCAG 2.x); the 0.55 threshold is a shade above the
 * usual 0.5 because these are saturated fills, where white text holds up
 * slightly further into the midtones than the raw formula suggests.
 */
export function readableInk(hex: string): string {
  const m = /^#?([0-9a-f]{6})$/i.exec(hex);
  if (!m) return "#ffffff";
  const n = parseInt(m[1], 16);
  const channel = (c: number) => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  };
  const luminance =
    0.2126 * channel((n >> 16) & 0xff) +
    0.7152 * channel((n >> 8) & 0xff) +
    0.0722 * channel(n & 0xff);
  return luminance > 0.55 ? "#141414" : "#ffffff";
}
