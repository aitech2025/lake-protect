import { defineConfig } from "@playwright/test";

const base = process.env.E2E_BASE ?? "http://web";

export default defineConfig({
  testDir: "./tests",
  workers: 1,
  fullyParallel: false,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  reporter: [["list"]],
  outputDir: "test-results/artifacts",
  use: {
    baseURL: base,
    viewport: { width: 1440, height: 900 },
    screenshot: "only-on-failure",
    launchOptions: {
      // The stack is reached as http://web inside Docker. Treat it as a secure origin so the
      // service worker, IndexedDB queue and geolocation behave as they would on localhost.
      args: [`--unsafely-treat-insecure-origin-as-secure=${base}`],
    },
  },
});
