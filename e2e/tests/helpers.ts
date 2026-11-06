import { expect, type Page } from "@playwright/test";

export async function login(page: Page, username: string): Promise<void> {
  await page.goto("/login");
  await page.getByTestId(`login-${username}`).click();
  await expect(page).not.toHaveURL(/\/login$/);
}

export async function logout(page: Page): Promise<void> {
  await page.evaluate(() => {
    localStorage.removeItem("lp.token");
    localStorage.removeItem("lp.user");
  });
}

export async function openAlert(page: Page, assetName: string): Promise<void> {
  await page.goto("/alerts");
  await page.locator('[data-testid^="alert-row-"]', { hasText: assetName }).first().click();
  await expect(page.getByTestId("alert-detail")).toBeVisible();
}

export async function stateOf(page: Page): Promise<string | null> {
  return page.locator(".detail-head .pill").getAttribute("data-state");
}

export const shot = (name: string) => `test-results/${name}.png`;
