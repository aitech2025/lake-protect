/**
 * The demo, start to finish, with two roles (DECISIONS.md D-057), on one machine with no internet.
 * Any request that leaves localhost fails the test. Run on a fresh demo (sh scripts/e2e.sh m9-demo).
 */
import { expect, test, type BrowserContext, type Page } from "@playwright/test";
import { shot } from "./helpers";

const external: string[] = [];

async function guard(context: BrowserContext): Promise<void> {
  await context.route("**/*", (route) => {
    const url = new URL(route.request().url());
    if (url.hostname === "localhost" || url.protocol === "data:" || url.protocol === "blob:") return route.continue();
    external.push(route.request().url());
    return route.abort();
  });
}

async function signIn(page: Page, username: string): Promise<void> {
  await page.evaluate(() => { localStorage.removeItem("lp.token"); localStorage.removeItem("lp.user"); localStorage.setItem("lp.lang", "en"); });
  await page.goto("/login");
  await page.getByTestId(`login-${username}`).click();
  await expect(page).toHaveURL(/\/alerts$/);
}

async function openIncident(page: Page, assetName: string): Promise<void> {
  await page.goto("/alerts");
  await page.locator('[data-testid^="alert-row-"]', { hasText: assetName }).first().click();
  await expect(page.getByTestId("alert-detail")).toBeVisible();
}

test("the demo runs end to end with two roles and no internet", async ({ browser }) => {
  test.setTimeout(240_000);
  const desk = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  await guard(desk);
  const page = await desk.newPage();
  await page.goto("/login");

  // 0. Demo data, and only two kinds of account.
  await expect(page.getByTestId("demo-badge")).toContainText("Demo data");
  await expect(page.locator('[data-testid^="login-"]')).toHaveCount(3);
  await page.screenshot({ path: shot("m12-00-sign-in") });

  // 1. An official opens a lake: week by week, with images, and its legal documents.
  await signIn(page, "demo.viewer2");
  await page.goto("/assets");
  await expect(page.locator(".list .row")).toHaveCount(20);
  await page.locator(".list .row", { hasText: "Demo Cheruvu 1" }).first().click();
  const weeks = page.getByTestId("weekly-record");
  await expect(weeks.locator("li.week")).toHaveCount(8);
  const latest = weeks.locator("li.week").first();
  await expect(latest).toContainText("Change found");
  await expect(latest).toContainText("Land fill");
  await expect.poll(() => weeks.locator("img").evaluateAll((els) => els.filter((e) => (e as HTMLImageElement).naturalWidth > 0).length)).toBeGreaterThan(3);
  await expect(page.getByTestId("documents")).toContainText("Recovery order");
  await weeks.scrollIntoViewIfNeeded();
  await page.screenshot({ path: shot("m12-01-week-by-week") });

  // 2. The new incident says plainly what changed, with the image pair and dates.
  await openIncident(page, "Demo Cheruvu 1");
  await expect(page.getByTestId("change-summary")).toContainText("Land fill of about");
  const imgs = page.getByTestId("image-pair").locator("img");
  await expect.poll(() => imgs.evaluateAll((els) => els.filter((e) => (e as HTMLImageElement).naturalWidth > 0).length)).toBe(2);
  await expect(page.getByTestId("dated-bracket")).toContainText("Last clear");
  await expect(page.getByTestId("legal-panel")).toContainText("Court register");
  // The official records a review; the incident moves to "Under review".
  await expect(page.getByTestId("action-CONFIRMED")).toHaveCount(0);
  await page.getByTestId("review-real_change").check();
  await page.getByTestId("review-note").fill("Fresh soil at the north-east edge on both images.");
  await page.getByTestId("review-submit").click();
  await expect(page.locator(".detail-head .pill")).toHaveAttribute("data-state", "UNDER_REVIEW");
  await expect(page.getByTestId("reviews")).toContainText("Fresh soil at the north-east edge");
  await page.screenshot({ path: shot("m12-02-review"), fullPage: true });

  // 3. What changed, by type, and the incidents that stop or are flagged.
  await page.goto("/alerts");
  await page.getByTestId("filter-change").selectOption("levelling");
  await expect(page.getByTestId("alert-list")).toContainText("Demo Parcel C");
  await page.getByTestId("filter-change").selectOption("");
  await page.getByTestId("group-DISMISSED").click();
  await expect(page.getByTestId("alert-list")).toContainText("Demo Cheruvu 6");
  await page.getByTestId("group-CLOSED").click();
  await expect(page.getByTestId("alert-list")).toContainText("Closed by the legal check");
  await page.getByTestId("group-active").click();
  await expect(page.locator('[data-testid^="alert-row-"]', { hasText: "Demo Cheruvu 7" })).toContainText("Court case");
  await page.screenshot({ path: shot("m12-03-incidents") });

  // 4. The admin decides: confirmed, with a note; then the evidence pack.
  await signIn(page, "demo.admin");
  await openIncident(page, "Demo Cheruvu 1");
  await page.getByTestId("action-CONFIRMED").click();
  await page.getByTestId("input-note").fill("Real change: fill inside recovered land, as the review says.");
  await page.getByTestId("submit-action").click();
  await expect(page.locator(".detail-head .pill")).toHaveAttribute("data-state", "CONFIRMED");
  await page.getByTestId("pack-generate").click();
  await expect(page.getByTestId("pack-pdf")).toBeVisible({ timeout: 60_000 });
  await page.screenshot({ path: shot("m12-04-confirmed-pack"), fullPage: true });

  // 5. The admin tags a legal document to the lake.
  await page.goto("/assets");
  await page.locator(".list .row", { hasText: "Demo Cheruvu 1" }).first().click();
  await page.getByTestId("doc-add").click();
  await page.getByTestId("doc-form").locator("select").selectOption("court_order");
  await page.getByTestId("doc-title").fill("Demo stay order");
  await page.getByTestId("doc-form").locator("input").nth(1).fill("DEMO-WP-9999/2026");
  await page.getByTestId("doc-form").getByRole("button", { name: "Save document" }).click();
  await expect(page.getByTestId("documents")).toContainText("DEMO-WP-9999/2026");

  // 6. The monthly page, for an official.
  await signIn(page, "demo.viewer2");
  await page.goto("/monthly");
  await expect(page.getByTestId("figure-new_alerts").locator("b")).not.toHaveText("");
  await expect(page.getByTestId("waiting-list")).toContainText("Demo Cheruvu 9");
  await page.screenshot({ path: shot("m12-05-monthly"), fullPage: true });

  // 7. The first official works in Telugu.
  await page.evaluate(() => { localStorage.removeItem("lp.token"); localStorage.removeItem("lp.user"); });
  await page.goto("/login");
  await page.getByTestId("login-demo.viewer1").click();
  await expect(page.getByRole("link", { name: "సంఘటనలు" })).toBeVisible();
  await page.screenshot({ path: shot("m12-06-telugu") });

  expect(external).toEqual([]);
  await desk.close();
});
