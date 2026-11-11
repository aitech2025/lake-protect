# UEF UI Audit

> First audit of this project; no earlier report existed. Every finding below already existed
> before any UI modernization. Each finding says how it was checked:
> **Browser** = seen in a screenshot or measured in the running app;
> **Code** = read in the source, not exercised; **Assumption** = inferred, not checked.

## Summary

- **Product:** Lake Protect (working name): the desk, the field app (offline phone app) and the monthly page.
- **Date:** 6 Nov 2026
- **Branch / commit:** `main` at `ffc6ae8` (M9). The working tree was clean apart from `docs/uef/`.
- **Environment:** a separate copy of the stack (`docker compose -p lpaudit`, ports 18180, 18100
  and 15544, with its own volumes) seeded with a fresh demo. The owner's `lakeprotect` volumes were
  not touched. The web image was built from the current source. Browser: headless Chromium
  (Playwright 1.65.0) from the project's own e2e image.

**In short:** the product looks consistent and purposeful. The boundary line styles mean the same
thing on the badge, the map and the legend. The demo band appears wherever demo data does. The
wording is plain, the monthly page reads at a glance, and the field app has large controls and
still fits in Telugu at 360 px. Every control has a name and every image has alt text, and no request
leaves the machine. The problems are concentrated in four places:

1. **Loading, error and no-access states look like empty data.** An auditor can see an empty log,
   and an analyst can lose the before and after images without being told.
2. **Below about 770 px**, the desk hides sign-out and the language switch, and some screens scroll sideways.
3. **Keyboard focus** is lost in the decision forms and invisible on two file pickers.
4. **Form control borders** are below the 3:1 contrast that WCAG requires for non-text elements.

None of the fixes needs an API, data or business-rule change.

## Current application

- **Framework and versions:** React 19.3.1, Vite 6.4.5, TypeScript 5.9.3 (strict), react-router-dom 7.18.5. Details in `PROJECT_PROFILE.md`.
- **Styling / component system:** three global CSS files, tokens in `web/src/styles.css` `:root`,
  in-house components (`components/Bits.tsx`), no component library. Vite ships all CSS as **one
  global 98 KB bundle**, so the desk and the field app share one class namespace (see A9).
- **Routing / state / data:** `BrowserRouter`, React context, a `fetch` wrapper and a `useAsync` hook.
  There is no shared loading, error or no-access pattern, so each page does its own (see A1).
  MapLibre draws the maps; IndexedDB holds the field app's offline queue.
- **Test coverage:** 235 API tests, including the section 6.8 wording scan over all web sources.
  14 Playwright browser tests at 1440×900 and 412×915. No web unit tests, no linter, no automated
  accessibility check.

## Method and evidence

- **Screens and widths:** every route was captured at 1440×900, 1024×768, 768×1024 and 390×844,
  plus 720×450 to stand in for 200% zoom on a 1440×900 laptop. The field app was captured at
  412×915 and 360×740. English and Telugu.
- **Roles:** analyst, nodal officer, legal officer, admin, auditor, senior officer, Field Officer 1 (no alerts) and Field Officer 2 (one overdue alert).
- **States** were forced with browser-side request interception only: a slow response, a 500
  error, an empty list, very long names, failed images, and offline. Real 403 and 404 responses were
  also opened. The backend was not changed.
- **Measured on every screen:** horizontal overflow, headings and landmarks, controls without a name,
  image alt text, text contrast (WCAG formula on the rendered colours), control-border contrast,
  target sizes, and keyboard Tab order with focus visibility.
- **Evidence:** [`evidence/2026-11-06-baseline/`](evidence/2026-11-06-baseline/) holds 18 key
  screenshots, `measurements.json`, `measurements-followup.json`, and the two scripts that produced
  them (`audit.cjs`, `audit2.cjs`), which can be re-run after changes. Screenshot names are cited in
  the tables below as `screenshot.png`.
- **Limits:** Chromium only. No screen-reader session, no real phone, and no axe (not installed;
  installing packages was out of scope). The contrast figures are an approximation; the two-colour
  gradient band was checked by hand.

## Route inventory

| Route | Persona | Purpose | Issues | Priority |
|---|---|---|---|---|
| `/login` | Everyone | Pick a demo role | Inline styles, no `main` landmark (A13) | P3 |
| `/alerts` | analyst, reviewer, nodal, legal, senior, admin, auditor | Queue: map, list, filters | Says "0 alerts" while loading (A1). Sign-out hidden below 760 px (A3). 29 Tab stops before the first list row (A4). White box behind filter labels (A9). Low-contrast control borders (A6) | **P1** |
| `/alerts/:id` | Same as queue | Alert detail, actions, case file, officer record | Blank while loading; images fail silently (A1, A2). Legal checklist forces sideways scroll at 768 px and below (A3). Focus lost in action forms (A4). Actions far down the page at 1100 px and below (A8). Date-strip labels spill out of their panel (A10) | **P1** |
| `/assets` | admin, nodal, analyst, legal | Assets and boundary versions | An error shows "0" and an empty list (A1). Heading inside a button; selected row shown by tint only (A11). Bare count (A12) | P2 |
| `/records` | admin, legal, nodal, analyst | Permits, works, court cases; CSV import | Table scrolls sideways at 390 px (A3). Import focus invisible (A5). Import errors shown as info (A13) | P2 |
| `/monthly` | senior, nodal, legal, admin, auditor | One-page monthly summary | Blank while loading (A1). "1 days late" (A12). Browser print hides the demo band (A14). Print button has no error handling (A17) | P2 |
| `/audit` | auditor, admin | Log, chain check, closure sample | A 403 renders as an empty log (A1). Table scrolls sideways at 390 px (A3). Raw event keys (A12) | P2 |
| `/field` | field_officer | "My alerts" | Small "no signal" checkbox; no sign-out (A15) | P3 |
| `/field/alerts/:id` | field_officer | Alert, capture, offline queue | Shows "No alerts assigned to you" while loading (A1). Photo picker focus invisible (A5). "No signal" badge 3.99:1 (A7) | P2 |

## Visual findings

| ID | Area | Observation | Impact | Evidence / route | Recommendation |
|---|---|---|---|---|---|
| **A3** (P1) | Responsive | **Browser:** below 760 px the rail hides `.who`, so **Sign out and the language switch disappear**. This also happens at 200% zoom on a 1280 px laptop (640 CSS px). The legal officer's editable checklist uses a fixed 4-column grid (`CaseFile.tsx:56`, `1fr 150px 1fr auto`). The page scrolls sideways by **66 px at 768** and **216 px at 390**, and the Save buttons are cut off. The Records and Audit tables are 38 px and 31 px wider than a 390 px screen. The tables have no plan for narrow screens. | Functions are lost on reflow (WCAG 1.4.10). The legal role can't use tablets. | `detail-phone-top.png`, `x-legal-tablet-checklist.png`, `records-phone.png`; `measurements-followup.json` `legalOverflow*` | Keep sign-out and language in the narrow nav. Stack checklist rows below about 900 px. Give tables a scroll wrapper with a visible edge, or stacked rows. |
| **A8** (P2) | Hierarchy: alert detail | **Browser:** at 1100 px and below the layout becomes one column. The "Next step" panel (the role's actions) then sits after the images, date strip, map, checklist and statement, far below the first screen at 1024 px. On a phone the `h1` wraps to three lines beside the boundary badge. **"Close as not real" (destructive) comes before, and is as wide as, "Confirm the change" (primary).** The order comes from the server's `allowed_actions`. | Decision-makers on laptops scroll past all the evidence to act. The first, equal-weight button is the destructive one. | `detail-desk-full.png`, `detail-phone-top.png`; `styles.css` `@media (max-width:1100px)` | Bring the actions panel near the top, or make it sticky, at narrow widths. Put the badge under the title on phones. Changing action order needs owner approval (see Decisions needed). |
| **A9** (P2) | CSS leaking between desk and field app | **Browser and code:** `field/field.css` styles `.field { background:#fff; min-height:100%; font-size:1.05rem }` for the field app's root element. Because the CSS is global, it also hits every desk `label.field`. The result is a white box behind "What this asset allows" and "Asset group" on the paper background (measured `labelBg rgb(255,255,255)`). | A visible glitch on the main queue. Shows the namespace risk for any future change. | `x-filter-label.png`, `queue-desk.png` | Rename the field app's root class (for example `.field-app`). No e2e test selects `.field`. |
| **A10** (P3) | Date strip | **Browser:** "First changed" spills 2 px past its panel at 1440, 12 px at 1280, 13 px past the screen at 390, and 60 px in Telugu at 390. When the dates are close, "Last clear" and "First changed" crowd together. | The core "when did it happen" graphic looks broken on narrow screens. | `detail-desk-full.png`; `measurements-followup.json` `bracket*`; `DatedBracket.tsx` | Keep labels inside the strip; flip the anchor near the edges. Stack the two labels when dates are close or the screen is narrow. |
| **A12** (P3) | Content | **Browser:** the audit "What" column shows raw event keys (`auth.login`, `timer.missed`) and "Item" shows `user 8` and `alert 18`. Records shows raw values ("building"). The monthly page says "1 days late". The Assets header shows a bare number ("20", or "0" on error). **Code:** hard-coded English `aria-label="Main"` (`Layout.tsx:31`) and `"State"` (`Queue.tsx:72`), and the map credit "Demo map (fictional)" (`MapView.tsx:24`) is not translated. | Not plain words for the auditor; English-only labels in a two-language app. | `audit-desk.png`, `monthly-desk.png` | Map event keys and record values to i18n labels; use i18next plurals; translate the aria labels and the map credit. **Every new string must pass `test_wording.py`.** |
| **A13** (P3) | Consistency | **Code:** 55 inline `style={{}}` props, about 118 hex literals outside tokens, and map and legend colours (`#46a0ff`, `#e6463c`, `#ffd640`) that are not in the palette. **Browser:** the checklist uses unstyled native `select` and `input` (`x-legal-tablet-checklist.png`). Records shows import errors in a blue info banner (`Records.tsx:126`). | The look drifts between screens; hard to change safely. | Code references above | Turn repeated inline layouts into classes; tokenise the remaining colours; route checklist controls through the shared form styles. |
| **A14** (P2) | Print | **Browser:** `@media print` hides `.demo-band` (`printDemoBand: "none"`). The "Print one page" button is not affected, because it downloads the server PDF, which carries its own demo marking. | Ctrl+P on any desk screen prints demo data with no label (rule 6). | `styles.css` `@media print`; `measurements.json` `checks.printDemoBand` | Keep the band in print, as a solid printable colour. |

## Interaction and accessibility findings

| Workflow / area | Observation | Impact | Regression risk |
|---|---|---|---|
| **A1 (P1) Loading, error, no-access and empty states** | **Browser:** while loading, the queue says "0 alerts. Highest priority first." over an empty list (`state-queue-loading.png`). Alert detail is a blank page while loading, with `aria-busy` and nothing visible. On a 500 error, Assets shows "0" and an empty list with no message, and the demo band disappears (`state-assets-error.png`). An analyst who opens `/audit` gets a 403, which renders as an **empty audit log with a working "Check the log" button** (`role-analyst-on-audit.png`). Records, Audit and Monthly show errors as a red line without `role="alert"`; only the queue offers "Try again". **Code:** the field alert shows "No alerts assigned to you." while IndexedDB loads, or when the alert isn't cached (`FieldApp.tsx:191`). | People read "nothing" when the truth is "not loaded" or "not allowed". This undermines an audit tool whose pitch is trust. | Medium. `useAsync` feeds every page; e2e waits for real content, so new loading UI must not reuse those test IDs. |
| **A2 (P1) Image pair** | **Browser:** while the before and after images load, each figure is 41 px tall (caption only), then jumps to 415 px, a 374 px layout shift. If the images fail, the figures **stay at 41 px with no message** (`state-detail-images-failed.png`). The confirmation box "I compared the before and after images" can still be ticked. | The evidence vanishes silently next to the gate that certifies it was reviewed. | Medium. Must keep `image-rendering: pixelated`, the alt text, `.pair` structure and the D-027 labels. Any change to the gate's behaviour is a business-rule change. |
| **A4 (P2) Keyboard flow and focus** | **Browser:** opening an action form with the keyboard (Enter on "Close as not real") sends **focus to `<body>`**, and Cancel does the same (`checks.actionFocus`). On the queue, Tab passes through 5 nav items, 2 selects, 8 chips, the map canvas and **14 map pins**: after 30 presses it still hasn't reached the first list row. There is no skip link. **Code:** `document.title` is always "Lake Protect" and focus doesn't move on route changes. | Keyboard and screen-reader users lose their place in the key decision forms and face a long trip to the alert list. | Medium. Pins are clicked by `.pin` in e2e; keep them clickable even if they leave the Tab order. |
| **A5 (P2) Invisible focus** | **Browser:** "Import CSV" (Records) puts focus on a 1×1 `.sr-only` input, and "Take or add a photo" (field app) on a 1×1, `opacity:0` input. Neither visible label shows a focus ring. | Fails WCAG 2.4.7 on two upload controls. | Low. Add a `:focus-within` ring to the label; keep `data-testid="photo-input"`. |
| **A6 (P2) Control boundaries** | **Browser:** input, select and textarea borders (`#b4beb8`) are **1.91:1** on white, and the field app's select and textarea (`#93a19a`) are 2.69:1. Chips are 1.68:1 and secondary buttons 1.84:1 on paper; the rail buttons are 2.2:1 on ink. | Text fields fail WCAG 1.4.11. Buttons are borderline, since their text identifies them. | Low. The existing `--ink-3` (#75848b) reaches 3.87:1 on white and 3.39:1 on paper. |
| **A7 (P2) Text contrast** | **Browser:** the "No signal: saving on this phone" badge (`.net.off`, white on #b07219) is **3.99:1**, the field officer's main offline signal. `.flag-overdue` and `.error` on paper are 4.47:1, just under 4.5:1; they pass on white panels (5.10:1). The demo band is fine (7.23:1 and 9.03:1 on its two stripes). | The offline signal is hard to read outdoors. | Low. #9a6315 reaches 5.04:1 behind white; #b8392a reaches 5.04:1 on paper. |
| **A11 (P3) Semantics** | **Browser:** headings jump from `h1` to `h3` on the queue, detail, assets and audit pages. **Code:** Assets rows put an `h3` inside a `<button>`, and the selected row is shown only by a faint tint (#eef3f0) with no `aria-pressed` or `aria-current`. The login page has no `main` landmark. | Harder to navigate by headings; the selected asset can't be perceived. | Low. |
| **A15 (P3) Field app** | **Browser:** there is **no sign-out** anywhere in the field app. A field officer who opens `/alerts` gets the desk with an empty dark rail and no way back (`role-field-on-desk.png`). The "Demo: no signal" checkbox is 13×13 px, and "Send now" is 40 px tall (under the 44 px used elsewhere in the field app). Closed map pins are 18 px with 2.55:1 contrast. The Telugu layout holds at 360 px (`field-alert-small-te.png`). | A dead end on shared phones; small targets. | Low to medium. Sign-out on the field app is a product decision. |
| **A16 (P3) Performance** | **Browser:** one 1.48 MB JS chunk (MapLibre included). `vite.config.ts` raises the chunk-size warning limit to 1,500 KB, so no warning shows. The service worker precaches 40 files; **about 279 KB of 659 KB of fonts are Cyrillic, Devanagari, Greek and Vietnamese**, which the app never shows. | Slower first load and wasted data on field phones. | **Protected:** this touches the PWA and Workbox config. Needs owner approval. |
| **A17 (P3) Monthly print** | **Code:** `Monthly.tsx` `print()` opens whatever the PDF request returns, with no loading or error handling, even if it's an error body. | A failed print opens a confusing tab. | Low. |

## Protected functionality

Everything in "Protected functionality" in `PROJECT_PROFILE.md` stays unchanged: the API and
backend, authentication, roles, the state machine, evidence packs, the audit chain, the offline sync
code, PWA settings, and `labels.ts` mappings. For the fixes above, the points most at risk:

- **Section 6.8 wording:** every new or changed string (loading, error and no-access messages, aria labels, plurals) must pass `docker compose exec api pytest tests/test_wording.py`.
- **Demo marking:** `DemoBand`, `useDemoOnScreen` and `data-testid="demo-badge"`. A1's error states must not hide the band when demo data was on screen before.
- **Action rendering:** render exactly what `allowed_actions` sends. Do not filter, relabel or reorder without approval.
- **The statement** "Imagery shows physical change. It does not establish title or legality." stays on the alert detail screen.
- **Boundary line language and synthetic-image rendering:** `image-rendering: pixelated` and the D-027 labels.
- **Test hooks:** 65 `data-testid`s; the class selectors `.pin`, `.photo-thumb`,
  `.monthly-map svg polygon`, `.list .row`, `.f-pair img`, `.detail-head`, `.detail-head .pill`;
  and 9 `getByRole` names.
- **Fully offline:** no CDN fonts, icons or scripts. The m9 test fails on any request that leaves localhost.

## Baseline checks

- **Build:** pass. `docker build --target build ./web` hit the cache on every layer, including
  `RUN npm run build` (`tsc -b && vite build`). The cache keys on file contents, so the current
  source has already type-checked and built. The served image (15:49 IST) is newer than the last
  source change (15:47 IST).
- **Lint:** not configured (no ESLint, Prettier or Biome).
- **Tests:** API **235 passed**, with 1 Starlette deprecation warning, in 48.9 s, run on the audit stack's own test database.
- **Browser:** Playwright **13 passed** (m5 to m8, 26.3 s) and **1 passed** (the m9 walkthrough,
  27.0 s), each on a fresh demo in the audit stack, run as `scripts/e2e.sh` does. The audit scripts
  measured 52 states with 0 script errors and 0 requests leaving the machine. The 11 console errors
  were all the 403, 404 and 500 responses the audit forced on purpose.
- **Known pre-existing failures:** none in the tests. All 17 findings above are pre-existing.

## Recommendations, risks and unknowns

### Quick wins (CSS or markup only, low risk)
1. Rename the field app's root `.field` class (A9).
2. Use `--ink-3` or a new `--control-border` token at 3:1 or better for input, select, textarea, chip and secondary-button borders (A6).
3. Darken the red used for text (A7, for example #b8392a) and the "No signal" badge background (A7, for example #9a6315).
4. Add a `:focus-within` ring on the two file-picker labels (A5).
5. Keep sign-out and the language switch in the narrow nav (A3, part).
6. Keep the demo band when printing (A14).
7. Plurals and translated aria labels (A12). Run the wording test.

### Page-level work
- **Shared states (A1, A2):** one loading pattern, one error pattern with retry and `role="alert"`, and one "you don't have access to this page" pattern for 403s, used on every page.
  Give the image pair fixed-size placeholders and a visible "image could not be loaded" message.
- **Alert detail (A8, A10):** move the actions panel up at 1100 px and below; fix the date-strip labels; put the badge under the title on phones.
- **Narrow layouts (A3):** stack the checklist rows; make the tables work on phones.
- **Keyboard (A4):** a skip link; take map pins out of the Tab order (the list already reaches every alert); move focus into opened forms and back to the trigger on cancel; per-route `document.title` and focus on the new page's `h1`.
- **Polish (A11 to A13, A15, A17).**

### Structural (owner approval needed)
- Scope CSS per surface (CSS modules or prefixes) and finish tokenising (A9, A13).
- Add ESLint with `jsx-a11y`, and `@axe-core/playwright` in the e2e suite: new dev dependencies.
- Code-split MapLibre and trim the precached font subsets (A16): touches the protected PWA config.

### Recommended sequence
1. Quick wins (A9, A6, A7, A5, A14, A3 sign-out, A12 strings). Then run the wording test and the e2e suite.
2. Shared states (A1, A2).
3. Narrow layouts and the detail page's hierarchy (A3, A8, A10).
4. Keyboard flow (A4).
5. Polish (A11, A13, A15, A17).
6. Structural items, once approved.

Next UEF step: **`/uef:design`**, which settles the tokens and patterns (states, form controls, narrow layouts) before `/uef:implement`.

### Decisions needed from the owner
- May "Close as not real" be shown after the primary action, or does the server's order carry meaning? (A8)
- When images fail to load, should the "I compared the images" box be disabled or annotated? This is business-rule adjacent. (A2)
- Should the field app have sign-out (shared phones)? (A15)
- Are new dev dependencies (ESLint, axe) and PWA precache changes allowed? (A16)

### Risks
- Most fixes touch shared CSS in one global file. Every change needs checking on both the desk and
  the field app, at 1440, 1024, 768 and 390 px, in both languages.
- New UI strings can trip the wording test, and Telugu versions need the native-speaker review (D-028).
- e2e relies on test IDs and seven class selectors; renaming any of them breaks the suite.

### Not verified (unknowns)
- Screen-reader behaviour (NVDA, TalkBack). Firefox and Safari. A real phone over HTTPS, its GPS and performance. Outdoor readability.
- 200% zoom was approximated with a 720×450 viewport, not real browser zoom.
- The quality of the Telugu text (it's a draft) and whether Telugu labels fit on every desk screen
  (the queue, detail and monthly pages were checked; the others were not).
- Whether the demo band's `role="status"` is announced too often by screen readers.

## Addendum, 6 Nov 2026 (found during `/uef:design`)

| ID | Workflow / area | Observation | Impact | Regression risk |
|---|---|---|---|---|
| **A18** (P2) | Focus on dark surfaces | **Calculated:** the 3 px focus ring (`--focus` #1f6fa8) has **2.70:1** contrast on the rail and field header (#1c2b33), and **2.27:1** on the active rail item (#26383f). Both are below 3:1. The rail's existing light blue (#7fb6dd) gives 6.68:1 and 5.60:1. | Keyboard focus is hard to see in the main navigation and the field app's header. | Low. Fixed by `--focus-inverse` in `UI_DESIGN_SYSTEM.md`. |

### Re-running the evidence

Run these from the project root in Git Bash. They use the isolated `lpaudit` stack, so the owner's
demo data is untouched. `$EVID` is `docs/uef/evidence/2026-11-06-baseline` as an absolute path;
`$OUT` is any empty folder.

```sh
export LP_WEB_PORT=18180 LP_API_PORT=18100 LP_DB_PORT=15544 MSYS_NO_PATHCONV=1
docker compose -p lpaudit up -d --no-build --wait db api web
docker compose -p lpaudit exec -T -e LP_ALLOW_RESET=true api python -m app.seed.reset
# audit scripts (write screenshots and measurements to $OUT/out)
cp "$EVID"/audit*.cjs "$OUT"/
docker run --rm --network container:lpaudit-web-1 --mount "type=bind,source=$OUT,target=/audit" \
  -w /e2e lakeprotect-e2e:dev node /audit/audit.cjs
# browser tests (reset before m5-m8 and again before m9, as scripts/e2e.sh does)
docker run --rm --network container:lpaudit-web-1 -e E2E_BASE=http://localhost \
  --mount "type=bind,source=$PWD/e2e/tests,target=/e2e/tests,readonly" \
  --mount "type=bind,source=$PWD/e2e/playwright.config.ts,target=/e2e/playwright.config.ts,readonly" \
  --mount "type=bind,source=$OUT,target=/e2e/test-results" \
  -w /e2e lakeprotect-e2e:dev npx playwright test m5-desk m6-field m7-evidence m8-monthly
docker compose -p lpaudit down -v
```
