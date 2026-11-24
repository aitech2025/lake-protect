/**
 * M11 done-check: the Sources page lists the four government sources with their data contracts,
 * says no agreement exists, and previews a sample load without writing anything.
 * Read-only: it uses dry runs only, so it needs no reset.
 */
import { expect, test } from "@playwright/test";
import { login, shot } from "./helpers";

test("a nodal officer previews the fictional lake register without writing anything", async ({ page }) => {
  await login(page, "demo.nodal");
  await page.getByRole("link", { name: "Sources" }).click();
  await expect(page).toHaveURL(/\/sources$/);
  for (const name of ["hmda_lpc", "irrigation", "bhu_bharati", "hydraa"]) {
    await expect(page.getByTestId(`source-${name}`)).toBeVisible();
  }
  await expect(page.getByTestId("source-hmda_lpc")).toContainText("None yet");
  await page.getByTestId("source-bhu_bharati").getByText("Data contract").click();
  await expect(page.getByTestId("source-bhu_bharati")).toContainText("ror_extract.csv");

  const runsBefore = await page.getByTestId("import-runs").locator("tbody tr").count().catch(() => 0);
  await page.getByTestId("run-hmda_lpc-sample-preview").click();
  const report = page.getByTestId("source-report");
  await expect(report).toContainText("Nothing has been written");
  await expect(report).toContainText("Assets created: 3");
  await expect(report.locator('tr[data-action="rejected"]')).toContainText("must cite its reference");
  await page.screenshot({ path: shot("m11-sources-preview"), fullPage: true });

  // A preview is not a load: the list of loads is unchanged after a reload.
  await page.reload();
  await expect(page.getByTestId("source-hmda_lpc")).toBeVisible();
  const runsAfter = await page.getByTestId("import-runs").locator("tbody tr").count().catch(() => 0);
  expect(runsAfter).toBe(runsBefore);
});

test("an analyst sees the sources but cannot load them", async ({ page }) => {
  await login(page, "demo.analyst");
  await page.goto("/sources");
  await expect(page.getByTestId("source-hydraa")).toBeVisible();
  await expect(page.locator('[data-testid^="run-"]')).toHaveCount(0);
});
