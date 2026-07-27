import { existsSync } from "node:fs";

/**
 * Pipeline artifacts are gitignored, so CI runs with no data: the static shells
 * render but every cached read throws. Tests that need real cards are gated on
 * the artifacts actually being present, which is true locally and false in CI.
 * The always-on tests above still guard the shells, page errors and layout.
 */
export const HAS_PIPELINE_DATA = existsSync("../data/current/pack_ev.json");
