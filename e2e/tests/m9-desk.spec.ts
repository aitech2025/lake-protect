/**
 * The desk, start to finish, on real data with the two role accounts (DECISIONS.md D-057, D-065),
 * on one machine with no internet: any request that leaves localhost fails the test.
 * An official reviews the top real incident from the saved screen; the admin dismisses and closes
 * it as a browser check; the monthly page and the audit log follow. Run on the preview stack and
 * reset it afterwards (README): the steps are test records.
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
  await expect(page).toHaveURL(/\/dashboard$/);
}

test("the desk runs on real data with two roles and no internet", async ({ browser }) => {
  test.setTimeout(180_000);
  const desk = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  await guard(desk);
  const page = await desk.newPage();
  await page.goto("/login");

  // 0. The role accounts, and nothing marked as demo data.
  await expect(page.locator('[data-testid^="login-"]')).toHaveCount(3);
  await expect(page.getByTestId("demo-badge")).toHaveCount(0);
  await page.screenshot({ path: shot("m18-10-login"), fullPage: true });

  // 1. The official: the overview, the inbox, then the top incident in the list.
  await signIn(page, "demo.viewer2");
  await expect(page.getByTestId("dash-figures")).toBeVisible();
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

  // 2. The admin decides and closes, each with a note.
  await signIn(page, "demo.admin");
  await page.goto(url);
  await page.getByTestId("action-DISMISSED").click();
  await page.getByTestId("input-note").fill("Browser check: dismissed on the preview stack.");
  await page.getByTestId("submit-action").click();
  await page.getByTestId("action-CLOSED").click();
  await page.getByTestId("input-note").fill("Browser check: closed.");
  await page.getByTestId("submit-action").click();
  await expect(page.locator(".detail-head .pill")).toHaveAttribute("data-state", "CLOSED");

  // 3. The monthly page and the audit log, whose chain still holds after the demo was removed.
  await page.goto("/monthly");
  await expect(page.getByTestId("monthly")).toBeVisible();
  await expect(page.getByTestId("monthly")).not.toContainText("Demo world");
  await page.goto("/audit");
  await page.getByTestId("verify-log").click();
  await expect(page.getByTestId("verify-result")).toHaveClass(/info/);
  await page.screenshot({ path: shot("m18-12-audit"), fullPage: true });

  expect(external).toEqual([]);
  await desk.close();
});
