import { expect, test, type Page } from "@playwright/test";

import { HAS_PIPELINE_DATA } from "./fixtures";

/**
 * Every page must render its own heading with no page errors.
 *
 * next-themes mutates <html> before paint, which React reports as a recovered
 * hydration error (#418) in production builds. It predates this suite and is
 * not a failure, so it's filtered rather than allowed to mask real errors.
 */
const KNOWN_RECOVERABLE = /Minified React error #418/;

function collectErrors(page: Page): string[] {
  const errors: string[] = [];
  page.on("pageerror", (e) => {
    if (!KNOWN_RECOVERABLE.test(String(e))) errors.push(String(e));
  });
  return errors;
}

const ROUTES = [
  { path: "/", heading: "Dashboard" },
  { path: "/packs", heading: "Pack Recommendations" },
  { path: "/cards", heading: "Cards" },
  { path: "/sets", heading: "Set Completion" },
  { path: "/decks", heading: "Decks" },
  { path: "/history", heading: "History" },
];

for (const { path, heading } of ROUTES) {
  test(`${path} renders its heading without page errors`, async ({ page }) => {
    const errors = collectErrors(page);
    await page.goto(path);
    await expect(
      page.getByRole("heading", { name: heading, level: 1 }).first(),
    ).toBeVisible();
    expect(errors).toEqual([]);
  });
}

test("/login renders its card without page errors", async ({ page }) => {
  // The only route with no <h1> — it's a centred card, not a page heading.
  const errors = collectErrors(page);
  await page.goto("/login");
  await expect(page.getByText("Owner sign-in")).toBeVisible();
  expect(errors).toEqual([]);
});

test("the page never scrolls horizontally", async ({ page }) => {
  // The layout guarantee that matters most on a phone.
  for (const { path } of [...ROUTES, { path: "/login" }]) {
    await page.goto(path);
    const overflow = await page.evaluate(
      () =>
        document.documentElement.scrollWidth >
        document.documentElement.clientWidth,
    );
    expect(overflow, `${path} overflows horizontally`).toBe(false);
  }
});

test("cards search filters the grid", async ({ page }) => {
  test.skip(!HAS_PIPELINE_DATA, "needs pipeline artifacts");
  await page.goto("/cards");
  const search = page.getByPlaceholder(/search cards/i).first();
  await search.waitFor();
  const countText = page.getByText(/showing \d+ of \d+/i).first();
  const before = await countText.textContent();
  await search.fill("Bulbasaur");
  await expect(countText).not.toHaveText(before ?? "");
});

test("the deck builder validates an empty deck", async ({ page }) => {
  test.skip(!HAS_PIPELINE_DATA, "needs pipeline artifacts");
  // The rules engine wired end to end: an empty deck reports all three errors.
  await page.goto("/decks/new");
  await expect(page.getByText(/add 20 more/i)).toBeVisible();
  await expect(page.getByText(/at least 1 Basic/i)).toBeVisible();
  await expect(page.getByText(/at least 1 energy type/i)).toBeVisible();
});

test("a long card name never stretches its tile past the grid", async ({ page }) => {
  test.skip(!HAS_PIPELINE_DATA, "needs pipeline artifacts");
  /*
   * Regression: a <button> sizes to fit-content, so a tile whose label was wider
   * than its grid track grew to the label's width and overlapped its neighbours
   * — Ancient Booster Energy Capsule rendered 211px wide in an 85px track. Only
   * long names were affected, which is why it showed up while filtering Trainers.
   */
  for (const path of ["/decks/new", "/cards"]) {
    await page.goto(path);
    const search = page.getByPlaceholder(/search cards/i).first();
    await search.waitFor();
    // The longest card names in the game, and the ones originally reported.
    await search.fill("Booster Energy");
    const overflowing = await page
      .locator("button")
      .filter({ has: page.locator('[class*="aspect-[5/7]"]') })
      // Annotated: evaluateAll widens to HTMLElement | SVGElement, and these are
      // all <button>s by construction.
      .evaluateAll((buttons: HTMLElement[]) =>
        buttons
          .filter((b) => {
            const parent = b.parentElement;
            return parent != null && b.offsetWidth > parent.offsetWidth + 1;
          })
          .map((b) => `${(b.textContent ?? "").slice(0, 40)} @ ${b.offsetWidth}px`),
      );
    expect(overflowing, `${path} has tiles wider than their track`).toEqual([]);
  }
});

test("a picker tile reads as one line of name plus owned count", async ({
  page,
}) => {
  test.skip(!HAS_PIPELINE_DATA, "needs pipeline artifacts");
  // Was three pieces over two lines: name, "N owned"/"none owned", and the score.
  await page.goto("/decks/new");
  const search = page.getByPlaceholder(/search cards/i).first();
  await search.waitFor();
  await search.fill("Pikachu");
  const tiles = page.locator('button[title^="Add "]');
  await tiles.first().waitFor();

  const texts = await tiles.allInnerTexts();
  expect(texts.join("\n")).not.toMatch(/owned/i);
  // At least one Pikachu printing is held, and it reads as a bare "Nx" chip.
  expect(texts.some((t) => /^Pikachu[\s\S]*\n\d+x$/.test(t))).toBe(true);
});

test("a Trainer card shows what it boosts", async ({ page }, testInfo) => {
  test.skip(!HAS_PIPELINE_DATA, "needs pipeline artifacts");
  // The mobile viewer keeps the tabs in a sheet, reached by swipe or button.
  const openTabs = async () => {
    if (testInfo.project.name === "mobile") {
      await page.getByLabel("Show related cards").click();
    }
  };
  // Erika's rule text is restricted to "your {G} Pokémon", so the relationship
  // has to survive the pipeline → artifact → catalog → tabs path.
  await page.goto("/cards");
  const search = page.getByPlaceholder(/search cards/i).first();
  await search.waitFor();
  await search.fill("Erika");
  await page.getByRole("button", { name: /Erika/ }).first().click();
  await openTabs();
  await expect(page.getByRole("tab", { name: /Boosts/ })).toBeVisible();
});

test("a boosted Pokémon shows the Trainers that help it", async ({
  page,
}, testInfo) => {
  test.skip(!HAS_PIPELINE_DATA, "needs pipeline artifacts");
  const openTabs = async () => {
    if (testInfo.project.name === "mobile") {
      await page.getByLabel("Show related cards").click();
    }
  };
  // The inverse direction: Pawmot is named by Nemona.
  await page.goto("/cards");
  const search = page.getByPlaceholder(/search cards/i).first();
  await search.waitFor();
  await search.fill("Pawmot");
  await page.getByRole("button", { name: /Pawmot/ }).first().click();
  await openTabs();
  await expect(page.getByRole("tab", { name: /Trainers that help/ })).toBeVisible();
});
