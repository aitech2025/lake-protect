"use strict";
// Date strip: no label overlaps another or leaves its panel, at every review width, in both languages.
const { chromium } = require("/e2e/node_modules/playwright");
const BASE = "http://localhost";
(async () => {
  const browser = await chromium.launch({ args: [`--unsafely-treat-insecure-origin-as-secure=${BASE}`] });
  const results = [];
  for (const user of ["demo.analyst", "demo.legal"]) {
    const ctx = await browser.newContext({ baseURL: BASE, viewport: { width: 1440, height: 900 } });
    const p = await ctx.newPage();
    await p.goto("/login");
    await p.getByTestId(`login-${user}`).click();
    await p.waitForURL((u) => !u.pathname.endsWith("/login"));
    const items = await p.evaluate(async () => (await (await fetch("/api/alerts", { headers: { Authorization: "Bearer " + localStorage.getItem("lp.token") } })).json()).items);
    for (const a of items) {
      for (const lang of ["en", "te"]) {
        await p.evaluate((l) => localStorage.setItem("lp.lang", l), lang);
        for (const w of [1440, 1280, 1024, 768, 390, 320]) {
          await p.setViewportSize({ width: w, height: 900 });
          await p.goto(`/alerts/${a.id}`);
          await p.waitForSelector("[data-testid=dated-bracket]", { timeout: 15000 });
          const r = await p.evaluate(() => {
            const strip = document.querySelector("[data-testid=dated-bracket]");
            const panel = strip.closest(".panel").getBoundingClientRect();
            const boxes = [...strip.querySelectorAll(".mark, .bracket-window span")].map((m) => m.getBoundingClientRect());
            let overlaps = 0;
            for (let i = 0; i < boxes.length; i++) for (let j = i + 1; j < boxes.length; j++) {
              const x = boxes[i], y = boxes[j];
              if (x.left < y.right - 1 && y.left < x.right - 1 && x.top < y.bottom - 1 && y.top < x.bottom - 1) overlaps++;
            }
            const escape = Math.max(0, ...boxes.map((b) => Math.max(b.right - panel.right, panel.left - b.left, b.bottom - panel.bottom)));
            return { overlaps, escape: Math.round(escape) };
          });
          results.push({ user, alert: a.asset_name, lang, w, ...r });
        }
      }
      if (user === "demo.legal") break; // the legal pass only needs one editable alert
    }
    await ctx.close();
  }
  await browser.close();
  const bad = results.filter((r) => r.overlaps || r.escape);
  console.log(`checked ${results.length} strip renders (${new Set(results.map((r) => r.alert)).size} alerts x 2 languages x 6 widths): ${bad.length} with overlap or escape`);
  for (const b of bad.slice(0, 15)) console.log(JSON.stringify(b));
})().catch((e) => { console.error(e); process.exit(1); });
