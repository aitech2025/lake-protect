"use strict";
// Phases 2-4 browser QA and the phase 4 review set. Runs against the isolated lpaudit stack.
// Read-only except the final step, which submits one action to check where focus lands.
const { chromium } = require("/e2e/node_modules/playwright");
const fs = require("fs");
const BASE = "http://localhost";
const OUT = "/audit/out";
fs.mkdirSync(OUT, { recursive: true });
const out = { review: {}, focus: {}, shell: {}, states: {} };
const WIDTHS = [[1440, 900], [1280, 720], [1024, 768], [768, 1024], [390, 844]];

const FOCUS = () => {
  const el = document.activeElement;
  if (!el || el === document.body) return "body";
  const tid = el.getAttribute("data-testid");
  return `${el.tagName.toLowerCase()}${el.id ? "#" + el.id : ""}${tid ? `[${tid}]` : ""} "${(el.innerText || el.getAttribute("aria-label") || "").trim().replace(/\s+/g, " ").slice(0, 40)}"`;
};
const LAYOUT = () => {
  const vh = innerHeight;
  const main = document.querySelector(".main");
  const dec = document.querySelector(".detail-decision");
  const r = dec && dec.getBoundingClientRect();
  const head = document.querySelector(".detail-head h1");
  return {
    mainOverflowX: main ? main.scrollWidth - main.clientWidth : null,
    decisionTop: r ? Math.round(r.top) : null,
    decisionInFirstScreen: r ? r.top < vh : null,
    firstActionBottom: (() => { const b = document.querySelector('[data-testid="actions"] .btn'); return b ? Math.round(b.getBoundingClientRect().bottom) : null; })(),
    h1Lines: head ? Math.round(head.getBoundingClientRect().height / parseFloat(getComputedStyle(head).lineHeight)) : null,
    actionOrder: [...document.querySelectorAll('[data-testid="actions"] [data-testid^="action-"]')].map((b) => b.getAttribute("data-testid").replace("action-", "")),
    headings: [...document.querySelectorAll("main h1, main h2, main h3")].map((h) => h.tagName),
    bracketEscape: (() => {
      const s = document.querySelector("[data-testid=dated-bracket]");
      if (!s) return null;
      const box = s.closest(".panel").getBoundingClientRect();
      return Math.max(0, ...[...s.querySelectorAll(".mark, .bracket-window span")].map((m) => { const b = m.getBoundingClientRect(); return Math.round(Math.max(b.right - box.right, box.left - b.left)); }));
    })(),
    title: document.title,
  };
};

(async () => {
  const browser = await chromium.launch({ args: [`--unsafely-treat-insecure-origin-as-secure=${BASE}`] });
  const signIn = async (ctx, user) => {
    const p = await ctx.newPage();
    await p.goto("/login");
    await p.getByTestId(`login-${user}`).click();
    await p.waitForURL((u) => !u.pathname.endsWith("/login"));
    await p.waitForLoadState("networkidle").catch(() => {});
    return p;
  };
  const alertsOf = (p) => p.evaluate(async () => (await (await fetch("/api/alerts", { headers: { Authorization: "Bearer " + localStorage.getItem("lp.token") } })).json()).items.map((a) => ({ id: a.id, name: a.asset_name, state: a.state })));
  const settle = async (p, ms = 1200) => { await p.waitForLoadState("networkidle").catch(() => {}); await p.waitForTimeout(ms); };

  // ---- Review set: alert detail per role, width and language
  const roles = [
    ["analyst", "demo.analyst", (as) => as.find((a) => a.name === "Demo Cheruvu 1")],
    ["nodal", "demo.nodal", (as) => as.find((a) => a.state === "CONFIRMED")],
    ["legal", "demo.legal", (as) => as.find((a) => a.state === "WITH_OFFICER")],
  ];
  for (const [role, user, pick] of roles) {
    const ctx = await browser.newContext({ baseURL: BASE, viewport: { width: 1440, height: 900 } });
    const p = await signIn(ctx, user);
    const target = pick(await alertsOf(p));
    for (const lang of ["en", "te"]) {
      await p.evaluate((l) => localStorage.setItem("lp.lang", l), lang);
      for (const [w, h] of WIDTHS) {
        await p.setViewportSize({ width: w, height: h });
        await p.goto(`/alerts/${target.id}`);
        await settle(p);
        const key = `${role}-${lang}-${w}x${h}`;
        await p.screenshot({ path: `${OUT}/review-${key}.png` });
        out.review[key] = await p.evaluate(LAYOUT);
        if (lang === "en" && (w === 1440 || w === 390)) {
          await p.addStyleTag({ content: "html,body,#root{height:auto!important}.shell{height:auto!important}.main{overflow:visible!important}" });
          await p.waitForTimeout(300);
          await p.screenshot({ path: `${OUT}/review-${key}-full.png`, fullPage: true });
        }
      }
    }
    await p.evaluate(() => localStorage.setItem("lp.lang", "en"));
    await ctx.close();
  }

  // ---- Shell: skip link, route focus, titles, narrow account controls
  {
    const ctx = await browser.newContext({ baseURL: BASE, viewport: { width: 1440, height: 900 } });
    const p = await signIn(ctx, "demo.analyst");
    await p.goto("/alerts");
    await settle(p);
    out.shell.queueTitle = await p.title();
    await p.evaluate(() => { const b = document.body; b.setAttribute("tabindex", "-1"); b.focus(); b.removeAttribute("tabindex"); });
    await p.keyboard.press("Tab");
    out.shell.firstTab = await p.evaluate(FOCUS);
    await p.screenshot({ path: `${OUT}/shell-skip-link.png`, clip: { x: 0, y: 0, width: 600, height: 120 } });
    await p.keyboard.press("Enter");
    out.shell.afterSkip = await p.evaluate(FOCUS);
    await p.keyboard.press("Tab");
    out.shell.tabAfterSkip = await p.evaluate(FOCUS);
    await p.locator('[data-testid^="alert-row-"]').first().click();
    await settle(p);
    out.shell.afterRouteChange = await p.evaluate(FOCUS);
    out.shell.detailTitle = await p.title();
    await p.setViewportSize({ width: 390, height: 844 });
    await p.goto("/alerts");
    await settle(p);
    out.shell.narrowAccount = await p.evaluate(() => [...document.querySelectorAll(".rail .who button")].map((b) => { const r = b.getBoundingClientRect(); return { text: b.innerText, visible: r.width > 0 && getComputedStyle(b).visibility !== "hidden", h: Math.round(r.height) }; }));
    await p.screenshot({ path: `${OUT}/shell-narrow.png`, clip: { x: 0, y: 0, width: 390, height: 260 } });
    await p.setViewportSize({ width: 320, height: 700 });
    await p.goto("/alerts");
    await settle(p);
    out.shell.at320 = await p.evaluate(() => ({ docOverflow: document.documentElement.scrollWidth - innerWidth, mainOverflow: (() => { const m = document.querySelector(".main"); return m.scrollWidth - m.clientWidth; })(), signOutVisible: [...document.querySelectorAll(".rail .who button")].every((b) => b.getBoundingClientRect().width > 0) }));
    await ctx.close();
  }

  // ---- States (browser-side interception only)
  {
    const ctx = await browser.newContext({ baseURL: BASE, viewport: { width: 1440, height: 900 } });
    const p = await signIn(ctx, "demo.analyst");
    const head = (await alertsOf(p)).find((a) => a.name === "Demo Cheruvu 1");
    const slow = (ms) => async (r) => { await new Promise((res) => setTimeout(res, ms)); await r.continue().catch(() => {}); };
    const fail = async (r) => r.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ detail: "Simulated server error (audit)" }) });
    const grab = () => p.evaluate(() => [...document.querySelectorAll("[data-state-kind], .evidence-note")].map((e) => `${e.getAttribute("data-state-kind") || "evidence"}: ${e.innerText.trim().replace(/\s+/g, " ").slice(0, 70)}`));

    await p.route("**/api/alerts", slow(5000));
    await p.goto("/alerts", { waitUntil: "domcontentloaded" });
    await p.waitForTimeout(1500);
    out.states.queueLoading = { shown: await grab(), count: await p.locator(".page-head .muted").innerText() };
    await p.screenshot({ path: `${OUT}/state-queue-loading.png` });
    await p.unroute("**/api/alerts");
    await p.route("**/api/alerts", fail);
    await p.goto("/alerts");
    await settle(p, 600);
    out.states.queueError = await grab();
    await p.unroute("**/api/alerts");
    await p.route("**/chips/**", slow(5000));
    await p.goto(`/alerts/${head.id}`, { waitUntil: "domcontentloaded" });
    await p.waitForTimeout(1800);
    out.states.imageLoading = { shown: await grab(), heights: await p.evaluate(() => [...document.querySelectorAll(".pair figure")].map((f) => Math.round(f.getBoundingClientRect().height))) };
    await p.waitForTimeout(5000);
    out.states.imageLoaded = await p.evaluate(() => [...document.querySelectorAll(".pair figure")].map((f) => Math.round(f.getBoundingClientRect().height)));
    await p.unroute("**/chips/**");
    await p.route("**/chips/**", (r) => r.fulfill({ status: 404, body: "" }));
    await p.goto(`/alerts/${head.id}`);
    await settle(p);
    out.states.imageFailed = { shown: await grab(), heights: await p.evaluate(() => [...document.querySelectorAll(".pair figure")].map((f) => Math.round(f.getBoundingClientRect().height))) };
    await p.screenshot({ path: `${OUT}/state-images-failed.png` });
    await p.unroute("**/chips/**");
    await p.goto("/alerts/999999");
    await settle(p, 600);
    out.states.detail404 = await grab();
    await p.goto("/audit");
    await settle(p, 800);
    out.states.audit403 = { shown: await grab(), verifyButton: await p.getByTestId("verify-log").count() };
    await p.screenshot({ path: `${OUT}/state-audit-403.png` });
    const admin = await browser.newContext({ baseURL: BASE, viewport: { width: 1440, height: 900 } });
    const pa = await signIn(admin, "demo.admin");
    await pa.route("**/api/assets", fail);
    await pa.goto("/assets");
    await settle(pa, 800);
    out.states.assetsError = { shown: await pa.evaluate(() => [...document.querySelectorAll("[data-state-kind]")].map((e) => e.innerText.trim().slice(0, 60))), count: await pa.locator(".page-head .muted").innerText() };
    await pa.screenshot({ path: `${OUT}/state-assets-error.png` });
    await pa.unroute("**/api/assets");
    await pa.setViewportSize({ width: 390, height: 844 });
    await pa.goto("/records");
    await settle(pa, 800);
    out.states.recordsPhone = await pa.evaluate(() => { const m = document.querySelector(".main"); const r = document.querySelector(".table-scroll"); return { mainOverflow: m.scrollWidth - m.clientWidth, regionScrolls: r ? r.scrollWidth > r.clientWidth : null, regionLabel: r && r.getAttribute("aria-label") }; });
    await pa.screenshot({ path: `${OUT}/state-records-phone.png` });
    await admin.close();

    // ---- Focus in the decision panel (keyboard)
    await p.goto(`/alerts/${head.id}`);
    await settle(p);
    out.focus.order = await p.evaluate(() => [...document.querySelectorAll('[data-testid="actions"] .btn')].map((b) => b.innerText.trim()));
    const confirm = p.getByTestId("action-CONFIRMED");
    await confirm.focus();
    await p.keyboard.press("Enter");
    await p.waitForTimeout(200);
    out.focus.afterOpen = await p.evaluate(FOCUS);
    await p.keyboard.press("Tab");
    out.focus.nextTab = await p.evaluate(FOCUS);
    await p.screenshot({ path: `${OUT}/focus-form-open.png`, clip: { x: 1000, y: 140, width: 440, height: 420 } });
    await p.locator('[data-testid="form-CONFIRMED"] button.btn.secondary').focus();
    await p.keyboard.press("Enter");
    await p.waitForTimeout(200);
    out.focus.afterCancel = await p.evaluate(FOCUS);
    // Submit (mutates the isolated demo): where does focus go once the action is done?
    await confirm.focus();
    await p.keyboard.press("Enter");
    await p.getByTestId("input-reviewed").check();
    await p.getByTestId("submit-action").focus();
    await p.keyboard.press("Enter");
    await p.waitForTimeout(1500);
    out.focus.afterSubmit = await p.evaluate(FOCUS);
    await p.screenshot({ path: `${OUT}/focus-after-submit.png`, clip: { x: 1000, y: 140, width: 440, height: 420 } });
    await ctx.close();
  }

  await browser.close();
  fs.writeFileSync(`${OUT}/p4-results.json`, JSON.stringify(out, null, 1));
  const { review, ...rest } = out;
  console.log(JSON.stringify(rest, null, 1));
  console.log("REVIEW (key: overflowX, decisionTop/inFirstScreen, firstActionBottom, h1Lines, bracketEscape, order)");
  for (const [k, v] of Object.entries(review)) console.log(k.padEnd(22), v.mainOverflowX, `${v.decisionTop}/${v.decisionInFirstScreen}`, v.firstActionBottom, v.h1Lines, v.bracketEscape, v.actionOrder.join(">"));
  console.log("headings (analyst-en-1440):", review["analyst-en-1440x900"].headings.join(" "), "| title:", review["analyst-en-1440x900"].title);
})().catch((e) => { console.error(e); process.exit(1); });
