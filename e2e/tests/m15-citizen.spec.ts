/**
 * M15, M16 and M17 done-check (DECISIONS.md D-062, D-063, D-064). A citizen reports on the public
 * portal in the demo world, from their phone's location, and gets a reference. The app:
 * - places the report on its location;
 * - opens a citizen incident;
 * - reviews the place with the (demo) satellite and finds a change the weekly screen has not seen.
 * An official then acknowledges it, adds a note, compares two satellite looks, attaches the legal
 * records and a document, asks for a sharper image and approves the incident. The admin approves
 * the sharper image and closes it. The citizen sees each step in Telugu. The WhatsApp conversation
 * makes a report too. A report away from every watched place goes on the weekly watch (and is
 * taken off it at the end, so a rerun starts from the same counts).
 * Everything is demo data: fictional places, demo numbers (+91 0000…), nothing leaves the machine.
 */
import { expect, test, type Page } from "@playwright/test";
import { login, logout, shot } from "./helpers";

// The fill at Demo Kunta 7 that only a citizen's report finds (`unscreened_changes` in world.yml):
// origin 81.50, 14.50, plus 955 m east and 3,605 m south.
const KUNTA_7 = { latitude: 14.467616, longitude: 81.508861 };
test.use({ geolocation: KUNTA_7, permissions: ["geolocation"] });

// A 24 x 24 PNG, drawn here, so no real photo is ever used.
const PNG = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAIAAABvFaqvAAAAOklEQVR4nGNMaPBhoAZgooopowaNGkQlwILMUXnwgVT9dxQEIIzB57VRg0YNogZAySLw9E4GGHxeAwAq5QVs/cpaywAAAABJRU5ErkJggg==",
  "base64",
);

/** The portal's form, from the phone's location, with a demo number and its demo code. */
async function reportFromPortal(page: Page, what: string, description: string, phone: string, shotName?: string): Promise<string> {
  await page.goto("/report?demo=1");
  await expect(page.getByTestId("portal-demo")).toBeVisible();
  await expect(page.getByTestId("lang-ur")).toHaveCount(0);
  await page.getByRole("button", { name: "Use my location" }).click();
  await expect(page.getByTestId("pin-status")).toContainText("Pin placed");
  await page.getByTestId(`what-${what}`).click();
  await page.getByTestId("photo-input").setInputFiles({ name: "site.png", mimeType: "image/png", buffer: PNG });
  await page.getByTestId("description").fill(description);
  await page.getByTestId("phone").fill(phone);
  await page.getByTestId("send-code").click();
  const demoCode = (await page.getByTestId("demo-code").textContent())!.match(/(\d{6})/)![1];
  await page.getByTestId("code").fill(demoCode);
  await page.getByTestId("verify-code").click();
  await expect(page.getByTestId("phone-verified")).toContainText("+91");
  await page.getByTestId("consent").check();
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

test("a citizen's report opens an incident, the satellite reviews it, and officials work it in the regular flow", async ({ page }) => {
  // 1. The public portal, demo world, no sign-in, English and Telugu only.
  const ref = await reportFromPortal(page, "dumping", "Lorries tipping soil at the edge of the kunta since yesterday.", "0000000003", "m16-01-portal-form");
  // At once: a case opened, and the satellite review found a change.
  await expect(page.getByTestId("report-done")).toContainText("Officials have opened a case");
  await expect(page.getByTestId("report-done")).toContainText("The newest satellite images show a change");
  await page.screenshot({ path: shot("m16-02-reference"), fullPage: true });

  // 2. An official opens the report's incident: the citizen's words, the review, the images.
  await login(page, "demo.viewer2");
  await page.getByTestId("nav-reports").click();
  await page.getByTestId(`report-row-${ref}`).getByRole("link", { name: ref }).click();
  await expect(page.getByTestId("report-detail")).not.toContainText("0000000003");
  await page.getByTestId("open-incident").click();
  await expect(page.getByTestId("citizen-origin")).toContainText(ref);
  await expect(page.getByTestId("citizen-origin")).toContainText("Lorries tipping soil");
  await expect(page.getByTestId("satellite-review-result")).toHaveText("A change is visible");
  await expect(page.getByTestId("change-summary")).toContainText("reported by a citizen");
  await expect(page.getByTestId("image-pair")).toBeVisible();
  await page.screenshot({ path: shot("m16-03-citizen-incident"), fullPage: true });
  const pill = page.locator(".detail-head .pill");

  // 3. The official acknowledges it: the review starts, and the citizen is told.
  await page.getByTestId("ack-note").fill("Seen. Looking at the images now.");
  await page.getByTestId("ack-submit").click();
  await expect(page.getByTestId("officer-ack")).toContainText("You have acknowledged this incident.");
  await expect(pill).toHaveAttribute("data-state", "UNDER_REVIEW");
  await page.getByTestId("note-text").fill("Fresh soil on the east edge on the newest image.");
  await page.getByTestId("note-submit").click();
  await expect(page.getByTestId("officer-notes")).toContainText("Fresh soil on the east edge");

  // Two satellite looks, two months ago and now, compared side by side.
  const looks = page.locator('[data-testid^="look-pick-"]');
  const past = new Date(Date.now() - 60 * 86_400_000).toISOString().slice(0, 10);
  await page.getByTestId("look-date").fill(past);
  await page.getByTestId("look-submit").click();
  await expect(looks).toHaveCount(2);
  await page.getByTestId("look-date").fill("");
  await page.getByTestId("look-submit").click();
  await expect(looks).toHaveCount(3);
  await looks.nth(1).check();
  await looks.nth(2).check();
  await expect(page.getByTestId("look-compare").locator("img")).toHaveCount(2);
  await expect(page.getByTestId("look-list")).toContainText("No change visible yet");
  await expect(page.getByTestId("look-list")).toContainText("A change is visible");

  // The legal records at the spot, and a document.
  await page.getByTestId("legal-attach").click();
  await expect(page.getByTestId("legal-snapshot")).toContainText("Demo Kunta 7");
  await expect(page.getByTestId("legal-snapshot")).toContainText("Section 22A");
  await page.getByTestId("doc-title").fill("Stop-work notice to the contractor");
  await page.getByTestId("doc-ref").fill("DEMO/SWN/2026/7");
  await page.getByTestId("doc-submit").click();
  await expect(page.getByTestId("doc-list")).toContainText("DEMO/SWN/2026/7");

  // A sharper image waits for the admin; the official approves the incident with a note.
  await page.getByTestId("sharper-note").fill("To see the extent of the fill");
  await page.getByTestId("sharper-submit").click();
  await expect(page.getByTestId("sharper-list")).toContainText("Waiting for the admin");
  await page.getByTestId("decide-approve").click();
  await page.getByTestId("decide-note").fill("Fill inside the kunta, seen on the looks of today and two months ago.");
  await page.getByTestId("decide-submit").click();
  await expect(pill).toHaveAttribute("data-state", "CONFIRMED");
  await page.getByTestId("officer-looks").scrollIntoViewIfNeeded();
  await page.screenshot({ path: shot("m17-01-official-actions"), fullPage: true });
  const incidentUrl = page.url();
  await logout(page);

  // 4. The admin approves the sharper image and closes the incident with a note.
  await login(page, "demo.admin");
  await page.goto(incidentUrl);
  await page.locator('[data-testid^="sharper-approve-"]').click();
  await expect(page.getByTestId("sharper-list")).toContainText("Approved");
  await page.getByTestId("decide-close").click();
  await page.getByTestId("decide-note").fill("Sent to the Irrigation Department for removal.");
  await page.getByTestId("decide-submit").click();
  await expect(pill).toHaveAttribute("data-state", "CLOSED");
  await page.screenshot({ path: shot("m17-02-admin-closed"), fullPage: true });

  // 5. The citizen checks the reference, in Telugu: every step, and not the officials' notes.
  await page.goto(`/report/track/${ref}?demo=1`);
  await page.getByTestId("lang-te").click();
  await expect(page.getByTestId("track-status")).toContainText("ముగిసింది");
  const events = page.getByTestId("track-events");
  await expect(events).toContainText("ఒక అధికారి దీన్ని సమీక్షిస్తున్నారు");
  await expect(events).toContainText("మరింత స్పష్టమైన ఉపగ్రహ చిత్రాలను");
  await expect(events).toContainText("మార్పును అధికారులు నిర్ధారించారు");
  await expect(events).not.toContainText("Irrigation Department for removal");
  await expect(events).not.toContainText("Fresh soil on the east edge");
  await page.screenshot({ path: shot("m16-04-track-telugu"), fullPage: true });
  await page.getByTestId("lang-en").click();

  // 6. The WhatsApp conversation, from a fictional number, on the desk's demo simulator.
  await page.goto("/reports/whatsapp");
  const say = async (text: string) => {
    await page.getByTestId("wa-text").fill(text);
    await page.getByTestId("wa-send").click();
  };
  await say("restart");
  await expect(page.getByTestId("wa-thread")).toContainText("2 తెలుగు");
  await say("1");
  await expect(page.getByTestId("wa-thread")).toContainText("Share the place");
  await say("Demo Kunta 2 near the bund");
  await expect(page.getByTestId("wa-thread")).toContainText("What is happening there?");
  await say("2");
  await say("SKIP");
  await say("A wall going up");
  await say("NO");
  await expect(page.locator(".wa-msg.out").last()).toContainText("GGR-");
  await expect(page.locator(".wa-msg.out").last()).toContainText("We found the place from your words: Demo Kunta 2");
  await page.screenshot({ path: shot("m16-05-whatsapp"), fullPage: true });
});

// Open ground in the demo world, about 1 km from every demo place, a little different on each run.
const OPEN_GROUND = { latitude: 14.545 + (Math.random() - 0.5) * 0.003, longitude: 81.556 + (Math.random() - 0.5) * 0.003 };

test.describe("a place no one watches yet", () => {
  test.use({ geolocation: OPEN_GROUND, permissions: ["geolocation"] });

  test("goes on the weekly watch from its incident", async ({ page }) => {
    const ref = await reportFromPortal(page, "construction", "A compound wall going up on open government land.", "0000000004");
    await login(page, "demo.admin");
    await openIncidentOf(page, ref);
    await expect(page.getByTestId("officer-watch")).toContainText("Add this place to the weekly satellite watch");
    await page.getByTestId("watch-name").fill(`Open land east of Demo Parcel C (${ref})`);
    await page.getByTestId("watch-reason-input").fill("Government land with a wall going up; watch it every week");
    await page.getByTestId("watch-submit").click();
    await expect(page.getByTestId("watch-on")).toContainText("is on the weekly watch");
    await page.screenshot({ path: shot("m17-03-weekly-watch"), fullPage: true });
    await page.goto(`/report/track/${ref}?demo=1`);
    await expect(page.getByTestId("track-events")).toContainText("weekly watch");
    // Stop watching it again, as m14 does, so a rerun starts from the same counts.
    await page.goto("/assets");
    await page.locator(".list .row", { hasText: ref }).first().click();
    await page.getByTestId("watch-toggle").click();
    await page.getByTestId("watch-reason").fill("End of the browser check");
    await page.getByTestId("watch-confirm").click();
    await expect(page.getByTestId("watch-status")).toContainText("Not watched since");
  });
});
