/**
 * M9 done-check: the section 14 demo, start to finish, on one machine with no internet.
 * Any request that leaves localhost fails the test. Run on a fresh demo (sh scripts/e2e.sh m9-demo),
 * ideally with docker-compose.offline.yml so no container has a route out.
 */
import { expect, test, type BrowserContext, type Page } from "@playwright/test";
import { shot, stateOf } from "./helpers";

const PHOTO = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAAAHUlEQVR4nGPU0tJiIAUwkaR6VMOohlENoxqGsQYAjeEAcvq9mfIAAAAASUVORK5CYII=",
  "base64",
);

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
  await expect(page).not.toHaveURL(/\/login$/);
}

async function headline(page: Page): Promise<void> {
  await page.goto("/alerts");
  await page.locator('[data-testid^="alert-row-"]', { hasText: "Demo Cheruvu 1" }).first().click();
  await expect(page.getByTestId("alert-detail")).toBeVisible();
}

test("the section 14 demo runs end to end with no internet", async ({ browser }) => {
  test.setTimeout(240_000);
  const desk = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  await guard(desk);
  const page = await desk.newPage();
  await page.goto("/login");

  // 0. Say "demo data" at the start.
  await expect(page.getByTestId("demo-badge")).toContainText("Demo data");
  await page.screenshot({ path: shot("m9-00-sign-in") });

  // 1. Map of watched assets.
  await signIn(page, "demo.admin");
  await page.goto("/assets");
  await expect(page.locator(".list .row")).toHaveCount(20);
  await page.waitForTimeout(1000);
  await page.screenshot({ path: shot("m9-01-assets-map") });

  // 2. New alert at Demo Cheruvu 1: before and after, with dates.
  await signIn(page, "demo.analyst");
  await headline(page);
  const imgs = page.getByTestId("image-pair").locator("img");
  await expect.poll(() => imgs.evaluateAll((els) => els.filter((e) => (e as HTMLImageElement).naturalWidth > 0).length)).toBe(2);
  await expect(page.getByTestId("dated-bracket")).toContainText("Last clear");
  await page.screenshot({ path: shot("m9-02-image-pair") });

  // 3. Legal check panel.
  await expect(page.getByTestId("legal-panel")).toContainText("Court register");
  await expect(page.getByTestId("boundary-seal")).toHaveAttribute("data-certainty", "confirmed");
  await page.getByTestId("legal-panel").scrollIntoViewIfNeeded();
  await page.screenshot({ path: shot("m9-03-legal-check") });

  // 4. Other alerts that stop: court hold, restoration work, watch list.
  await page.goto("/alerts");
  await page.getByTestId("group-legal").click();
  await expect(page.getByTestId("alert-list")).toContainText("Demo Cheruvu 7");
  await page.getByTestId("group-closed").click();
  await expect(page.getByTestId("alert-list")).toContainText("Closed: authorised work or permit");
  await page.getByTestId("group-watch").click();
  await expect(page.getByTestId("alert-list")).toContainText("Demo Kunta 5");
  await page.screenshot({ path: shot("m9-04-stops") });

  // 5. Analyst confirms, nodal officer assigns.
  await headline(page);
  await page.getByTestId("action-CONFIRMED").click();
  await page.getByTestId("input-reviewed").check();
  await page.getByTestId("submit-action").click();
  await expect.poll(() => stateOf(page)).toBe("CONFIRMED");
  await signIn(page, "demo.nodal");
  await headline(page);
  await page.getByTestId("action-ASSIGNED").click();
  await page.getByTestId("input-owner").selectOption({ label: "Demo Field Officer 1" });
  await page.getByTestId("submit-action").click();
  await expect.poll(() => stateOf(page)).toBe("ASSIGNED");
  await page.screenshot({ path: shot("m9-05-assigned") });

  // 6. Phone, offline, in Telugu.
  const phone = await browser.newContext({ viewport: { width: 412, height: 915 } });
  await guard(phone);
  const p = await phone.newPage();
  await p.goto("/login");
  await p.getByTestId("login-demo.field1").click();
  await expect(p.getByRole("heading", { level: 1 })).toHaveText("నా హెచ్చరికలు");
  const card = p.locator('[data-testid^="field-alert-"]', { hasText: "డెమో చెరువు 1" });
  await expect(card).toBeVisible();
  await p.getByTestId("demo-no-signal").check();
  await expect(p.getByTestId("net-status")).toContainText("సిగ్నల్ లేదు");
  await card.click();
  await p.getByTestId("photo-input").setInputFiles({ name: "photo.png", mimeType: "image/png", buffer: PHOTO });
  await p.getByTestId("pos-mode").selectOption("site");
  await p.getByTestId("get-gps").click();
  await expect(p.getByTestId("distance-ok")).toBeVisible();
  await p.getByTestId("outcome-confirmed").check();
  await p.getByTestId("stage").selectOption("soil_dumped");
  await p.getByTestId("save-visit").click();
  await expect(p.getByTestId("queue-count")).toContainText("1");
  await p.screenshot({ path: shot("m9-06-phone-offline-telugu"), fullPage: true });
  await p.getByTestId("demo-no-signal").uncheck();
  await expect(p.getByTestId("sync-result")).toBeVisible({ timeout: 30_000 });
  await phone.close();

  // 7. Evidence pack and checklist.
  await signIn(page, "demo.legal");
  await headline(page);
  await expect.poll(() => stateOf(page)).toBe("FIELD_CONFIRMED");
  for (const key of ["boundary_confirmed", "joint_survey_done", "survey_notice_given", "no_live_court_matter", "title_permits_reviewed", "notice_and_hearing", "construction_dated"]) {
    const row = page.getByTestId(`check-${key}`);
    await row.locator("select").selectOption(key === "notice_and_hearing" ? "not_applicable" : "yes");
    await row.locator("input").fill(`DEMO-REF-${key}`);
    await row.getByRole("button").click();
    await expect(row).toContainText("Demo Legal Officer");
  }
  await page.getByTestId("generate-pack").click();
  await expect(page.getByTestId("pack-message")).toContainText("version 1 generated");
  await page.getByTestId("check-pack-v1").click();
  await expect(page.getByTestId("pack-message")).toContainText("files match their hashes");
  await page.getByTestId("case-file").scrollIntoViewIfNeeded();
  await page.screenshot({ path: shot("m9-07-evidence-pack") });

  // 8. Officer record. The nodal officer sends it on; the officer records the action.
  await signIn(page, "demo.nodal");
  await headline(page);
  await page.getByTestId("action-PACK_READY").click();
  await page.getByTestId("submit-action").click();
  await expect.poll(() => stateOf(page)).toBe("PACK_READY");
  await page.getByTestId("action-WITH_OFFICER").click();
  await page.getByTestId("submit-action").click();
  await expect.poll(() => stateOf(page)).toBe("WITH_OFFICER");
  await signIn(page, "demo.legal");
  await headline(page);
  await expect(page.getByTestId("officer-record")).toContainText("The system suggests no outcome");
  await page.getByTestId("officer-notice_ref").fill("DEMO/NOTICE/2026/101");
  await page.getByTestId("officer-order_ref").fill("DEMO/ORDER/2026/055");
  await page.getByTestId("officer-record-action").click();
  await expect.poll(() => stateOf(page)).toBe("POST_ACTION_WATCH");
  await page.getByTestId("officer-record").scrollIntoViewIfNeeded();
  await page.screenshot({ path: shot("m9-08-officer-record") });

  // 9. Audit view: the log checks out.
  await signIn(page, "demo.auditor");
  await page.goto("/audit");
  await page.getByTestId("verify-log").click();
  await expect(page.getByTestId("verify-result")).toContainText("The log is intact");
  await expect(page.getByTestId("demo-badge")).toBeVisible();
  await page.screenshot({ path: shot("m9-09-audit") });

  // 10. Monthly page.
  await signIn(page, "demo.senior");
  await expect(page).toHaveURL(/\/monthly$/);
  await expect(page.getByTestId("figure-action_taken").locator("b")).not.toHaveText("0");
  await page.screenshot({ path: shot("m9-10-monthly"), fullPage: true });

  expect(external, `requests that tried to leave the machine: ${external.join(", ")}`).toEqual([]);
  await desk.close();
});
