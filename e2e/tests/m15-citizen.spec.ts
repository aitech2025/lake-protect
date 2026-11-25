/**
 * M15 done-check (DECISIONS.md D-062): a citizen reports on the public portal in the demo world,
 * verifies a demo phone, gets a reference; an official records a check; the admin closes it; the
 * citizen sees each step in their own language. The WhatsApp conversation makes a report too.
 * Everything is demo data: fictional places, demo numbers (+91 0000…), nothing leaves the machine.
 */
import { expect, test } from "@playwright/test";
import { login, logout, shot } from "./helpers";

// A 24 x 24 PNG, drawn here, so no real photo is ever used.
const PNG = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAIAAABvFaqvAAAAOklEQVR4nGNMaPBhoAZgooopowaNGkQlwILMUXnwgVT9dxQEIIzB57VRg0YNogZAySLw9E4GGHxeAwAq5QVs/cpaywAAAABJRU5ErkJggg==",
  "base64",
);

test("a citizen reports, officials act, and the citizen sees each step", async ({ page }) => {
  // 1. The public portal, demo world, no sign-in.
  await page.goto("/report?demo=1");
  await expect(page.getByTestId("portal-demo")).toBeVisible();
  await page.getByTestId("lang-ur").click();
  await expect(page.getByTestId("portal")).toHaveAttribute("dir", "rtl");
  await page.screenshot({ path: shot("m15-01-portal-urdu"), fullPage: true });
  await page.getByTestId("lang-en").click();
  await expect(page.getByTestId("portal")).toHaveAttribute("dir", "ltr");

  const map = page.getByTestId("portal-map");
  await expect(map.locator("canvas")).toBeVisible();
  const box = (await map.boundingBox())!;
  await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
  await expect(page.getByTestId("pin-status")).toContainText("Pin placed");
  await page.getByTestId("what-construction").click();
  await page.getByTestId("photo-input").setInputFiles({ name: "site.png", mimeType: "image/png", buffer: PNG });
  await page.getByTestId("description").fill("A wall going up near the bund, started this week.");
  await page.getByTestId("phone").fill("0000000003");
  await page.getByTestId("send-code").click();
  const demoCode = (await page.getByTestId("demo-code").textContent())!.match(/(\d{6})/)![1];
  await page.getByTestId("code").fill(demoCode);
  await page.getByTestId("verify-code").click();
  await expect(page.getByTestId("phone-verified")).toContainText("+91");
  await page.getByTestId("consent").check();
  await page.screenshot({ path: shot("m15-02-portal-form"), fullPage: true });
  await page.getByTestId("report-submit").click();
  await expect(page.getByTestId("report-done")).toBeVisible();
  const ref = (await page.getByTestId("report-ref").textContent())!.trim();
  expect(ref).toMatch(/^GGR-[0-9A-Z]{4}-[0-9A-Z]{4}$/);
  await expect(page.getByTestId("report-done")).toContainText("We received your report");
  await page.screenshot({ path: shot("m15-03-reference"), fullPage: true });

  // 2. An official sees it on the desk and records a check. No phone number is shown.
  await login(page, "demo.viewer2");
  await page.getByTestId("nav-reports").click();
  await page.getByTestId(`report-row-${ref}`).getByRole("link", { name: ref }).click();
  await expect(page.getByTestId("report-detail")).toContainText("Officials never see the number");
  await expect(page.getByTestId("report-detail")).not.toContainText("0000000003");
  await page.getByTestId("check-not-visible").check();
  await page.getByTestId("check-note").fill("Too small for this week's image; nothing visible yet.");
  await page.getByTestId("check-submit").click();
  await expect(page.getByTestId("report-history")).toContainText("Too small for this week's image");
  await expect(page.getByTestId("close-form")).toHaveCount(0); // only the admin closes
  await logout(page);

  // 3. The admin closes it with a reason the citizen will read.
  await login(page, "demo.admin");
  await page.goto("/reports");
  await page.getByTestId(`report-row-${ref}`).getByRole("link", { name: ref }).click();
  await page.getByTestId("close-reason").selectOption("passed_on");
  await page.getByTestId("close-dept").selectOption("municipal");
  await page.getByTestId("close-note").fill("A private compound wall on patta land next to the lake. Sent to the municipality.");
  await page.getByTestId("close-submit").click();
  await expect(page.getByTestId("report-status")).toHaveText("Closed");
  // No SMS gateway yet: each update waits as queued, then held by the notifier; never sent later.
  await expect(page.getByTestId("report-messages")).toContainText(/queued|held/);
  await page.screenshot({ path: shot("m15-04-desk-report"), fullPage: true });

  // 4. The citizen checks the reference, in Telugu.
  await page.goto(`/report/track/${ref}?demo=1`);
  await page.getByTestId("lang-te").click();
  await expect(page.getByTestId("track-status")).toContainText("ముగిసింది");
  await expect(page.getByTestId("track-events")).toContainText("పురపాలక సంస్థ");
  await expect(page.getByTestId("track-events")).not.toContainText("Sent to the municipality"); // internal notes stay inside
  await page.screenshot({ path: shot("m15-05-track-telugu"), fullPage: true });
  await page.getByTestId("lang-en").click();

  // 5. The WhatsApp conversation, from a fictional number, on the desk's demo simulator.
  await page.goto("/reports/whatsapp");
  const say = async (text: string) => {
    await page.getByTestId("wa-text").fill(text);
    await page.getByTestId("wa-send").click();
  };
  await say("restart");
  await expect(page.getByTestId("wa-thread")).toContainText("1 English");
  await say("1");
  await expect(page.getByTestId("wa-thread")).toContainText("Share the place");
  await page.getByTestId("wa-location").click();
  const wmap = page.getByTestId("wa-map");
  await expect(wmap.locator("canvas")).toBeVisible();
  const wbox = (await wmap.boundingBox())!;
  await page.mouse.click(wbox.x + wbox.width / 2, wbox.y + wbox.height / 2);
  await expect(page.getByTestId("wa-thread")).toContainText("What is happening there?");
  await say("1");
  await say("SKIP");
  await say("Lorries tipping soil at night");
  await say("NO");
  await expect(page.getByTestId("wa-thread")).toContainText("Thank you.");
  await expect(page.locator(".wa-msg.out").last()).toContainText("GGR-");
  await page.screenshot({ path: shot("m15-06-whatsapp"), fullPage: true });
});
