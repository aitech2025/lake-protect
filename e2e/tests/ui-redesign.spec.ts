import { expect, test } from "@playwright/test";
import { login } from "./helpers";
import AxeBuilder from "@axe-core/playwright";

async function signInViewer(page: import("@playwright/test").Page) {
  const response = await page.request.get("/api/auth/demo-users");
  expect(response.ok()).toBeTruthy();
  const users = await response.json() as { username: string; role: string; language?: string }[];
  const viewer = users.find((user) => user.role === "viewer" && user.language === "en") ?? users.find((user) => user.role === "viewer");
  expect(viewer, "a viewer demo account should be seeded").toBeTruthy();
  await login(page, viewer!.username);
}

test("redesigned shell preserves role navigation, asset search and map access", async ({ page }) => {
  await page.goto("/login");
  await page.evaluate(() => localStorage.setItem("lp.lang", "en"));
  await page.reload();

  await signInViewer(page);
  await expect(page.getByTestId("dashboard")).toBeVisible();
  await expect(page.getByTestId("nav-officials")).toHaveCount(0);

  const search = page.getByRole("combobox", { name: "Search assets, incidents and reports" });
  await search.fill("Lake");
  const result = page.locator("#global-search-results a").first();
  await expect(result).toBeVisible();
  await result.click();
  await expect(page.getByTestId("asset360")).toBeVisible();
  await expect(page.getByTestId("asset360-map")).toBeVisible();
  await page.getByRole("tab", { name: "Inspections" }).click();
  await expect(page.getByTestId("asset-inspections")).toBeVisible();

  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "Open navigation" }).click();
  await page.getByTestId("nav-map").click();
  await expect(page.getByTestId("full-map-page")).toBeVisible();
  await expect(page.getByTestId("full-asset-map").locator("button.pin-wrap").first()).toBeVisible();
  const markerAssetId = await page.getByTestId("full-asset-map").evaluate((root) => {
    const markers = Array.from(root.querySelectorAll<HTMLButtonElement>("button.pin-wrap"));
    const exposed = markers.find((marker) => {
      const rect = marker.getBoundingClientRect();
      const hit = document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2);
      return hit === marker || (hit !== null && marker.contains(hit));
    });
    return exposed?.dataset.assetId ?? null;
  });
  expect(markerAssetId, "the full map should expose a clickable asset marker").toBeTruthy();
  const marker = page.getByTestId("full-asset-map").locator(`button.pin-wrap[data-asset-id="${markerAssetId}"]`);
  await expect(marker).toBeVisible();
  await marker.click();
  await expect(page.getByTestId("asset360")).toBeVisible();
  await expect(page.getByTestId("asset360-map")).toBeVisible();

  await page.setViewportSize({ width: 768, height: 1024 });
  await page.goto("/alerts");
  await expect(page.locator("main h1").first()).toBeVisible();
  const hasHorizontalOverflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
  expect(hasHorizontalOverflow, "tablet layout should not overflow horizontally").toBeFalsy();

  await page.goto("/login");
  await login(page, "demo.admin");
  await expect(page.getByTestId("nav-officials")).toBeVisible();

  for (const route of ["/dashboard", "/map", "/inbox", "/officials", "/alerts", "/reports", "/assets", "/records", "/sources", "/audit", "/satellites", "/monthly", "/registry", "/system", "/whatsapp-test", "/citizen-operations"]) {
    await page.goto(route);
    await expect(page.locator("main h1, .full-map-head h1").first(), `${route} should render its page heading`).toBeVisible();
  }

  await page.goto("/report");
  await expect(page.getByTestId("portal")).toBeVisible();
  await page.goto("/report/track");
  await expect(page.locator(".portal h1").first()).toBeVisible();
  await page.goto("/report/track/GGR-UIQA-0000");
  await expect(page.getByTestId("track-view")).toHaveCount(0);
  await expect(page.getByRole("alert")).toBeVisible();

  const dynamicIds = await page.evaluate(async () => {
    const token = localStorage.getItem("lp.token");
    const headers = token ? { Authorization: `Bearer ${token}` } : {};
    const [alerts, reports] = await Promise.all([
      fetch("/api/alerts", { headers }).then((r) => r.ok ? r.json() : null),
      fetch("/api/reports", { headers }).then((r) => r.ok ? r.json() : null),
    ]);
    return { alert: alerts?.items?.[0]?.id, report: reports?.items?.[0]?.id };
  });
  await page.goto(`/alerts/${dynamicIds.alert ?? "uiqa-not-found"}`);
  await expect(page.locator('[data-testid="alert-detail"], [data-state-kind="not-found"], [data-state-kind="error"]').first()).toBeVisible();
  await page.goto(`/reports/${dynamicIds.report ?? "uiqa-not-found"}`);
  await expect(page.locator('[data-testid="report-detail"], [data-state-kind="not-found"], [data-state-kind="error"]').first()).toBeVisible();

  await page.goto("/dashboard");
  await page.locator(".profile-menu summary").click();
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login$/);
});

test("global search identifies and retries a source that failed independently", async ({ page }) => {
  await page.goto("/login");
  await page.evaluate(() => localStorage.setItem("lp.lang", "en"));
  await page.reload();
  await signInViewer(page);

  let failOnce = true;
  await page.route("**/api/alerts", async (route) => {
    if (failOnce) { failOnce = false; await route.abort(); return; }
    await route.continue();
  });
  const search = page.getByRole("combobox", { name: "Search assets, incidents and reports" });
  await search.fill("Lake");
  await expect(page.getByTestId("search-partial")).toContainText("Incidents");
  await page.getByTestId("search-partial").getByRole("button", { name: "Retry" }).click();
  await expect(page.getByTestId("search-partial")).toHaveCount(0);
  await expect(page.locator("#global-search-results a").first()).toBeVisible();
});

test("redesigned routes pass automated WCAG AA checks at desktop, tablet and mobile widths", async ({ page }) => {
  test.setTimeout(360_000);
  await page.goto("/login");
  await page.evaluate(() => localStorage.setItem("lp.lang", "en"));
  await page.reload();
  await login(page, "demo.admin");

  const dynamicRoutes = await page.evaluate(async () => {
    const token = localStorage.getItem("lp.token");
    const headers = token ? { Authorization: `Bearer ${token}` } : {};
    const [assets, alerts, reports] = await Promise.all([
      fetch("/api/assets", { headers }).then((r) => r.ok ? r.json() : null),
      fetch("/api/alerts", { headers }).then((r) => r.ok ? r.json() : null),
      fetch("/api/reports", { headers }).then((r) => r.ok ? r.json() : null),
    ]);
    return [
      `/assets/${assets?.features?.[0]?.id ?? "uiqa-not-found"}`,
      `/alerts/${alerts?.items?.[0]?.id ?? "uiqa-not-found"}`,
      `/reports/${reports?.items?.[0]?.id ?? "uiqa-not-found"}`,
      "/report/track/GGR-UIQA-0000",
    ];
  });
  const routes = ["/login", "/dashboard", "/map", "/inbox", "/officials", "/alerts", "/reports", "/assets", "/records", "/sources", "/audit", "/satellites", "/monthly", "/registry", "/system", "/whatsapp-test", "/citizen-operations", "/report", "/report/track", ...dynamicRoutes];
  const widths = [1440, 768, 390];
  const violations: string[] = [];
  for (const width of widths) {
    await page.setViewportSize({ width, height: width === 390 ? 844 : 1024 });
    for (const route of routes) {
      await page.goto(route);
      await expect(page.locator("h1, .page-state h2").first(), `${route} should show a page or error heading at ${width}px`).toBeVisible();
      const result = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
      for (const violation of result.violations) {
        const nodes = violation.nodes.slice(0, 5).map((node) => {
          const check = node.any.find((item) => item.id === "color-contrast");
          const data = check?.data as { fgColor?: string; bgColor?: string; contrastRatio?: number } | undefined;
          return `${node.target.join(" ")}${data ? ` ${data.fgColor}/${data.bgColor} (${data.contrastRatio})` : ""}`;
        });
        violations.push(`${route}@${width} ${violation.id}: ${nodes.join(", ")}`);
      }
    }
  }
  expect(violations, violations.join("\n")).toEqual([]);
});
