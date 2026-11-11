"use strict";
// Follow-up read-only checks for the UEF audit.
const { chromium } = require("/e2e/node_modules/playwright");
const fs = require("fs");
const BASE = "http://localhost";
const out = {};
(async () => {
  const browser = await chromium.launch({ args: [`--unsafely-treat-insecure-origin-as-secure=${BASE}`] });
  const login = async (ctx, user) => {
    const p = await ctx.newPage();
    await p.goto("/login");
    await p.getByTestId(`login-${user}`).click();
    await p.waitForURL((u) => !u.pathname.endsWith("/login"));
    await p.waitForLoadState("networkidle").catch(() => {});
    return p;
  };

  // 1. White box behind queue filter labels
  let ctx = await browser.newContext({ baseURL: BASE, viewport: { width: 1440, height: 900 } });
  let p = await login(ctx, "demo.analyst");
  await p.goto("/alerts");
  await p.waitForTimeout(1200);
  out.filterLabel = await p.evaluate(() => {
    const l = document.querySelector("label.field");
    const s = l.querySelector("select");
    const cs = getComputedStyle(l);
    return { labelBg: cs.backgroundColor, labelBox: l.getBoundingClientRect().toJSON(), selectBox: s.getBoundingClientRect().toJSON(), selectBg: getComputedStyle(s).backgroundColor, colorScheme: getComputedStyle(document.documentElement).colorScheme };
  });
  await p.locator("label.field").first().screenshot({ path: "/audit/out/x-filter-label.png" });

  // 2. Dated bracket marks escaping their panel (desktop)
  const id = await p.evaluate(async () => (await (await fetch("/api/alerts", { headers: { Authorization: "Bearer " + localStorage.getItem("lp.token") } })).json()).items.find((a) => a.asset_name === "Demo Cheruvu 1").id);
  for (const w of [1440, 1280, 1024]) {
    await p.setViewportSize({ width: w, height: 900 });
    await p.goto(`/alerts/${id}`);
    await p.waitForTimeout(1500);
    out[`bracket${w}`] = await p.evaluate(() => {
      const panel = document.querySelector("[data-testid=dated-bracket]").closest(".panel").getBoundingClientRect();
      return [...document.querySelectorAll(".bracket .mark")].map((m) => { const r = m.getBoundingClientRect(); return { text: m.innerText.replace(/\n/g, " "), left: Math.round(r.left - panel.left), rightOverPanel: Math.round(r.right - panel.right), top: Math.round(r.top) }; });
    });
  }
  await ctx.close();

  // 3. Legal officer detail (editable checklist) at tablet and laptop widths
  ctx = await browser.newContext({ baseURL: BASE, viewport: { width: 1024, height: 900 } });
  p = await login(ctx, "demo.legal");
  const wo = await p.evaluate(async () => (await (await fetch("/api/alerts", { headers: { Authorization: "Bearer " + localStorage.getItem("lp.token") } })).json()).items.find((a) => a.state === "WITH_OFFICER").id);
  for (const w of [1440, 1280, 1100, 1024, 900, 768, 390]) {
    await p.setViewportSize({ width: w, height: 900 });
    await p.goto(`/alerts/${wo}`);
    await p.waitForTimeout(1300);
    out[`legalOverflow${w}`] = await p.evaluate(() => {
      const m = document.querySelector(".main");
      const row = document.querySelector("[data-testid^=check-]");
      return { mainOverflow: m.scrollWidth - m.clientWidth, checklistRowWidth: row ? Math.round(row.getBoundingClientRect().width) : null, asideWidth: Math.round(document.querySelector("aside").getBoundingClientRect().width) };
    });
  }
  await p.setViewportSize({ width: 768, height: 1024 });
  await p.goto(`/alerts/${wo}`);
  await p.waitForTimeout(1500);
  await p.locator("[data-testid=checklist]").scrollIntoViewIfNeeded();
  await p.screenshot({ path: "/audit/out/x-legal-tablet-checklist.png" });
  await ctx.close();

  // 4. Monthly map SVG semantics and pluralisation
  ctx = await browser.newContext({ baseURL: BASE, viewport: { width: 1440, height: 900 } });
  p = await login(ctx, "demo.senior");
  await p.goto("/monthly");
  await p.waitForTimeout(1200);
  out.monthlySvg = await p.evaluate(() => { const s = document.querySelector(".monthly-map svg"); return s ? { role: s.getAttribute("role"), ariaHidden: s.getAttribute("aria-hidden"), ariaLabel: s.getAttribute("aria-label"), title: s.querySelector("title") && s.querySelector("title").textContent, shapes: s.querySelectorAll("*").length } : null; });
  out.monthlyLate = await p.evaluate(() => [...document.querySelectorAll(".overdue-list b")].map((b) => b.innerText));
  await ctx.close();

  // 5. Field app: any sign-out control?
  ctx = await browser.newContext({ baseURL: BASE, viewport: { width: 412, height: 915 } });
  p = await login(ctx, "demo.field2");
  await p.waitForTimeout(1500);
  out.fieldButtons = await p.evaluate(() => [...document.querySelectorAll("button, a")].map((b) => (b.innerText || "").trim()).filter(Boolean));
  await ctx.close();

  await browser.close();
  fs.writeFileSync("/audit/out/results2.json", JSON.stringify(out, null, 1));
  console.log(JSON.stringify(out, null, 1));
})().catch((e) => { console.error(e); process.exit(1); });
