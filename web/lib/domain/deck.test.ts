import { describe, expect, it } from "vitest";

import {
  DECK_SIZE,
  type Deck,
  copiesByName,
  deckCardCount,
  deckRatioHint,
  deckSummary,
  isDeckLegal,
  ownedByName,
  validateDeck,
  type DeckSlot,
} from "@/lib/domain/deck";
import type { CatalogCard } from "@/types";

let seq = 0;

function card(partial: Partial<CatalogCard> & { name: string }): CatalogCard {
  seq += 1;
  return {
    set_code: "A1",
    card_number: seq,
    rarity: "common",
    pokemon_type: "Grass",
    card_category: "Pokemon",
    trainer_subtype: null,
    stage: "Basic",
    expansion: "Genetic Apex",
    is_ex: false,
    owned: 0,
    printing_group: null,
    power_score: 30,
    power_score_kind: "pokemon",
    boosts: null,
    evolves_from: null,
    ...partial,
    // Derived last so overriding `owned` alone keeps the dex slot consistent.
    dex_owned: partial.dex_owned ?? (partial.owned ?? 0) > 0,
  };
}

const trainer = (name: string, extra: Partial<CatalogCard> = {}) =>
  card({
    name,
    card_category: "Trainer",
    trainer_subtype: "Supporter",
    pokemon_type: null,
    stage: null,
    power_score: 25,
    power_score_kind: "trainer",
    ...extra,
  });

/** A legal 20-card deck: 1 Basic ×2, filled out with distinct Trainers. */
function legalDeck(overrides: Partial<Deck> = {}): Deck {
  const entries = [{ card: card({ name: "Bulbasaur" }), count: 2 }];
  for (let i = 0; i < 9; i += 1) {
    entries.push({ card: trainer(`Filler ${i}`), count: 2 });
  }
  return { entries, energyTypes: ["Grass"], ...overrides };
}

const codes = (deck: Deck) => validateDeck(deck).map((i) => i.code);

describe("counting", () => {
  it("counts copies, not distinct cards", () => {
    expect(deckCardCount(legalDeck())).toBe(DECK_SIZE);
  });

  it("aggregates copies by name across different printings", () => {
    // The same card from two sets is still that card, twice over.
    const deck: Deck = {
      entries: [
        { card: card({ name: "Poké Ball", set_code: "A1" }), count: 1 },
        { card: card({ name: "Poké Ball", set_code: "PROMO-A" }), count: 1 },
      ],
      energyTypes: ["Grass"],
    };
    expect(copiesByName(deck).get("Poké Ball")).toBe(2);
  });
});

describe("deck size", () => {
  it("accepts exactly 20", () => {
    expect(codes(legalDeck())).not.toContain("deck-size");
    expect(isDeckLegal(legalDeck())).toBe(true);
  });

  it("rejects 19 and 21", () => {
    const short = legalDeck();
    short.entries[0].count = 1;
    expect(codes(short)).toContain("deck-size");

    const long = legalDeck();
    long.entries[0].count = 3;
    expect(codes(long)).toContain("deck-size");
  });

  it("says how many to add or remove", () => {
    const short = legalDeck();
    short.entries[0].count = 1;
    const issue = validateDeck(short).find((i) => i.code === "deck-size");
    expect(issue?.message).toContain("add 1");
  });
});

describe("copy limit", () => {
  it("allows two copies of a name", () => {
    expect(codes(legalDeck())).not.toContain("copy-limit");
  });

  it("rejects three copies spread across different printings", () => {
    // The rule is per card name — splitting copies across sets must not evade it.
    const deck: Deck = {
      entries: [
        { card: card({ name: "Bulbasaur", set_code: "A1" }), count: 2 },
        { card: card({ name: "Bulbasaur", set_code: "PROMO-A" }), count: 1 },
        { card: trainer("Filler"), count: 2 },
      ],
      energyTypes: ["Grass"],
    };
    const issue = validateDeck(deck).find((i) => i.code === "copy-limit");
    expect(issue).toBeDefined();
    expect(issue?.cards).toContain("Bulbasaur");
    expect(isDeckLegal(deck)).toBe(false);
  });
});

describe("basic Pokémon requirement", () => {
  it("errors when every Pokémon is an evolution", () => {
    const deck = legalDeck();
    deck.entries[0] = {
      card: card({ name: "Ivysaur", stage: "Stage1", evolves_from: "Bulbasaur" }),
      count: 2,
    };
    expect(codes(deck)).toContain("no-basic");
    expect(isDeckLegal(deck)).toBe(false);
  });

  it("errors when the deck holds no Pokémon at all", () => {
    const deck: Deck = {
      entries: [{ card: trainer("Filler"), count: 20 }],
      energyTypes: ["Grass"],
    };
    expect(codes(deck)).toContain("no-basic");
  });

  it("warns instead of erroring when a stage is simply unrecorded", () => {
    // 190 Pokémon in the reference have no stage; claiming "no Basic" for those
    // would be confidently wrong rather than unknown.
    const deck = legalDeck();
    deck.entries[0] = { card: card({ name: "Mystery", stage: null }), count: 2 };
    const found = codes(deck);
    expect(found).toContain("unverifiable-basic");
    expect(found).not.toContain("no-basic");
    expect(isDeckLegal(deck)).toBe(true);
  });
});

describe("energy zone", () => {
  it("requires at least one type", () => {
    expect(codes(legalDeck({ energyTypes: [] }))).toContain("energy-none");
  });

  it("rejects more than three types", () => {
    const deck = legalDeck({
      energyTypes: ["Grass", "Fire", "Water", "Lightning"],
    });
    expect(codes(deck)).toContain("energy-too-many");
    expect(isDeckLegal(deck)).toBe(false);
  });

  it("warns when a Pokémon's type isn't generated", () => {
    const deck = legalDeck({ energyTypes: ["Water"] });
    const issue = validateDeck(deck).find((i) => i.code === "energy-mismatch");
    expect(issue?.cards).toContain("Bulbasaur");
    // Unplayable, but the game still lets you register it.
    expect(issue?.severity).toBe("warning");
  });

  it("never flags Colorless Pokémon, which any energy pays for", () => {
    const deck = legalDeck({ energyTypes: ["Water"] });
    deck.entries[0] = {
      card: card({ name: "Eevee", pokemon_type: "Colorless" }),
      count: 2,
    };
    expect(codes(deck)).not.toContain("energy-mismatch");
  });

  it("warns about a selected type no Pokémon uses", () => {
    const deck = legalDeck({ energyTypes: ["Grass", "Metal"] });
    expect(codes(deck)).toContain("energy-unused");
  });

  it("does not report unused energy when nothing at all matches", () => {
    // That case is already covered by energy-mismatch; saying both is noise.
    const deck = legalDeck({ energyTypes: ["Water"] });
    expect(codes(deck)).not.toContain("energy-unused");
  });
});

describe("evolution lines", () => {
  it("warns when an evolution has no parent in the deck", () => {
    const deck = legalDeck();
    deck.entries[0] = {
      card: card({ name: "Ivysaur", stage: "Stage1", evolves_from: "Bulbasaur" }),
      count: 1,
    };
    deck.entries.push({ card: card({ name: "Oddish" }), count: 1 });
    const issue = validateDeck(deck).find(
      (i) => i.code === "missing-evolution-parent",
    );
    expect(issue?.cards).toContain("Ivysaur");
    expect(issue?.severity).toBe("warning");
  });

  it("is satisfied when the parent is present", () => {
    const deck = legalDeck();
    deck.entries[0] = { card: card({ name: "Bulbasaur" }), count: 1 };
    deck.entries.push({
      card: card({ name: "Ivysaur", stage: "Stage1", evolves_from: "Bulbasaur" }),
      count: 1,
    });
    expect(codes(deck)).not.toContain("missing-evolution-parent");
  });

  it("resolves ex and Mega names to their base species", () => {
    const deck = legalDeck();
    deck.entries[0] = { card: card({ name: "Venusaur ex" }), count: 1 };
    deck.entries.push({
      card: card({
        name: "Mega Venusaur ex",
        stage: "Stage2",
        evolves_from: "Venusaur ex",
      }),
      count: 1,
    });
    expect(codes(deck)).not.toContain("missing-evolution-parent");
  });
});

describe("issue ordering", () => {
  it("puts errors before warnings", () => {
    const deck = legalDeck({ energyTypes: ["Water"] });
    deck.entries[0].count = 1; // wrong size (error) + energy mismatch (warning)
    const severities = validateDeck(deck).map((i) => i.severity);
    expect(severities.indexOf("error")).toBeLessThan(severities.indexOf("warning"));
  });
});

describe("ownedByName", () => {
  it("sums copies across printings", () => {
    const catalog = [
      card({ name: "Poké Ball", set_code: "A1", owned: 1 }),
      card({ name: "Poké Ball", set_code: "PROMO-A", owned: 2 }),
      card({ name: "Unowned", owned: 0 }),
    ];
    const owned = ownedByName(catalog);
    expect(owned.get("Poké Ball")).toBe(3);
    expect(owned.has("Unowned")).toBe(false);
  });
});

describe("deckSummary", () => {
  const buildable = card({ name: "Bulbasaur", owned: 2 });

  it("splits Pokémon from Trainers and tallies stages", () => {
    const deck: Deck = {
      entries: [
        { card: buildable, count: 2 },
        { card: card({ name: "Ivysaur", stage: "Stage1" }), count: 1 },
        { card: trainer("Professor's Research"), count: 2 },
      ],
      energyTypes: ["Grass"],
    };
    const s = deckSummary(deck, [buildable]);
    expect(s.total).toBe(5);
    expect(s.pokemon).toBe(3);
    expect(s.trainers).toBe(2);
    expect(s.stageCounts).toEqual({ Basic: 2, Stage1: 1 });
  });

  it("keeps the two score scales apart", () => {
    const deck: Deck = {
      entries: [
        { card: card({ name: "Strong", power_score: 80 }), count: 1 },
        { card: trainer("Useful", { power_score: 20 }), count: 1 },
      ],
      energyTypes: ["Grass"],
    };
    const s = deckSummary(deck, []);
    expect(s.averagePokemonPower).toBe(80);
    expect(s.averageTrainerUtility).toBe(20);
  });

  it("reports null averages rather than zero when a kind is absent", () => {
    const deck: Deck = {
      entries: [{ card: card({ name: "Only Pokémon" }), count: 1 }],
      energyTypes: ["Grass"],
    };
    expect(deckSummary(deck, []).averageTrainerUtility).toBeNull();
  });

  it("weights the average by copies", () => {
    const deck: Deck = {
      entries: [
        { card: card({ name: "A", power_score: 90 }), count: 3 },
        { card: card({ name: "B", power_score: 10 }), count: 1 },
      ],
      energyTypes: ["Grass"],
    };
    expect(deckSummary(deck, []).averagePokemonPower).toBe(70);
  });

  it("lists cards you're short of, worst first", () => {
    const catalog = [
      card({ name: "Bulbasaur", owned: 1 }),
      card({ name: "Rare Thing", owned: 0 }),
    ];
    const deck: Deck = {
      entries: [
        { card: card({ name: "Bulbasaur" }), count: 2 },
        { card: card({ name: "Rare Thing" }), count: 2 },
      ],
      energyTypes: ["Grass"],
    };
    const s = deckSummary(deck, catalog);
    expect(s.missing.map((m) => m.name)).toEqual(["Rare Thing", "Bulbasaur"]);
    expect(s.missing[0]).toMatchObject({ needed: 2, owned: 0, short: 2 });
  });

  it("counts ownership across printings when deciding what's missing", () => {
    const catalog = [
      card({ name: "Poké Ball", set_code: "A1", owned: 1 }),
      card({ name: "Poké Ball", set_code: "PROMO-A", owned: 1 }),
    ];
    const deck: Deck = {
      entries: [{ card: card({ name: "Poké Ball" }), count: 2 }],
      energyTypes: ["Grass"],
    };
    expect(deckSummary(deck, catalog).missing).toEqual([]);
  });
});

describe("ratio guidance", () => {
  /** A full 20-card deck with the requested split. */
  function split(pokemon: number, trainers: number): Deck {
    const entries: DeckSlot[] = [];
    for (let i = 0; i < pokemon; i += 1) {
      entries.push({ card: card({ name: `Mon ${i}` }), count: 1 });
    }
    for (let i = 0; i < trainers; i += 1) {
      entries.push({ card: trainer(`Item ${i}`), count: 1 });
    }
    return { entries, energyTypes: ["Grass"] };
  }

  it("says nothing about a typical split", () => {
    for (const [p, t] of [
      [8, 12],
      [10, 10],
      [12, 8],
    ]) {
      expect(deckRatioHint(summaryOf(split(p, t))), `${p}/${t}`).toBeNull();
    }
  });

  it("nudges a Pokémon-heavy deck", () => {
    // Legal — there is no Trainer minimum — but usually a mistake.
    expect(deckRatioHint(summaryOf(split(20, 0)))).toMatch(/20 Pokémon is a lot/);
    expect(deckRatioHint(summaryOf(split(13, 7)))).toMatch(/13 Pokémon/);
  });

  it("nudges a Trainer-heavy deck about its Bench", () => {
    expect(deckRatioHint(summaryOf(split(4, 16)))).toMatch(/Only 4 Pokémon/);
    expect(deckRatioHint(summaryOf(split(7, 13)))).toMatch(/empty Bench/);
  });

  it("prefers the Pokémon-heavy message when both ends could apply", () => {
    // 15/5 is over the top of the band, so it reads as too many Pokémon — not as
    // too few Trainers, which in a fixed-20 deck is the same fact said backwards.
    expect(deckRatioHint(summaryOf(split(15, 5)))).toMatch(/15 Pokémon is a lot/);
  });

  it("stays quiet while the deck is still being built", () => {
    // 0 Trainers in a 4-card deck is not yet a Trainer problem.
    expect(deckRatioHint(summaryOf(split(4, 0)))).toBeNull();
    expect(deckRatioHint({ total: 0, pokemon: 0, trainers: 0 })).toBeNull();
  });

  it("reaches the summary, which is where it is rendered", () => {
    expect(deckSummary(split(20, 0), []).ratioHint).toMatch(/Pokémon is a lot/);
    expect(deckSummary(split(10, 10), []).ratioHint).toBeNull();
  });

  it("never makes a deck illegal", () => {
    // The whole point: guidance cannot block registration.
    const heavy = split(20, 0);
    expect(deckRatioHint(summaryOf(heavy))).not.toBeNull();
    expect(isDeckLegal(heavy)).toBe(true);
    expect(validateDeck(heavy)).toEqual([]);
  });
});

function summaryOf(deck: Deck) {
  const s = deckSummary(deck, []);
  return { total: s.total, pokemon: s.pokemon, trainers: s.trainers };
}
