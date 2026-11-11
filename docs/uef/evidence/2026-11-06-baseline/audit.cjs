"use strict";
// UEF UI audit: read-only browser evidence against the isolated `lpaudit` stack.
// Runs inside the project's e2e image, sharing the web container's network (http://localhost).
const { chromium } = require("/e2e/node_modules/playwright");
const fs = require("fs");
const path = require("path");

const OUT = "/audit/out";
fs.mkdirSync(OUT, { recursive: true });
const BASE = "http://localhost";
const VP = {
  desk: { width: 1440, height: 900 },
  laptop: { width: 1024, height: 768 },
  tablet: { width: 768, height: 1024 },
  phone: { width: 390, height: 844 },
  zoom200: { width: 720, height: 450 },
  field: { width: 412, height: 915 },
  small: { width: 360, height: 740 },
};
const R = { pages: {}, tabs: {}, checks: {}, console: [], external: [], errors: [], ids: {} };
let step = "init";
let browser;

const FULL_CSS = "html,body,#root{height:auto!important}.shell{height:auto!important}.main{overflow:visible!important}";

async function newCtx(viewport = VP.desk, opts = {}) {
  const ctx = await browser.newContext({ baseURL: BASE, viewport, ...opts });
  ctx.on("request", (r) => {
    const u = r.url();
    if (!u.startsWith(BASE) && !u.startsWith("data:") && !u.startsWith("blob:")) R.external.push({ step, u });
  });
  return ctx;
}
async function newPage(ctx) {
  const p = await ctx.newPage();
  p.on("console", (m) => { if (m.type() === "error") R.console.push({ step, text: m.text().slice(0, 300) }); });
  p.on("pageerror", (e) => R.console.push({ step, text: "pageerror: " + e.message.slice(0, 300) }));
  return p;
}
async function settle(page, extra = 700) {
  try { await page.waitForLoadState("networkidle", { timeout: 8000 }); } catch { /* maps keep polling */ }
  await page.waitForTimeout(extra);
}
async function login(page, user) {
  await page.goto("/login");
  await page.getByTestId(`login-${user}`).click();
  await page.waitForURL((u) => !u.pathname.endsWith("/login"), { timeout: 15000 });
  await settle(page);
}
async function go(page, url, extra) {
  await page.goto(url);
  await settle(page, extra);
}
async function shot(page, name, full = false) {
  const file = path.join(OUT, name + ".png");
  if (full) {
    const h = await page.addStyleTag({ content: FULL_CSS });
    await page.waitForTimeout(250);
    await page.screenshot({ path: file, fullPage: true });
    await h.evaluate((n) => n.remove());
    await page.waitForTimeout(100);
  } else {
    await page.screenshot({ path: file });
  }
}

// ---------------------------------------------------------------- in-page measurement
const MEASURE = () => {
  const vw = document.documentElement.clientWidth;
  const desc = (el) => {
    if (!el || !el.tagName) return String(el);
    let s = el.tagName.toLowerCase();
    const tid = el.getAttribute("data-testid");
    if (tid) s += `[${tid}]`;
    if (typeof el.className === "string" && el.className.trim()) s += "." + el.className.trim().split(/\s+/).slice(0, 3).join(".");
    return s;
  };
  const visible = (el) => {
    const r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) return false;
    const cs = getComputedStyle(el);
    return cs.visibility !== "hidden" && cs.display !== "none";
  };
  const parse = (c) => {
    const m = c && c.match(/rgba?\(([^)]+)\)/);
    if (!m) return null;
    const p = m[1].split(/[\s,/]+/).filter(Boolean).map(Number);
    return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 };
  };
  const lum = ({ r, g, b }) => {
    const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
  };
  const ratio = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
  const blend = (fg, bg) => ({ r: fg.r * fg.a + bg.r * (1 - fg.a), g: fg.g * fg.a + bg.g * (1 - fg.a), b: fg.b * fg.a + bg.b * (1 - fg.a), a: 1 });
  const hex = (c) => "#" + [c.r, c.g, c.b].map((v) => Math.round(v).toString(16).padStart(2, "0")).join("");
  const bgOf = (el) => {
    const layers = [];
    let image = false;
    for (let e = el; e && e.nodeType === 1; e = e.parentElement) {
      const cs = getComputedStyle(e);
      if (cs.backgroundImage && cs.backgroundImage !== "none") image = true;
      const c = parse(cs.backgroundColor);
      if (c && c.a > 0) { layers.push(c); if (c.a >= 1) break; }
    }
    let bg = { r: 255, g: 255, b: 255, a: 1 };
    for (let i = layers.length - 1; i >= 0; i--) bg = blend(layers[i], bg);
    return { bg, image };
  };

  // Overflow
  const main = document.querySelector(".main");
  const overflow = { doc: document.documentElement.scrollWidth - vw, main: main ? main.scrollWidth - main.clientWidth : null, offenders: [] };
  for (const el of document.querySelectorAll("body *")) {
    if (!visible(el) || el.closest(".maplibregl-map")) continue;
    const r = el.getBoundingClientRect();
    if (r.right > vw + 1 || r.left < -1) {
      const p = el.parentElement;
      const pr = p && p.getBoundingClientRect();
      if (!pr || (pr.right <= vw + 1 && pr.left >= -1)) overflow.offenders.push({ el: desc(el), left: Math.round(r.left), right: Math.round(r.right), text: (el.innerText || "").trim().slice(0, 40) });
    }
  }
  overflow.offenders = overflow.offenders.slice(0, 12);

  const headings = [...document.querySelectorAll("h1,h2,h3,h4,h5,h6")].filter(visible).map((h) => h.tagName[1] + " " + (h.innerText || "").trim().replace(/\s+/g, " ").slice(0, 50));
  const landmarks = {};
  for (const sel of ["main", "nav", "header", "footer", "aside", "[role=main]", "[role=navigation]", "[role=banner]", "[role=status]", "[role=alert]"]) landmarks[sel] = document.querySelectorAll(sel).length;

  const nameOf = (el) => {
    const al = el.getAttribute("aria-label");
    if (al && al.trim()) return al.trim();
    const lb = el.getAttribute("aria-labelledby");
    if (lb) { const t = lb.split(/\s+/).map((id) => (document.getElementById(id) || {}).innerText || "").join(" ").trim(); if (t) return t; }
    if (el.labels && el.labels.length) { const t = [...el.labels].map((l) => l.innerText).join(" ").trim(); if (t) return t; }
    if (!["INPUT", "SELECT", "TEXTAREA"].includes(el.tagName)) { const tx = (el.innerText || "").trim(); if (tx) return tx; }
    const img = el.querySelector && el.querySelector("img[alt]");
    if (img && img.alt.trim()) return img.alt.trim();
    if (el.title && el.title.trim()) return "title-only:" + el.title.trim();
    if (el.placeholder) return "placeholder-only:" + el.placeholder;
    return "";
  };
  const controls = [...document.querySelectorAll("button, a[href], input:not([type=hidden]), select, textarea, [role=button], [tabindex]:not([tabindex='-1'])")];
  const unnamed = controls.map((el) => ({ el: desc(el), name: nameOf(el), visible: visible(el) })).filter((x) => !x.name || /^(placeholder|title)-only/.test(x.name));

  const images = {
    imgNoAlt: [...document.querySelectorAll("img")].filter((i) => !i.hasAttribute("alt")).map(desc),
    ariaLabelWithoutRole: [...document.querySelectorAll("div[aria-label], span[aria-label]")].filter((e) => !e.getAttribute("role")).map((e) => desc(e) + " label=" + e.getAttribute("aria-label").slice(0, 30)),
    svgUnlabelled: [...document.querySelectorAll("svg")].filter((s) => s.getAttribute("aria-hidden") !== "true" && !s.closest("[aria-hidden=true]") && !s.getAttribute("role") && !s.querySelector("title") && !s.getAttribute("aria-label")).map((s) => desc(s.parentElement) + ">svg"),
  };

  // Text contrast (approximation of WCAG 1.4.3; background images flagged for manual check)
  const fails = new Map();
  const manual = new Map();
  let checked = 0;
  const tw = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (tw.nextNode()) {
    const n = tw.currentNode;
    const txt = n.nodeValue.trim();
    if (!txt) continue;
    const el = n.parentElement;
    if (!el || !visible(el)) continue;
    if (el.closest("svg, script, style, option, .sr-only")) continue;
    if (el.closest("button:disabled, [disabled]")) continue;
    const cs = getComputedStyle(el);
    let fg = parse(cs.color);
    if (!fg) continue;
    let op = 1;
    for (let e = el; e && e.nodeType === 1; e = e.parentElement) op *= parseFloat(getComputedStyle(e).opacity);
    if (op === 0) continue;
    const { bg, image } = bgOf(el);
    const f = blend({ ...fg, a: fg.a * op }, bg);
    const r = ratio(f, bg);
    const size = parseFloat(cs.fontSize);
    const w = parseInt(cs.fontWeight, 10);
    const large = size >= 24 || (size >= 18.66 && w >= 700);
    const need = large ? 3 : 4.5;
    checked++;
    if (image) {
      const k = cs.color + desc(el);
      if (!manual.has(k)) manual.set(k, { fg: hex(f), el: desc(el), sample: txt.slice(0, 40) });
    } else if (r < need) {
      const k = `${hex(f)}|${hex(bg)}|${size}|${w}`;
      if (!fails.has(k)) fails.set(k, { ratio: +r.toFixed(2), need, fg: hex(f), bg: hex(bg), size, weight: w, sample: txt.slice(0, 40), el: desc(el), count: 0 });
      fails.get(k).count++;
    }
  }

  // Non-text contrast of control boundaries (WCAG 1.4.11): border vs outside, or fill vs outside
  const ntc = new Map();
  for (const el of document.querySelectorAll("input:not([type=hidden]):not([type=checkbox]):not([type=radio]):not([type=file]), select, textarea, .chip, .btn.secondary, .f-sync button, .rail .who button, .f-head button, .f-outcome label")) {
    if (!visible(el)) continue;
    const cs = getComputedStyle(el);
    const bc = parse(cs.borderTopColor);
    const bw = parseFloat(cs.borderTopWidth);
    const outer = bgOf(el.parentElement).bg;
    const inner = bgOf(el).bg;
    const border = bc && bw > 0 ? ratio(blend(bc, outer), outer) : 0;
    const fill = ratio(inner, outer);
    const best = Math.max(border, fill);
    const k = desc(el).replace(/\[[^\]]*\]/g, "") + "|" + (bc ? hex(bc) : "none");
    if (!ntc.has(k)) ntc.set(k, { el: desc(el), border: bc ? hex(bc) : "none", borderWidth: bw, outside: hex(outer), borderRatio: +border.toFixed(2), fillRatio: +fill.toFixed(2), pass: best >= 3, count: 0 });
    ntc.get(k).count++;
  }

  // Target sizes (WCAG 2.5.8 minimum 24x24; 44x44 recommended for field use)
  const small = [];
  let under44 = 0;
  let targets = 0;
  for (const el of document.querySelectorAll("button, a[href], input:not([type=hidden]), select, textarea, [role=button], .chip")) {
    if (!visible(el)) continue;
    const cs = getComputedStyle(el);
    if (el.type === "file" && cs.opacity === "0") continue;
    if (el.classList.contains("sr-only")) continue;
    const r = el.getBoundingClientRect();
    targets++;
    const inlineLink = el.tagName === "A" && cs.display === "inline";
    if ((r.width < 24 || r.height < 24) && !inlineLink) small.push({ el: desc(el), w: Math.round(r.width), h: Math.round(r.height), text: (el.innerText || el.getAttribute("aria-label") || el.value || "").trim().slice(0, 30) });
    else if (r.width < 44 || r.height < 44) under44++;
  }

  const railButtons = [...document.querySelectorAll(".rail button, .rail a")].map((b) => ({ text: (b.innerText || "").trim().slice(0, 30), visible: visible(b) }));
  return {
    lang: document.documentElement.lang,
    title: document.title,
    overflow,
    headings,
    landmarks,
    unnamed,
    images,
    contrast: { checked, fails: [...fails.values()].sort((a, b) => a.ratio - b.ratio), manual: [...manual.values()].slice(0, 6) },
    nonText: [...ntc.values()],
    targets: { total: targets, under24: small.slice(0, 25), under24Count: small.length, under44 },
    railButtons,
    demoBand: Boolean(document.querySelector("[data-testid=demo-badge]")),
  };
};

async function measure(page, key, extra = {}) {
  step = "measure " + key;
  try {
    const m = await page.evaluate(MEASURE);
    R.pages[key] = { url: page.url().replace(BASE, ""), viewport: page.viewportSize(), ...m, ...extra };
  } catch (e) {
    R.errors.push({ step, e: String(e).slice(0, 300) });
  }
}
async function capture(page, key, full = false, extra) {
  step = "shot " + key;
  try { await shot(page, key, full); } catch (e) { R.errors.push({ step, e: String(e).slice(0, 300) }); }
  await measure(page, key, extra);
}

const FOCUS_INFO = () => {
  const el = document.activeElement;
  if (!el || el === document.body) return { el: "body" };
  const r = el.getBoundingClientRect();
  const cs = getComputedStyle(el);
  const tid = el.getAttribute("data-testid");
  let op = 1;
  for (let e = el; e && e.nodeType === 1; e = e.parentElement) op *= parseFloat(getComputedStyle(e).opacity);
  const outline = cs.outlineStyle !== "none" && parseFloat(cs.outlineWidth) > 0 ? `${cs.outlineWidth} ${cs.outlineStyle} ${cs.outlineColor}` : "none";
  const label = (el.getAttribute("aria-label") || (el.labels && el.labels[0] && el.labels[0].innerText) || el.innerText || el.value || "").trim().replace(/\s+/g, " ").slice(0, 40);
  const cls = typeof el.className === "string" && el.className.trim() ? "." + el.className.trim().split(/\s+/).slice(0, 2).join(".") : "";
  const inView = r.bottom > 0 && r.top < innerHeight && r.right > 0 && r.left < innerWidth;
  const hiddenFocus = op === 0 || r.width <= 2 || r.height <= 2 || (outline === "none" && cs.boxShadow === "none") || !inView;
  return { el: el.tagName.toLowerCase() + (tid ? `[${tid}]` : "") + cls, label, w: Math.round(r.width), h: Math.round(r.height), outline, opacity: +op.toFixed(2), inView, hiddenFocus };
};

async function tabWalk(page, key, n = 30) {
  step = "tab " + key;
  try {
    await page.evaluate(() => { const b = document.body; b.setAttribute("tabindex", "-1"); b.focus(); b.removeAttribute("tabindex"); });
    const seq = [];
    for (let i = 0; i < n; i++) {
      await page.keyboard.press("Tab");
      await page.waitForTimeout(40);
      seq.push(await page.evaluate(FOCUS_INFO));
    }
    R.tabs[key] = seq;
  } catch (e) {
    R.errors.push({ step, e: String(e).slice(0, 300) });
  }
}

const delay = (ms) => new Promise((r) => setTimeout(r, ms));
async function routed(page, pattern, handler, fn) {
  await page.route(pattern, handler);
  try { await fn(); } catch (e) { R.errors.push({ step, e: String(e).slice(0, 300) }); }
  await page.unroute(pattern).catch(() => {});
}
const slow = (ms) => async (route) => { await delay(ms); await route.continue().catch(() => {}); };
const fail500 = async (route) => route.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ detail: "Simulated server error (audit)" }) });

async function run(name, fn) {
  step = name;
  try { await fn(); } catch (e) { R.errors.push({ step: name, e: String(e).slice(0, 400) }); }
}

(async () => {
  browser = await chromium.launch({ args: [`--unsafely-treat-insecure-origin-as-secure=${BASE}`] });

  // ------------------------------------------------------------ login (signed out)
  await run("login", async () => {
    const ctx = await newCtx(VP.desk);
    const p = await newPage(ctx);
    await go(p, "/login");
    await capture(p, "login-desk");
    await tabWalk(p, "login-desk", 14);
    R.checks.ariaLogin = await p.locator("body").ariaSnapshot().catch((e) => String(e));
    await p.setViewportSize(VP.phone);
    await go(p, "/login");
    await capture(p, "login-phone", true);
    await p.evaluate(() => localStorage.setItem("lp.lang", "te"));
    await go(p, "/login");
    await capture(p, "login-phone-te", true);
    await ctx.close();
  });

  // ------------------------------------------------------------ analyst: queue, detail, states
  await run("analyst", async () => {
    const ctx = await newCtx(VP.desk);
    const p = await newPage(ctx);
    await login(p, "demo.analyst");
    const alerts = await p.evaluate(async () => {
      const r = await fetch("/api/alerts", { headers: { Authorization: "Bearer " + localStorage.getItem("lp.token") } });
      return (await r.json()).items.map((a) => ({ id: a.id, code: a.code, name: a.asset_name, state: a.state, overdue: a.overdue }));
    });
    R.ids.alerts = alerts;
    const byName = (n) => alerts.find((a) => a.name === n);
    const byState = (s) => alerts.find((a) => a.state === s);
    const headline = byName("Demo Cheruvu 1") || alerts[0];
    R.ids.headline = headline;
    R.ids.withOfficer = byState("WITH_OFFICER") || byState("PACK_READY");
    R.ids.fieldConfirmed = byState("FIELD_CONFIRMED") || byState("PACK_READY");
    R.ids.confirmed = byState("CONFIRMED");
    R.ids.hold = byState("HOLD_LEGAL");

    // Queue at every width
    await go(p, "/alerts", 1200);
    await capture(p, "queue-desk");
    await tabWalk(p, "queue-desk", 30);
    R.checks.ariaQueue = (await p.locator("main").ariaSnapshot().catch((e) => String(e))).slice(0, 6000);
    for (const [vp, full] of [["laptop", false], ["tablet", true], ["phone", true], ["zoom200", false]]) {
      await p.setViewportSize(VP[vp]);
      await go(p, "/alerts", 1200);
      await capture(p, `queue-${vp}`, full);
    }
    await p.setViewportSize(VP.phone);
    await go(p, "/alerts", 800);
    await tabWalk(p, "queue-phone", 12);

    // Detail of the headline alert
    await p.setViewportSize(VP.desk);
    await go(p, `/alerts/${headline.id}`, 1500);
    await capture(p, "detail-desk");
    await shot(p, "detail-desk-full", true);
    await tabWalk(p, "detail-desk", 40);
    R.checks.ariaDetail = (await p.locator("main").ariaSnapshot().catch((e) => String(e))).slice(0, 9000);

    // Focus after opening and cancelling an action form (keyboard)
    step = "focus-action-form";
    const actionBtn = p.locator('[data-testid="actions"] button[data-testid^="action-"]').first();
    if (await actionBtn.count()) {
      const label = (await actionBtn.innerText()).trim();
      await actionBtn.focus();
      await p.keyboard.press("Enter");
      await p.waitForTimeout(300);
      const afterOpen = await p.evaluate(FOCUS_INFO);
      await p.keyboard.press("Tab");
      const afterTab = await p.evaluate(FOCUS_INFO);
      await shot(p, "detail-action-form-open");
      const cancel = p.locator('[data-testid^="form-"] button.btn.secondary').first();
      await cancel.focus();
      await p.keyboard.press("Enter");
      await p.waitForTimeout(300);
      const afterCancel = await p.evaluate(FOCUS_INFO);
      R.checks.actionFocus = { label, afterOpen, afterTabFromThere: afterTab, afterCancel };
    }

    for (const [vp, full] of [["laptop", true], ["tablet", true], ["phone", true], ["zoom200", false]]) {
      await p.setViewportSize(VP[vp]);
      await go(p, `/alerts/${headline.id}`, 1500);
      await capture(p, `detail-${vp}`, full);
    }
    await p.setViewportSize(VP.phone);
    await go(p, `/alerts/${headline.id}`, 1200);
    await capture(p, "detail-phone-top");

    // Telugu
    await p.setViewportSize(VP.desk);
    await p.evaluate(() => localStorage.setItem("lp.lang", "te"));
    await go(p, "/alerts", 1200);
    await capture(p, "queue-desk-te");
    await go(p, `/alerts/${headline.id}`, 1500);
    await capture(p, "detail-desk-te", true);
    await p.setViewportSize(VP.phone);
    await go(p, `/alerts/${headline.id}`, 1500);
    await capture(p, "detail-phone-te", true);
    await p.evaluate(() => localStorage.setItem("lp.lang", "en"));

    // States, by browser-side interception only
    await p.setViewportSize(VP.desk);
    step = "queue-loading";
    await routed(p, "**/api/alerts", slow(6000), async () => {
      await p.goto("/alerts", { waitUntil: "domcontentloaded" });
      await p.waitForTimeout(1500);
      await capture(p, "state-queue-loading");
    });
    step = "queue-error";
    await routed(p, "**/api/alerts", fail500, async () => { await go(p, "/alerts", 800); await capture(p, "state-queue-error"); });
    step = "queue-empty";
    await routed(p, "**/api/alerts", (r) => r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ items: [], has_demo: false }) }), async () => {
      await go(p, "/alerts", 800);
      await capture(p, "state-queue-empty");
    });
    step = "queue-long";
    const longify = async (route) => {
      const resp = await route.fetch();
      const j = await resp.json();
      if (j.items && j.items[0]) {
        j.items[0].asset_name = "Demo Cheruvu with a deliberately long name to test wrapping in the list and on the map";
        j.items[0].owner_name = "Demo Field Officer with an unusually long full name";
      }
      await route.fulfill({ response: resp, json: j });
    };
    await routed(p, "**/api/alerts", longify, async () => {
      await go(p, "/alerts", 1200);
      await capture(p, "state-queue-long-desk");
      await p.setViewportSize(VP.phone);
      await go(p, "/alerts", 1200);
      await capture(p, "state-queue-long-phone", true);
      await p.setViewportSize(VP.desk);
    });
    step = "detail-loading";
    await routed(p, `**/api/alerts/${headline.id}`, slow(6000), async () => {
      await p.goto(`/alerts/${headline.id}`, { waitUntil: "domcontentloaded" });
      await p.waitForTimeout(1500);
      await capture(p, "state-detail-loading");
    });
    step = "detail-error";
    await routed(p, `**/api/alerts/${headline.id}`, fail500, async () => { await go(p, `/alerts/${headline.id}`, 800); await capture(p, "state-detail-error"); });
    step = "detail-404";
    await go(p, "/alerts/999999", 800);
    await capture(p, "state-detail-404");
    step = "detail-chips-slow";
    await routed(p, "**/chips/**", slow(5000), async () => {
      await p.goto(`/alerts/${headline.id}`, { waitUntil: "domcontentloaded" });
      await p.waitForTimeout(1800);
      const before = await p.evaluate(() => [...document.querySelectorAll(".pair figure")].map((f) => Math.round(f.getBoundingClientRect().height)));
      await shot(p, "state-detail-images-loading");
      await p.waitForTimeout(5000);
      const after = await p.evaluate(() => [...document.querySelectorAll(".pair figure")].map((f) => Math.round(f.getBoundingClientRect().height)));
      R.checks.imagePairHeights = { whileLoading: before, afterLoad: after };
    });
    step = "detail-chips-fail";
    await routed(p, "**/chips/**", (r) => r.fulfill({ status: 404, body: "" }), async () => {
      await go(p, `/alerts/${headline.id}`, 1200);
      await shot(p, "state-detail-images-failed");
      R.checks.imagePairFailed = await p.evaluate(() => [...document.querySelectorAll(".pair figure")].map((f) => ({ h: Math.round(f.getBoundingClientRect().height), text: f.innerText.trim().slice(0, 60) })));
    });
    step = "analyst-forbidden";
    await go(p, "/audit", 1000);
    await capture(p, "role-analyst-on-audit");
    await ctx.close();
  });

  // ------------------------------------------------------------ nodal: assign form on a confirmed alert
  await run("nodal", async () => {
    if (!R.ids.confirmed) return;
    const ctx = await newCtx(VP.desk);
    const p = await newPage(ctx);
    await login(p, "demo.nodal");
    await go(p, `/alerts/${R.ids.confirmed.id}`, 1500);
    const assign = p.locator('[data-testid="action-ASSIGNED"]');
    if (await assign.count()) { await assign.click(); await p.waitForTimeout(500); }
    await capture(p, "detail-nodal-assign-form");
    await ctx.close();
  });

  // ------------------------------------------------------------ legal: checklist, case file, officer record
  await run("legal", async () => {
    const ctx = await newCtx(VP.desk);
    const p = await newPage(ctx);
    await login(p, "demo.legal");
    if (R.ids.withOfficer) {
      await go(p, `/alerts/${R.ids.withOfficer.id}`, 1500);
      await capture(p, "detail-legal-officer-record");
      await shot(p, "detail-legal-officer-record-full", true);
      await p.setViewportSize(VP.phone);
      await go(p, `/alerts/${R.ids.withOfficer.id}`, 1500);
      await capture(p, "detail-legal-officer-record-phone", true);
      await p.setViewportSize(VP.desk);
    }
    if (R.ids.fieldConfirmed) {
      await go(p, `/alerts/${R.ids.fieldConfirmed.id}`, 1500);
      await capture(p, "detail-legal-checklist", true);
      await p.setViewportSize(VP.phone);
      await go(p, `/alerts/${R.ids.fieldConfirmed.id}`, 1500);
      await capture(p, "detail-legal-checklist-phone", true);
    }
    await ctx.close();
  });

  // ------------------------------------------------------------ admin: assets, records
  await run("admin", async () => {
    const ctx = await newCtx(VP.desk);
    const p = await newPage(ctx);
    await login(p, "demo.admin");
    await go(p, "/assets", 1500);
    await capture(p, "assets-desk");
    const firstRow = p.locator(".list button.row").first();
    if (await firstRow.count()) { await firstRow.click(); await settle(p, 1200); }
    await capture(p, "assets-desk-selected", true);
    await tabWalk(p, "assets-desk", 16);
    await p.setViewportSize(VP.phone);
    await go(p, "/assets", 1500);
    if (await firstRow.count()) { await firstRow.click(); await settle(p, 1200); }
    await capture(p, "assets-phone-selected", true);
    await p.setViewportSize(VP.desk);
    await go(p, "/records", 1000);
    await capture(p, "records-desk");
    await tabWalk(p, "records-desk", 14);
    await p.setViewportSize(VP.phone);
    await go(p, "/records", 1000);
    await capture(p, "records-phone", true);
    await p.setViewportSize(VP.desk);
    step = "assets-error";
    await routed(p, "**/api/assets", fail500, async () => { await go(p, "/assets", 1000); await capture(p, "state-assets-error"); });
    step = "records-error";
    await routed(p, "**/api/records/**", fail500, async () => { await go(p, "/records", 800); await capture(p, "state-records-error"); });
    await ctx.close();
  });

  // ------------------------------------------------------------ auditor
  await run("auditor", async () => {
    const ctx = await newCtx(VP.desk);
    const p = await newPage(ctx);
    await login(p, "demo.auditor");
    await go(p, "/audit", 1000);
    await capture(p, "audit-desk");
    await p.getByTestId("verify-log").click();
    await p.waitForTimeout(1500);
    await shot(p, "audit-desk-verified");
    await p.setViewportSize(VP.phone);
    await go(p, "/audit", 1000);
    await capture(p, "audit-phone");
    await p.setViewportSize(VP.desk);
    step = "audit-error";
    await routed(p, "**/api/audit?*", fail500, async () => { await go(p, "/audit", 800); await capture(p, "state-audit-error"); });
    await ctx.close();
  });

  // ------------------------------------------------------------ senior officer: monthly
  await run("senior", async () => {
    const ctx = await newCtx(VP.desk);
    const p = await newPage(ctx);
    await login(p, "demo.senior");
    await go(p, "/monthly", 1200);
    await capture(p, "monthly-desk", true);
    await tabWalk(p, "monthly-desk", 16);
    await p.setViewportSize(VP.tablet);
    await go(p, "/monthly", 1200);
    await capture(p, "monthly-tablet", true);
    await p.setViewportSize(VP.phone);
    await go(p, "/monthly", 1200);
    await capture(p, "monthly-phone", true);
    await p.setViewportSize(VP.desk);
    await p.evaluate(() => localStorage.setItem("lp.lang", "te"));
    await go(p, "/monthly", 1200);
    await capture(p, "monthly-desk-te", true);
    await p.evaluate(() => localStorage.setItem("lp.lang", "en"));
    await go(p, "/monthly", 1200);
    await p.emulateMedia({ media: "print" });
    await p.waitForTimeout(300);
    await shot(p, "monthly-print-media", true);
    R.checks.printDemoBand = await p.evaluate(() => { const b = document.querySelector("[data-testid=demo-badge]"); return b ? getComputedStyle(b).display : "absent"; });
    await p.emulateMedia({ media: "screen" });
    step = "monthly-error";
    await routed(p, "**/api/bulletins/**", fail500, async () => { await go(p, "/monthly", 800); await capture(p, "state-monthly-error"); });
    await ctx.close();
  });

  // ------------------------------------------------------------ field app
  await run("field2", async () => {
    const ctx = await newCtx(VP.field, { permissions: ["geolocation"], geolocation: { longitude: 0, latitude: 0, accuracy: 10 }, hasTouch: true, isMobile: true });
    const p = await newPage(ctx);
    await login(p, "demo.field2");
    await p.waitForSelector('[data-testid^="field-alert-"]', { timeout: 20000 }).catch(() => {});
    await settle(p, 800);
    await capture(p, "field-list");
    const link = p.locator('[data-testid^="field-alert-"]').first();
    if (await link.count()) {
      await link.click();
      await settle(p, 1500);
      await capture(p, "field-alert", true);
      await tabWalk(p, "field-alert", 24);
      R.checks.ariaField = (await p.locator("main").ariaSnapshot().catch((e) => String(e))).slice(0, 6000);
      step = "field-validation";
      await p.getByTestId("save-visit").click();
      await p.waitForTimeout(400);
      await shot(p, "field-alert-validation", false);
      R.checks.fieldValidation = await p.evaluate(() => { const m = document.querySelector("[data-testid=save-message]"); const r = m && m.getBoundingClientRect(); return m ? { text: m.innerText, role: m.getAttribute("role"), top: Math.round(r.top), viewportH: innerHeight, focus: document.activeElement && document.activeElement.getAttribute("data-testid") } : null; });
      const url = p.url();
      await p.setViewportSize(VP.small);
      await go(p, url.replace(BASE, ""), 1500);
      await capture(p, "field-alert-small", true);
      await p.evaluate(() => localStorage.setItem("lp.lang", "te"));
      await go(p, url.replace(BASE, ""), 1500);
      await capture(p, "field-alert-small-te", true);
      await go(p, "/field", 1000);
      await capture(p, "field-list-small-te");
      await p.evaluate(() => localStorage.setItem("lp.lang", "en"));
      await p.setViewportSize(VP.field);
      step = "field-offline";
      await go(p, "/field", 1000);
      await ctx.setOffline(true);
      await p.waitForTimeout(1200);
      await capture(p, "field-list-offline");
      await ctx.setOffline(false);
    }
    step = "field-on-desk-route";
    await go(p, "/alerts", 1000);
    await capture(p, "role-field-on-desk");
    await ctx.close();
  });
  await run("field1", async () => {
    const ctx = await newCtx(VP.field, { hasTouch: true, isMobile: true });
    const p = await newPage(ctx);
    await login(p, "demo.field1");
    await settle(p, 2500);
    await capture(p, "field1-list-te");
    await ctx.close();
  });

  await browser.close();
  fs.writeFileSync(path.join(OUT, "results.json"), JSON.stringify(R, null, 1));
  console.log("done", Object.keys(R.pages).length, "pages measured,", R.errors.length, "errors,", R.console.length, "console errors,", R.external.length, "external requests");
})().catch((e) => {
  fs.writeFileSync(path.join(OUT, "results.json"), JSON.stringify({ ...R, fatal: String(e) }, null, 1));
  console.error("fatal", e);
  process.exit(1);
});
