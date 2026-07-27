import { expect, test, type Page } from "@playwright/test";

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
  await page.goto("/cards");
  const search = page.getByPlaceholder(/search cards/i).first();
  await search.waitFor();
  const countText = page.getByText(/showing \d+ of \d+/i).first();
  const before = await countText.textContent();
  await search.fill("Bulbasaur");
  await expect(countText).not.toHaveText(before ?? "");
});

test("the deck builder validates an empty deck", async ({ page }) => {
  // The rules engine wired end to end: an empty deck reports all three errors.
  await page.goto("/decks/new");
  await expect(page.getByText(/add 20 more/i)).toBeVisible();
  await expect(page.getByText(/at least 1 Basic/i)).toBeVisible();
  await expect(page.getByText(/at least 1 energy type/i)).toBeVisible();
});
