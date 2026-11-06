/**
 * M5 done-check: an analyst confirms or closes from a real image pair, and a nodal officer assigns.
 * Runs against a freshly reset demo database (fictional data only).
 */
import { expect, test } from "@playwright/test";
import { login, logout, openAlert, shot, stateOf } from "./helpers";

test.describe.configure({ mode: "serial" });

test("analyst sees the queue with the demo badge and a map", async ({ page }) => {
  await login(page, "demo.analyst");
  await expect(page).toHaveURL(/\/alerts$/);
  await expect(page.getByTestId("demo-badge")).toBeVisible();
  await expect(page.locator('[data-testid^="alert-row-"]').first()).toBeVisible();
  await expect(page.locator(".pin").first()).toBeVisible();
  await page.waitForTimeout(800); // let base-map tiles paint for the screenshot
  await page.screenshot({ path: shot("m5-01-queue") });
});

test("analyst confirms the headline alert after comparing the image pair", async ({ page }) => {
  await login(page, "demo.analyst");
  await openAlert(page, "Demo Cheruvu 1");
  const imgs = page.getByTestId("image-pair").locator("img");
  await expect(imgs).toHaveCount(2);
  await expect.poll(() => imgs.evaluateAll((els) => els.every((e) => (e as HTMLImageElement).naturalWidth > 0))).toBe(true);
  await expect(page.getByTestId("boundary-seal")).toHaveAttribute("data-certainty", "confirmed");
  await expect(page.getByTestId("legal-panel")).toContainText("Inside the lake boundary");
  await expect(page.getByTestId("statement")).toHaveText("Imagery shows physical change. It does not establish title or legality.");
  await expect(page.getByTestId("dated-bracket")).toBeVisible();
  await page.waitForTimeout(800);
  await page.screenshot({ path: shot("m5-02-alert-detail"), fullPage: true });

  await page.getByTestId("action-CONFIRMED").click();
  await page.getByTestId("submit-action").click();
  await expect(page.getByRole("alert")).toContainText("image_pair_reviewed"); // refused until the pair is reviewed
  await page.getByTestId("input-reviewed").check();
  await page.getByTestId("submit-action").click();
  await expect.poll(() => stateOf(page)).toBe("CONFIRMED");
});

test("closing as not real takes two different people", async ({ page }) => {
  await login(page, "demo.analyst");
  await openAlert(page, "Demo Parcel C");
  await expect(page.getByTestId("image-pair").locator("img")).toHaveCount(2);
  await page.getByTestId("action-CLOSED_NOT_REAL").click();
  await page.getByTestId("input-code").selectOption("transient_object");
  await page.getByTestId("input-reason").fill("Stored building material, gone on the next image");
  await page.getByTestId("submit-action").click();
  await expect(page.getByTestId("actions").getByRole("status")).toContainText("Waiting for a second person");
  await expect(page.getByTestId("actions")).toContainText("Waiting for a second person to sign");
  expect(await stateOf(page)).toBe("TRIAGE");

  await logout(page);
  await login(page, "demo.reviewer");
  await openAlert(page, "Demo Parcel C");
  await page.getByTestId("action-CLOSED_NOT_REAL").click();
  await page.getByTestId("submit-action").click();
  await expect.poll(() => stateOf(page)).toBe("CLOSED_NOT_REAL");
  await page.screenshot({ path: shot("m5-03-closed-by-two") });
});

test("nodal officer assigns the confirmed alert to a field officer", async ({ page }) => {
  await login(page, "demo.nodal");
  await openAlert(page, "Demo Cheruvu 1");
  await page.getByTestId("action-ASSIGNED").click();
  await page.getByTestId("input-owner").selectOption({ label: "Demo Field Officer 1" });
  await page.getByTestId("submit-action").click();
  await expect.poll(() => stateOf(page)).toBe("ASSIGNED");
  await expect(page.locator(".detail-head")).toContainText("Demo Field Officer 1");
  await page.screenshot({ path: shot("m5-04-assigned") });
});

test("the desk switches to Telugu", async ({ page }) => {
  await login(page, "demo.nodal");
  await page.getByRole("button", { name: "తెలుగు" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("హెచ్చరికలు");
  await expect(page.getByTestId("demo-badge")).toContainText("డెమో డేటా");
  await page.screenshot({ path: shot("m5-05-telugu") });
  await page.getByRole("button", { name: "English" }).click();
});
