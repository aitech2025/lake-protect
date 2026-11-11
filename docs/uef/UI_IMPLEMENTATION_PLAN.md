# UEF UI Implementation Plan

> **Status: APPROVED** (owner, 6 Nov 2026). Not started. It implements Direction A
> ("Survey sheet, refined") from `UI_DESIGN_SYSTEM.md` and fixes audit findings A1 to A18 in
> `UI_AUDIT.md`. Work is done per phase through `/uef:implement`, one commit per phase, on a branch.

## Scope

- **Pages / workflows:**
  - All desk routes (`/login`, `/alerts`, `/alerts/:id`, `/assets`, `/records`, `/monthly`, `/audit`).
  - The field app (`/field`, `/field/alerts/:id`).
  - The ten-minute demo walkthrough (`docs/DEMO.md`) end to end.
  - The pilot screen is **Alert detail**, with a review stop after it (phase 4).
- **Out of scope:**
  - Everything under `api/`, `pipeline/`, `data/` and the migrations, including the server-rendered
    evidence-pack PDF, the monthly PDF and the image chips.
  - Authentication, roles, nav visibility per role, the state machine, and `allowed_actions` content.
  - `vite.config.ts` PWA/Workbox settings and `nginx.conf` (D4: PWA changes not approved).
  - New UI libraries, and axe in the e2e suite (not approved).
  - Direction B.
  - Review of the Telugu text by a native speaker (D-028; still required before real use).
  - HTTPS for real phones (D-032).
- **Approval reference:** the owner approved Direction A and answered D1 to D4 on 6 Nov 2026 (`/uef:design` session).

### Owner decisions

| ID | Question | Answer (6 Nov 2026) | Affects |
|---|---|---|---|
| **D1** | May the decision panel show forward actions first, closures after and utilities last (presentation only; same actions, same labels)? | **Yes, reorder.** | Phase 4 (A8) |
| **D2** | When the before or after image fails to load, should the "I compared the before and after images" box be disabled? | **No. Show the failure only;** the tick box is unchanged. | Phase 2, phase 4 (A2) |
| **D3** | Add a sign-out control to the field app (shared phones)? | **Yes.** | Phase 7 (A15) |
| **D4** | New dev tooling and PWA changes? | **ESLint with `jsx-a11y`: yes. `@axe-core/playwright`: no. Font-subset trim and lazy MapLibre: no.** | Phase 8 (A13, A16) |

## Existing behaviour to preserve

- **API usage:** every `api()` call, its path, method, body and error handling (`web/src/api.ts`
  unchanged). The token stays in `localStorage`. Reading `ApiError.status` for page states is
  read-only.
- **Permissions:**
  - `NAV` role lists in `Layout.tsx`.
  - The `canEdit`, `canMake`, `canRecord`, `canImport` and `canRequestImagery` checks.
  - `homeFor()` role routing.
  - The server stays the authority. A 403 is shown as "forbidden", never hidden.
- **Workflows:**
  - Analyst confirmation needs the image-pair tick.
  - Two-person closures.
  - Nodal assignment with owner and due date.
  - Checklist save per item.
  - Evidence pack generate, open, download and check.
  - Officer record save and record-action.
  - Audit log check.
  - Monthly PDF.
  - Field capture: photo SHA-256, GPS, the 50 m warning (warn, never block), offline queue, sync and the demo switches (D-031).
- **Product rules:**
  - The section 6.8 wording (checked by `test_wording.py`).
  - The statement on the alert detail.
  - The demo band and tags whenever demo records are on screen.
  - The boundary line language.
  - Pixelated synthetic chips.
  - No request leaves localhost.
- **Test hooks:**
  - All 65 `data-testid` values.
  - The class selectors `.pin`, `.photo-thumb`, `.monthly-map svg polygon`, `.list .row`, `.f-pair img`, `.detail-head`, `.detail-head .pill`.
  - The 9 `getByRole` names used in `e2e/tests`.

## Proposed changes

| Page/component | Change | Reuse existing? | Dependencies | Risk |
|---|---|---|---|---|
| Tokens (`styles.css`, new `theme.ts`, colour values in `labels.ts` and `MapView.tsx`, `field.css`, `monthly.css`) | Semantic tokens; `--border-control`, `--border-control-inverse`, `--focus-inverse`, `--text-danger`, `--status-offline`; spacing scale; `--step--2`; Telugu line heights; print demo band (A6, A7, A14, A18) | Extends the current `:root` | None | Low |
| Field app root class (`FieldApp.tsx`, `field.css`) | `.field` renamed to `.field-app` (A9) | Yes | None. No test uses `.field` | Low |
| File pickers (`Records.tsx`, `FieldApp.tsx`, CSS) | `:focus-within` ring on the label (A5) | Yes | None | Low |
| `useAsync` and new `PageState` (`components/Bits.tsx`, new `components/PageState.tsx`, i18n) | `useAsync` also returns `loading` and `status`; one component for loading, error (with retry), forbidden, not-found and empty (A1) | Extends `useAsync` (same return fields plus new ones) | New i18n strings (wording test) | Medium: used by every page |
| Evidence image (`AuthImage` in `Bits.tsx`, `.pair` CSS) | Reserved square frame; loading and failed states with retry (A2); the comparison tick box is unchanged (D2) | Extends `AuthImage` | None | Low to medium |
| Table region (`Assets.tsx`, `Records.tsx`, `Audit.tsx`, CSS) | `.table-scroll` wrapper with label and edge fade (A3) | New small wrapper | i18n | Low |
| Form fields (CSS, `CaseFile.tsx` checklist) | Shared field styles for the checklist's select and input; row stacks below 900 px (A3, A13) | Yes | None | Low to medium (`check-*` IDs kept) |
| Shell (`Layout.tsx`, `App.tsx`, CSS, i18n) | Skip link; top bar below 760 px keeps name, language and sign-out; translated nav label; per-route `document.title`; focus to `h1` on route change; inverse focus ring (A3, A4, A12, A18) | Yes | i18n | Medium: every desk page |
| **Alert detail** (`AlertDetail.tsx`, `CaseFile.tsx`, `OfficerRecord.tsx`, `DatedBracket.tsx`, CSS) | Grid areas `head / decision / evidence / side`, with the decision panel early in the DOM; header with the badge below the title under 600 px; heading levels; focus in and out of action forms; date-strip labels kept inside; quiet style for "Request sharper imagery"; actions ordered forward first, closures after, utilities last (D1 approved; every action still rendered) (A3, A4, A8, A10, A11) | Yes | None | **Medium to high**: most e2e steps run here |
| Queue (`Queue.tsx`, `MapView.tsx`, CSS) | List before the map in the DOM, with grid areas putting the map on the left at 1100 px and wider; pins `tabindex=-1` and `aria-hidden` (still clickable); translated chip-group label; "Loading …" count; long names wrap (A1, A3, A4, A12) | Yes | None | Medium (`.pin`, `.list .row`, `alert-row-*`) |
| Assets | `aria-current` plus left rule for the selected row; heading moved out of the button; labelled count; page states (A1, A11, A12) | Yes | i18n | Low |
| Records | Import result shown as ok or stop; table region; file-picker focus (A3, A5, A13) | Yes | None | Low |
| Audit | Forbidden state for 403; event keys and items shown as i18n labels; hash shown as text; table region (A1, A3, A12) | Yes | i18n | Low |
| Monthly | i18next plurals ("1 day late"); print button busy and error states; page states (A1, A12, A17) | Yes | i18n | Low (`figure-*`, `print-monthly`) |
| Login | `main` landmark; inline styles moved to classes (A11, A13) | Yes | None | Low (`login-*`) |
| Field app | Loading state distinct from "No alerts assigned"; 44 px "Send now" and demo-switch targets; offline badge colour; link back from desk routes; sign-out in the header (D3 approved; uses the existing `logout()` from `auth.tsx`) (A1, A7, A15) | Yes | None | Low to medium (m6 offline tests) |
| Linting (`web/package.json`, `package-lock.json`, new `web/eslint.config.js`) | ESLint 9 flat config with `typescript-eslint`, `eslint-plugin-react-hooks` and `eslint-plugin-jsx-a11y`; a `lint` script; fix or justify each finding (D4 approved in part) | New dev dependencies only (no runtime change) | D4 | Low to medium: adds lockfile churn. Installed in a container, never in the OneDrive folder |

## Implementation sequence

1. **Phase 0: approval.** Done on 6 Nov 2026 (see "Owner decisions"). Next: create branch `uef/direction-a` from `main`.
2. **Phase 1: foundations and quick wins.**
   - Scope: tokens, control borders, inverse focus ring, danger text, offline badge colour, `.field` renamed to `.field-app`, file-picker focus, print demo band. No layout changes. Fixes A5, A6, A7, A9, A14 and A18.
   - Exit: contrast and focus figures re-measured with `audit.cjs`; wording test and full e2e green.
3. **Phase 2: shared patterns.**
   - Scope: `useAsync` status, `PageState`, evidence image, table region, shared form-field styles. Fixes A1, A2 and A3 (tables), plus A13 (forms).
   - Exit: each forced state (slow, 500, 403, 404, empty, failed image) shows its own screen.
4. **Phase 3: shell.**
   - Scope: skip link, narrow top bar with account controls, titles, route focus. Fixes A3 (sign-out) and A4.
   - Exit: sign-out and language reachable at 320 to 1440 px; titles per route.
5. **Phase 4: representative screen, alert detail.**
   - Scope: decision panel placement, header, headings, form focus, checklist stacking, date strip. Fixes A3, A4, A8, A10 and A11.
   - **Stop for owner review:** screenshots at 1440, 1280×720, 1024, 768 and 390 px in English and Telugu, for the analyst, nodal and legal roles. Continue only after approval.
6. **Phase 5: queue.** List-first DOM, pins out of the Tab order, loading count, long names.
7. **Phase 6: remaining desk pages.** Assets, Records, Audit, Monthly, Login. Fixes A11, A12, A13 and A17.
8. **Phase 7: field app.** Loading versus empty, targets, the desk dead end, and sign-out (D3). Fixes A1, A7 and A15.
9. **Phase 8: linting.** Add ESLint with `jsx-a11y` (D4); fix what it finds in the files changed by phases 1 to 7; record any rule turned off, and why. A16 (performance) stays open by decision.

## Progress

| Phase | Status | Branch / commit | Verification |
|---|---|---|---|
| 0 Approval | Done, 6 Nov 2026 | Branch `uef/direction-a` created from `main` at `ffc6ae8` | n/a |
| 1 Foundations and quick wins | **Implemented, not committed** (6 Nov 2026) | `uef/direction-a`, working tree | Build and type check pass. API 235 passed (wording scan included). Browser 14 of 14 passed. Re-measured against the baseline: text contrast failures 32 → 0, control-border failures 10 → 0; no change to overflow, headings or Tab order on any of 52 screens. Evidence: [`evidence/2026-11-06-phase1/`](evidence/2026-11-06-phase1/) |

| 2 Shared patterns | **Implemented, not committed** (7 Nov 2026) | `uef/direction-a`, staged | See phase 4 row (verified together) |
| 3 Shell | **Implemented, not committed** (7 Nov 2026) | `uef/direction-a`, staged | See phase 4 row |
| 4 Alert detail (representative screen) | **Implemented, not committed: waiting for the owner's review** (7 Nov 2026) | `uef/direction-a`, working tree | Build and type check pass. API 236 passed (the wording scan now includes `PageState.tsx`). Browser 14 of 14 passed. Baseline audit re-run: text contrast failures 32 → 0; control-border failures to 0; sideways scroll removed on all 6 narrow screens that had it. Decision panel in the first screen on all 30 review screens. Date strip: 240 renders (every demo alert, both languages, 1440 to 320 px) with no overlapping or escaping label. Evidence: [`evidence/2026-11-07-phase2-4/`](evidence/2026-11-07-phase2-4/) |

### Phase 4 review (owner)

The 30 screenshots are in [`evidence/2026-11-07-phase2-4/review/`](evidence/2026-11-07-phase2-4/review/), named `review-<role>-<language>-<width>x<height>.png`. They cover the analyst (`Demo Cheruvu 1`, waiting for review), the nodal officer (a confirmed alert) and the legal officer (`Demo Cheruvu 2`, with officer), each at 1440×900, 1280×720, 1024×768, 768×1024 and 390×844, in English and Telugu. Two full-page shots show the whole page at 1440 (analyst) and 390 (legal).

What to look for:
1. **Decision panel position.** At 1100 px and below it now sits directly under the header, above the images.
2. **Action order (D1).** "Confirm the change" comes before "Close as not real", and "Request sharper imagery" is now a quiet link.
3. **Header on phones.** The boundary badge sits under the title.
4. **Date strip.** On wide screens, the change window is one line above the axis. On narrow strips, the dated marks are a short list under the axis.

**Phases 2 to 4 notes.**
- **What changed:**
  - `useAsync` reports `loading` and `status`.
  - New `PageState` (loading, error with retry, forbidden, not found) and `TableRegion` (`components/PageState.tsx`).
  - `AuthImage frame` gives the image pair fixed frames with failure and retry.
  - Skip link, translated nav label, focus on `main` after navigation, and per-page titles.
  - Narrow top bar keeps name, language and sign-out.
  - On the alert detail, the decision panel moved into the grid and heading levels go `h1` then `h2`.
  - Action forms move focus to their heading and back to their button.
  - Checklist rows stack by column width (container queries).
  - The date strip was rewritten.
- **Found and fixed during QA:** at 390 px the legal officer's date strip overlapped two labels ("Watching since" and "Alert raised"). Marks are now sorted by date and drop to a second row when close; on narrow strips they become a list.
- **Preserved:**
  - Every `data-testid` and every class the tests select.
  - Exactly one button, select and input per checklist row.
  - The `actions` region has a single `role="status"`, and no extra `role="alert"` regions appear in normal use.
  - `allowed_actions` are all rendered.
  - The "I compared the before and after images" gate is unchanged (D2).
  - No API, auth, role or data changes.
- **Not yet done (later phases):**
  - The queue's long Tab path through the map pins (phase 5).
  - Field app loading state and sign-out (phase 7).
  - Raw audit event names and plurals (phase 6).
  - ESLint (phase 8).
- **Staging:** phases 1 to 3 are staged in git's index and phase 4 is in the working tree, so each phase can still become its own commit. Patches for each phase are kept for this session.

**Phase 1 notes.**
- **Changed files:** `web/src/styles.css`, `web/src/field/field.css`, `web/src/field/FieldApp.tsx` (root class only) and `web/src/bulletin/monthly.css`.
- **Extra fix from renaming `.field` (A9):** the field app's `.field` rule also enlarged every "With field team" state pill (`.pill.field`) from 13 px to 16.8 px. All six pill types now measure 13 px.
- **Deferred to phase 6 (A13):** `theme.ts`, which mirrors the colours used in JavaScript (MapLibre paint, `GROUP_COLOUR`, legends). Phase 1 kept to CSS.
- **Still open by design:** focus loss in action forms (A4, phase 4); failed images (A2, phase 2).
- **Known measurement quirk:** the generic `audit.cjs` heuristic still flags the two file inputs as "hidden focus", because it inspects the 1×1 input itself. `audit-p1.cjs` checks the label that now carries the ring: 3 px `--focus`.

## Acceptance criteria

- **Visual:**
  - Changed files use tokens, not new hex literals.
  - One primary button per context.
  - No panels inside panels.
  - The boundary badge, pills, demo band and image chips look the same as the baseline screenshots apart from the planned changes.
- **Functional:**
  - API tests pass (235 at baseline), including `test_wording.py` over every new string.
  - All 14 browser tests pass (m5 to m9), and the m9 walkthrough still makes no request outside localhost.
  - Every workflow listed under "Existing behaviour to preserve" works by hand on a fresh demo.
- **Responsive:**
  - No sideways page scroll from 320 px to 1440 px, except inside labelled table regions.
  - Sign-out and language are reachable at every width.
  - The decision panel is in the first screen of the alert detail at 1024×768 and 1280×720.
  - The Telugu layouts hold at 360 px (field) and 390 px (desk).
- **Accessibility:**
  - Text at least 4.5:1, or 3:1 for large text.
  - Control boundaries and focus rings at least 3:1 on every surface, including the rail.
  - Every Tab stop shows a visible ring.
  - Focus never lands on `<body>` after opening, cancelling or submitting a form.
  - Headings are sequential, there is a skip link, and each route has its own `document.title`.
  - Loading, error, forbidden and empty states are announced.
  - Measured with the baseline `audit.cjs`; `npm run lint` (with `jsx-a11y`) reports no errors.
- **Performance:**
  - No new runtime dependencies.
  - The JS bundle grows by no more than 10 KB (from 1,479,391 bytes).
  - No layout shift when the image pair loads (frames reserved).
  - The PWA settings and precache list are unchanged (D4).

## Verification and rollback

- **Isolated stack** (leaves the owner's demo data alone; `scripts/e2e.sh` would reset it):

  ```sh
  export LP_WEB_PORT=18180 LP_API_PORT=18100 LP_DB_PORT=15544
  docker compose -p lpaudit up -d --build --wait db api web
  docker compose -p lpaudit exec -T -e LP_ALLOW_RESET=true api python -m app.seed.reset
  docker compose -p lpaudit exec -T api pytest -q -p no:cacheprovider
  ```

- **Browser tests:** as `scripts/e2e.sh` does, against the isolated stack:
  - reset, then run m5-desk, m6-field, m7-evidence and m8-monthly;
  - reset again, then run m9-demo.

  Run them with `docker run --network container:lpaudit-web-1 lakeprotect-e2e:dev npx playwright test …`, mounting `e2e/tests` and `playwright.config.ts` read-only (the command is recorded in `UI_AUDIT.md`).
- **Before and after evidence:**
  - Re-run `docs/uef/evidence/2026-11-06-baseline/audit.cjs` and `audit2.cjs`. They are mounted at `/audit` and write to `/audit/out`.
  - Compare against the baseline screenshots and `measurements.json`: contrast failures, Tab sequences, overflow and states.
- **Lint** (phase 8 onward). The named volume keeps `node_modules` out of OneDrive:

  ```sh
  docker run --rm -v "$PWD/web:/app" -v lp_web_node_modules:/app/node_modules -w /app node:24-alpine \
    sh -c "npm ci --no-audit --no-fund && npm run lint"
  ```

- **Hand checks per phase:**
  - Keyboard-only run of the demo script steps that phase touches.
  - Telugu on the changed screens.
  - Print preview of the monthly page and one desk page.
- **Routes and viewports:** every route at 1440×900, 1280×720, 1024×768, 768×1024 and 390×844; field at 412×915 and 360×740.
- **Rollback:**
  - One commit per phase on `uef/direction-a`. Undo a phase with `git revert <commit>`, then `docker compose up -d --build web`.
  - No API, database or data changes are planned, so no data rollback is needed.
  - Tear down the isolated stack with `docker compose -p lpaudit down -v` (that project only).
