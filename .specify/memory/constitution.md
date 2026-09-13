# LLM Dungeon Adventure Constitution

## Core Principles

### I. Meaningful, Automated Testing (NON-NEGOTIABLE)
Every behavior and edge case MUST have an automated test before that work is complete.
Tests MUST exercise real behavior, real failure modes, and boundary conditions; tests
written to inflate a coverage number are prohibited. There is no coverage target — coverage
is a signal, not a goal.

Tests MUST be fully automated with no manual steps. Every pull request MUST automatically
trigger the full suite in CI and MUST be blocked from merging until that run passes. A
passing suite and a green CI run make a feature complete and mergeable.

Integration tests MUST run against a local stub or emulator of each external cloud
dependency they exercise (e.g. the Azure Cosmos DB emulator) rather than a live Azure
resource. A dependency with no viable stub MUST be named in that feature's plan with a
documented fallback — for example a narrowly scoped contract test against the live
resource, run only where unavoidable. As much testing as is practical MUST run locally; the
live environment is never a substitute for local automated testing.

Rationale: confidence comes from tests that verify real behavior, not from a metric, and
only a repository-enforced gate makes that consistent. The project keeps no test-only cloud
environment (Principle IV), so local stubs are the only way to keep integration tests both
fast and fully automated.

### II. Secure-by-Default Access (NON-NEGOTIABLE)
Every user-facing page and every API endpoint — including status and health endpoints that
reveal application detail — MUST require Microsoft Entra ID sign-in. Nothing is anonymous.
Access MUST be limited to an explicit allow-list of Microsoft accounts; there is no open
sign-up and no tenant-wide access. Authorization MUST be enforced server-side in the Azure
Functions backend; a client-side check alone is never sufficient.

One exception: a dedicated automation identity MAY bypass interactive sign-in for local
automated tests, under the guardrails in Security & Access Control Requirements. That
bypass MUST NOT be reachable, configurable, or present as code or configuration in the live
environment.

Rationale: this is a private application for a named set of accounts, and client-side
gating is trivially bypassed. Requiring interactive sign-in on every local test run would
make Principle I impractical, so a strictly local, non-deployable bypass is permitted
instead of weakening live authentication.

### III. Defined Technology Stack
The backend MUST be Python deployed as Azure Functions; the frontend MUST be ReactJS
running in a standard web browser. Any deviation — a different language, framework, or
hosting model — requires a documented justification and a constitution amendment before
adoption. New code MUST target the latest LTS major of each runtime (Node.js for frontend
tooling, Python for the backend) and the latest stable major of each core framework (e.g.
React) at the time it is written; the project MUST NOT knowingly adopt or stay pinned to a
major approaching end-of-support while a current one is available.

Rationale: a fixed stack keeps the build focused, and starting from current majors avoids
accumulating a forced, disruptive migration later.

### IV. Right-Sized Scope — YAGNI, Not Enterprise-Grade (NON-NEGOTIABLE)
This is a small application for a specific, named set of users, not an enterprise product,
and MUST NOT be designed or specified as one. It has no defined scale, performance, or
throughput requirements: designs, infrastructure, and code MUST NOT anticipate scale that
has not been specified, and MUST prefer the simplest design that satisfies the current
stated requirements. Add a scaling mechanism only when a stated requirement calls for one.

A spec, plan, or task MUST NOT introduce an enterprise-grade pattern — single sign-on or
federated identity beyond the mandated Entra ID allow-list (Principle II), multi-tenant
architecture, any persistent environment beyond local development and the single live one,
role or permission hierarchies beyond the allow-list's roles, or dedicated scaling and
high-availability infrastructure — unless a concrete, stated requirement calls for it.
Where work starts trending toward such a pattern, the author (human or AI) MUST stop and
ask the requesting user whether it is actually needed rather than assuming it or silently
including it.

Rationale: enterprise defaults are reached for out of habit and quietly inflate scope,
cost, and complexity for a project with neither the user base nor the requirements to
justify them.

### V. Observability & AI Cost Transparency (NON-NEGOTIABLE)
Telemetry MUST be collected through OpenTelemetry and exported to Azure Application
Insights; replacing either half of that pairing requires an amendment. OpenTelemetry MUST
instrument both the Python backend and the ReactJS frontend, and Application Insights MUST
be the sink for traces, metrics, and logs.

Every LLM call MUST record — as structured telemetry, not free-text logs — the full prompt,
the full response, input and output token counts, computed cost for that call, and latency.
Each MUST be attributable to a request or session, so cost and performance trace back to a
specific user action, and the telemetry MUST support aggregate views of total spend, token
consumption trends, and latency and error rates over time. Captured prompts and responses
are operational data and MUST remain inside the same access-controlled Azure environment;
telemetry MUST NOT become a way around Principle II.

Rationale: LLM calls are both the core mechanism and the primary variable cost. Without
structured telemetry the team cannot track runaway spend, diagnose slow or failing prompts,
or reason about the experience users actually get.

### VI. Zero-Trust Azure Resource Communication (NON-NEGOTIABLE)
Authentication between Azure resources (Functions to Storage, Key Vault, the LLM service,
Application Insights, or any other first-party Azure service) MUST use Managed Identities —
never shared keys, connection strings, or service principal secrets — wherever the target
service supports Managed Identity. Connectivity between backend Azure resources MUST use
Private Endpoints or equivalent private networking, with public network access disabled
wherever a private path is available. Any exception MUST be documented and justified.

Rationale: every dependency here is a first-party Azure service, so long-lived secrets and
public network paths would needlessly widen the credential-leakage and network-exposure
surface of an application already required to have no public access (Principle II).

### VII. UI Design System & Accessibility Compliance (NON-NEGOTIABLE)
The frontend MUST be built exclusively on this project's design-token layer and shared
component classes — no ad hoc colors, fonts, spacing, or one-off reimplementations of a
component the system already provides. The interface MUST meet the visual, interaction-
state, readability, layout, and accessibility requirements in UI Design System
Requirements.

Rationale: this project's screens are built incrementally across many features; without one
enforced design system and accessibility bar, screens built in different cycles drift apart
visually and behaviorally and become harder to maintain.

### VIII. PII Protection by Design (NON-NEGOTIABLE)
Personally identifiable information — a real person's email address, name, phone number,
physical address, or any other data identifying a specific individual — MUST live only in
an access-controlled store: the application's database (e.g. Cosmos DB), Azure Key Vault,
or an equivalent managed secret store. A feature MAY persist PII only where its
specification explicitly requires it and secures it there.

PII MUST NOT appear in the GitHub repository, in commit messages, in issues, pull request
descriptions or comments, or in logs, traces, or telemetry — and more broadly on any
surface where this project's output could become publicly accessible or durably retained
beyond the team's control, CI logs and published artifacts included. Where such a surface
must discuss a record involving PII, it MUST reference that record indirectly — a role, an
internal identifier, or a phrase such as "the seed administrator's entry". Test data,
fixtures, seed data, and documentation MUST use synthetic values.

Rationale: GitHub issues, pull requests, and commit history are broadly accessible,
retained indefinitely, and not access-controlled the way the application's own stores are.
PII posted there cannot reliably be un-published.

### IX. Implementer Design Latitude (Non-Blocking)
For a feature with a user-facing UI, the implementing agent or team MAY proceed straight to
implementation on its own design judgment, guided by the design system (Principle VII) and
its own spec. A pre-implementation mockup or sign-off from the requesting user or product
owner is NOT required and MUST NOT be used to block or delay implementation. A task list
MAY include a design walkthrough as an optional, non-blocking checkpoint.

Rationale: the team has chosen speed toward an MVP over getting the design right first
time, accepting that rework surfaces later through use. Principle VII still constrains
whatever is built, regardless of who approved the layout.

### X. AI Agent Division of Labor: Agents Push & Open PRs, Humans Merge (NON-NEGOTIABLE)
A local AI coding agent MAY write code, run local tests, and perform all spec-related work
— intake, specify, clarify, plan, tasks, analyze. Spec-related work MUST stay local; it
MUST NOT be delegated to a GitHub-side review agent.

Work MUST start from a synced tree. Before any development or spec-related work begins on a
branch, that branch MUST be brought up to date with `origin/main` — `git fetch origin`, then
a fast-forward, merge, or rebase. A conflict MUST be resolved on the branch by whoever is
doing the work, preserving both sides' intent, never discarding one side to clear it. Where
an artifact states that code already exists — a module path, symbol, constant, field,
endpoint, or configuration value — that statement MUST match `origin/main`, read from the
synced tree or from `origin/main` directly (e.g. `git show origin/main:<path>`). Identifiers
an artifact proposes to create are exempt; a dependency on unmerged work MUST be named as
such rather than described as already landed.

Once local work is ready, the agent MUST push the branch and open the pull request itself
(e.g. `gh pr create`), carrying the `AI Generated` label and a label naming the agent, and
linking to no session or transcript of its own. Before pushing, the agent MUST confirm the
state of any pull request associated with that branch (e.g. `gh pr view <branch> --json
state`): where that pull request is merged or closed the agent MUST NOT push, even though
the push would succeed, but MUST branch off current `main` and open a new pull request.
Pushing to a branch whose pull request is still open is permitted, and is the normal way to
address review feedback.

An agent MUST NOT merge a pull request or enable auto-merge on one, by any route — not
`gh pr merge`, not a REST call (`gh api --method PUT .../merge`), not a GraphQL
`mergePullRequest` mutation — regardless of what any tool's configuration happens to permit.
The pull request MUST instead go through the review pass required by Development Workflow &
Quality Gates, triggered explicitly by the requesting user or by the agent when asked, never
automatically on push. That review posts findings; it produces no approving review and does
not merge. The requesting user reads those findings together with the required checks, then
merges manually. Writing the fix, pushing the branch, and opening the pull request are
not restricted by this rule; only the GitHub-side merge is.

An agent MAY resolve a GitHub issue end to end as ordinary local development work. It MAY
close an issue (e.g. `gh issue close`) only where the requesting user has asked it to close
that issue and it has verified the resolving work is merged to `origin/main`, and it MUST
state what it verified. Absent that, the issue is closed by its pull request merging or by
the requesting user; an agent MUST NOT close one on its own initiative.

Rationale: a pull request opened by an automation identity through a GitHub Actions workflow
is treated as an outside contributor's, so its checks sit pending a manual approval click
every time; opening it as the developer's own authenticated action avoids that gate. Merging
stays manual because that is where the decision to accept a change is made, and a
findings-only review pass would otherwise let a change land with nobody having weighed it.
Reusing a merged or closed pull request's branch hides new work, since that PR is no longer
in anyone's review queue.

### XI. Artifacts and Code Stay Clean — Git Is the History
A feature's spec artifacts (`spec.md`, `plan.md`, `research.md`, `data-model.md`,
`quickstart.md`, `tasks.md`, and anything else under that feature's folder) record
decisions, not the history of decisions. A line or two of rationale beside a decision is
fine; multiple lines of narrative explaining why a decision was made or reversed are NOT
permitted — that belongs in the commit message or pull request description. A superseded
decision MUST be edited in place, carrying at most a short note (e.g. "Supersedes: <old
approach>, <why in under 15 words>"), never a retained explanation of the old decision
beside the new one.

Source code comments follow the same restraint. A comment MAY note a short, non-obvious
reason for a line (e.g. a workaround for a specific external constraint) but MUST NOT
narrate what the code does, restate implementation detail the governing spec already
documents, or record how the implementation reached its current form.

This constitution is held to the same standard: it states the rules in force and carries no
record of its own amendments.

Rationale: these are working documents read repeatedly, and narrative about past reversals
buries the decision actually in force. Git already preserves that reasoning at the commit
that made it.

## Security & Access Control Requirements

- The frontend MUST obtain tokens through a supported Microsoft identity library (e.g.
  MSAL), and the backend MUST validate that token on every request.
- Authorization MUST be allow-list based. Adding or removing an account MUST be an explicit,
  auditable change — an Entra ID app role assignment or equivalent managed configuration —
  never an implicit or self-service action.
- No Azure Function endpoint may be configured with anonymous access.
- Secrets and credentials (LLM API keys, Entra ID client secrets) MUST NOT be committed to
  the repository; they MUST live in Azure-managed configuration (Function App settings or
  Key Vault references).
- Application code and design MUST follow OWASP Top 10 practices appropriate to the stack:
  input validation and output encoding, parameterized data access, sound authentication and
  session handling, an access-control check at every server-side entry point, secure default
  configuration, and safe handling of dependencies with known vulnerabilities. This is a
  baseline proportionate to the project's size, not enterprise security tooling.
- The local automation bypass (Principle II) MUST be gated by a build-time or deploy-time
  condition structurally absent from the live environment's build and deploy configuration —
  for example a code path wired in only for local test runs — never a runtime environment
  variable or request header alone, since either could be misconfigured or spoofed against
  the live deployment. Live sign-in and server-side authorization MUST have no disable path,
  flag, or override of any kind.
- The automation identity MUST carry no real user's credentials and MUST NOT correspond to a
  real Microsoft account on the live allow-list.
- Any change touching the automation bypass or the Entra ID sign-in and authorization path
  MUST receive the deepest review tier, with the reviewer explicitly confirming the bypass
  remains unreachable from the live environment.

## Dependency & Supply Chain Requirements

- Dependencies (Python packages, npm packages, GitHub Actions, container base images) MUST
  come only from official public registries and marketplaces, MUST be pinned by a committed
  lockfile (`requirements.txt` / `poetry.lock`, `package-lock.json`) so builds are
  reproducible, and MUST NOT sit on a version carrying a known, unpatched critical or
  high-severity vulnerability when a fixed version exists.
- Automated dependency vulnerability scanning (GitHub Dependabot or equivalent) MUST be
  enabled on the repository. A critical or high-severity advisory affecting a dependency in
  use MUST be remediated — upgraded, patched, or accepted with a documented exception —
  never silently ignored.
- This is a proportionate baseline, not an enterprise supply-chain program: no SBOM
  generation and no third-party vendor security review unless a concrete, stated
  requirement calls for one.

## Development Workflow & Quality Gates

- All changes MUST go through a pull request. No work of any kind happens on `main`, and
  direct pushes to it are not permitted.
- This repository merges exclusively by squash, so the PR title — not any commit message —
  becomes the sole commit on `main` and is what semantic-release reads. Every PR title MUST
  follow Conventional Commits, `type(scope): description`, and MUST pass the required
  `check-title` status check. The allowed `type` and `scope` values live in
  `scripts/pr-title-config.js`; scope is required on every title, even one whose scope never
  gates a version bump.
- Every pull request MUST have a review pass before merge, covering correctness, compliance
  with this constitution, and meaningful test quality rather than the mere presence of tests.
  That pass is performed by an AI review agent on the pull request (Principle X); this
  project has one maintainer, so a second contributor's approving review is unavailable and
  the repository ruleset accordingly requires zero approving reviews. Skipping the pass — an
  emergency fix, say — MUST be called out explicitly by the person directing the work.
- Review depth MUST be chosen deliberately rather than defaulted to, weighing blast radius
  first, then diff size, then how the change was authored. A change touching authentication,
  secrets, permissions, CI/CD, deployment, infrastructure, persisted-data schema, release
  machinery, or this constitution and the agent instruction files that mirror it MUST
  receive the deepest review available, whatever its size.
- A pull request description MUST carry the account of the change that survives to `main`:
  the problem it addresses and the evidence for it, what was decided and why, what was
  actually tested and what that returned, what is deliberately left undone, and the review
  tier being recommended. It MUST NOT claim a check that was not run, quote a measurement
  that was not taken, or assert an approving review.
- A cross-artifact consistency analysis MUST treat as blocking any statement that code
  already exists — a module path, symbol, constant, field, or endpoint — where that code is
  absent from `origin/main` and is not declared as a named, not-yet-merged dependency
  (Principle X). Identifiers an artifact proposes to create are not findings.
- Work MAY run in the primary checkout, in a git worktree, or in a devcontainer; none of
  those is ever required or refused. A session MAY read and edit anywhere in the repository
  it is working in, including another checkout or worktree, and MAY switch branches as the
  work requires; uncommitted work MUST be committed or stashed before a switch that would
  otherwise carry or lose it.
- A worktree MUST live at `.worktrees/<branch>`, its directory name spelling out its branch
  name exactly; the container identity and the lifecycle tools key off that equality.
- Worktrees and branches MUST be pruned once their pull request is merged, and merge MUST be
  determined from GitHub's record of that pull request (`bin/wt-prune`), never from git
  ancestry — squash merging means a merged branch's tip is never an ancestor of `main`, so
  every ancestry test reports merged work as unmerged. Pruning MUST NOT remove a worktree
  holding uncommitted or untracked work, or a branch whose pull request is open, closed
  unmerged, or absent.
- A worktree whose copy of this constitution is behind `origin/main` SHOULD be synced before
  work continues in it, since it is otherwise governed by superseded rules (`bin/wt-sync`
  reports this). Staleness is a warning, not a block.

## Environments & Deployment Pipeline

- GitHub is the system of record for source code; Azure is the exclusive cloud host.
- There are exactly two places code is built and tested: a contributor's local machine and
  the single live environment in Azure. The project MUST NOT stand up an additional
  persistent environment — staging, UAT, QA — without a documented requirement and a
  constitution amendment (Principle IV).
- The only path from a merged change to the live environment is a GitHub Actions workflow;
  there is no manual or portal deployment path for application code.
- Credentials and configuration needed by deployment workflows MUST be stored as GitHub
  Actions secrets or environment secrets and variables, never committed to the repository.
- CI (build and test) and CD (deploy to live) both run as GitHub Actions workflows, and a
  deployment MUST NOT deploy a change that has not passed the required CI checks.

## UI Design System Requirements

### Design tokens & components

- Every color, font, spacing, radius, and shadow value MUST come from the design-token layer
  (CSS custom properties: `--color-*`, `--font-*`, `--space-*`, `--radius-*`, `--shadow-*`).
  A literal hex value, a bare font-family name, or a magic pixel value that a token already
  covers is a review blocker.
- Components MUST be built from the design system's shared classes and primitives (buttons,
  inputs, form fields, cards, navigation, tables, tags, dialogs, dividers, segmented
  controls); a screen MUST NOT reimplement a control the system already provides, or
  introduce a component or visual-style class duplicating one.
- The token stylesheet — the "Modernist" design system — MUST live in the app as a single
  layer, never re-derived, re-typed, or forked per screen. A screen that needs a token the
  layer lacks extends that one layer; it does not keep its own copy.
- A screen MAY introduce a small number of narrowly scoped layout or behavior utility
  classes with no visual-design opinion of their own (a numeral treatment, a row hover tint,
  a scroll-container rule); everything else MUST be a design-system class or a token-based
  inline style.

### Non-negotiable visual rules

1. Zero corner radius — nothing in the interface is rounded.
2. Flush-left alignment — headings, body copy, and in-control labels start at the left
   padding edge; nothing is centered.
3. Section separation uses visible dividing rules, not whitespace alone.
4. The accent color is used sparingly — the primary action, small emphasis, and at most one
   prominent field per surface. Paragraph-size text never uses the raw accent color, only a
   darker, more legible variant.
5. Layout structure (grid, equal-width cells, consistent horizontal rhythm) stays visible
   rather than hidden behind whitespace.
6. Oversized numerals (a step number, a list index, a section number) are the one permitted
   expressive typographic device; they remain type, not illustration. No illustration or
   emoji appears elsewhere in the product.
7. Photography is rendered in grayscale; imagery is never tinted or colorized.
8. Icons come from a single, consistent icon set, sized for interface use.

### Interaction states

Every interactive element MUST ship all four states, themed through the design system and
never left at browser defaults. State styling lives in the shared design-system layer;
screens MUST NOT restyle these locally.

- Hover: an accent tint, or a mixed tint for outlined and ghost variants.
- Pressed: one step past the base accent shade.
- Focus: a visible `:focus-visible` outline in the accent color with a small offset. A
  default browser focus ring fails review.
- Disabled: reduced opacity paired with a `not-allowed` cursor.

### Readability & interaction requirements

1. Long-form reading prose renders at or above the design system's body text size, with its
   line-height or greater, and modern text wrapping (`text-wrap: pretty` or equivalent).
2. An interface label rendered below the body text size MUST be uppercase with
   letter-spacing.
3. Touch and click targets MUST be at least 24x24 CSS px (WCAG 2.5.8).
4. User-facing copy is plain, warm, and concrete — no technical jargon or raw error codes —
   and every failure or dead-end state offers a next action.
5. The interface MUST NOT use shaming language, artificial time pressure, or punitive UI
   patterns. This governs tone and interface pressure only, never what outcomes a feature
   may legitimately produce.

### Layout and scroll contract

1. The application shell is fixed to the viewport, with no page-level scroll, at desktop and
   tablet widths without exception. Below the mobile breakpoint a screen MAY switch to
   page-level scrolling instead, provided every fixed-viewport surface above that breakpoint
   still honors this rule unchanged.
2. Where a screen scrolls one region within that fixed shell, the chrome around it —
   headers, input rows, side panels — stays fixed and reachable rather than scrolling away.
3. Every primary surface MUST remain usable down to a 320 px viewport width. Below that
   floor, secondary panels collapse above the primary content rather than disappearing, and
   any persistent input row stays pinned.

### Accessibility

- Body copy meets at least a 4.5:1 contrast ratio against its background; interface chrome
  and large type meet at least 3:1. The raw accent color at its default value is roughly
  3:1 and MUST NOT be used for paragraph-size text.
- Every surface is fully operable by keyboard alone, with a visible focus indicator at all
  times.
- Semantic HTML comes first: real form elements, real buttons, real labels. Native controls
  are preferred over custom equivalents.
- Meaning is never carried by color alone — progress indicators, states, and tags pair color
  with text or an icon.

## Governance

This constitution supersedes any conflicting team practice, convention, or prior informal
agreement for this project. Every pull request and review MUST verify compliance with it,
and any added complexity — a new service, new infrastructure, a deviation from the defined
stack — MUST be explicitly justified in the pull request description.

Amendments MUST be made through a pull request that updates this file, states the rationale
for the change, and passes the review gate before merge. Versioning is semantic: MAJOR for
backward-incompatible governance or principle removals and redefinitions, MINOR for a new
principle or section or materially expanded guidance, PATCH for clarifications and wording
fixes. The Last Amended date MUST be updated on every change to this file's content. What
changed and why belongs in that pull request, not in this file.

Every implementation plan (`plan.md`) MUST include a Constitution Check stating how each UI
Design System requirement is satisfied or requesting an explicit, justified exception. A
cross-artifact consistency analysis MUST treat a contradiction with the design-token,
visual-rules, interaction-state, or layout and scroll requirements as a blocking finding.

What a screen is for, which affordances it offers, which entry points reach it, and which
business rules it enforces are its feature spec's to state and to change. This constitution
takes no position on any of them, and a spec that scopes one of them out is making an
ordinary product decision, not seeking an amendment.

**Version**: 10.0.0 | **Ratified**: 2026-08-28 | **Last Amended**: 2026-09-13
