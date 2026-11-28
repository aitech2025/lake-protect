/**
 * The desk, start to finish, on real data with the two role accounts (DECISIONS.md D-057, D-065),
 * on one machine with no internet: any request that leaves localhost fails the test, except the
 * online street map, which the Map and Overview try first and do without (D-068).
 * An official reviews the top real incident from the saved screen; the admin dismisses and closes
 * it as a browser check; the monthly page and the audit log follow. Run on the preview stack and
 * reset it afterwards (README): the steps are test records.
 */
import { expect, test, type BrowserContext, type Page } from "@playwright/test";
import { shot } from "./helpers";

const external: string[] = [];
// The Map and Overview try the online street map first and fall back to local files (D-068).
const BASE_MAP = /^https:\/\/tiles\.openfreemap\.org\//;

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
  await expect(page).toHaveURL(/\/(dashboard|alerts)$/); // a field officer starts at their field visits (D-067)
}

test("the desk runs on real data with four personas and no internet", async ({ browser }) => {
  test.setTimeout(180_000);
  const desk = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  await guard(desk);
  const page = await desk.newPage();
  await page.goto("/login");

  // 0. The persona accounts (D-067), and nothing marked as demo data.
  await expect(page.locator('[data-testid^="login-"]')).toHaveCount(6);
  await expect(page.getByTestId("demo-badge")).toHaveCount(0);
  await page.screenshot({ path: shot("m18-10-login"), fullPage: true });

  // 1. The district officer: the overview, the inbox, then the top incident in their districts.
  await signIn(page, "demo.district2");
  await expect(page.getByTestId("dash-figures")).toBeVisible();
  // With no internet the overview map falls back to the local world outlines and satellite tiles.
  await expect(page.getByTestId("dashboard-map").locator("canvas")).toBeVisible();
  await page.getByTestId("nav-inbox").click();
  await expect(page.getByTestId("inbox")).toBeVisible();
  await page.getByTestId("nav-alerts").click();
  const first = page.locator('[data-testid^="alert-row-"]').first();
  await expect(first).toBeVisible();
  await first.click();
  await expect(page.getByTestId("alert-detail")).toBeVisible();
  await expect(page.getByTestId("detail-map")).toBeVisible();
  await expect(page.getByTestId("statement")).toBeVisible();
  const url = page.url();
  await page.getByTestId("review-needs_site_visit").check();
  await page.getByTestId("review-note").fill("Browser check: needs a look on the ground.");
  await page.getByTestId("review-submit").click();
  await expect(page.getByTestId("reviews")).toContainText("Browser check");
  await page.screenshot({ path: shot("m18-11-real-incident"), fullPage: true });

  // 2. They send a field officer, who reports from the place.
  await page.getByTestId("action-assign").click();
  await page.locator('[data-testid^="assign-officer-"]').first().check();
  await page.getByTestId("assign-note").fill("Browser check: photograph the bund.");
  await page.getByTestId("assign-submit").click();
  await expect(page.getByTestId("fieldwork-assignment")).toBeVisible();
  await signIn(page, "demo.field2");
  await page.goto(url);
  await page.getByTestId("action-field_report").click();
  await page.getByTestId("fr-outcome-false_alarm").check();
  await page.getByTestId("fr-findings").fill("Browser check: no fill on the ground.");
  await page.getByTestId("fr-submit").click();
  await expect(page.getByTestId("field-report")).toBeVisible();

  // 3. The district officer recommends; the senior official approves and closes, each with a note.
  await signIn(page, "demo.district2");
  await page.goto(url);
  await page.getByTestId("action-recommend").click();
  await page.getByTestId("rec-dismiss").check();
  await page.getByTestId("rec-note").fill("Browser check: the field report shows no change.");
  await page.getByTestId("rec-submit").click();
  await expect(page.getByTestId("recommendation")).toBeVisible();
  await signIn(page, "demo.senior");
  await page.goto(url);
  await page.getByTestId("action-DISMISSED").click();
  await page.getByTestId("input-note").fill("Browser check: dismissed on the preview stack.");
  await page.getByTestId("submit-action").click();
  await page.getByTestId("action-CLOSED").click();
  await page.getByTestId("input-note").fill("Browser check: closed.");
  await page.getByTestId("submit-action").click();
  await expect(page.locator(".detail-head .pill")).toHaveAttribute("data-state", "CLOSED");

  // 4. The monthly page and the audit log (State-level), whose chain still holds after the demo was removed.
  await page.goto("/monthly");
  await expect(page.getByTestId("monthly")).toBeVisible();
  await expect(page.getByTestId("monthly")).not.toContainText("Demo world");
  await page.goto("/audit");
  await page.getByTestId("verify-log").click();
  await expect(page.getByTestId("verify-result")).toHaveClass(/info/);
  await page.screenshot({ path: shot("m18-12-audit"), fullPage: true });

  expect(external.filter((u) => !BASE_MAP.test(u))).toEqual([]);
  await desk.close();
});
