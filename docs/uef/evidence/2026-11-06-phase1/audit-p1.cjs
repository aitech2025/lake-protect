"use strict";
// Phase 1 browser QA: targeted checks for A5, A6, A7, A9 (+ pill size), A14, A18. Read-only.
const { chromium } = require("/e2e/node_modules/playwright");
const fs = require("fs");
const BASE = "http://localhost";
const OUT = "/audit/out";
fs.mkdirSync(OUT, { recursive: true });
const out = {};
const RATIO = `(a, b) => {
  const p = (c) => c.match(/[\\d.]+/g).slice(0, 3).map(Number);
  const L = (c) => { const [r, g, b] = p(c).map((v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
  const x = L(a), y = L(b); return +((Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05)).toFixed(2);
}`;

(async () => {
  const browser = await chromium.launch({ args: [`--unsafely-treat-insecure-origin-as-secure=${BASE}`] });
  const login = async (ctx, user) => {
    const p = await ctx.newPage();
    await p.goto("/login");
    await p.getByTestId(`login-${user}`).click();
    await p.waitForURL((u) => !u.pathname.endsWith("/login"));
    await p.waitForLoadState("networkidle").catch(() => {});
    await p.waitForTimeout(800);
    return p;
  };
  const tabUntil = async (p, pred, max = 40) => {
    await p.evaluate(() => { const b = document.body; b.setAttribute("tabindex", "-1"); b.focus(); b.removeAttribute("tabindex"); });
    for (let i = 0; i < max; i++) {
      await p.keyboard.press("Tab");
      if (await p.evaluate(pred)) return i + 1;
    }
    return -1;
  };

  // A18: focus ring on the rail; A9: filter label background; pill sizes
  let ctx = await browser.newContext({ baseURL: BASE, viewport: { width: 1440, height: 900 } });
  let p = await login(ctx, "demo.analyst");
  await p.goto("/alerts");
  await p.waitForTimeout(1200);
  await tabUntil(p, () => document.activeElement && document.activeElement.closest(".rail") && document.activeElement.classList.contains("active"));
  out.railFocus = await p.evaluate(`(() => { const r = ${RATIO}; const el = document.activeElement; const cs = getComputedStyle(el);
    return { el: el.textContent.trim(), outline: cs.outlineWidth + " " + cs.outlineStyle + " " + cs.outlineColor,
      vsActiveBg: r(cs.outlineColor, cs.backgroundColor), vsRail: r(cs.outlineColor, getComputedStyle(document.querySelector(".rail")).backgroundColor) }; })()`);
  await p.locator(".rail").screenshot({ path: `${OUT}/p1-rail-focus.png` });
  await p.keyboard.press("Tab"); await p.keyboard.press("Tab"); await p.keyboard.press("Tab");
  out.railButtonFocus = await p.evaluate(`(() => { const r = ${RATIO}; const el = document.activeElement; const cs = getComputedStyle(el);
    return { el: el.textContent.trim(), outlineColor: cs.outlineColor, vsRail: r(cs.outlineColor, "rgb(28,43,51)"), border: cs.borderTopColor, borderVsRail: r(cs.borderTopColor, "rgb(28,43,51)") }; })()`);
  await p.locator(".rail .who").screenshot({ path: `${OUT}/p1-rail-who-focus.png` });
  out.filterLabel = await p.evaluate(() => { const l = document.querySelector("label.field"); const s = l.querySelector("select"); return { labelBg: getComputedStyle(l).backgroundColor, selectBorder: getComputedStyle(s).borderTopColor }; });
  await p.locator(".page-head").screenshot({ path: `${OUT}/p1-queue-head.png` });
  out.pills = await p.evaluate(() => [...new Set([...document.querySelectorAll(".pill")].map((x) => `${x.className} ${getComputedStyle(x).fontSize}`))]);
  const fieldRow = p.locator(".list .row", { has: p.locator(".pill.field") }).first();
  if (await fieldRow.count()) await fieldRow.screenshot({ path: `${OUT}/p1-field-pill-row.png` });
  // danger text in the detail header (overdue on paper)
  const overdueId = await p.evaluate(async () => (await (await fetch("/api/alerts", { headers: { Authorization: "Bearer " + localStorage.getItem("lp.token") } })).json()).items.find((a) => a.overdue).id);
  await p.goto(`/alerts/${overdueId}`);
  await p.waitForTimeout(1200);
  out.overdueFlag = await p.evaluate(`(() => { const r = ${RATIO}; const f = document.querySelector(".detail-head .flag-overdue"); return f ? { color: getComputedStyle(f).color, onPaper: r(getComputedStyle(f).color, "rgb(238,241,236)") } : null; })()`);
  await p.locator(".detail-head").screenshot({ path: `${OUT}/p1-detail-head.png` });
  await ctx.close();

  // A5: Records import picker focus
  ctx = await browser.newContext({ baseURL: BASE, viewport: { width: 1440, height: 900 } });
  p = await login(ctx, "demo.admin");
  await p.goto("/records");
  await p.waitForTimeout(800);
  const n = await tabUntil(p, () => document.activeElement && document.activeElement.type === "file");
  out.importFocus = await p.evaluate(() => { const l = document.activeElement.closest("label"); const cs = getComputedStyle(l); return { tabs: null, labelOutline: `${cs.outlineWidth} ${cs.outlineStyle} ${cs.outlineColor}` }; });
  out.importFocus.tabs = n;
  await p.locator(".page-head").screenshot({ path: `${OUT}/p1-records-import-focus.png` });
  await ctx.close();

  // A5 field photo picker, A18 field header, A7 offline badge
  ctx = await browser.newContext({ baseURL: BASE, viewport: { width: 412, height: 915 }, hasTouch: true, isMobile: true });
  p = await login(ctx, "demo.field2");
  await p.waitForSelector('[data-testid^="field-alert-"]', { timeout: 20000 });
  out.fieldRootClass = await p.getByTestId("field-app").getAttribute("class");
  await p.evaluate(() => { const b = document.body; b.setAttribute("tabindex", "-1"); b.focus(); b.removeAttribute("tabindex"); });
  await p.keyboard.press("Tab");
  out.fieldHeadFocus = await p.evaluate(`(() => { const r = ${RATIO}; const el = document.activeElement; const cs = getComputedStyle(el); return { el: el.textContent.trim(), outlineColor: cs.outlineColor, vsHeader: r(cs.outlineColor, "rgb(28,43,51)") }; })()`);
  await p.locator(".f-head").screenshot({ path: `${OUT}/p1-field-head-focus.png` });
  await p.locator('[data-testid^="field-alert-"]').first().click();
  await p.waitForTimeout(1200);
  const m = await tabUntil(p, () => document.activeElement && document.activeElement.getAttribute("data-testid") === "photo-input");
  out.photoFocus = await p.evaluate(() => { const cs = getComputedStyle(document.querySelector(".f-photo")); return { labelOutline: `${cs.outlineWidth} ${cs.outlineStyle} ${cs.outlineColor}` }; });
  out.photoFocus.tabs = m;
  await p.locator(".f-photo").scrollIntoViewIfNeeded();
  await p.locator(".f-capture").screenshot({ path: `${OUT}/p1-field-photo-focus.png` });
  out.fieldBorders = await p.evaluate(`(() => { const r = ${RATIO}; return [".f-field select", ".f-field textarea", ".f-outcome label"].map((s) => { const e = document.querySelector(s); const c = getComputedStyle(e).borderTopColor; return { s, c, vsWhite: r(c, "rgb(255,255,255)") }; }); })()`);
  await p.goto("/field");
  await p.waitForTimeout(800);
  await ctx.setOffline(true);
  await p.waitForTimeout(1000);
  out.offlineBadge = await p.evaluate(`(() => { const r = ${RATIO}; const b = document.querySelector("[data-testid=net-status]"); const cs = getComputedStyle(b); return { text: b.textContent, bg: cs.backgroundColor, ratio: r(cs.color, cs.backgroundColor) }; })()`);
  await p.locator(".f-head").screenshot({ path: `${OUT}/p1-field-offline.png` });
  await ctx.setOffline(false);
  await ctx.close();

  // A14: demo band in print (browser print of desk pages)
  ctx = await browser.newContext({ baseURL: BASE, viewport: { width: 1440, height: 900 } });
  p = await login(ctx, "demo.senior");
  await p.goto("/monthly");
  await p.waitForTimeout(1200);
  await p.emulateMedia({ media: "print" });
  out.printBand = await p.evaluate(() => { const b = document.querySelector("[data-testid=demo-badge]"); const cs = getComputedStyle(b); return { display: cs.display, border: `${cs.borderTopWidth} ${cs.borderTopStyle} ${cs.borderTopColor}`, color: cs.color, text: b.innerText }; });
  await p.pdf({ path: `${OUT}/p1-monthly-print.pdf`, format: "A4", printBackground: false });
  await p.emulateMedia({ media: "screen" });
  await p.goto("/alerts");
  await p.waitForTimeout(1200);
  await p.pdf({ path: `${OUT}/p1-queue-print.pdf`, format: "A4", printBackground: false });
  await ctx.close();

  await browser.close();
  fs.writeFileSync(`${OUT}/p1-results.json`, JSON.stringify(out, null, 1));
  console.log(JSON.stringify(out, null, 1));
})().catch((e) => { console.error(e); process.exit(1); });
