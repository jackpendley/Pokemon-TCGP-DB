import { describe, expect, it } from "vitest";

import {
  boostsPokemon,
  hasBoosts,
  pokemonBoostedBy,
  recommendedTrainers,
  trainersBoosting,
} from "@/lib/domain/boosts";
import type { CatalogCard, TrainerBoosts } from "@/types";

let seq = 0;

function pokemon(name: string, type: string, extra: Partial<CatalogCard> = {}) {
  seq += 1;
  return {
    set_code: "A1",
    card_number: seq,
    name,
    rarity: "common",
    pokemon_type: type,
    card_category: "Pokemon",
    trainer_subtype: null,
    stage: "Basic",
    expansion: "Genetic Apex",
    is_ex: false,
    owned: 0,
    printing_group: null,
    power_score: 40,
    power_score_kind: "pokemon",
    boosts: null,
    evolves_from: null,
    ...extra,
    // Derived last so overriding `owned` alone keeps the dex slot consistent.
    dex_owned: extra.dex_owned ?? (extra.owned ?? 0) > 0,
  } satisfies CatalogCard;
}

function trainer(
  name: string,
  boosts: TrainerBoosts | null,
  extra: Partial<CatalogCard> = {},
) {
  return pokemon(name, "Grass", {
    card_category: "Trainer",
    trainer_subtype: "Supporter",
    pokemon_type: null,
    stage: null,
    power_score: 25,
    power_score_kind: "trainer",
    boosts,
    ...extra,
  });
}

const NONE: TrainerBoosts = { names: [], types: [] };

const ninetales = pokemon("Ninetales", "Fire");
const magmar = pokemon("Magmar", "Fire");
const squirtle = pokemon("Squirtle", "Water");

const blaine = trainer("Blaine", { names: ["Ninetales", "Magmar"], types: [] });
const misty = trainer("Misty", { names: [], types: ["Water"] });
const giovanni = trainer("Giovanni", NONE);
const pokeBall = trainer("Poké Ball", null);

const CATALOG = [ninetales, magmar, squirtle, blaine, misty, giovanni, pokeBall];

describe("hasBoosts", () => {
  it("is false for a generic Trainer and for an unscored one", () => {
    // Emptiness is how "works in any deck" is encoded, so it must not count as
    // an affinity — otherwise every deck would "specifically want" Giovanni.
    expect(hasBoosts(giovanni)).toBe(false);
    expect(hasBoosts(pokeBall)).toBe(false);
  });

  it("is true once a name or a type is named", () => {
    expect(hasBoosts(blaine)).toBe(true);
    expect(hasBoosts(misty)).toBe(true);
  });
});

describe("boostsPokemon", () => {
  it("matches by name", () => {
    expect(boostsPokemon(blaine, ninetales)).toBe(true);
    expect(boostsPokemon(blaine, squirtle)).toBe(false);
  });

  it("matches by energy type", () => {
    expect(boostsPokemon(misty, squirtle)).toBe(true);
    expect(boostsPokemon(misty, ninetales)).toBe(false);
  });

  it("never matches a Pokémon with no type against a type restriction", () => {
    expect(boostsPokemon(misty, pokemon("Unown", null as never))).toBe(false);
  });
});

describe("trainersBoosting", () => {
  it("finds the Trainers that call a Pokémon out, generic ones excluded", () => {
    expect(trainersBoosting(CATALOG, ninetales).map((c) => c.name)).toEqual([
      "Blaine",
    ]);
    expect(trainersBoosting(CATALOG, squirtle).map((c) => c.name)).toEqual(["Misty"]);
  });

  it("returns nothing for a Trainer, which has no boosters of its own", () => {
    expect(trainersBoosting(CATALOG, blaine)).toEqual([]);
  });

  it("orders by utility score", () => {
    const weak = trainer("Weak Ally", { names: ["Ninetales"], types: [] }, {
      power_score: 10,
    });
    const strong = trainer("Strong Ally", { names: ["Ninetales"], types: [] }, {
      power_score: 60,
    });
    expect(
      trainersBoosting([...CATALOG, weak, strong], ninetales).map((c) => c.name),
    ).toEqual(["Strong Ally", "Blaine", "Weak Ally"]);
  });
});

describe("pokemonBoostedBy", () => {
  it("resolves a name list to cards", () => {
    expect(pokemonBoostedBy(CATALOG, blaine).map((c) => c.name).sort()).toEqual([
      "Magmar",
      "Ninetales",
    ]);
  });

  it("resolves a type restriction to every Pokémon of that type", () => {
    expect(pokemonBoostedBy(CATALOG, misty).map((c) => c.name)).toEqual(["Squirtle"]);
  });

  it("puts owned cards first", () => {
    const owned = pokemon("Rapidash", "Fire", { owned: 3 });
    const blaine2 = trainer("Blaine", {
      names: ["Ninetales", "Rapidash"],
      types: [],
    });
    expect(
      pokemonBoostedBy([...CATALOG, owned], blaine2).map((c) => c.name),
    ).toEqual(["Rapidash", "Ninetales"]);
  });

  it("returns nothing for a generic Trainer", () => {
    expect(pokemonBoostedBy(CATALOG, giovanni)).toEqual([]);
  });
});

describe("recommendedTrainers", () => {
  it("matches on either the deck's Pokémon names or its energy types", () => {
    expect(
      recommendedTrainers(CATALOG, {
        names: ["Ninetales"],
        types: [],
      }).map((c) => c.name),
    ).toEqual(["Blaine"]);
    expect(
      recommendedTrainers(CATALOG, { names: [], types: ["Water"] }).map((c) => c.name),
    ).toEqual(["Misty"]);
  });

  it("recommends nothing for an empty deck rather than everything", () => {
    expect(recommendedTrainers(CATALOG, { names: [], types: [] })).toEqual([]);
  });

  it("excludes cards already in the deck", () => {
    expect(
      recommendedTrainers(CATALOG, {
        names: ["Ninetales"],
        types: [],
        inDeck: new Set(["Blaine"]),
      }),
    ).toEqual([]);
  });

  it("collapses reprints to one row, preferring a printing you own", () => {
    const reprint = trainer("Misty", { names: [], types: ["Water"] }, {
      set_code: "A4b",
      owned: 2,
    });
    const rows = recommendedTrainers([...CATALOG, reprint], {
      names: [],
      types: ["Water"],
    });
    expect(rows).toHaveLength(1);
    expect(rows[0].set_code).toBe("A4b");
  });
});
