import { existsSync, readFileSync } from "node:fs";

/**
 * Pipeline artifacts are gitignored, so CI runs with no data: the static shells
 * render but every cached read throws. Tests that need real cards are gated on
 * the artifacts actually being present, which is true locally and false in CI.
 * The always-on tests above still guard the shells, page errors and layout.
 */
export const HAS_PIPELINE_DATA = existsSync("../data/current/pack_ev.json");


/**
 * A card name that genuinely has several printings in one printing group, or null.
 *
 * Groups are sourced from Pokémon Zone rather than inferred across the catalog,
 * so which cards are grouped depends on the collection — hardcoding a name makes
 * the test fail when the data legitimately changes.
 */
export function groupedCardName(): string | null {
  try {
    const groups = JSON.parse(
      readFileSync("../data/reference/printing_groups.json", "utf-8"),
    ) as { groups: { name: string | null; coords: [string, number][] }[] };
    const g = groups.groups.find((x) => x.coords.length > 1 && x.name);
    return g?.name ?? null;
  } catch {
    return null;
  }
}
