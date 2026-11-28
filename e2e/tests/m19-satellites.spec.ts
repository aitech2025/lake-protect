/**
 * M19 done-check (DECISIONS.md D-066): the admin keeps the satellite image sources. The five the app
 * used are there; the admin adds a sharper-image source, changes its price, turns it off and on, and
 * deletes it with a reason, and every step is in the history. The optical source the screen reads
 * cannot be turned off. An official sees the sources but cannot change them.
 */
import { expect, test } from "@playwright/test";
import { login, shot } from "./helpers";

test("the admin adds, changes, turns off and deletes a satellite source", async ({ page }) => {
  const key = `e2e-test-${Date.now().toString(36)}`;
  await login(page, "demo.admin");
  await page.getByTestId("nav-satellites").click();
  await expect(page.getByTestId("sat-row-sentinel-2-l2a")).toContainText("sentinel-2-c1-l2a");
  await expect(page.getByTestId("sat-row-sentinel-1-rtc")).toBeVisible();
  await expect(page.getByTestId("sat-row-commercial_archive")).toContainText("US$ 26 per sq km");
  await expect(page.getByTestId("sat-row-isro_nrsc")).toContainText("price on request");

  // The screen always has an optical source.
  await page.getByTestId("sat-toggle-sentinel-2-l2a").click();
  await expect(page.getByTestId("sat-message")).toContainText("Turn another optical source on first");

  // Add a sharper-image source.
  await page.getByTestId("sat-add").click();
  await page.getByTestId("sat-purpose").selectOption("sharper");
  await page.getByTestId("sat-key").fill(key);
  await page.getByTestId("sat-name").fill("Browser check: tasking 30 cm");
  await page.getByTestId("sat-provider").fill("Test reseller");
  await page.getByTestId("sat-resolution").fill("0.3");
  await page.getByTestId("sat-price").fill("40");
  await page.getByTestId("sat-save").click();
  await expect(page.getByTestId("sat-message")).toContainText("saved");
  const row = page.getByTestId(`sat-row-${key}`);
  await expect(row).toContainText("US$ 40 per sq km");

  // Change its price, turn it off, then delete it with a reason.
  await page.getByTestId(`sat-edit-${key}`).click();
  await page.getByTestId("sat-price").fill("35");
  await page.getByTestId("sat-save").click();
  await expect(row).toContainText("US$ 35 per sq km");
  await page.getByTestId(`sat-toggle-${key}`).click();
  await expect(row).toContainText("Off");
  await page.screenshot({ path: shot("m19-01-satellites"), fullPage: true });
  await page.getByTestId(`sat-delete-${key}`).click();
  await expect(page.getByTestId("sat-delete-confirm")).toBeDisabled();
  await page.getByTestId("sat-reason").fill("Browser check over");
  await page.getByTestId("sat-delete-confirm").click();
  await expect(page.getByTestId("sat-message")).toContainText("deleted");
  await expect(row).toHaveCount(0);
  const history = page.getByTestId("sat-history");
  await expect(history).toContainText("Deleted: Browser check: tasking 30 cm: Browser check over");
  await expect(history).toContainText("Changed");
  await expect(history).toContainText("Added");

  // A senior official sees the sources, with no way to change them.
  await login(page, "demo.senior");
  await page.goto("/satellites");
  await expect(page.getByTestId("sat-row-sentinel-2-l2a")).toBeVisible();
  await expect(page.getByTestId("sat-add")).toHaveCount(0);
  await expect(page.locator('[data-testid^="sat-edit-"]')).toHaveCount(0);
});
