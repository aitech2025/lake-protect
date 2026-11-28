/**
 * M14 done-check (DECISIONS.md D-061): the admin adds a location to watch by drawing it, the
 * same place cannot be added twice from a file, and stopping the watch keeps the record.
 * Endowment and forest land are shown as planned. Runs on the real data: the location it adds is
 * stopped again at the end, so a rerun starts from the same counts.
 */
import { expect, test } from "@playwright/test";
import { login, shot } from "./helpers";

test("the admin adds, refuses a duplicate of, and stops watching a location", async ({ page }) => {
  await login(page, "demo.admin");
  await page.goto("/assets");

  // The statewide registry supports district → mandal drill-down without losing map context.
  const districtFilter = page.getByTestId("filter-district");
  const mandalFilter = page.getByTestId("filter-mandal");
  await expect(districtFilter).toBeVisible();
  await expect.poll(async () => districtFilter.locator("option").count()).toBeGreaterThan(1);
  expect(await districtFilter.locator("option").count()).toBeGreaterThan(1);
  let selectedDistrict = "";
  for (let i = 1; i < await districtFilter.locator("option").count(); i++) {
    await districtFilter.selectOption({ index: i });
    if (await mandalFilter.locator("option").count() > 1) {
      selectedDistrict = await districtFilter.inputValue();
      break;
    }
  }
  expect(selectedDistrict).not.toBe("");
  await mandalFilter.selectOption({ index: 1 });
  const selectedMandal = await mandalFilter.inputValue();
  const filteredRows = await page.locator(".list .row").allTextContents();
  expect(filteredRows.length).toBeGreaterThan(0);
  expect(filteredRows.every((row) => row.includes(selectedDistrict) && row.includes(selectedMandal))).toBeTruthy();
  await page.getByTestId("clear-area-filters").click();

  // Asset 360 must expose source class and avoid implying authority for unverified outlines.
  await page.locator(".list .row", { hasText: "Kapra lake" }).first().click();
  await expect(page).toHaveURL(/\/assets\/\d+$/);
  await expect(page.getByTestId("asset360")).toBeVisible();
  await expect(page.getByTestId("asset360")).toContainText(/OpenStreetMap/i);
  await page.goto("/assets");

  // What GeoGuard watches now, and what is planned.
  await expect(page.getByTestId("kind-card-water_body")).toContainText("99 watched");
  await expect(page.getByTestId("kind-card-endowment_land")).toContainText("Planned");
  await page.getByTestId("kind-card-forest_land").locator("summary").click();
  await expect(page.getByTestId("kind-card-forest_land")).toContainText("Forest Department");
  const before = Number((await page.getByTestId("kind-card-government_land").textContent())?.match(/(\d+) watched/)?.[1]);
  await page.screenshot({ path: shot("m14-01-locations"), fullPage: true });

  // Add: government land, drawn on the Sentinel-2 map.
  await page.getByTestId("add-location-open").click();
  await expect(page.getByTestId("kind-forest_land").locator("input")).toBeDisabled();
  await page.getByTestId("kind-government_land").click();
  const map = page.getByTestId("draw-map");
  await expect(map.locator("canvas")).toBeVisible();
  const box = (await map.boundingBox())!;
  const cx = box.x + box.width * 0.3, cy = box.y + box.height * 0.75;
  for (const [dx, dy] of [[0, 0], [14, 0], [14, 12], [0, 12]]) {
    await page.mouse.click(cx + dx, cy + dy);
  }
  await expect(page.getByTestId("draw-points")).toContainText("4 corners");
  await page.getByTestId("draw-finish").click();
  await expect(page.getByTestId("outline-check")).toContainText("sq m");
  await page.getByTestId("loc-name").fill(`Test parcel, browser check ${Date.now()}`);
  await page.getByTestId("loc-district").fill("Ranga Reddy");
  await expect(page.getByTestId("loc-status-drawn")).toContainText("for watching only");
  await page.screenshot({ path: shot("m14-02-add-drawn"), fullPage: true });
  await page.getByTestId("loc-submit").click();
  await expect(page.getByTestId("added-message")).toContainText("The next weekly screen includes it");
  await expect(page.getByTestId("watch-status")).toContainText("Watched every week");
  await expect(page.getByTestId("watch-history")).toContainText("Added by hand");
  await expect(page.getByTestId("kind-card-government_land")).toContainText(`${before + 1} watched`);

  // The same place from a file is refused, with a way to open the one already watched.
  const geometry = await page.evaluate(async () => {
    const r = await fetch("/api/assets?dataset=real", { headers: { Authorization: `Bearer ${localStorage.getItem("lp.token")}` } });
    const fc = await r.json();
    return fc.features.find((f: { properties: { name: string } }) => f.properties.name === "Kapra lake").geometry;
  });
  await page.getByTestId("add-location-open").click();
  await page.getByTestId("mode-upload").click();
  await page.getByTestId("loc-file").setInputFiles({ name: "kapra.geojson", mimeType: "application/geo+json", buffer: Buffer.from(JSON.stringify({ type: "Feature", properties: {}, geometry })) });
  await expect(page.getByTestId("outline-check")).toContainText("same place as Kapra lake");
  await page.getByRole("button", { name: "Open the location already watched" }).first().click();
  await expect(page.getByTestId("watch-status")).toContainText("Watched every week");

  // Stop watching the test location: nothing is deleted, and the reason is kept.
  await page.locator(".list .row", { hasText: "Test parcel, browser check" }).last().click();
  const assetRoute = new URL(page.url());
  const assetId = assetRoute.pathname.split("/").at(-1);
  await page.goto(`/assets?asset=${assetId}`);
  await page.getByTestId("watch-toggle").click();
  await expect(page.locator(".watch-form .banner")).toContainText("Nothing is deleted");
  await page.getByTestId("watch-reason").fill("End of the browser check");
  await page.getByTestId("watch-confirm").click();
  await expect(page.getByTestId("watch-status")).toContainText("Not watched since");
  await expect(page.getByTestId("watch-status")).toContainText("End of the browser check");
  await expect(page.getByTestId("kind-card-government_land")).toContainText(`${before} watched`);
  await page.screenshot({ path: shot("m14-03-stopped"), fullPage: true });
});
