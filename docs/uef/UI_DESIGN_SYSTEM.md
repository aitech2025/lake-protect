# UEF Project UI Design System

> **Status: APPROVED, Direction A** (owner, 6 Nov 2026). Not implemented yet; see `UI_IMPLEMENTATION_PLAN.md`.
> Inputs: `PROJECT_PROFILE.md`, `UI_AUDIT.md` (findings A1 to A18) and the UEF standards.
> Brand identity is kept: palette, Noto type, the boundary line language, the mark and the demo band.
> Every contrast figure was calculated with the WCAG formula.

## Design intent

- **Product personality:** a careful public-records clerk, not a surveillance console. Quiet, exact,
  and plain-spoken. It shows what is known, how sure it is, and who must act next. It never decides.
- **Audience:**
  - Senior officials in demos: glanceable, map and picture first, plain words. Often on a laptop or a
    1280×720 projector (assumption: check before the meeting).
  - Analysts, nodal and legal officers: dense desk work at 1280 to 1920 px.
  - Auditors: long tables.
  - Field officers: low-cost Android phones, outdoors, often offline, Telugu first.
- **Design principles:**
  1. **Certainty is visible.** The boundary line language (solid, dashed, dotted) and the state groups appear the same everywhere: badge, map, legend and list.
  2. **Never look empty when you are not.** Loading, failed, forbidden and empty are four different screens.
  3. **One next step.** Each context has one primary action, near where the decision is made. Closures are never the first or loudest button.
  4. **Evidence keeps its shape.** Image frames, dates and the statement hold their place while loading, on failure, in print and in Telugu.
  5. **Flat paper, few layers.** One level of panels on paper. Elevation only for things that float over maps.
  6. **Works in both languages, at every width, by keyboard.** No function disappears when the screen narrows.
- **Reference products** (for qualities, not looks): government records registers and survey sheets
  (line conventions, plain tables); the GOV.UK Design System (plain language, error and empty
  patterns, focus treatment); Ordnance Survey and Survey of India map legends (line style as meaning).
- **Patterns to avoid:**
  - Dark "command centre" dashboards and full-bleed satellite viewers (`CONTEXT.md` section 1 says not to build one).
  - KPI-card grids, gradients as decoration, and nested cards.
  - Icon-only controls.
  - Hover-only information.
  - Colour-only status.
  - Imagery that looks sharper than 10 m.
  - Any styling that implies a verdict (for example red "alarm" treatments on unverified changes).

## Directions considered

### Direction A: "Survey sheet, refined" (recommended)

Keep the current identity and skeleton, and make it complete and robust:
- a semantic token layer over the existing palette;
- one spacing scale;
- shared loading, error, forbidden and empty patterns;
- WCAG-compliant control borders and focus rings;
- a narrow-screen shell that keeps every function;
- on the alert detail, a **decision panel** that sits beside the evidence on wide screens and directly under the title on narrow ones.

```text
≥1100 px                                                   <1100 px
┌ Demo data  Fictional places, people and records ─────┐   ┌ Demo data ─────────────────┐
│RAIL│ All alerts / DEMO-2026-0019        ┌───────────┐ │   │ Alerts Assets … తెలుగు Sign out│
│    │ Demo Cheruvu 1                     │── Marked  │ │   │ Demo Cheruvu 1              │
│    │ [Waiting for review] Soil fill ·   │   ground v1│ │   │ [Waiting for review] Due 7 Nov│
│    │ 1.11 acre · Due 7 Nov 2026         └───────────┘ │   │ ── Marked on the ground v1  │
│    │ ┌Before────────┐┌After─────────┐ ┌Next step────┐ │   │ ┌Next step───────────────┐ │
│    │ │ pixel chip   ││ pixel chip   │ │[Confirm the │ │   │ │[Confirm the change]    │ │
│    │ └18 Oct 2026───┘└23 Oct 2026───┘ │ change]     │ │   │ │[Close as not real]     │ │
│    │ When the change happened ─────── │[Close as not│ │   │ └────────────────────────┘ │
│    │ Boundary and change (map)        │ real]       │ │   │ Before / After             │
│    │ Case-readiness checklist         └─────────────┘ │   │ When the change happened   │
│    │ Imagery shows physical change…   Case file       │   │ Boundary and change        │
│    │                                  Checks, History │   │ Checklist · Statement      │
└────┴──────────────────────────────────────────────────┘   │ Case file · Checks · History│
                                                           └────────────────────────────┘
```

- **For:**
  - Fixes all 18 audit findings with the smallest change to what people have already seen.
  - Small diff, low e2e risk (test IDs and the seven class selectors stay).
  - No new dependencies, and it lands before the officials' demo and M2/M3.
- **Against:**
  - The alert detail is still a long page of panels.
  - The link between the screen and the evidence-pack PDF stays implicit.

### Direction B: "Case file"

Reframe evidence screens as a dossier that mirrors the evidence pack (section 9.3):
- a **sticky case bar**: name, state, boundary badge, due date and the primary action;
- numbered sections in pack order (1 Boundary, 2 Dated image pair, 3 When it happened, 4 Field record, 5 Checklist, 6 Statement), separated by hairline rules instead of boxed panels;
- a narrow right "margin" for checks and history;
- the queue becomes a list-first **register** with a smaller map.

```text
┌ case bar (sticky) ─────────────────────────────────────────────────────────────┐
│ Demo Cheruvu 1  [Waiting for review]  ── Marked on the ground v1  Due 7 Nov  [Confirm the change] │
└────────────────────────────────────────────────────────────────────────────────┘
  1  Boundary ───────────────────────────────────  │ margin
  2  Dated image pair  [Before] [After] ─────────   │ What the system checked
  3  When the change happened ───────────────────   │ History
  4  Field record ───────────────────────────────   │
  5  Case-readiness checklist ───────────────────   │
  6  Imagery shows physical change. It does not establish title or legality.
```

- **For:**
  - The strongest expression of "your cases hold up": the same structure on screen and in the PDF officials receive.
  - Fewer containers; the primary action is always visible.
- **Against:**
  - A large restructure of `AlertDetail.tsx` and the queue.
  - Sticky bars cost scarce height at 1280×720 and on phones.
  - Numbered sections need a decision on which items count as "evidence".
  - More e2e and visual risk before the demo.
  - The register feel suits legal and audit users more than analysts triaging on a map.

### Considered and rejected: "Operations console"
A dark, map-dominant screen with floating panels. Rejected because it is the satellite-viewer product
`CONTEXT.md` rules out. It also prints and reads poorly outdoors, and it is the generic dashboard
look the UEF standards warn against.

### Recommendation
**Direction A.** It is the right risk level for a prototype heading into an officials' demo and the
detection milestones, and it keeps the existing identity. B's one idea that is actually a fix, the
action panel near the top, is part of A as the decision panel (audit A8). B can be revisited for the
alert detail after M3, when real cases exist to test the dossier structure against.

## Approved visual direction

**Direction A, "Survey sheet, refined"**, approved by the owner on 6 Nov 2026, with no changes requested.
It keeps the existing identity and completes it with semantic tokens, accessible control and focus
contrast, distinct page states, and narrow layouts that keep every function. The alert detail gets a
decision panel near the top. It suits a prototype heading into an officials' demo: it fixes every
audit finding with the least change to what people know, and with no new runtime dependencies.

Owner decisions that shape the components below:
- **D1, action order: approved.** Forward actions first, closures after, quiet utilities last. Presentation only.
- **D2, failed images: show the failure only.** The "I compared the before and after images" tick box behaves as it does today.
- **D3, field app sign-out: approved.**
- **D4, tooling:**
  - ESLint with `jsx-a11y`: approved.
  - Axe in e2e: not approved.
  - Font-subset trim and lazy MapLibre: not approved, so the PWA settings stay unchanged.

## Foundations (Direction A)

All tokens live in `web/src/styles.css` `:root`. Values used by JavaScript (MapLibre paint, pin
colours) are mirrored in one `web/src/theme.ts`, with a comment in each file pointing to the other.
`labels.ts` keeps its state-to-group **mapping** unchanged; only its colour values move to `theme.ts`.

### Colour

**Base palette (kept as is):**

| Token | Value | Usage |
|---|---|---|
| `--paper` | `#eef1ec` | Page background |
| `--sheet` | `#ffffff` | Panels, tables, inputs |
| `--ink` | `#1c2b33` | Text, primary buttons, rail, field header |
| `--ink-2` | `#4a5a62` | Muted text (6.29:1 on paper) |
| `--ink-3` | `#75848b` | Non-text only: control borders, ticks, dots (3.87:1 on sheet, 3.39:1 on paper) |
| `--rule` | `#d3dad4` | Decorative dividers only (no contrast role) |
| `--ftl` | `#1f6fa8` | Links, focus on light surfaces, confirmed boundary, "field" group |
| `--buffer` | `#c4402f` | Buffer line, overdue marks, "legal" group (non-text, or text on sheet only) |
| `--green` | `#2d7a57` | "Officer" group, online |
| `--amber` | `#b07219` | "Review" group, preliminary boundary (non-text) |
| `--violet` / `--violet-tint` | `#6e3fa3` / `#efe7f8` | Demo marking |

**Semantic layer (new; every pair meets WCAG AA):**

| Token | Value | Usage |
|---|---|---|
| `--surface-page` | `var(--paper)` | Page background |
| `--surface-raised` | `var(--sheet)` | Panels, tables, form fields |
| `--surface-sunken` | `#f4f6f3` | Table headers, row hover, notes (replaces three near-identical literals) |
| `--surface-inverse` / `--surface-inverse-2` | `var(--ink)` / `#26383f` | Rail, field header / rail hover and active |
| `--text` / `--text-muted` | `var(--ink)` / `var(--ink-2)` | Body / secondary text |
| `--text-on-inverse` | `#dfe7e3` | Rail text (11.56:1) |
| `--text-danger` | `#b8392a` **new** | Overdue flags, error text, danger buttons (5.04:1 on paper, 5.74:1 on sheet). Fixes A7 |
| `--border-control` | `var(--ink-3)` | Borders of inputs, selects, textareas, chips and secondary buttons (3.39:1 or better). Fixes A6 |
| `--border-control-inverse` | `#6c7f87` | Buttons on the rail and field header (3.48:1 on ink). Fixes A6 |
| `--focus` | `var(--ftl)` | Focus ring on light surfaces (4.73:1 on paper, 5.39:1 on sheet) |
| `--focus-inverse` | `#7fb6dd` **new** | Focus ring on rail and field header (6.68:1 on ink, 5.60:1 on active). Fixes A18 |
| `--status-offline` | `#9a6315` **new** | "No signal" badge behind white text (5.04:1). Fixes A7 |

**State groups** (queue bars, pills, map pins; the mapping in `labels.ts` stays the same):

| Group | Mark (pin, bar) | Pill background / text | Pill contrast |
|---|---|---|---|
| review | `#b07219` | `#fdf0d9` / `#6f4708` | 7.22:1 |
| field | `#1f6fa8` | `#dcebf6` / `#164f78` | 7.12:1 |
| legal | `#c4402f` | `#f6dfdb` / `#8c2c1f` | ≥7:1 |
| officer | `#2d7a57` | `#dbefe5` / `#1f5a40` | ≥7:1 |
| watch | `#6b5a91` | `#e7e4ef` / `#4b3a6e` | 7.86:1 |
| closed | `#8a979d` | `#eceeec` / `#4a5a62` | 6.15:1 |
| overdue | `var(--buffer)` | uses the `--text-danger` flag with the words "Overdue since …" | text, not colour |

Pins always keep their white ring and dark outline, so the closed grey (2.55:1 on the map
background) still has a visible edge. Pin meaning is also given by the list and labels.

**Feedback banners** (text always states the problem; colour supports it):

| Kind | Background / text / left rule | Role |
|---|---|---|
| info | `#dcebf6` / `#164f78` / `--ftl` | `status` |
| warn | `#fdf0d9` / `#6f4708` / `--amber` | `status` |
| stop (error, refusal) | `#f6dfdb` / `#8c2c1f` / `--buffer` | `alert` |
| ok | `#dbefe5` / `#1d5039` / `--green` | `status` |

**Demo and imagery exceptions:**
- **Demo band:** stripes `#6e3fa3` and `#5d3290` with white text (7.23:1 and 9.03:1).
  - **In print:** white background, `--violet` 2 px border and dark "Demo data" text. This works whether or not the browser prints backgrounds. Fixes A14.
- **Imagery overlay palette:** `--overlay-ftl #46a0ff`, `--overlay-buffer #e6463c`, `--overlay-change #ffd640`.
  - These are drawn on dark synthetic chips by the server, and they are deliberately brighter than the desk tokens.
  - Legends next to images use these values; legends next to the map use the map palette.
- **Map palette:** background `#f0ece2`, boundary `--ftl`, buffer `--buffer`, watch ring `--ink-3`, change fill `#e0a526` with line `#7a4f05`.

### Typography

Noto Sans with Noto Sans Telugu, self-hosted, weights 400, 600 and 700. No new fonts. Nothing below 12 px.

| Role | Font/token | Size | Weight | Line height |
|---|---|---|---|---|
| Page title (`h1`) | `--step-3` | 1.9rem (30.4 px) | 700 | 1.2 (Telugu 1.35; no negative letter-spacing in Telugu) |
| Section title (`h2`, `.title-m`) | `--step-2` | 1.4rem (22.4 px) | 700 | 1.25 (Telugu 1.4) |
| Panel title (`h2`/`h3` as structure requires, styled `.title-s`) | `--step-1` | 1.125rem (18 px) | 600 | 1.3 (Telugu 1.45) |
| Body | `--step-0` | 0.9375rem (15 px) | 400 | 1.5 (Telugu 1.65) |
| Meta, labels, table text | `--step--1` | 0.8125rem (13 px) | 400 or 600 | 1.45 (Telugu 1.6) |
| Micro: legends, map and date-strip labels, demo tag | `--step--2` **new** | 0.75rem (12 px) | 400 or 600 | 1.35 |
| Figures (monthly, priority) | `--step-figure` | 2.6rem, and `--step-2` for the priority score | 700, tabular numbers | 1 |
| Field body / field button | `--field-step-0` / `--field-step-1` | 1.0625rem (17 px) / 1.15rem | 400 / 700 | 1.5 (Telugu 1.65) |

**Rule:** heading **level** follows the page structure (`h1` page, `h2` panels, `h3` within a panel).
Visual size comes from the `.title-*` classes, so fixing the skipped levels (A11) does not change the look.

### Spacing and geometry

- **Spacing scale:**
  - `--space-1` 4 px, `--space-2` 8 px, `--space-3` 12 px, `--space-4` 16 px, `--space-5` 24 px, `--space-6` 32 px, `--space-7` 48 px.
  - Existing in-between values (0.35, 0.4, 0.6 and 1.25rem) snap to the nearest step.
  - Panel padding is `--space-4`, the gap between panels `--space-4`, and the gap between page sections `--space-5`.
- **Content max width:**
  - Desk page 1480 px (kept).
  - Running text, notes and the statement: 72ch.
  - Field app: 640 px.
  - Login: 980 px.
- **Grid and breakpoints** (from the content, and tested at the listed widths):

  | Width | Change |
  |---|---|
  | ≥1100 | Desk two-column layouts: queue map and list; detail evidence with a 380 px side column |
  | <1100 | Detail is one column, with the **decision panel directly under the header**; queue is one column with the **list first**, then the map |
  | <900 | Checklist edit rows stack (label above the controls row); monthly figures in 3 columns, then 2 below 600 |
  | <760 | The rail becomes a top bar: nav links on one row, and a second row with name, **language and sign-out (always visible)** |
  | <600 | Image pair stacks; detail header puts the boundary badge below the title |

  Test widths: 1440, 1280×720 (projector), 1024, 768, 390, and 360 for the field app.
- **Radius scale:** `--radius-s` 4 px (controls, pills, banners, badge), `--radius-m` 8 px (panels, figures, map frames, field cards), `--radius-pill` 999 px (filter chips only). No others.
- **Borders:** 1 px `--rule` for panel and table dividers; 1 px `--border-control` for controls; 2 px for emphasis (boundary badge, field cards and options, statement).
- **Elevation:** none on panels.
  - One level, `--shadow-float: 0 0 0 1px rgb(28 43 51 / .12), 0 1px 3px rgb(28 43 51 / .18)`, for map legends, pin labels and the field sync bar if it becomes sticky.
  - Map controls keep MapLibre's own styling.

## Components

Each component lists its variants, states, accessibility requirements and the test hooks it must keep.

| Component | Variants and states | Accessibility | Keep (tests and rules) |
|---|---|---|---|
| **Button** | primary (ink fill), secondary (sheet, `--border-control`), danger (sheet, `--text-danger` border and text), quiet (link style, for tertiary actions such as "Request sharper imagery"). States: hover, `:focus-visible`, active, disabled (0.45 opacity plus `aria-disabled` reason text). Minimum height 40 px on the desk, 48 to 56 px in the field app. | Text label always; one primary per context; disabled buttons explain why in adjacent text (`.why`) linked by `aria-describedby`. | `.btn`, every `data-testid` |
| **Decision panel** (the "Next step" actions) | Collapsed list of action buttons; one action expanded into an inline form. **Order (D1, approved): forward actions first, closures (`CLOSED_*`) after, quiet utilities last.** Every action in `allowed_actions` is still rendered, with the same label; only the order and weight change. | On opening, focus moves to the form's heading (`tabIndex=-1`); on cancel or submit, focus returns to the button that opened it. Errors use `role="alert"`; success uses `role="status"`. | `data-testid="actions"`, `action-*`, `form-*`, `submit-action`, `input-*`; renders exactly the `allowed_actions` it is given |
| **Form field** | Label above; input, select or textarea 40 px minimum (field app 48 px); help text; error text. | Every control is labelled; the error is linked by `aria-describedby`; border `--border-control`; focus ring 3 px `--focus` with 2 px offset. | `label.field` (desk), `.f-field` (field app) |
| **File picker** | A button-styled `<label>` wrapping a visually hidden `input[type=file]`. | `:focus-within` draws the focus ring on the label (A5); the chosen file count is announced via `role="status"`. | `photo-input`, Records import |
| **Checkbox and radio** | Native controls at 20 px, with the whole label as the target; field options are 52 px rows. | Native semantics; `fieldset` and `legend` for groups. | `input-reviewed`, `outcome-*`, `demo-no-signal` |
| **Filter chips** | Toggle buttons, pressed shown by ink fill. A group label is visible or set with `aria-label` (translated). | `aria-pressed`; the group has a translated label (A12). | `.chip`, `group-*` |
| **Status pill** | One per state group. | Text names the state; colour supports it. | `.pill`, `data-state`, `.detail-head .pill` |
| **Boundary badge** | Solid, dashed or dotted, as today. | Line style plus text. | `boundary-seal`, `data-certainty`; **visual unchanged** |
| **Demo band and demo tag** | Screen: striped. Print: bordered (see Colour). | `role="status"` kept; announced once per page. | `demo-badge`; shown whenever demo records are on screen |
| **Banner** | info, warn, stop, ok. | `role` per the table in Colour. | `.banner.*`, `.f-banner.*` |
| **Page state** **new** | `loading` (reserved layout with a "Loading …" text, no animation), `error` (stop banner, message, **Try again**), `forbidden` (403: "Your role cannot open this page." plus a link to the role's home page), `not-found` (404 plus a link back), `empty` (a plain sentence and the next step where one exists). | Loading text is in a `role="status"` region; errors use `role="alert"`; the page `h1` is always rendered. | Fixes A1. New strings must pass the wording test. |
| **Evidence image (image pair)** | A frame with the image's aspect ratio reserved before it loads; states loaded, loading ("Loading image …"), failed ("This image could not be loaded." plus **Try again**); the caption with its date is always shown. | `alt` with the formatted date; the failed state is announced. The comparison tick box is **unchanged** (D2: show the failure only). | Fixes A2. `.pair`, `image-pair`, `image-rendering: pixelated`, D-027 labels |
| **Panel** | One level on paper: title, body. No panels inside panels. | Title is a heading at the correct level. | `.panel`, `.section` |
| **Facts list** | `dl.facts`: two columns, stacking below 600 px. | Native `dl`. | `legal-panel` |
| **Data table** | Wrapped in a `.table-scroll` region (`role="region"`, translated `aria-label`, `tabindex="0"`), with a fade at the right edge when content overflows. Numbers are tabular and right-aligned. | Keyboard-scrollable; real `th` with `scope`. | Fixes A3. `table.grid`, `boundary-versions` |
| **Checklist row** | Read-only: status and item. Edit: item, then a row of select, reference and Save that **stacks below 900 px**. Uses the shared form-field styles (A13). | Each control labelled with the item name. | `check-*`, `checklist` |
| **Date strip** | Marks are kept inside the strip: anchors flip near the edges, and the two labels for the change stack when their dates are close or the screen is under 600 px. | Also exposed as text: "Changed between 18 Oct 2026 and 23 Oct 2026". | Fixes A10. `dated-bracket` |
| **Map frame** | Map plus a floating legend. Pins are **removed from the Tab order and hidden from assistive technology**, because the alert list gives the same targets. They stay clickable. | The map canvas keeps MapLibre's label; the legend is real text. | Fixes A4. `.pin`, `queue-map`, `detail-map` |
| **Navigation shell** | Rail at 760 px and wider; top bar below 760 px with account controls always visible; a **Skip to content** link first; per-route `document.title` ("Demo Cheruvu 1 · Alerts · Lake Protect"). | `nav` with a translated label; `main`; focus moves to the new page's `h1` on route change. | Fixes A3, A4. Nav visibility per role is **unchanged** (`NAV` in `Layout.tsx`) |
| **Field app shell** | Header (name, network badge, language, **sign-out**, approved under D3), sync bar, one column. Root class renamed from `.field` to `.field-app` (A9). | 44 px minimum targets; "Send now" at 44 px; the demo switch label gives a 44 px target. | `field-app`, `net-status`, `sync-now`, `queue-count` |

### Page-specific exceptions
- **Monthly page:** print-first, one A4 page; large tabular figures; no decision panel.
- **Field app:** its own larger type scale, full-width buttons, no hover effects, no rail; `f-` class prefix.
- **Login:** role cards stay as large buttons; gains a `main` landmark; inline styles move to classes.
- **Synthetic image chips:** pixelated, labels drawn by the server; never smoothed, scaled up beyond their pixels, or cropped.

## Interaction, motion and responsive rules

- **Focus:**
  - Every focusable element shows a 3 px ring: `--focus` on light surfaces, `--focus-inverse` on ink.
  - Focus never lands on `<body>` after an action. Inline forms move focus in, and return it to the opening button on close.
  - Route changes move focus to the new `h1`. Tab order follows the visual order (DOM order matches the layout areas).
- **Hover:** a background tint only (`--surface-sunken`, or `--surface-inverse-2` on the rail). Hover never carries information; for example, the audit hash in a `title` attribute becomes visible text or a disclosure.
- **Pressed and selected:** `aria-pressed` for toggles; `aria-current` for the selected asset and the current page. A selected row gets a 3 px left rule as well as its tint, so the selection never rests on colour alone (A11).
- **Loading:** reserved layout plus text; no spinners or shimmer; counts read "Loading …" and never "0" until data has arrived (A1).
- **Feedback:** messages appear next to the control that caused them; success uses `role="status"` and failure `role="alert"`; errors are never styled as info (A13).
- **Motion:** none beyond 120 ms colour and background transitions on hover and focus. The existing `prefers-reduced-motion` rule stays. Maps keep `duration: 0` fits.
- **Narrow screens:**
  - No function is hidden at any width (sign-out and language included).
  - Data tables scroll inside their own region; nothing else scrolls sideways.
  - Long names wrap, and never truncate an asset name without showing the full name.
- **Language:** layouts allow 40% longer Telugu strings; no fixed-width text boxes; no upper-case transforms; dates and numbers through `fmtDate` and i18next plurals.
- **Wording:** all new strings follow `CONTEXT.md` section 6.8 and are checked by `test_wording.py`. Telugu strings are drafts (D-028).

## Approved examples and change log

- **Representative screen (proposed): Alert detail, `/alerts/:id`.**
  - It appears in demo steps 2, 3, 5, 7 and 8.
  - It carries the most findings (A1, A2, A3, A4, A8, A10, A11), and it uses nearly every component above.
  - Once foundations are in place, it is the pilot that proves the direction. The queue follows.
- **Baseline screenshots:** [`evidence/2026-11-06-baseline/`](evidence/2026-11-06-baseline/).
- **Change log:**
  - 6 Nov 2026: Directions A and B proposed; A recommended. A18 (focus ring contrast on ink) found during design and added to the audit.
  - 6 Nov 2026: the owner approved Direction A. D1 reorder approved; D2 show failure only; D3 field sign-out approved; D4 ESLint with `jsx-a11y` approved, axe and the PWA changes not approved.
  - 7 Nov 2026: phases 1 to 4 implemented, with the alert detail as the representative screen; waiting for the owner's review. Three implementation details refine the component table:
    - **Date strip:** the change window is a single line above the axis, aligned towards the change. Dated marks are sorted by date, drop to a second row when closer than 24% of the strip, and become a list under the axis when the strip is narrower than 520 px.
    - **Decision panel:** after an action, focus moves to its result message.
    - **Failed evidence images:** the failure is announced with `role="status"` rather than `alert`, so it never competes with a form error.
