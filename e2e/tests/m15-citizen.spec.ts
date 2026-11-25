/**
 * M15 and M16 done-check (DECISIONS.md D-062, D-063). A citizen reports on the public portal in
 * the demo world, from their phone's location, and gets a reference. The app:
 * - places the report on its location;
 * - opens a citizen incident;
 * - reviews the place with the (demo) satellite and finds a change the weekly screen has not seen.
 * Officials then work it in the regular flow (review, sharper imagery, confirm, close), and the
 * citizen sees each step in Telugu. The WhatsApp conversation makes a report too.
 * Everything is demo data: fictional places, demo numbers (+91 0000…), nothing leaves the machine.
 */
import { expect, test } from "@playwright/test";
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

test("a citizen's report opens an incident, the satellite reviews it, and officials work it in the regular flow", async ({ page }) => {
  // 1. The public portal, demo world, no sign-in, English and Telugu only.
  await page.goto("/report?demo=1");
  await expect(page.getByTestId("portal-demo")).toBeVisible();
  await expect(page.getByTestId("lang-ur")).toHaveCount(0);
  await page.getByRole("button", { name: "Use my location" }).click();
  await expect(page.getByTestId("pin-status")).toContainText("Pin placed");
  await page.getByTestId("what-dumping").click();
  await page.getByTestId("photo-input").setInputFiles({ name: "site.png", mimeType: "image/png", buffer: PNG });
  await page.getByTestId("description").fill("Lorries tipping soil at the edge of the kunta since yesterday.");
  await page.getByTestId("phone").fill("0000000003");
  await page.getByTestId("send-code").click();
  const demoCode = (await page.getByTestId("demo-code").textContent())!.match(/(\d{6})/)![1];
  await page.getByTestId("code").fill(demoCode);
  await page.getByTestId("verify-code").click();
  await expect(page.getByTestId("phone-verified")).toContainText("+91");
  await page.getByTestId("consent").check();
  await page.screenshot({ path: shot("m16-01-portal-form"), fullPage: true });
  await page.getByTestId("report-submit").click();
  await expect(page.getByTestId("report-done")).toBeVisible();
  const ref = (await page.getByTestId("report-ref").textContent())!.trim();
  expect(ref).toMatch(/^GGR-[0-9A-Z]{4}-[0-9A-Z]{4}$/);
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
  await page.getByTestId("review-needs_site_visit").check();
  await page.getByTestId("review-note").fill("Fresh soil on the east edge on the newest image. A sharper image would show the extent.");
  await page.getByTestId("review-submit").click();
  await page.screenshot({ path: shot("m16-03-citizen-incident"), fullPage: true });
  const incidentUrl = page.url();
  await logout(page);

  // 3. The admin asks for a sharper image, confirms with a note, and closes with a note.
  await login(page, "demo.admin");
  await page.goto(incidentUrl);
  await page.getByRole("button", { name: "Request sharper imagery" }).click();
  await expect(page.getByTestId("actions")).toContainText("Request recorded");
  await page.getByTestId("action-CONFIRMED").click();
  await page.getByTestId("input-note").fill("Fill inside the kunta, confirmed on the review and the images.");
  await page.getByTestId("submit-action").click();
  await page.getByTestId("action-CLOSED").click();
  await page.getByTestId("input-note").fill("Sent to the Irrigation Department for removal.");
  await page.getByTestId("submit-action").click();
  await expect(page.locator(".detail-head .pill")).toHaveAttribute("data-state", "CLOSED");

  // 4. The citizen checks the reference, in Telugu: every step, and not the officials' notes.
  await page.goto(`/report/track/${ref}?demo=1`);
  await page.getByTestId("lang-te").click();
  await expect(page.getByTestId("track-status")).toContainText("ముగిసింది");
  const events = page.getByTestId("track-events");
  await expect(events).toContainText("ఒక అధికారి దీన్ని సమీక్షిస్తున్నారు");
  await expect(events).toContainText("మరింత స్పష్టమైన ఉపగ్రహ చిత్రాలను");
  await expect(events).toContainText("మార్పును అధికారులు నిర్ధారించారు");
  await expect(events).not.toContainText("Irrigation Department for removal");
  await page.screenshot({ path: shot("m16-04-track-telugu"), fullPage: true });
  await page.getByTestId("lang-en").click();

  // 5. The WhatsApp conversation, from a fictional number, on the desk's demo simulator.
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
