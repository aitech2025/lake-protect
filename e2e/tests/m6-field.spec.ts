/**
 * M6 done-check: capture works offline, syncs on reconnect, the distance warning works and the
 * language toggle works. Runs against a freshly reset demo database (fictional data only).
 */
import { expect, test, type APIRequestContext } from "@playwright/test";
import { shot } from "./helpers";

test.describe.configure({ mode: "serial" });

// A small valid PNG, standing in for a phone photo.
const PHOTO = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAAAHUlEQVR4nGPU0tJiIAUwkaR6VMOohlENoxqGsQYAjeEAcvq9mfIAAAAASUVORK5CYII=",
  "base64",
);

async function token(request: APIRequestContext, username: string): Promise<string> {
  const res = await request.post("/api/auth/login", { data: { username } });
  expect(res.ok()).toBeTruthy();
  return (await res.json()).token;
}

async function apiAs(request: APIRequestContext, username: string) {
  const headers = { Authorization: `Bearer ${await token(request, username)}` };
  return {
    get: async (path: string) => (await request.get(`/api${path}`, { headers })).json(),
    post: async (path: string, data: unknown) => request.post(`/api${path}`, { headers, data }),
  };
}

let alertId = 0;
let centre: [number, number] = [0, 0];

test("set up: the headline alert is assigned to Demo Field Officer 1", async ({ request }) => {
  const analyst = await apiAs(request, "demo.analyst");
  const nodal = await apiAs(request, "demo.nodal");
  const items = (await analyst.get("/alerts")).items as { id: number; asset_name: string; state: string; lon: number; lat: number }[];
  const headline = items.find((a) => a.asset_name === "Demo Cheruvu 1")!;
  alertId = headline.id;
  centre = [headline.lon, headline.lat];
  // The M5 suite may already have confirmed and assigned it through the desk.
  if (headline.state === "TRIAGE") {
    expect((await analyst.post(`/alerts/${alertId}/transitions`, { to: "CONFIRMED", data: { image_pair_reviewed: true } })).ok()).toBeTruthy();
  }
  if (headline.state !== "ASSIGNED") {
    const officers = (await nodal.get("/users?role=field_officer")) as { id: number; name: string }[];
    const f1 = officers.find((o) => o.name === "Demo Field Officer 1")!;
    expect((await nodal.post(`/alerts/${alertId}/transitions`, { to: "ASSIGNED", data: { owner_user_id: f1.id } })).ok()).toBeTruthy();
  }
  expect((await analyst.get(`/alerts/${alertId}`)).state).toBe("ASSIGNED");
});

test("field officer captures offline, and the visit syncs on reconnect", async ({ browser, request }) => {
  const far: [number, number] = [centre[0] + 0.004, centre[1]]; // about 430 m east
  const context = await browser.newContext({ permissions: ["geolocation"], geolocation: { longitude: far[0], latitude: far[1], accuracy: 8 }, viewport: { width: 412, height: 915 } });
  const page = await context.newPage();

  // Online: sign in. Demo Field Officer 1 prefers Telugu.
  await page.goto("/login");
  await page.getByTestId("login-demo.field1").click();
  await expect(page).toHaveURL(/\/field$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("నా హెచ్చరికలు");
  await expect(page.locator('[data-testid^="field-alert-"]', { hasText: "డెమో చెరువు 1" })).toBeVisible();
  await page.screenshot({ path: shot("m6-01-list-telugu"), fullPage: true });

  // Language toggle back to English.
  await page.getByTestId("field-lang").click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("My alerts");

  // Let the service worker take control, then reload so it caches this session's data and tiles.
  await page.evaluate(async () => { await navigator.serviceWorker.ready; });
  await page.reload();
  await expect.poll(() => page.evaluate(() => Boolean(navigator.serviceWorker.controller))).toBe(true);
  const card = page.locator('[data-testid^="field-alert-"]', { hasText: "Demo Cheruvu 1" });
  await expect(card).toBeVisible();

  // Signal lost. The app still opens from the phone.
  await context.setOffline(true);
  await page.reload();
  await expect(page.getByTestId("net-status")).toContainText("No signal");
  await card.click();
  await expect(page.getByTestId("field-alert")).toBeVisible();
  await expect(page.getByTestId("counsel-note")).toContainText("This is an observation, not a survey. Do not enter private land.");
  const imgs = page.locator(".f-pair img");
  await expect(imgs).toHaveCount(2);
  await expect.poll(() => imgs.evaluateAll((els) => els.every((e) => (e as HTMLImageElement).naturalWidth > 0))).toBe(true);

  // Device GPS says 430 m away: warned, not blocked.
  await page.getByTestId("get-gps").click();
  await expect(page.getByTestId("distance-warning")).toBeVisible();
  await expect(page.getByTestId("distance-warning")).toContainText("You can still save");
  await page.screenshot({ path: shot("m6-02-distance-warning"), fullPage: true });

  // Demo position at the site: no warning.
  await page.getByTestId("pos-mode").selectOption("site");
  await page.getByTestId("get-gps").click();
  await expect(page.getByTestId("distance-ok")).toBeVisible();

  await page.getByTestId("photo-input").setInputFiles({ name: "photo.png", mimeType: "image/png", buffer: PHOTO });
  await expect(page.getByTestId("photo-count")).toContainText("1");
  await page.getByTestId("outcome-confirmed").check();
  await page.getByTestId("stage").selectOption("soil_dumped");
  await page.getByTestId("notes").fill("Fresh soil heap at the lake edge.");
  await page.getByTestId("save-visit").click();
  await expect(page.getByTestId("save-message")).toContainText("Saved on this phone");
  await expect(page.getByTestId("queue-count")).toContainText("1 visits waiting");
  await page.screenshot({ path: shot("m6-03-saved-offline"), fullPage: true });

  // Still offline after a reload: the capture is still queued.
  await page.goto("/field");
  await expect(page.getByTestId("queue-count")).toContainText("1 visits waiting");

  // Nothing reached the server yet.
  const analyst = await apiAs(request, "demo.analyst");
  expect((await analyst.get(`/alerts/${alertId}`)).state).toBe("ASSIGNED");

  // Signal back: the queue sends itself.
  await context.setOffline(false);
  await expect(page.getByTestId("queue-count")).toContainText("Nothing waiting", { timeout: 30_000 });
  await expect(page.getByTestId("sync-result")).toContainText("Seen on site");
  await page.screenshot({ path: shot("m6-04-synced"), fullPage: true });

  const detail = await analyst.get(`/alerts/${alertId}`);
  expect(detail.state).toBe("FIELD_CONFIRMED");
  const check = detail.field_checks[0];
  expect(check.photo_count).toBe(1);
  expect(check.device_time).toBeTruthy();
  expect(check.synced_at).toBeTruthy();
  expect(new Date(check.synced_at).getTime()).toBeGreaterThanOrEqual(new Date(check.device_time).getTime());
  expect(check.distance_to_candidate_m).toBeLessThan(50);
  expect(check.notes).toContain("[Demo: simulated position]");
  await context.close();
});

test("the demo no-signal switch queues instead of sending", async ({ browser }) => {
  const context = await browser.newContext({ viewport: { width: 412, height: 915 } });
  const page = await context.newPage();
  await page.goto("/login");
  await page.getByTestId("login-demo.field2").click();
  await expect(page.getByTestId("net-status")).toContainText("Online");
  await page.getByTestId("demo-no-signal").check();
  await expect(page.getByTestId("net-status")).toContainText("No signal");
  await expect(page.getByTestId("sync-now")).toBeDisabled();
  await context.close();
});
