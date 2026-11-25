/**
 * The demo, start to finish, with two roles (DECISIONS.md D-057), on one machine with no internet.
 * Since M13 it starts at the overview and the inbox (D-059, D-060).
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
  await expect(page).toHaveURL(/\/dashboard$/);
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

  // 1. An official starts at the overview: the state, then a district, a mandal, and the incidents
  //    behind one number.
  await signIn(page, "demo.viewer2");
  await expect(page.getByTestId("dash-figures")).toBeVisible();
  await expect(page.getByTestId("dash-children")).toContainText("Demo North District");
  await expect(page.getByTestId("dash-children")).toContainText("Demo South District");
  await expect(page.getByTestId("trend").locator("svg")).toHaveCount(2);
  await page.screenshot({ path: shot("m13-01-overview"), fullPage: true });
  await page.getByTestId("dash-row-Demo North District").getByRole("button").click();
  await expect(page.getByTestId("dash-path")).toContainText("Demo North District");
  await page.getByTestId("dash-row-Demo Mandal 1").getByRole("button").click();
  await expect(page.getByTestId("dash-children")).toContainText("Demo Village 1");
  await page.screenshot({ path: shot("m13-02-mandal"), fullPage: true });
  await page.getByTestId("dash-Demo Village 1-open").click();
  await expect(page.getByTestId("linked-filter")).toContainText("Demo Village 1");
  await expect(page.locator('[data-testid^="alert-row-"]', { hasText: "Demo Cheruvu 1" })).toHaveCount(1);

  // 2. The official's inbox: the new incident in their area, a reminder, and how each was sent.
  await expect(page.getByTestId("inbox-count")).not.toHaveText("");
  await page.getByTestId("nav-inbox").click();
  const opened = page.getByTestId("note-incident_opened").filter({ hasText: "Demo Cheruvu 1" });
  await expect(opened).toHaveCount(1);
  await expect(opened).toContainText("Land fill");
  await expect(opened.getByTestId("delivery-email")).toContainText("sent");
  await expect(opened.getByTestId("delivery-whatsapp")).toContainText("held");
  await expect(page.getByTestId("note-reminder").filter({ hasText: "Demo Cheruvu 1" })).toHaveCount(1);
  await page.screenshot({ path: shot("m13-03-inbox"), fullPage: true });

  // 3. The official opens a lake: week by week, with images, and its legal documents.
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

  // 4. The new incident says plainly what changed, with the image pair and dates.
  await openIncident(page, "Demo Cheruvu 1");
  await expect(page.getByTestId("ack-banner")).toBeVisible();
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
  // The review acknowledged the notification and its reminder.
  await expect(page.getByTestId("ack-banner")).toHaveCount(0);
  await page.screenshot({ path: shot("m12-02-review"), fullPage: true });

  // 5. What changed, by type, and the incidents that stop or are flagged.
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

  // 6. The admin sees who was told and how, and who has not acknowledged.
  await signIn(page, "demo.admin");
  await page.getByTestId("nav-officials").click();
  await expect(page.getByTestId("channel-email")).toContainText("Ready");
  await expect(page.getByTestId("channel-sms")).toContainText("Not set up");
  await expect(page.getByTestId("person-demo.viewer2").getByTestId("person-areas")).toContainText("Demo North District");
  await expect(page.getByTestId("delivery-log")).toContainText("held");
  await page.getByTestId("send-digest").click();
  await expect(page.getByTestId("officials-message")).toContainText("already sent");  // the seed sent this week's
  await page.screenshot({ path: shot("m13-04-officials"), fullPage: true });
  await page.getByTestId("nav-inbox").click();
  await page.getByTestId("inbox-all").click();
  await expect(page.getByTestId("note-not_acknowledged").first()).toBeVisible();

  // 7. The admin decides: confirmed, with a note; then the evidence pack.
  await openIncident(page, "Demo Cheruvu 1");
  await page.getByTestId("action-CONFIRMED").click();
  await page.getByTestId("input-note").fill("Real change: fill inside recovered land, as the review says.");
  await page.getByTestId("submit-action").click();
  await expect(page.locator(".detail-head .pill")).toHaveAttribute("data-state", "CONFIRMED");
  await page.getByTestId("pack-generate").click();
  await expect(page.getByTestId("pack-pdf")).toBeVisible({ timeout: 60_000 });
  await page.screenshot({ path: shot("m12-04-confirmed-pack"), fullPage: true });

  // 8. The admin tags a legal document to the lake.
  await page.goto("/assets");
  await page.locator(".list .row", { hasText: "Demo Cheruvu 1" }).first().click();
  await page.getByTestId("doc-add").click();
  await page.getByTestId("doc-form").locator("select").selectOption("court_order");
  await page.getByTestId("doc-title").fill("Demo stay order");
  await page.getByTestId("doc-form").locator("input").nth(1).fill("DEMO-WP-9999/2026");
  await page.getByTestId("doc-form").getByRole("button", { name: "Save document" }).click();
  await expect(page.getByTestId("documents")).toContainText("DEMO-WP-9999/2026");

  // 9. The monthly page, for an official.
  await signIn(page, "demo.viewer2");
  await page.goto("/monthly");
  await expect(page.getByTestId("figure-new_alerts").locator("b")).not.toHaveText("");
  await expect(page.getByTestId("waiting-list")).toContainText("Demo Cheruvu 9");
  await page.screenshot({ path: shot("m12-05-monthly"), fullPage: true });

  // 10. The first official works in Telugu.
  await page.evaluate(() => { localStorage.removeItem("lp.token"); localStorage.removeItem("lp.user"); });
  await page.goto("/login");
  await page.getByTestId("login-demo.viewer1").click();
  await expect(page.getByRole("link", { name: "సంఘటనలు" })).toBeVisible();
  await page.screenshot({ path: shot("m12-06-telugu") });

  expect(external).toEqual([]);
  await desk.close();
});
