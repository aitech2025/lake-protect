/** M8: officer record and the monthly page. Fictional data only. */
import { expect, test, type APIRequestContext } from "@playwright/test";
import { login, openAlert, shot, stateOf } from "./helpers";

test.describe.configure({ mode: "serial" });

const month = new Date().toISOString().slice(0, 7);

async function bulletin(request: APIRequestContext) {
  const tok = (await (await request.post("/api/auth/login", { data: { username: "demo.senior" } })).json()).token;
  return (await request.get(`/api/bulletins/${month}?dataset=demo`, { headers: { Authorization: `Bearer ${tok}` } })).json();
}

test("senior officer lands on the monthly page, and its figures match the records", async ({ page, request }) => {
  await login(page, "demo.senior");
  await expect(page).toHaveURL(/\/monthly$/);
  await expect(page.getByTestId("demo-badge")).toBeVisible();
  const data = await bulletin(request);
  for (const k of ["watched", "new_alerts", "verified", "action_taken", "overdue"]) {
    await expect(page.getByTestId(`figure-${k}`).locator("b")).toHaveText(String(data.counts[k]));
  }
  const list = page.getByTestId("overdue-list");
  await expect(list).toContainText("Demo Cheruvu 9"); // assigned, past its 7-day timer
  await expect(list).toContainText("Demo Cheruvu 2"); // with the officer, past 30 days
  await expect(page.locator(".monthly-map svg polygon").first()).toBeVisible();
  await page.screenshot({ path: shot("m8-01-monthly"), fullPage: true });
});

test("legal officer records the officer's action, and the monthly page counts it", async ({ page, request }) => {
  const before = (await bulletin(request)).counts;
  await login(page, "demo.legal");
  await openAlert(page, "Demo Cheruvu 2");
  const panel = page.getByTestId("officer-record");
  await expect(panel).toContainText("The system suggests no outcome");
  await page.getByTestId("officer-notice_ref").fill("DEMO/NOTICE/2026/044");
  await page.getByTestId("officer-order_ref").fill("DEMO/ORDER/2026/019");
  await page.getByTestId("officer-action_date").fill(new Date().toISOString().slice(0, 10));
  await page.getByTestId("officer-record-action").click();
  await expect(page.getByTestId("officer-message")).toContainText("Action recorded");
  await expect.poll(() => stateOf(page)).toBe("POST_ACTION_WATCH");
  await page.screenshot({ path: shot("m8-02-officer-record"), fullPage: true });

  const after = (await bulletin(request)).counts;
  expect(after.action_taken).toBe(before.action_taken + 1);
  expect(after.overdue).toBe(before.overdue - 1); // no longer waiting on the officer
});

test("the one-page monthly PDF downloads", async ({ request }) => {
  const tok = (await (await request.post("/api/auth/login", { data: { username: "demo.senior" } })).json()).token;
  const pdf = await request.get(`/api/bulletins/${month}/pdf?dataset=demo`, { headers: { Authorization: `Bearer ${tok}` } });
  expect(pdf.headers()["content-type"]).toBe("application/pdf");
  const body = (await pdf.body()).toString("latin1");
  expect(body.startsWith("%PDF")).toBe(true);
  // The page count is checked with pypdf in api/tests/test_monthly.py and in the M8 done-check.
});
