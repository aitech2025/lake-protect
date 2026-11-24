/**
 * M10 done-check: the desk switches between the real Hyderabad lakes and the fictional demo
 * world, never mixing them, and real maps use the offline Sentinel-2 base map.
 */
import { expect, test } from "@playwright/test";
import { login } from "./helpers";

test("the desk shows real lakes on the Sentinel-2 map, apart from the demo world", async ({ page }) => {
  const tiles: string[] = [];
  page.on("request", (r) => {
    if (r.url().includes("/api/tiles/")) tiles.push(r.url());
  });
  await login(page, "demo.viewer2");

  // Demo world first (the default): demo band on screen, demo tiles only.
  await expect(page.getByTestId("dataset-demo")).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByTestId("demo-badge")).toBeVisible();

  await page.getByTestId("dataset-real").click();
  await expect(page.getByTestId("dataset-real")).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByTestId("screening-summary")).toBeVisible();
  // No demo record on screen, so no demo band.
  await expect(page.getByTestId("demo-badge")).toHaveCount(0);
  // Every alert listed is real.
  for (const code of await page.locator('[data-testid^="alert-row-"]').evaluateAll((els) => els.map((e) => e.getAttribute("data-testid") ?? ""))) {
    expect(code).not.toContain("DEMO-");
  }
  await expect.poll(() => tiles.some((u) => u.includes("/tiles/s2/"))).toBe(true);

  await page.goto("/assets");
  await expect(page.locator(".list .row").first()).toBeVisible();
  const names = await page.locator(".list .row h3").allTextContents();
  expect(names.length).toBeGreaterThan(50);
  expect(names.some((n) => n.startsWith("Demo "))).toBe(false);

  // The choice is remembered in this browser, and switching back restores the demo world.
  await page.reload();
  await expect(page.getByTestId("dataset-real")).toHaveAttribute("aria-pressed", "true");
  await page.getByTestId("dataset-demo").click();
  await expect(page.locator(".list .row h3").first()).toContainText("Demo");
});
