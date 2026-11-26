import { expect, test } from "@playwright/test";
import { login } from "./helpers";

test("admin can inspect citizen review queues and disabled provider states", async ({ page }) => {
  await login(page, "demo.admin");
  await page.goto("/citizen-operations");
  await expect(page.getByTestId("citizen-operations")).toBeVisible();
  await expect(page.getByTestId("citizen-review-queue")).toBeVisible();
  await expect(page.getByTestId("citizen-message-queue")).toBeVisible();
  await expect(page.getByTestId("citizen-channel-readiness")).toBeVisible();
  await expect(page.getByText("WhatsApp inbound")).toBeVisible();
});
