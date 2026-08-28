<!--
Sync Impact Report
Version change: 1.3.0 → 1.4.0
Modified principles: none renamed or removed
Modified sections:
  - UI Design System Requirements → Screen contracts: the acceptance-reference
    prototype now exists in-repo at `specs/designs/` (four screens + README + vendored
    stylesheet), replacing the prior "not yet part of this repository" placeholder.
    Each screen bullet now names its concrete file, and the admin wizard's six steps
    are enumerated by name.
  - UI Design System Requirements → Design tokens & components: named the concrete
    vendored stylesheet (`specs/designs/styles.css`) and added a new rule limiting
    screen-local utility classes, both sourced from `specs/designs/README.md`'s
    implementer notes.
Added sections: none
Removed sections: none
Source: `specs/designs/` (README.md "Notes for implementers", styles.css, and the four
  screen files), added to the repo since the v1.3.0 amendment.
Templates requiring follow-up: none — dependent templates read this file at runtime and
  are not modified by this command.
Deferred/TODO placeholders: none.
Carried-forward note (from the v1.3.0 amendment, now resolved): the acceptance-reference
  prototype was previously absent from the repo; it has now been added at
  `specs/designs/` and is named below. The "story cannot be published without a
  completed test play" rule still needs reconciling into 005-story-publishing's
  functional requirements — see specs/designs/README.md's Gaps note — not addressed
  by this constitution-only command.
-->

# LLM Dungeon Adventure Constitution

## Core Principles

### I. Meaningful, Automated Testing (NON-NEGOTIABLE)
Every functionality and edge case MUST have a corresponding automated test before that
work is considered complete. Tests MUST exercise meaningful behavior, real failure modes,
and boundary/edge conditions — tests written merely to inflate a coverage number are
prohibited. There is NO 100% code coverage requirement or goal; coverage is a signal, not
a target. All tests MUST be fully automatable (no manual steps) and MUST run as part of
every pull request; a pull request MUST NOT be merged while any required test is failing.

Rationale: The team explicitly wants confidence from tests that verify real behavior,
not a coverage metric. Automating tests in the PR pipeline is the only way to enforce
this consistently as the game's dungeon logic, LLM interactions, and API surface grow.

### II. Secure-by-Default Access (NON-NEGOTIABLE)
The application MUST require sign-in via Microsoft Entra ID for every user-facing page
and every API endpoint — there is no public or anonymous access to any part of the
system, including status/health endpoints that reveal application details. Access MUST
be restricted to an explicit allow-list of specific Microsoft accounts; there is no
open sign-up or tenant-wide access by default. Authorization checks MUST be enforced
server-side in the Azure Functions backend; a client-side (ReactJS) check alone is never
sufficient, since it can be bypassed.

Rationale: The project is explicitly scoped as a private application for a specific,
named set of Microsoft accounts, not a public product. Server-side enforcement is
required because client-side gating is trivially bypassable.

### III. Defined Technology Stack
The backend MUST be implemented in Python and deployed as Azure Functions. The frontend
MUST be implemented in ReactJS and run in a standard web browser. Any deviation from
this stack (a different language, framework, or hosting model) requires a documented
justification and an amendment to this constitution before adoption.

Rationale: A fixed, agreed stack keeps the small initial build focused and avoids
architectural churn while the game's core mechanics are still being established.

### IV. Simplicity Over Premature Scale (YAGNI)
The project currently has no defined scale, performance, or throughput requirements.
Designs, infrastructure, and code MUST NOT be built to anticipate scale that has not
been specified. Prefer the simplest design that correctly satisfies the current, known
requirements; add scaling mechanisms only when a real, stated requirement calls for them.

Rationale: Building for hypothetical scale now would add complexity and cost with no
corresponding, documented need, and would slow down early iteration on gameplay and the
LLM-driven dungeon experience.

### V. Continuous Integration Gate
GitHub is the system of record for source code, and Azure is the exclusive cloud hosting
provider for this application. Every pull request MUST automatically trigger the full
automated test suite via CI. A pull request MUST be blocked from merging while the CI
test run has not passed.

Rationale: Automated, PR-gated testing (Principle I) is only effective if it is actually
enforced by the repository's merge process, not left to manual discipline.

### VI. Observability & AI Cost Transparency (NON-NEGOTIABLE)
The application MUST emit telemetry via OpenTelemetry as the instrumentation/collection
layer, with Azure Application Insights as the telemetry sink; no alternate collector or
sink may replace this pairing without a constitution amendment. Every LLM interaction
MUST be observable: the prompt sent and the response received MUST be captured in
telemetry, alongside per-prompt token usage (input/output), per-prompt cost, and
latency/performance data. This data MUST be queryable well enough to answer, at any
time, "what did our AI usage cost, and how well did it perform" without ad-hoc log
spelunking.

Rationale: LLM calls are both the core gameplay mechanism and the primary variable cost
of this project. Without structured, standardized telemetry, the team cannot track
runaway spend, diagnose slow or failing prompts, or reason about the dungeon experience
LLM users are actually getting.

### VII. Zero-Trust Azure Resource Communication (NON-NEGOTIABLE)
All authentication between Azure resources (e.g., Azure Functions calling Storage, Key
Vault, an LLM/AI service, Application Insights, or any other first-party Azure service)
MUST use Managed Identities, not shared keys, connection strings, or service principal
secrets, wherever the target service supports Managed Identity authentication. All
network connectivity between Azure resources MUST use Private Endpoints (or equivalent
private networking); public network access MUST be disabled on backend Azure resources
wherever a private connectivity path is available. Any exception (a service that
genuinely cannot use Managed Identity or Private Endpoints) MUST be explicitly
documented and justified.

Rationale: This is a backend where every dependency is a first-party Azure service, so
there is no reason to rely on long-lived secrets or public network paths between them —
doing so would needlessly widen the credential-leakage and network-exposure surface for
an application that is already required to have no public access (Principle II).

### VIII. UI Design System & Accessibility Compliance (NON-NEGOTIABLE)
The frontend MUST be built exclusively on this project's design-token layer and shared
component classes — no ad hoc colors, fonts, spacing, or one-off component
reimplementations. The interface MUST meet the visual, interaction-state, readability,
layout, and accessibility requirements detailed in the UI Design System Requirements
section below. Every implementation plan MUST include a Constitution Check confirming
these UI requirements are satisfied, or requesting an explicit, justified exception.

Rationale: This project's specs are built incrementally across many features (login,
story authoring, gameplay, save/continue); without a single enforced design system and
accessibility bar, screens built in different cycles would visually and behaviorally
drift apart, degrading the experience and making the interface harder to maintain.

## Security & Access Control Requirements

- Authentication MUST use Microsoft Entra ID; the frontend MUST use a supported
  Microsoft identity library (e.g., MSAL) to obtain tokens, and the Azure Functions
  backend MUST validate those tokens on every request.
- Authorization MUST be allow-list based: only specific, pre-approved Microsoft accounts
  may access the application. Adding or removing an account from the allow-list MUST be
  an explicit, auditable change (e.g., Entra ID app role assignment or an equivalent
  managed configuration), not an implicit or self-service action.
- No Azure Function endpoint may be configured with anonymous access; every endpoint
  MUST require an authenticated, authorized identity.
- Secrets and credentials (e.g., LLM API keys, Entra ID client secrets) MUST NOT be
  committed to the GitHub repository; they MUST be stored in Azure-managed configuration
  (e.g., Function App application settings or Key Vault references).
- The Azure Functions backend MUST authenticate to other Azure resources it depends on
  (Storage, Key Vault, the LLM/AI service, Application Insights, etc.) using a Managed
  Identity (system-assigned or user-assigned) rather than a stored key, connection
  string, or client secret, wherever that resource supports Managed Identity auth.
- Backend Azure resources MUST be connected via Private Endpoints for inter-resource
  traffic, with public network access disabled on those resources, unless a specific,
  documented exception applies.

## Observability & Telemetry Requirements

- Instrumentation MUST use OpenTelemetry (OTel) SDKs/APIs in both the Python (Azure
  Functions) backend and the ReactJS frontend; OTel is the collector layer.
- Azure Application Insights MUST be configured as the telemetry sink (traces, metrics,
  and logs) that OpenTelemetry data is exported to.
- Every call to an LLM MUST record: the full prompt sent, the full response received,
  input token count, output token count, computed cost for that call, and call latency,
  as structured telemetry (not free-text logs alone).
- Prompt/response telemetry MUST be attributable to a request/session so per-prompt cost
  and performance can be traced back to a specific player action.
- Aggregate views (e.g., Application Insights dashboards or workbooks) MUST be
  achievable from this telemetry to answer ongoing questions about total AI spend,
  token consumption trends, and LLM latency/error rates over time.
- Telemetry MUST NOT be used to bypass Principle II: captured prompts/responses are
  operational data and MUST remain within the same access-controlled Azure environment,
  not exposed publicly.

## Development Workflow & Quality Gates

- All changes MUST go through a pull request on GitHub; direct pushes to the main branch
  are not permitted.
- Every pull request MUST include automated tests for the functionality and edge cases
  it introduces or changes, per Principle I.
- CI MUST run the full automated test suite on every pull request, per Principle V; a
  failing run blocks merge.
- Code review by at least one other contributor is required before merge, focused on
  correctness, adherence to this constitution, and meaningful test quality (not just
  presence of tests).

## UI Design System Requirements

### Design tokens & components

- Every color, font, spacing, radius, and shadow value used in the frontend MUST come
  from the project's design-token layer (CSS custom properties, e.g. `--color-*`,
  `--font-*`, `--space-*`, `--radius-*`, `--shadow-*`); a literal hex value, a bare
  font-family name, or a magic pixel value that a token already covers is a review
  blocker.
- Components MUST be built from the design system's shared component
  classes/primitives (buttons, inputs, form fields, cards, navigation, tables, tags,
  dialogs, dividers, segmented controls); no parallel, screen-specific reimplementation
  of a control the system already provides.
- The design-token stylesheet MUST be vendored into the app as a single token layer;
  tokens are never re-derived, re-typed, or forked per screen. The current token
  source is `specs/designs/styles.css` (the "Modernist" design system) — copy it into
  the app unmodified, per `specs/designs/README.md`.
- A screen MUST NOT introduce a new component or visual-style class that duplicates
  something the design system already provides. A screen MAY introduce a small number
  of narrowly-scoped layout/behavior utility classes (e.g., a numeral treatment, a row
  hover tint, a scroll-container rule) that have no visual-design opinion of their own —
  everything else MUST be a design-system class or a token-based inline style.

### Non-negotiable visual rules

1. Zero corner radius — nothing in the interface is rounded.
2. Flush-left alignment — headings, body copy, and in-control labels start at the left
   padding edge; nothing is centered.
3. Section separation uses visible dividing rules, not whitespace alone.
4. The accent color is used sparingly — for the primary action, small emphasis, and at
   most one prominent field per surface; paragraph-size text never uses the raw accent
   color, only a darker, more legible variant of it.
5. Layout structure (grid, equal-width cells, consistent horizontal rhythm) stays
   visible rather than hidden behind whitespace.
6. Oversized numerals (e.g., a chapter number, a list index, a wizard step) are the one
   permitted expressive/playful typographic device in this design system; they remain
   type, not illustration — no illustration or emoji is used elsewhere in the product.
7. Photography is rendered in grayscale; imagery is never tinted or colorized.
8. Icons come from a single, consistent icon set, sized for interface use.

### Interaction states

Every interactive element MUST ship all four states, themed through the design
system — never left at browser defaults:

- Hover: an accent tint (or a mixed tint for outlined/ghost variants).
- Pressed: one step past the base/resting accent shade.
- Focus: a visible `:focus-visible` outline in the accent color with a small offset;
  a default browser focus ring (e.g., unstyled blue) fails review.
- Disabled: reduced opacity paired with a `not-allowed` cursor.

State styling lives in the shared design-system layer; individual screens MUST NOT
restyle these states locally.

### Readability & interaction requirements

1. Story/narrative prose renders at a minimum comfortable reading size, with generous
   line-height and modern text-wrapping for readability.
2. Interface labels never fall below a minimum legible size; any label styled below the
   body-text size threshold is rendered uppercase with letter-spacing to stay legible.
3. Touch and click targets meet a minimum size in their shorter dimension; the player's
   free-text instruction input is taller than a standard control, for comfortable use.
4. Player input MUST be interpreted forgivingly — the system does not require exact
   spelling or phrasing to act on an instruction; any correction is offered as a
   suggestion, never required, and never blocks the player's turn.
5. Suggested actions MUST always be available as an alternative to free-text typing, so
   a player can always proceed without composing their own sentence.
6. Player-facing copy is plain, warm, and concrete — no technical jargon or raw error
   codes shown to players, and every failure or dead-end state offers a next action
   rather than leaving the player stuck.
7. Player-facing surfaces MUST NOT use shaming language, artificial time pressure, or
   punitive UI patterns. This governs tone and interface pressure tactics only — it does
   not remove the game's own configured success/failure outcomes (see
   `008-core-gameplay`), which remain a legitimate, narratively-framed part of gameplay.

### Layout and scroll contract

1. The application shell is fixed to the viewport (no page-level scroll).
2. On the play surface, only the story pane scrolls; the title bar, instruction input,
   suggested actions, and status panel remain fixed and always reachable.
3. The story pane auto-scrolls to the newest turn.
4. Each primary application surface remains usable down to a defined minimum viewport
   width; below that floor, secondary panels (e.g., a status panel) collapse above the
   primary content rather than disappearing, and the input row stays pinned.

### Screen contracts

The prototype at `specs/designs/` is the acceptance reference for these screens' layout
and copy; this constitution wins on rules where the two disagree. It contains four
screens, a shared vendored stylesheet, and a README mapping each screen to the spec(s)
that govern its behavior (see `specs/designs/README.md`).

- **Login** (`specs/designs/01-login.html`) — Microsoft identity sign-in only,
  consistent with Principle II: no password field, no local accounts, no alternate
  identity provider.
- **Adventure select** (`specs/designs/02-story-select.html`) — in-progress adventures
  are listed first, showing progress and last-played information; not-yet-started
  (published) adventures follow after a visible divider; resuming an in-progress
  adventure is reachable in one action from its list row.
- **Play surface** (`specs/designs/03-play.html`) — a persistent title/status bar
  offering an explicit checkpoint-save action and a pause-and-exit action; a scrolling
  story pane; an instruction input paired with suggested actions; a status panel
  showing current location/goal/progress and a hint action. Exiting always goes through
  the pause screen — never an unconfirmed destructive action.
- **Administrator story-authoring wizard** (`specs/designs/04-admin-wizard.html`) — a
  six-step, administrator-facing flow whose steps (name & cover, world & setting, tone
  & reading level, session length, test play, publish & assign) are reachable in any
  order; the adventure's core premise and its content-safety configuration are required
  fields. A story MUST NOT be publishable (see `005-story-publishing`) until it has
  completed a test play.

### Save and session behaviour

1. Autosave after every turn is the default behavior and is stated to the player in the
   UI.
2. A manual save creates a named checkpoint and confirms visibly and briefly.
3. Exiting never loses a turn already taken; the pause/exit screen states where the
   game was saved.
4. Session length is configurable per adventure; the game offers a natural stopping
   point rather than abruptly cutting a player off.

### Accessibility

- Body copy meets at least a 4.5:1 contrast ratio against its background; interface
  chrome and large type meet at least 3:1. The raw accent color at its default value is
  roughly 3:1 and MUST NOT be used for paragraph-size text.
- Every surface is fully operable by keyboard alone, with a visible focus indicator at
  all times.
- Semantic HTML is used first: real form elements, real buttons, real labels; native
  controls are preferred over custom-built equivalents.
- Meaning is never carried by color alone — progress indicators, states, and tags pair
  color with text or an icon.

## Governance

This constitution supersedes any conflicting team practice, ad-hoc convention, or prior
informal agreement for this project. All pull requests and reviews MUST verify
compliance with the principles and requirements above; any added complexity (new
services, new infrastructure, deviation from the defined stack) MUST be explicitly
justified in the PR description.

Amendments to this constitution MUST be made via a pull request that updates this file,
states the rationale for the change, and is reviewed and approved before merge.
Versioning follows semantic versioning: MAJOR for backward-incompatible governance or
principle removals/redefinitions, MINOR for new principles or materially expanded
guidance, PATCH for clarifications and wording fixes. `LAST_AMENDED_DATE` MUST be
updated on every change that modifies this file's content.

Every implementation plan (`plan.md`) MUST include a Constitution Check section that
states how each UI Design System requirement is satisfied, or requests an explicit,
justified exception. A cross-artifact consistency analysis MUST treat a contradiction
with the design-token, visual-rules, interaction-state, or layout/scroll requirements
above as a blocking finding. No feature may ship a screen that is not traceable to a
screen contract above or to a documented amendment extending it.

**Version**: 1.4.0 | **Ratified**: 2026-08-28 | **Last Amended**: 2026-08-28
