/** M7: the case file screen. Pack versions, integrity check, draft mark, checklist. Fictional data only. */
import { expect, test } from "@playwright/test";
import { login, openAlert, shot } from "./helpers";

test.describe.configure({ mode: "serial" });

test("legal officer sees the seeded pack, checks it, and makes a new version", async ({ page }) => {
  await login(page, "demo.legal");
  await openAlert(page, "Demo Cheruvu 2");
  const caseFile = page.getByTestId("case-file");
  await expect(caseFile.getByTestId("pack-v1")).toContainText("draft for counsel review");
  await caseFile.getByTestId("check-pack-v1").click();
  await expect(page.getByTestId("pack-message")).toContainText("files match their hashes");

  // The checklist shows the recorded gap, and the field photos load.
  await expect(page.getByTestId("checklist")).toContainText("Checklist gaps");
  await expect.poll(() => page.locator(".photo-thumb").evaluateAll((els) => els.filter((e) => (e as HTMLImageElement).naturalWidth > 0).length)).toBeGreaterThanOrEqual(2);

  await caseFile.getByTestId("generate-pack").click();
  await expect(page.getByTestId("pack-message")).toContainText("version 2 generated");
  await expect(caseFile.getByTestId("pack-v2")).toBeVisible();
  await expect(caseFile.getByTestId("pack-v1")).toBeVisible(); // never overwritten
  await page.screenshot({ path: shot("m7-01-case-file"), fullPage: true });
});

test("the PDF and zip download as single files", async ({ page, request }) => {
  const tok = (await (await request.post("/api/auth/login", { data: { username: "demo.legal" } })).json()).token;
  const headers = { Authorization: `Bearer ${tok}` };
  const items = (await (await request.get("/api/alerts", { headers })).json()).items as { id: number; asset_name: string }[];
  const id = items.find((a) => a.asset_name === "Demo Cheruvu 2")!.id;
  const pdf = await request.get(`/api/alerts/${id}/evidence-pack/pdf?version=1`, { headers });
  expect(pdf.headers()["content-type"]).toBe("application/pdf");
  expect((await pdf.body()).subarray(0, 4).toString()).toBe("%PDF");
  const zip = await request.get(`/api/alerts/${id}/evidence-pack?version=1`, { headers });
  expect(zip.headers()["content-type"]).toBe("application/zip");
  expect(zip.headers()["x-manifest-sha256"]).toMatch(/^[0-9a-f]{64}$/);
  await page.goto("/login"); // keep the page fixture in use for consistent reporting
});
