# UEF Project Profile

> Created by `/uef:onboard` on 6 Nov 2026 at commit `ffc6ae8` (M9). Every entry is taken from the
> repository. Values not found are marked **Unknown**. Source of truth for the product is
> `CONTEXT.md`; build state is in `PROGRESS.md`; departures are in `DECISIONS.md`.

## Product

- **Product name:** Lake Protect (working name). `README.md`
- **Purpose:** A monitoring loop for Telangana's lakes and government land. Free satellite data
  screens each asset weekly, a rules engine checks the legal position of each change, field teams
  verify it, and officers receive a case file. The pitch is "your cases hold up", not a map viewer
  (`CONTEXT.md` section 1: "Do not build a satellite-map viewer").
- **Stage:** Prototype. Milestones M0, M1, M4 to M9 are done; M2 and M3 (detection, backtest) have
  not started. **All data on screen is fictional demo data.** No detection result exists yet.
- **Primary audience:** HYDRAA staff. The demo audience is senior officials, who "should grasp every
  screen at a glance, so favour pictures, maps and plain words over tables of numbers"
  (`CONTEXT.md` section 2).
- **Personas / roles** (`api/app/enums.py` `Role`, `CONTEXT.md` section 2):

  | Role | Who | Main surface | Home route (`auth.tsx` `homeFor`) |
  |---|---|---|---|
  | `analyst` | Vendor or desk staff | Desk | `/alerts` |
  | `reviewer` | Second analyst, co-signs closures | Desk | `/alerts` |
  | `field_officer` | HYDRAA Lake Protection Teams | Field app (phone) | `/field` |
  | `nodal_officer` | Named HYDRAA officer; assigns, watches timers | Desk | `/alerts` |
  | `legal_officer` | HYDRAA legal team | Desk | `/alerts` |
  | `senior_officer` | Commissioner, Secretary | Monthly page | `/monthly` |
  | `auditor` | Internal or external | Audit view | `/audit` |
  | `admin` | Vendor | Desk | `/alerts` |

- **Main journeys** (`docs/DEMO.md`, walked end to end by `e2e/tests/m9-demo.spec.ts`):
  1. Sign in by demo role (no password; demo accounts only).
  2. Analyst opens an alert, compares the dated image pair, reads the legal check, confirms the change.
  3. Nodal officer assigns it to a field officer.
  4. Field officer (Telugu by default) opens it on a phone, offline, captures photo and position, saves; the visit queues and syncs on reconnect.
  5. Legal officer fills the case-readiness checklist, generates the evidence pack, opens the PDF, checks integrity.
  6. Nodal officer marks the case file ready and sends it to the officer; legal officer records the officer's action.
  7. Auditor checks the hash-chained log. Senior officer reads and prints the monthly page.
- **Brand references:**
  - Mark: inline SVG lake outline (solid) inside a dashed buffer line (`web/src/components/Layout.tsx` `Mark`).
  - Stated palette idea: "Survey-sheet palette: cool paper, slate ink, FTL blue, buffer red" (`web/src/styles.css` header).
  - Identity rule: **line style encodes boundary certainty everywhere** (solid = confirmed,
    dashed = preliminary, dotted = estimated), on the map and on the boundary badge.
  - Demo marking: purple diagonal-striped band; `docs/DEMO.md` step 0 says "Point at the purple band".
- **Desired visual qualities** (from the docs and code comments):
  - Large, map-first layouts (`CONTEXT.md` section 9.1).
  - Plain words, readable at a glance by senior officials.
  - Field app: "one column, large type and targets, high contrast for outdoor light" (`field.css`).
  - Monthly page: one printable A4 page.
  - Dense but scannable operational desk (queue, detail, tables).
- **Patterns to avoid:**
  - The generic SaaS and decorative patterns in the UEF visual standard.
  - Anything that reads as a "satellite-map viewer" product.
  - Imagery that looks sharper than 10 m Sentinel data. Chips must keep hard pixel edges
    (`image-rendering: pixelated`, D-027).
  - Any visual or verbal suggestion that the system decides legality or recommends an outcome
    (`CONTEXT.md` section 1, rule 1).
  - Showing status by colour alone (state pills, map pins and boundary lines currently pair colour
    with text or line style; keep it that way).

## Existing technology

Versions are the resolved versions in `web/package-lock.json` (lockfile v3) unless noted.

- **React/framework version:** React 19.3.1, react-dom 19.3.1. Vite 6.4.5 SPA with
  `@vitejs/plugin-react` 4.7.0. No meta-framework (not Next.js).
- **Language:** TypeScript 5.9.3, `strict: true`, `noUnusedLocals`, `noUnusedParameters`
  (`web/tsconfig.json`). Node 24 (`node:24-alpine` in `web/Dockerfile`; host has Node 24.18.0, npm 11.14.1).
- **Package manager:** npm (`package-lock.json`; `npm ci` in `web/Dockerfile` and `e2e/Dockerfile`).
- **Styling / Tailwind version:** No Tailwind. Plain global CSS with CSS custom properties:
  `web/src/styles.css` (191 lines), `web/src/bulletin/monthly.css`, `web/src/field/field.css`.
  No CSS modules, no CSS-in-JS. 55 inline `style={{…}}` props in TSX.
- **Component library:** None. In-house components only (see "Component conventions").
- **Icon and animation libraries:** None. Icons and marks are inline SVG. No motion library and
  almost no transitions; a global `prefers-reduced-motion` rule disables all transitions and animations.
- **Routing / state / data fetching:**
  - Routing: react-router-dom 7.18.5, `BrowserRouter` with declarative `<Routes>` (`App.tsx`, nested `<Routes>` in `field/FieldApp.tsx`).
  - State: React context only (`AuthProvider` in `auth.tsx`, `DemoProvider` in `demo.tsx`) plus local `useState`. No global store.
  - Data: custom `fetch` wrapper `api()` in `web/src/api.ts` and a `useAsync` hook in `components/Bits.tsx`. No React Query or SWR. Bearer token in `localStorage` (`lp.token`).
  - Offline: idb 8.0.4 (IndexedDB queue and alert cache), vite-plugin-pwa 1.3.0 with Workbox, workbox-window 7.4.1.
  - Maps: maplibre-gl 5.24.0 with local raster tiles from `/api/tiles/demo/…`, no glyphs or sprites.
  - i18n: i18next 25.10.10 and react-i18next 15.7.4; `web/src/i18n/en.json` and `te.json` (draft Telugu, D-028).
  - Fonts: `@fontsource/noto-sans` and `@fontsource/noto-sans-telugu` 5.3.0, weights 400/600/700, self-hosted.
- **Forms and validation:** Native controlled inputs, no form library, no client validation library.
  The server is the authority; errors come back as `ApiError` messages.

## Commands

The supported workflow runs everything in Docker. `node_modules` must stay **outside this OneDrive
folder** (`README.md`, `CONTEXT.md` section 11). `web/node_modules` and `e2e/node_modules` are
absent on the host, by design.

- **Install:** No host install step. Web dependencies install inside the image build (`npm ci` in
  `web/Dockerfile`). First run: copy `.env.example` to `.env`, set secrets, then
  `docker compose up -d --build` and
  `docker compose exec -e LP_ALLOW_RESET=true api python -m app.seed.reset`.
- **Development:** `docker compose up -d --build`, then http://localhost:8180 (desk) and
  http://localhost:8180/field (field app). The `web` container serves a **production build through
  nginx**, so UI changes show only after `docker compose up -d --build web`. A Vite dev script exists
  (`npm run dev`, proxying `/api` to `http://api:8000`, a Docker network name) but no compose service
  runs it: **how it is meant to be used is Unknown.**
- **Build:** `npm run build` (`tsc -b && vite build`), run by `docker compose build web`.
- **Lint:** **None configured.** No ESLint, Prettier or Biome config or dependency, although nine
  source files carry `eslint-disable` comments.
- **Typecheck:** `tsc -b`, only as the first half of `npm run build`. No separate script.
- **Unit tests:** **None for the web app.** API: `docker compose exec api pytest` (235 passed at M9).
  This suite includes `api/tests/test_wording.py`, which **scans every `.ts`, `.tsx`, `.css`, `.json`,
  `.svg` and `.md` file under `web/src` and `web/public`**, so it must be run after any UI copy change.
  Pipeline: `C:\lp-cache\venv\Scripts\python -m pytest pipeline/tests -p no:cacheprovider`.
- **E2E tests:** `sh scripts/e2e.sh` (Playwright 1.65.0, Chromium only, in Docker; 14 passed at M9).
  One suite: `sh scripts/e2e.sh m5-desk` (also `m6-field`, `m7-evidence`, `m8-monthly`, `m9-demo`).
  **Each run resets the demo database first.** No-internet proof: see `README.md` ("To prove the demo
  runs with no internet").

## Routes and scope

Nav visibility comes from `NAV` in `web/src/components/Layout.tsx`. Client route guards
(`RequireUser` in `App.tsx`) check only that someone is signed in; **role enforcement is server-side**
(`require_roles` in `api/app/routers/*.py`).

| Route | Persona | Purpose | Priority | Notes |
|---|---|---|---|---|
| `/login` | Everyone | Pick a demo account by role | High | First screen of the demo; shows the demo band and language toggle. Inline styles. |
| `/alerts` | analyst, reviewer, nodal, legal, senior, admin, auditor | Alert queue: map and list together, state filters, priority order | High | Home for most desk roles. Map and list share hover state. |
| `/alerts/:id` | Same as queue | Alert detail: boundary badge, before/after images, dated bracket, map, legal check panel, role actions, history, case file, officer record, section 6.8 statement | Highest | Largest screen (`AlertDetail.tsx` 312 lines, plus `CaseFile.tsx`, `OfficerRecord.tsx`). Action buttons come from the server's `allowed_actions`. |
| `/assets` | admin, nodal, analyst, legal | Asset map, cohort, boundary versions with source and baseline date | Medium | Uses `table.grid`. |
| `/records` | admin, legal, nodal, analyst | Permits, authorised works, court cases; CSV import (admin, legal) | Medium | API also lets `auditor` read records, but there is no nav link for them. |
| `/monthly` | senior, nodal, legal, admin, auditor | One-page monthly figures, map, overdue by who must act, overdue list | High | Home for `senior_officer`. "Print one page" downloads the server-rendered PDF. |
| `/audit` | auditor, admin | Full log, chain check, random closure sample | Medium | Home for `auditor`. Uses `table.grid`. |
| `/field` | field_officer | "My alerts", sorted by due date; sync status | Highest | PWA, phone width (tests use 412×915). Telugu default for Demo Field Officer 1. Separate shell, no desk rail. |
| `/field/alerts/:id` | field_officer | Alert, small map, image pair, instruction, capture form, offline queue | Highest | Demo-only "no signal" and "position" switches (D-031). |
| `*` | — | Redirect to the role's home, or `/login` | — | |

## Protected functionality

Per the UEF safe-change policy, none of the following may change during UI work without explicit
approval from the owner.

**Backend and data (all of it):** `api/` (routers, `rules/`, `workflow/` state machine, timers and
escalation, `evidence/`, `audit/` hash chain, `bulletin/`, `security.py`, `models.py`, `migrations/`,
`seed/`), `pipeline/`, `data/`, `docker-compose*.yml`, Dockerfiles.

**Web code that carries contracts or rules, not presentation:**
- `web/src/api.ts`: API base, token handling, error shape, `AlertRow`/`User` types.
- `web/src/auth.tsx`: login, token lifecycle, offline cached user, `homeFor` role routing.
- `web/src/field/sync.ts`, `store.ts`, `geo.ts`: offline queue, idempotent send by `client_uuid`,
  SHA-256 photo hashes, device and server time, 50 m distance warning (warn, never block).
- `web/vite.config.ts` PWA/Workbox config and `web/nginx.conf` (precache, tile cache, `/api` proxy).
- `web/src/components/labels.ts`: state-to-group mapping and `certainty()`. Colours may be
  re-tokenised, but the mapping must not change.
- Role visibility: `NAV` in `Layout.tsx`, and `canEdit`/`canMake`/`canRecord`/`canImport`/
  `canRequestImagery` checks in `CaseFile.tsx`, `OfficerRecord.tsx`, `Records.tsx`, `AlertDetail.tsx`.
- `web/src/demo.tsx`: when the demo band appears.

**Product rules that are visible in the UI (`CONTEXT.md` sections 1, 6.8, 9):**
- **Wording (section 6.8):** a list of banned English words and Telugu stems, enforced by
  `api/tests/test_wording.py` over all web sources. New or reworded copy must pass it.
- **The statement** "Imagery shows physical change. It does not establish title or legality." must
  stay on the alert detail screen (and in every evidence pack).
- **Demo marking:** a visible "Demo data" band whenever `is_demo` records are on screen
  (`DemoBand`, `useDemoOnScreen`, `data-testid="demo-badge"`), and `DemoTag` on records.
- **Boundary certainty is always visible**, and the badge's line style matches the map line.
- **Confirmation gate:** the analyst must tick "I compared the before and after images" before confirming.
- **Officer record:** "The system suggests no outcome. The officer decides." No suggested outcome.
- **Field note, pending counsel:** "This is an observation, not a survey. Do not enter private land."
- **Draft marks** stay on the Telugu text (D-028) and the section 63(4) certificate (D-033).
- **Fully offline demo:** no fonts, icons, scripts, styles or tiles from the internet. The M9 test fails
  on any request that leaves localhost. This rules out CDN-hosted fonts or icon sets.

**Test hooks the browser tests depend on:**
- 65 `data-testid` attributes in `web/src`, used 122 times in `e2e/tests`.
- CSS class selectors: `.pin`, `.photo-thumb`, `.monthly-map svg polygon`, `.list .row`,
  `.f-pair img`, `.detail-head`, `.detail-head .pill`.
- 9 `getByRole` lookups (accessible names in English and Telugu matter).

## Existing design system

- **Brand colours** (`web/src/styles.css` `:root`):

  | Token | Value | Use |
  |---|---|---|
  | `--paper` | `#eef1ec` | Page background |
  | `--sheet` | `#ffffff` | Panels, tables, cards |
  | `--ink` | `#1c2b33` | Text, primary buttons, rail, `theme-color` |
  | `--ink-2` / `--ink-3` | `#4a5a62` / `#75848b` | Secondary and tertiary text |
  | `--rule` | `#d3dad4` | Borders and dividers |
  | `--ftl` | `#1f6fa8` | Links, focus ring, confirmed boundary, "field" group |
  | `--buffer` | `#c4402f` | Buffer line, overdue, danger, "legal" group |
  | `--green` | `#2d7a57` | "Officer" group, online |
  | `--amber` | `#b07219` | "Review" group, preliminary boundary, warnings |
  | `--violet` / `--violet-tint` | `#6e3fa3` / `#efe7f8` | Demo band and tag |

  Group colours for maps and lists are duplicated as literals in `GROUP_COLOUR` (`labels.ts`).
- **Typography:** Noto Sans with Noto Sans Telugu, self-hosted, weights 400/600/700. Scale tokens
  `--step--1` 0.8125rem, `--step-0` 0.9375rem (body), `--step-1` 1.125rem, `--step-2` 1.4rem,
  `--step-3` 1.9rem. Body line-height 1.5, raised to 1.65 when `lang="te"`. The field app uses a
  larger base (1.05rem) and 40 to 64 px minimum control heights (the sync bar's buttons are the 40px ones). The monthly figures use 2.6rem tabular numbers.
- **Spacing / geometry:** rem-based spacing written inline in each rule; **no spacing tokens**. Radius
  tokens `--radius-s` 4px and `--radius-m` 8px, plus 999px chips. 1px `--rule` borders. Almost no
  shadows (map pins only). Focus: 3px `--focus` outline with 2px offset on `:focus-visible`.
- **Token location:** `web/src/styles.css` `:root` only. Not all colours use tokens: 86 hex literals in
  the three CSS files (pill, banner and hover tints, rail colours) and 32 in TS/TSX (`labels.ts`,
  `MapView.tsx`, `Layout.tsx` mark, `Login.tsx`).
- **Component conventions:**
  - Global classes: `.page`, `.page-head`, `.btn` (`.secondary`, `.danger`), `.panel`, `.section`,
    `.pill.<group>`, `.banner.<warn|stop|info>`, `.seal.<certainty>`, `.chip[aria-pressed]`,
    `label.field`, `label.check`, `table.grid`, `dl.facts`, `.timeline`, `.note`, `.statement`.
  - The field app uses `f-` prefixed classes in `field.css`.
  - Shared React pieces: `BoundarySeal`, `StatePill`, `AuthImage`, `LineSwatch`, `useAsync`
    (`components/Bits.tsx`), `DatedBracket`, `MapView`, `Layout`/`Mark`, `DemoBand`/`DemoTag`.
  - Desk shell: 216px dark navigation rail plus a scrolling main area. Breakpoints are 1100px and
    760px in `styles.css`, and 1000px in `monthly.css`. Field app: one column, max 640px.
  - Print: `@media print` hides the rail and demo band; `monthly.css` hides buttons and chips.

## Constraints and known issues

**Environment constraints**
- Browsers: the demo runs in Chrome or Edge on one laptop (`docs/DEMO.md`). Browser tests use
  Chromium only (D-029). Firefox and Safari are **untested**.
- Tested viewports: desk 1440×900, phone 412×915. No tablet or narrow-desk test exists.
- No internet at demo time; everything must be bundled or served locally (M9).
- Real phones need HTTPS, which is not set up (D-032). The field app is exercised at phone width on the laptop.
- Telugu strings are drafts awaiting a native speaker (D-028). Layouts must tolerate Telugu text
  length and the taller line-height.
- OneDrive folder: never install `node_modules` or create virtual environments inside the project.
- Deployment target is a government data centre or an approved India cloud region. No cloud-only
  services (`CONTEXT.md` section 10).

**Existing observations, not yet verified in a browser (for `/uef:audit` to confirm or dismiss).**
These come from reading the code. They existed before any UI modernization.
1. Below 760px the desk rail hides `.brand` and `.who`, which removes the **sign-out and language
   buttons** on narrow desk screens.
2. `table.grid` (assets, records, audit) has no narrow-screen strategy such as a scroll wrapper.
3. Signed-in users can open any desk URL; a role without access sees whatever the server's 403
   produces, since client guards do not check role.
4. Browser print (Ctrl+P) hides the demo band. The "Print one page" button is unaffected, because it
   downloads the server PDF, which carries its own demo marking.
5. 55 inline styles and about 120 hex literals sit outside the token system.
6. Rail button and secondary-text contrast have not been measured. No automated accessibility check
   (such as axe) is in the e2e suite.

**Unknowns**
- How the Vite dev server (`npm run dev`) is meant to be used, given its `api:8000` proxy target and
  no compose service for it.
- Whether a host-side typecheck or build is acceptable, and where its `node_modules` would live
  (only `C:\lp-cache` is named, for the Python venv).
- Formal brand guidelines beyond the code. None found in the repo.
- Owner's appetite for adding a linter, an accessibility checker or new UI dependencies.
- Whether the reviewer, senior officer and auditor are meant to see the full queue (they have the nav
  link; server filtering per role was not inspected for this profile).
