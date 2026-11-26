# GeoGuard Civic UI refresh

**Date:** 26 November 2026  
**Implementation branch:** `feat/geoguard-civic-ui-refresh`  
**Product:** GeoGuard (formerly Lake Protect)

## Design decision

Adopt the Civic Slate & Water-Ledger direction for the official desk. The visual language takes cues from shadcn/ui and 21st.dev—quiet surfaces, precise borders, compact controls, clear focus states and deliberate spacing—without importing a second component framework into the existing React application.

The current application is React 19, TypeScript, Vite, React Router and MapLibre, with English/Telugu support. The refresh keeps those foundations, existing route contracts, API calls, authorization checks, map interactions, citizen portal and PWA behaviour intact.

## Visual system

- Canvas `#f6f7f9`; raised surface `#ffffff`; subtle surface `#eef1f5`.
- Primary ink `#111827`; secondary ink `#475569`; muted ink `#64748b`.
- Civic teal `#0f4c5c` for navigation, links and primary actions.
- Confirmed `#135e29`; verify `#8a5300`; watch `#3730a3`; legal hold `#6b21a8`; SLA attention `#c2410c`.
- Noto Sans / Noto Sans Telugu remain self-hosted to preserve offline desk and Telugu rendering. Inter and JetBrains Mono are font-family preferences with system fallbacks; no external font request is introduced.
- Monospaced/tabular numerals are used for identifiers, hashes, coordinates and numeric evidence values.
- Boundary certainty continues to use line style as well as colour: solid, dashed and dotted.

## Information hierarchy

Every candidate review should make these facts easy to locate, in this order:

1. Boundary status, source and version.
2. Dated observation bracket: baseline, last clear observation and first changed observation, with policy cutoff where supplied by the API.
3. Physical change summary, imagery dates and sensor provenance.
4. Procedural incident state and recorded reviews.
5. Actions permitted by the existing server-provided `allowed_actions`.

The alert detail and Evidence Pack panel display the disclaimer:

> Imagery shows physical change. It does not establish title or legality.

Triage remains owner-blind. Personal owner/claimant names are not added to queues, maps or pre-confirmation screens.

## Product governance constraints

This design request does not authorize a workflow or backend contract change. In particular, it does not restore retired field-officer roles, two-person closure sign-offs, officer assignment, enforcement routing or escalation/SLA timers. The approved application model remains the two-role `admin` / `viewer` model and the OPEN → UNDER_REVIEW → CONFIRMED / DISMISSED → CLOSED lifecycle described in D-057.

The supplied ACTION / VERIFY / WATCH vocabulary is not fabricated from existing boundary fields. The UI may only show an operating mode once an authoritative API field and its policy mapping are defined. Until then, the boundary status/provenance and server-provided available actions remain explicit.

Government connectors continue to be labelled as templates, sample/file intake or not configured until authorization exists. The UI must not imply live government connectivity.

## Component and library policy

- Use existing React components and accessible native controls with shadcn-inspired styling.
- Use MapLibre for existing map and boundary workflows. deck.gl is not introduced until a measured rendering requirement justifies it.
- Do not add TanStack Table solely for styling; consider it when column pinning, complex grouping or server-side table state is required.
- Use 21st.dev patterns selectively as design references. Avoid animation-heavy blocks and marketing components.
- Keep transitions restrained (roughly 140 ms), respect reduced-motion preferences, and preserve keyboard navigation.

## Current implementation increment

- [x] Civic Slate semantic tokens and shared visual overrides.
- [x] Responsive workspace shell with grouped navigation, route context and account controls.
- [x] Consistent styling for buttons, forms, badges, panels, tables, map frames and evidence surfaces.
- [x] Prominent disclaimer on Alert Detail and Evidence Pack summary/preview.
- [ ] Page-by-page interaction and visual QA in English and Telugu at desktop, tablet and mobile widths.
- [ ] Confirm all existing E2E selectors and user journeys remain green.
- [ ] Further refine overview, queue, Asset 360, records, inbox and administration after visual QA.

## Acceptance criteria

- No backend, ML, data, database, auth or government connector contract changes.
- Existing API requests, role checks, routes, PWA/offline support and citizen portal continue to work.
- Boundary source/status and dated evidence remain visible; no premature legal conclusion or owner identity is introduced.
- Alert Detail and Evidence Pack preview always display the evidentiary disclaimer.
- Responsive at 390 px through wide desktop; no icon-only navigation or horizontal page overflow (except labelled table/map workspaces).
- English and Telugu layouts remain readable and keyboard accessible.
