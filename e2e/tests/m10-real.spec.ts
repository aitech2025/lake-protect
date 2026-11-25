/**
 * M10 and M18 done-check (DECISIONS.md D-065): GeoGuard shows real data only. There is no demo
 * switch, no demo band and no drawn demo map: the desk lists the real lakes and their incidents
 * on the offline Sentinel-2 base map.
 */
import { expect, test } from "@playwright/test";
import { login } from "./helpers";

test("the desk shows only real lakes, on the Sentinel-2 map", async ({ page }) => {
  const tiles: string[] = [];
  page.on("request", (r) => {
    if (r.url().includes("/api/tiles/")) tiles.push(r.url());
  });
  await login(page, "demo.viewer2");
  await expect(page.getByTestId("dataset-demo")).toHaveCount(0);
  await expect(page.getByTestId("demo-badge")).toHaveCount(0);

  // The overview groups the real lakes by district (from OpenStreetMap boundaries, D-060).
  await expect(page.getByTestId("dash-path")).toContainText("Telangana");
  await expect(page.getByTestId("dash-children")).toContainText("Medchal–Malkajgiri");
  await expect(page.getByText("not the revenue record")).toBeVisible();
  await page.getByTestId("nav-alerts").click();
  await expect(page.getByTestId("screening-summary")).toBeVisible();
  const rows = page.locator('[data-testid^="alert-row-"]');
  await expect(rows.first()).toBeVisible();
  for (const code of await rows.evaluateAll((els) => els.map((e) => e.textContent ?? ""))) {
    expect(code).not.toContain("DEMO-");
  }
  await expect.poll(() => tiles.some((u) => u.includes("/tiles/s2/"))).toBe(true);
  expect(tiles.some((u) => u.includes("/tiles/demo/"))).toBe(false);

  await page.goto("/assets");
  await expect(page.locator(".list .row").first()).toBeVisible();
  const names = await page.locator(".list .row h3").allTextContents();
  expect(names.length).toBeGreaterThan(50);
  expect(names.some((n) => n.startsWith("Demo "))).toBe(false);
});
