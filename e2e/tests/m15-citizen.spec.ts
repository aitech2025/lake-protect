/**
 * M15 to M18 done-check (DECISIONS.md D-062 to D-065), on real data only. A citizen reports on the
 * public portal from their phone's location at a real lake (Mallampet Cheruvu) and gets a reference.
 * The app places the report and opens a citizen incident whose satellite review waits for the
 * screener. An official then:
 * - acknowledges it and adds a note;
 * - asks for two satellite looks (two months ago and now), which the test answers as the screener
 *   would, and compares them side by side;
 * - attaches the legal records and a document;
 * - asks for a sharper image and approves the incident.
 * The admin approves the image and closes it. The citizen sees each step in Telugu.
 * A report on open ground goes on the weekly watch, and is taken off it at the end so a rerun
 * starts from the same counts.
 * The reports are test records on the preview stack; reset it afterwards (README).
 */
import { expect, test, type APIRequestContext, type Page } from "@playwright/test";
import { login, shot } from "./helpers";

// Mallampet Cheruvu, Medchal–Malkajgiri (a point on its water spread, from OpenStreetMap).
const MALLAMPET = { latitude: 17.557538, longitude: 78.377187 };
// Open ground in Ranga Reddy district, over 30 km from every watched place; a little different each run.
const OPEN_GROUND = { latitude: 17.15 + (Math.random() - 0.5) * 0.004, longitude: 78.12 + (Math.random() - 0.5) * 0.004 };
const TOKEN = { "X-Pipeline-Token": process.env.LP_PIPELINE_TOKEN ?? "" };

// A 24 x 24 PNG, drawn here, so no real photo is ever used.
const PNG_B64 =
  "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAIAAABvFaqvAAAAOklEQVR4nGNMaPBhoAZgooopowaNGkQlwILMUXnwgVT9dxQEIIzB57VRg0YNogZAySLw9E4GGHxeAwAq5QVs/cpaywAAAABJRU5ErkJggg==";
const PNG = Buffer.from(PNG_B64, "base64");

/** The portal's form, from the phone's location. Updates by SMS wait for the State's gateway. */
async function reportFromPortal(page: Page, what: string, description: string, shotName?: string): Promise<string> {
  await page.goto("/report");
  await expect(page.getByTestId("portal")).toBeVisible();
  await expect(page.getByTestId("lang-ur")).toHaveCount(0);
  await page.getByRole("button", { name: "Use my location" }).click();
  await expect(page.getByTestId("pin-status")).toContainText("Pin placed");
  await page.getByTestId(`what-${what}`).click();
  await page.getByTestId("photo-input").setInputFiles({ name: "site.png", mimeType: "image/png", buffer: PNG });
  await page.getByTestId("description").fill(description);
  await expect(page.getByTestId("updates-unavailable")).toBeVisible();
  if (shotName) await page.screenshot({ path: shot(shotName), fullPage: true });
  await page.getByTestId("report-submit").click();
  await expect(page.getByTestId("report-done")).toBeVisible();
  const ref = (await page.getByTestId("report-ref").textContent())!.trim();
  expect(ref).toMatch(/^GGR-[0-9A-Z]{4}-[0-9A-Z]{4}$/);
  return ref;
}

async function openIncidentOf(page: Page, ref: string): Promise<void> {
  await page.getByTestId("nav-reports").click();
  await page.getByTestId(`report-row-${ref}`).getByRole("link", { name: ref }).click();
  await page.getByTestId("open-incident").click();
  await expect(page.getByTestId("citizen-origin")).toContainText(ref);
}

/** Answer the pending looks of an incident as `lp review-reports` would, newest request last. */
async function answerLooks(request: APIRequestContext, alertId: number, results: string[]): Promise<void> {
  const pending = (await (await request.get("/api/pipeline/reviews", { headers: TOKEN })).json()).reviews
    .filter((r: { alert_id: number; kind: string }) => r.alert_id === alertId && r.kind === "requested")
    .sort((a: { id: number }, b: { id: number }) => a.id - b.id);
  expect(pending.length).toBe(results.length);
  for (const [i, look] of pending.entries()) {
    const asOf = look.look_date ?? new Date().toISOString().slice(0, 10);
    const body = {
      status: "done", result: results[i], as_of: asOf, after_date: asOf, after_png_b64: PNG_B64,
      scenes: [{ sensor: "sentinel-2-l2a", scene_id: `E2E-LOOK-${look.id}`, acquired_at: `${asOf}T05:20:00Z` }],
      ...(results[i] === "change_found"
        ? { before_date: asOf, before_png_b64: PNG_B64, change: { change_type: "soil_fill", area_sq_m: 1600, first_changed_at: asOf } }
        : {}),
    };
    const out = await request.post(`/api/pipeline/reviews/${look.id}`, { headers: TOKEN, data: body });
    expect(out.status()).toBe(200);
  }
}

test.describe("a report at a real lake", () => {
  test.use({ geolocation: MALLAMPET, permissions: ["geolocation"] });

  test("opens an incident that officials work from the panel, and the citizen sees each step", async ({ page, request }) => {
    test.skip(!TOKEN["X-Pipeline-Token"], "Set LP_PIPELINE_TOKEN for the e2e container (docker-compose.yml passes it from .env)");
    // 1. The public portal: real places only, no sign-in, English and Telugu.
    const ref = await reportFromPortal(page, "dumping", "Lorries tipping soil at the edge of the cheruvu since yesterday.", "m18-01-portal-form");
    await expect(page.getByTestId("report-done")).toContainText("Officials have opened a case");
    await page.screenshot({ path: shot("m18-02-reference"), fullPage: true });

    // 2. An official opens the report's incident: the citizen's words, the satellite review waiting.
    await login(page, "demo.viewer2");
    await openIncidentOf(page, ref);
    await expect(page.getByTestId("citizen-origin")).toContainText("Lorries tipping soil");
    await expect(page.getByTestId("satellite-review-result")).toHaveText("Waiting for the satellite review");
    await expect(page.locator("h1")).toContainText("Mallampet Cheruvu");
    const pill = page.locator(".detail-head .pill");
    const alertId = Number(page.url().split("/").pop());

    // 3. Acknowledge (the review starts, and the citizen is told) and a note.
    await page.getByTestId("ack-note").fill("Seen. Asking for satellite looks.");
    await page.getByTestId("ack-submit").click();
    await expect(page.getByTestId("officer-ack")).toContainText("You have acknowledged this incident.");
    await expect(pill).toHaveAttribute("data-state", "UNDER_REVIEW");
    await page.getByTestId("note-text").fill("The bund road is the likely way in for the lorries.");
    await page.getByTestId("note-submit").click();
    await expect(page.getByTestId("officer-notes")).toContainText("The bund road");

    // Two satellite looks, two months ago and now: the screener answers, and they are compared.
    const looks = page.locator('[data-testid^="look-pick-"]');
    const past = new Date(Date.now() - 60 * 86_400_000).toISOString().slice(0, 10);
    await page.getByTestId("look-date").fill(past);
    await page.getByTestId("look-submit").click();
    await expect(looks).toHaveCount(2);
    await page.getByTestId("look-date").fill("");
    await page.getByTestId("look-submit").click();
    await expect(looks).toHaveCount(3);
    await answerLooks(request, alertId, ["no_change", "change_found"]);
    await page.reload();
    await looks.nth(1).check();
    await looks.nth(2).check();
    await expect(page.getByTestId("look-compare").locator("img")).toHaveCount(2);
    await expect(page.getByTestId("look-list")).toContainText("No change visible yet");
    await expect(page.getByTestId("look-list")).toContainText("A change is visible");

    // The legal records at the spot, and a document.
    await page.getByTestId("legal-attach").click();
    await expect(page.getByTestId("legal-snapshot")).toContainText("Mallampet Cheruvu");
    await expect(page.getByTestId("legal-snapshot")).toContainText("Section 22A");
    await page.getByTestId("doc-title").fill("Browser check: notice reference only");
    await page.getByTestId("doc-ref").fill("E2E/TEST/2026/1");
    await page.getByTestId("doc-submit").click();
    await expect(page.getByTestId("doc-list")).toContainText("E2E/TEST/2026/1");

    // A sharper image waits for the admin; the official approves the incident with a note.
    await page.getByTestId("sharper-note").fill("To see the extent of the fill");
    await page.getByTestId("sharper-submit").click();
    await expect(page.getByTestId("sharper-list")).toContainText("Waiting for the admin");
    await page.getByTestId("decide-approve").click();
    await page.getByTestId("decide-note").fill("Browser check: approved on the looks of today and two months ago.");
    await page.getByTestId("decide-submit").click();
    await expect(pill).toHaveAttribute("data-state", "CONFIRMED");
    await page.getByTestId("officer-looks").scrollIntoViewIfNeeded();
    await page.screenshot({ path: shot("m18-03-official-actions"), fullPage: true });
    const incidentUrl = page.url();

    // 4. The admin approves the sharper image and closes the incident with a note.
    await login(page, "demo.admin");
    await page.goto(incidentUrl);
    await page.locator('[data-testid^="sharper-approve-"]').click();
    await expect(page.getByTestId("sharper-list")).toContainText("Approved");
    await page.getByTestId("decide-close").click();
    await page.getByTestId("decide-note").fill("Browser check: closed.");
    await page.getByTestId("decide-submit").click();
    await expect(pill).toHaveAttribute("data-state", "CLOSED");

    // 5. The citizen checks the reference, in Telugu: every step, and not the officials' notes.
    await page.goto(`/report/track/${ref}`);
    await page.getByTestId("lang-te").click();
    await expect(page.getByTestId("track-status")).toContainText("ముగిసింది");
    const events = page.getByTestId("track-events");
    await expect(events).toContainText("ఒక అధికారి దీన్ని సమీక్షిస్తున్నారు");
    await expect(events).toContainText("మరింత స్పష్టమైన ఉపగ్రహ చిత్రాలను");
    await expect(events).toContainText("మార్పును అధికారులు నిర్ధారించారు");
    await expect(events).not.toContainText("bund road");
    await page.screenshot({ path: shot("m18-04-track-telugu"), fullPage: true });
    await page.getByTestId("lang-en").click();
  });
});

test.describe("a place no one watches yet", () => {
  test.use({ geolocation: OPEN_GROUND, permissions: ["geolocation"] });

  test("goes on the weekly watch from its incident", async ({ page }) => {
    const ref = await reportFromPortal(page, "construction", "A compound wall going up on open land.");
    await login(page, "demo.admin");
    await openIncidentOf(page, ref);
    await expect(page.getByTestId("officer-watch")).toContainText("Add this place to the weekly satellite watch");
    await page.getByTestId("watch-name").fill(`Browser check place (${ref})`);
    await page.getByTestId("watch-reason-input").fill("Browser check: watch it every week");
    await page.getByTestId("watch-submit").click();
    await expect(page.getByTestId("watch-on")).toContainText("is on the weekly watch");
    await page.screenshot({ path: shot("m18-05-weekly-watch"), fullPage: true });
    await page.goto(`/report/track/${ref}`);
    await expect(page.getByTestId("track-events")).toContainText("weekly watch");
    // A citizen location remains an incident candidate until authority verification. It is not
    // converted into a permanent registry asset here, so there is no asset watch to stop.
  });
});
