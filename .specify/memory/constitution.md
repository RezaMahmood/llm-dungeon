<!--
Sync Impact Report
Version change: 8.1.0 -> 9.0.0
Modified principles: XIII (AI Agent Division of Labor) — the sync requirement is kept but
  no longer forbids reading another checkout; the division of labor, the merge prohibition
  and the issue-closing conditions are unchanged.
Modified sections:
  - Development Workflow & Quality Gates: the session-isolation requirement ("A session
    MUST NOT read or write another session's checkout or worktree") is REMOVED, and the
    worktree/container bullets are restated as tools a contributor may use rather than a
    separation anyone must maintain. The constitution-staleness gate is downgraded from a
    block to a warning.
  - Principle XIII and AI Agent / GitHub Handoff Requirements: the requirement that an
    artifact's claims about existing code match `origin/main` is unchanged, but it is now
    stated as an accuracy rule about the trunk rather than a ban on reading other
    branches, worktrees or checkouts.
Added sections: none.
Removed sections: the session-isolation requirement (see above).
Rationale for MAJOR: a governance requirement is withdrawn, not clarified. Concurrent
  multi-session work is no longer a project requirement — work is taken one bug or feature
  at a time — so the isolation rule and the hooks enforcing it were blocking ordinary
  work (a session unable to edit after a branch change, unable to resolve a conflict
  locally, or forced into a container for a one-line change) while protecting against a
  collision that no longer occurs. Worktrees and containers survive as options; only their
  compulsory, enforced separation is gone.
Deferred/TODO placeholders: none.
Earlier Sync Impact Reports are in this file's git history.
--># LLM Dungeon Adventure Constitution

## Core Principles

### I. Meaningful, Automated Testing (NON-NEGOTIABLE)
Every behavior and edge case MUST have an automated test before that work is complete.
Tests MUST exercise real behavior, real failure modes, and boundary conditions; tests
written to inflate a coverage number are prohibited. There is no coverage target —
coverage is a signal, not a goal. Tests MUST be fully automated with no manual steps,
MUST run on every pull request, and a pull request MUST NOT merge while a required test
is failing. Integration tests MUST run locally against stubs or emulators of external
cloud dependencies rather than live Azure resources (see Environments & Deployment
Pipeline). As much testing as is practical MUST run locally; the live environment is not
a substitute for local automated testing.

Rationale: confidence comes from tests that verify real behavior, not from a metric, and
only a PR-gated suite enforces that consistently. The project maintains no test-only
cloud environment (Principle XII), so local stubs are the only way to keep integration
tests both fast and fully automated.

### II. Secure-by-Default Access (NON-NEGOTIABLE)
Every user-facing page and every API endpoint — including status and health endpoints
that reveal application detail — MUST require Microsoft Entra ID sign-in. Nothing is
anonymous. Access MUST be limited to an explicit allow-list of Microsoft accounts; there
is no open sign-up and no tenant-wide access. Authorization MUST be enforced server-side
in the Azure Functions backend; a client-side check alone is never sufficient. The one
exception: a dedicated automation identity MAY bypass interactive sign-in for local
automated tests, under the guardrails in Security & Access Control Requirements. That
bypass MUST NOT be reachable, configurable, or present as code or configuration in the
live environment.

Rationale: this is a private application for a named set of accounts, and client-side
gating is trivially bypassed. Requiring interactive sign-in on every local test run would
make Principle I's fast, frequent local testing impractical, so a strictly local,
non-deployable bypass is permitted instead of weakening live authentication.

### III. Defined Technology Stack
The backend MUST be Python deployed as Azure Functions; the frontend MUST be ReactJS
running in a standard web browser. Any deviation — a different language, framework, or
hosting model — requires a documented justification and a constitution amendment before
adoption. New code MUST target the latest LTS major of each runtime (Node.js for frontend
tooling, Python for the backend) and the latest stable major of each core framework
(e.g. React) at the time it is written; the project MUST NOT knowingly adopt or stay
pinned to a major approaching end-of-support while a current one is available.

Rationale: a fixed stack keeps the build focused while core mechanics are still being
established, and starting from current majors avoids accumulating a forced, disruptive
migration later.

### IV. Simplicity Over Premature Scale (YAGNI)
The project has no defined scale, performance, or throughput requirements. Designs,
infrastructure, and code MUST NOT anticipate scale that has not been specified. Prefer
the simplest design that correctly satisfies the current stated requirements; add a
scaling mechanism only when a stated requirement calls for one.

Rationale: building for hypothetical scale adds complexity and cost against no documented
need, and slows early iteration on gameplay.

### V. Continuous Integration Gate
GitHub is the system of record for source code; Azure is the exclusive cloud host. Every
pull request MUST automatically trigger the full automated test suite in CI, and MUST be
blocked from merging until that run passes.

Rationale: PR-gated testing (Principle I) is only effective if the repository enforces it
rather than leaving it to manual discipline.

### VI. Observability & AI Cost Transparency (NON-NEGOTIABLE)
Telemetry MUST be collected through OpenTelemetry and exported to Azure Application
Insights; replacing either half of that pairing requires an amendment. Every LLM
interaction MUST be observable — prompt sent, response received, input and output token
counts, computed cost, and latency — captured as structured telemetry that can answer, at
any time, "what did our AI usage cost, and how well did it perform" without ad-hoc log
spelunking. Detail: Observability & Telemetry Requirements.

Rationale: LLM calls are both the core gameplay mechanism and the primary variable cost.
Without structured telemetry the team cannot track runaway spend, diagnose slow or failing
prompts, or reason about the experience players actually get.

### VII. Zero-Trust Azure Resource Communication (NON-NEGOTIABLE)
Authentication between Azure resources (Functions to Storage, Key Vault, the LLM service,
Application Insights, or any other first-party Azure service) MUST use Managed Identities
— never shared keys, connection strings, or service principal secrets — wherever the
target service supports Managed Identity. Connectivity between backend Azure resources
MUST use Private Endpoints or equivalent private networking, with public network access
disabled wherever a private path is available. Any exception MUST be documented and
justified.

Rationale: every dependency here is a first-party Azure service, so long-lived secrets and
public network paths would needlessly widen the credential-leakage and network-exposure
surface of an application that is already required to have no public access
(Principle II).

### VIII. UI Design System & Accessibility Compliance (NON-NEGOTIABLE)
The frontend MUST be built exclusively on this project's design-token layer and shared
component classes — no ad hoc colors, fonts, spacing, or one-off reimplementations of a
component the system already provides. The interface MUST meet the visual, interaction-
state, readability, layout, and accessibility requirements in UI Design System
Requirements. Every implementation plan MUST include a Constitution Check confirming
those requirements are satisfied or requesting an explicit, justified exception.

Rationale: this project's screens are built incrementally across many features; without
one enforced design system and accessibility bar, screens built in different cycles drift
apart visually and behaviorally and become harder to maintain.

### IX. *(Retired in v7.0.0 — see Sync Impact Report)*
This number governed manual/user-verified testing as part of feature completion. The
project now handles that entirely outside the speckit workflow, so this constitution takes
no position on it — neither requiring it nor guaranteeing it is non-blocking. The number
stays retired, unreassigned, rather than renumbering Principles X–XIV, so their existing
external references keep resolving.

### X. PII Protection by Design (NON-NEGOTIABLE)
Personally identifiable information — a real person's email address, name, phone number,
physical address, or any other data identifying a specific individual — MUST live only in
a secure, access-controlled store: the application's database, Azure Key Vault, or an
equivalent managed secret store. PII MUST NOT appear in the GitHub repository, in commit
messages, in issues, pull request descriptions or comments, or in application logs,
traces, or telemetry. Where such a surface must discuss a record involving PII, it MUST
reference that record indirectly — a role, an internal identifier, or a phrase such as
"the seed administrator's entry". Detail: PII & Data Protection Requirements.

Rationale: GitHub issues, pull requests, and commit history are broadly accessible and
retained indefinitely, and are not access-controlled the way the application's own stores
are. PII posted there cannot reliably be un-published, which defeats the point of
restricting where that data may live.

### XI. Implementer Design Latitude (Non-Blocking)
For a feature with a user-facing UI, the implementing agent or team MAY proceed straight
to implementation on its own design judgment, guided by the design system and screen
contracts (Principle VIII, UI Design System Requirements). A pre-implementation mockup or
sign-off from the requesting user or product owner is NOT required and MUST NOT be used to
block or delay implementation. A task list MAY include a design walkthrough as an optional,
non-blocking checkpoint at the author's discretion.

Rationale: the team has chosen speed toward an MVP over getting the design right on the
first attempt, accepting that design rework surfaces later, through use outside this
workflow, rather than up front. Principle VIII still constrains whatever is built to this
project's design system, token layer, and accessibility bar, regardless of who approved the
layout.

### XII. Right-Sized Scope — Not Enterprise-Grade (NON-NEGOTIABLE)
This is a small application for a specific, named set of users, not an enterprise product,
and MUST NOT be designed or specified as one. A spec, plan, or task MUST NOT introduce an
enterprise-grade pattern — including single sign-on or federated identity beyond the
mandated Entra ID allow-list (Principle II), multi-tenant architecture, any persistent
environment beyond local development and the single live one (Environments & Deployment
Pipeline), role or permission hierarchies beyond the allow-list's roles, or dedicated
scaling and high-availability infrastructure — unless a concrete, stated requirement calls
for it. Where work starts trending toward such a pattern, the author (human or AI) MUST
stop and ask the requesting user whether it is actually needed rather than assuming it or
silently including it.

Rationale: enterprise defaults are reached for out of habit and quietly inflate scope,
cost, and complexity for a project with neither the user base nor the requirements to
justify them. This turns Principle IV's general YAGNI stance into an enforced process
check for the patterns most likely to be assumed rather than requested.

### XIII. AI Agent Division of Labor: Agents Push & Open PRs, Humans Merge (NON-NEGOTIABLE)
A local AI coding agent MAY write code, run local tests, and perform all spec-related
work — intake, specify, clarify, plan, tasks, analyze. Spec-related work MUST stay local:
it MUST NOT be delegated to a GitHub-side review agent.

Work MUST start from a synced tree. Before any development or spec-related work begins on
a branch — planning, tasks, clarify, and analyze included, not implementation alone — that
branch MUST be brought up to date with `origin/main`. A conflict with `origin/main` MUST
be resolved on the branch, by whoever or whatever is doing the work, rather than worked
around or deferred; resolving it MUST preserve both sides' intent, never discard one side
to clear the conflict. Where an artifact states that code already exists — a module path,
symbol, constant, field, endpoint, or configuration value — that statement MUST match
`origin/main`, not an unmerged branch or a stale local `main`. Identifiers an artifact
proposes to create are exempt; a dependency on unmerged work MUST be named as such rather
than described as already landed.

Once local work is ready, the agent MUST push the branch and open the pull request itself
(e.g. `gh pr create`), labelled per AI Agent / GitHub Handoff Requirements. Every push of
new work MUST be visible as its own open pull request: an agent MUST NOT push follow-up
commits onto the branch of a pull request that has already been merged or closed, even
where that branch still exists and the push would succeed. Such work MUST go onto a fresh
branch behind a new pull request.

An agent MUST NOT merge a pull request and MUST NOT enable auto-merge on one, by any
route, even where it has the technical means. The pull request MUST instead go through the AI
review pass required by Development Workflow & Quality Gates, triggered explicitly by the
requesting user or by the agent when asked — never automatically on push. That review
posts findings; it does not produce a formal approving review and does not merge. The requesting user or product owner
MUST read those findings together with the required CI and status checks, then merge
manually.

An agent MAY resolve a GitHub issue end-to-end — writing the fix, pushing the branch, and
opening the pull request — as ordinary local development work. An agent MAY close a GitHub
issue (e.g. `gh issue close`) only where the requesting user has asked it to close that
issue and it has verified the resolving work is merged to `origin/main`. Absent that, the
issue is closed by its pull request merging or by the requesting user; an agent MUST NOT
close one on its own initiative.

Rationale: a pull request opened by an automation identity through a GitHub Actions
workflow is treated as an outside contributor's, so its checks sit pending a manual
"approve and run workflows" click every time; having the agent open the PR as the
developer's own authenticated action avoids that gate, while the GitHub-side review pass
still applies consistently whichever local tool pushed the branch. Merging stays manual
because that is where the decision to accept a change is made, and a findings-only review
pass would otherwise let a change land with nobody having weighed it. Closing an issue is
not the same act: it records a decision a human already made at merge, so an agent may do
it on request once the fix is on the trunk. Reusing a merged or closed pull request's
branch hides new work, since that PR is no longer in anyone's review queue. Syncing before
work is the root prevention for artifacts that assert identifiers existing only on an
unmerged branch: once the branch carries `origin/main`, reading the tree is reading the
trunk.

### XIV. Spec Artifacts and Code Stay Clean — Git Is the History
A feature's spec artifacts (`spec.md`, `plan.md`, `research.md`, `data-model.md`,
`quickstart.md`, `tasks.md`, and anything else under that feature's `specs/` folder)
record decisions, not the history of decisions. A line or two of rationale beside a
decision is fine; multiple lines of narrative explaining why a decision was made or
reversed are NOT permitted — that belongs in the commit message or pull request
description. A superseded decision MUST be edited in place, carrying at most a short note
(e.g. "Supersedes: <old approach>, <why in under 15 words>"), never a retained explanation
of the old decision beside the new one.

Source code comments follow the same restraint. A comment MAY note a short, non-obvious
reason for a line (e.g. a workaround for a specific external constraint) but MUST NOT
narrate what the code does, restate implementation detail the governing spec already
documents, or record how the implementation reached its current form.

This constitution's own Sync Impact Report is the single exception, and it carries only
the current amendment; earlier reports live in git history.

Rationale: spec artifacts are working documents read repeatedly through a feature's life,
and narrative about past reversals buries the decision actually in force. Git already
preserves that reasoning at the commit that made it. The same holds for code: a comment
restating the spec drifts out of sync with it as the code evolves.

## Security & Access Control Requirements

- The frontend MUST obtain tokens through a supported Microsoft identity library (e.g.
  MSAL), and the Azure Functions backend MUST validate that token on every request.
- Authorization MUST be allow-list based. Adding or removing an account MUST be an
  explicit, auditable change — an Entra ID app role assignment or equivalent managed
  configuration — never an implicit or self-service action.
- No Azure Function endpoint may be configured with anonymous access.
- Secrets and credentials (LLM API keys, Entra ID client secrets) MUST NOT be committed to
  the repository; they MUST live in Azure-managed configuration (Function App settings or
  Key Vault references).
- Backend authentication to Azure dependencies and private connectivity between them are
  governed by Principle VII.
- Application code and design MUST follow OWASP Top 10 practices appropriate to the stack:
  input validation and output encoding, parameterized data access, sound authentication and
  session handling, an access-control check at every server-side entry point, secure default
  configuration, and safe handling of dependencies with known vulnerabilities. This is a
  baseline proportionate to the project's size, not enterprise security tooling
  (Principle XII).
- The local automation bypass (Principle I, Principle II) MUST be gated by a build-time or
  deploy-time condition that is structurally absent from the live environment's build and
  deploy configuration — for example a code path wired in only for local test runs — never a
  runtime environment variable or request header alone, since either could be misconfigured
  or spoofed against the live deployment. Live sign-in and server-side authorization MUST
  have no disable path, flag, or override of any kind.
- The automation identity MUST carry no real user's credentials and MUST NOT correspond to a
  real Microsoft account on the live allow-list. It exists only so local automated tests can
  exercise authorized-user code paths without an interactive sign-in.
- Any change touching the automation bypass or the Entra ID sign-in and authorization path
  MUST receive the deepest review tier (Development Workflow & Quality Gates), with the
  reviewer explicitly confirming the bypass remains unreachable from the live environment.

## Dependency & Supply Chain Security Requirements

- Dependencies (Python packages, npm packages, GitHub Actions, container base images) MUST
  come only from official public registries and marketplaces, MUST be pinned by a committed
  lockfile (`requirements.txt` / `poetry.lock`, `package-lock.json`) so builds are
  reproducible, and MUST NOT sit on a version carrying a known, unpatched critical or
  high-severity vulnerability when a fixed version exists.
- Automated dependency vulnerability scanning (GitHub Dependabot or equivalent) MUST be
  enabled on the repository. A critical or high-severity advisory affecting a dependency in
  use MUST be remediated — upgraded, patched, or accepted with a documented exception —
  never silently ignored.
- Runtime and framework major versions follow Principle III.
- This is a proportionate baseline for a small application's supply chain, not an
  enterprise supply-chain program: no SBOM generation and no third-party vendor security
  review unless a concrete, stated requirement calls for it (Principle XII).

## PII & Data Protection Requirements

Principle X fixes where PII may live and which surfaces it MUST NOT reach. These are its
specifics:

- The permitted stores are the application's database (e.g. Cosmos DB), Azure Key Vault, or
  an equivalent managed secret store.
- Test data, fixtures, seed data, and documentation MUST use synthetic values, never a real
  person's actual information.
- General-purpose logs, traces, and telemetry MUST NOT capture a user's email, name, or
  other identifying data. A feature MAY persist PII only where its specification explicitly
  requires it and secures it within an access-controlled store.
- The rule reaches every surface where this project's output could become publicly
  accessible or durably retained beyond the team's control — issue tracker, CI logs,
  published artifacts, external documentation — not just the repository's commit history.

## Observability & Telemetry Requirements

- OpenTelemetry SDKs and APIs MUST instrument both the Python (Azure Functions) backend and
  the ReactJS frontend.
- Azure Application Insights MUST be the sink for traces, metrics, and logs.
- Every LLM call MUST record the full prompt, the full response, input token count, output
  token count, computed cost for that call, and latency, as structured telemetry rather
  than free-text logs.
- Prompt and response telemetry MUST be attributable to a request or session, so cost and
  performance trace back to a specific player action.
- The telemetry MUST support aggregate views (Application Insights dashboards or workbooks)
  of total AI spend, token consumption trends, and LLM latency and error rates over time.
- Captured prompts and responses are operational data and MUST remain inside the same
  access-controlled Azure environment; telemetry MUST NOT become a way around Principle II.

## AI Agent / GitHub Handoff Requirements

Principle XIII fixes the division of labor. These are its mechanics, and they govern
GitHub-side actions only — they do not change where code is written or tested.

- A pull request an agent opens MUST carry the `AI Generated` label and a label naming the
  agent that produced it, MUST NOT link to the agent's own session or transcript, and MUST
  NOT have auto-merge enabled.
- Before pushing to a remote branch, an agent MUST confirm the state of any pull request
  associated with it (e.g. `gh pr view <branch> --json state`). If that pull request is
  merged or closed, the agent MUST NOT push; it MUST branch off the current main and open a
  new pull request, labelled as above. Pushing to a branch whose pull request is still open
  is permitted and is the normal way to address review feedback.
- The merge prohibition covers every route, not only `gh pr merge`: enabling auto-merge, a
  REST call (`gh api --method PUT .../merge`), and a GraphQL `mergePullRequest` mutation are
  equally prohibited, and the rule holds regardless of what any tool's configuration happens
  to permit. Writing the fix, pushing the branch, and opening the pull request are not
  restricted by this rule; only the GitHub-side merge is.
- When an agent closes an issue under Principle XIII's two conditions, it MUST state what it
  verified. Where either condition fails, it MUST leave the issue open and say why.
- Syncing a branch before spec-related work means `git fetch origin` followed by a
  fast-forward, merge or rebase of `origin/main` into the branch, resolving any conflict
  in the process. Existing code an artifact describes MUST then be read from that synced
  tree or from `origin/main` directly (e.g. `git show origin/main:<path>`), so that what
  it asserts is true of the trunk rather than of one branch's unmerged state.
- Skipping the review pass — for instance an emergency fix — MUST be called out explicitly
  by the person directing the work. It is never a default agent behavior.

## Development Workflow & Quality Gates

- All changes MUST go through a pull request; direct pushes to `main` are not permitted.
- This repository merges exclusively by squash, so the PR title — not any commit message —
  becomes the sole commit on `main` and is what semantic-release reads. Every PR title MUST
  follow Conventional Commits format, `type(scope): description`, and MUST pass the required
  `check-title` status check. The allowed `type` and `scope` values live in
  `scripts/pr-title-config.js` (mirrored into `.github/workflows/pr-title-check.yml`);
  scope is required on every title, even one whose scope never gates a version bump.
- Every pull request MUST include automated tests for the functionality and edge cases it
  changes (Principle I), and CI MUST run the full suite on it (Principle V); a failing run
  blocks merge.
- Every pull request MUST have a review pass before merge, covering correctness, compliance
  with this constitution, and meaningful test quality rather than the mere presence of
  tests. That pass is performed by an AI review agent on the pull request (Principle XIII);
  this project has one maintainer, so a second contributor's approving review is
  unavailable and the repository ruleset accordingly requires zero approving reviews.
  Review depth MUST be chosen deliberately rather than defaulted to, weighing blast radius
  first, then diff size, then how the change was authored. A change touching
  authentication, secrets, permissions, CI/CD, deployment, infrastructure, persisted-data
  schema, release machinery, or this constitution and the agent instruction files that
  mirror it MUST receive the deepest review available, whatever its size.
- A pull request description MUST carry the account of the change that survives to `main`:
  the problem it addresses and the evidence for it, what was decided and why, what was
  actually tested and what that returned, what is deliberately left undone, and the review
  tier being recommended. It MUST NOT claim a check that was not run, quote a measurement
  that was not taken, or assert an approving review.
- A passing test suite and a green CI run make a feature complete and mergeable. This
  constitution does not require, or forbid, any manual or user-verified testing step beyond
  that; where the project wants one, it happens outside the speckit workflow.
- A cross-artifact consistency analysis MUST treat as blocking any statement that code
  already exists — a module path, symbol, constant, field, or endpoint — where that code is
  absent from `origin/main` and is not declared as a named, not-yet-merged dependency
  (Principle XIII). Identifiers an artifact proposes to create are not findings.
- Work MAY run in the primary checkout, in a git worktree (`bin/wt <branch>`), or in a
  devcontainer. No branch type requires any of them, and none is refused any of them; the
  choice is the contributor's per session, never a precondition for working. Worktrees and
  containers remain useful for keeping more than one piece of work in flight, but the
  project takes work one bug or feature at a time and requires no separation between
  sessions.
- A session MAY read and edit anywhere in the repository it is working in, including
  another checkout or worktree, and MAY switch branches as the work requires. Uncommitted
  work MUST be committed or stashed before a switch that would otherwise carry or lose it.
- No work of any kind happens directly on `main`.
- A worktree that is created MUST live at `.worktrees/<branch>`, its directory name spelling
  out its branch name exactly; the container identity and the lifecycle tools key off that
  equality.
- Worktrees and branches MUST be pruned once their pull request is merged, and merge MUST be
  determined from GitHub's record of that pull request (`bin/wt-prune`), never from git
  ancestry — squash merging means a merged branch's tip is never an ancestor of `main`, so
  every ancestry test reports merged work as unmerged. Pruning MUST NOT remove a worktree
  holding uncommitted or untracked work, or a branch whose pull request is open, closed
  unmerged, or absent.
- A worktree whose copy of this constitution is behind `origin/main` SHOULD be synced
  before work continues in it, since it is otherwise governed by superseded rules;
  `bin/wt-sync` reports this, and a MAJOR-version gap is reported prominently. Staleness is
  a warning, not a block: syncing the branch is the fix, and refusing to start the session
  that would do the syncing helps nobody.
- See `docs/WORKTREE_CONTAINER_WORKFLOW.md` for how worktrees and containers work when a
  session uses them; that document describes an option, not a required workflow.

## Environments & Deployment Pipeline

- There are exactly two places code is built and tested: a contributor's local machine
  (including a worktree's devcontainer, where one is used) and the single live environment
  in Azure.
  The project MUST NOT stand up an additional persistent environment — staging, UAT, QA —
  without a documented requirement and a constitution amendment (Principle XII).
- The only path from a merged change to the live environment is a GitHub Actions workflow;
  there is no manual or portal deployment path for application code.
- Credentials and configuration needed by deployment workflows MUST be stored as GitHub
  Actions secrets or environment secrets and variables, never committed to the repository.
- CI (build and test) and CD (deploy to live) both run as GitHub Actions workflows, and a
  deployment MUST NOT deploy a change that has not passed the required CI checks.
- Automated integration tests MUST run against a local stub or emulator of each external
  cloud dependency they exercise (e.g. the Azure Cosmos DB emulator) instead of a live Azure
  resource (Principle I). A dependency with no viable stub MUST be called out explicitly in
  that feature's plan, with a documented fallback — for example a narrowly scoped contract
  test against the real live resource, run only where unavoidable.

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
- The token stylesheet MUST be vendored into the app as a single layer, never re-derived,
  re-typed, or forked per screen. Its source is `specs/designs/styles.css` (the "Modernist"
  design system), copied in unmodified per `specs/designs/README.md`.
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
6. Oversized numerals (a chapter number, a list index, a wizard step) are the one permitted
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

1. Story and narrative prose renders at or above the design system's body text size, with
   its line-height or greater, and modern text wrapping (`text-wrap: pretty` or equivalent).
2. An interface label rendered below the body text size MUST be uppercase with
   letter-spacing.
3. Touch and click targets MUST be at least 24x24 CSS px (WCAG 2.5.8). The player's
   free-text instruction input is taller than a standard control.
4. Player input MUST be interpreted forgivingly: exact spelling or phrasing is never
   required to act on an instruction, and any correction is offered as a suggestion that
   never blocks the player's turn.
5. Suggested actions MUST always be available alongside free-text typing, so a player can
   proceed without composing a sentence.
6. Player-facing copy is plain, warm, and concrete — no technical jargon or raw error codes
   — and every failure or dead-end state offers a next action.
7. Player-facing surfaces MUST NOT use shaming language, artificial time pressure, or
   punitive UI patterns. This governs tone and interface pressure only; the game's own
   configured success and failure outcomes (`008-core-gameplay-done`) remain a legitimate,
   narratively framed part of gameplay.

### Layout and scroll contract

1. The application shell is fixed to the viewport; there is no page-level scroll.
2. On the play surface only the story pane scrolls; the title bar, instruction input,
   suggested actions, and status panel stay fixed and reachable.
3. The story pane auto-scrolls to the newest turn.
4. Every primary surface MUST remain usable down to a 320 px viewport width. Below that
   floor, secondary panels (e.g. the status panel) collapse above the primary content rather
   than disappearing, and the input row stays pinned.

### Screen contracts

The prototype at `specs/designs/` is the acceptance reference for these screens' layout and
copy; where it and this constitution disagree, this constitution wins. It holds six screens,
the shared vendored stylesheet, and a README (`specs/designs/README.md`) mapping each screen
to the specs governing its behavior.

A screen contract MAY exist without a prototype screen where the governing spec explicitly
defers visual design, recording that deferral as an exception in its plan's Constitution
Check. For such a screen the contract text below is the sole acceptance reference: it fixes
purpose, required affordances, and entry points, leaving layout and copy to the implementer
within the design-token, interaction-state, and accessibility requirements above, none of
which the deferral relaxes.

- **Login** (`specs/designs/01-login.html`) — Microsoft identity sign-in only
  (Principle II): no password field, no local accounts, no alternate identity provider.
- **Adventure select** (`specs/designs/02-story-select.html`) — in-progress adventures
  first, showing progress and last-played information; published, not-yet-started
  adventures follow a visible divider. Resuming is reachable in one action from a list row.
- **Play surface** (`specs/designs/03-play.html`) — a persistent title/status bar offering
  an explicit checkpoint-save and a pause-and-exit action; a scrolling story pane; an
  instruction input paired with suggested actions; a status panel showing location, goal,
  progress, and a hint action. Exiting always goes through the pause screen, never an
  unconfirmed destructive action.
- **Administrator story-authoring wizard** (`specs/designs/04-admin-wizard.html`) — six
  steps (name & cover, world & setting, tone & reading level, session length, test play,
  publish & assign) reachable in any order. The adventure's core premise and its
  content-safety configuration are required. A story MUST NOT be publishable
  (`005-story-publishing-done`) until it has completed a test play.
- **Administrator — people** (`specs/designs/05-admin-users.html`) — add a Player or
  Administrator by email; existing accounts list their roles and are removed one at a time
  behind a confirmation dialog, never in bulk. Accounts are Microsoft identities only, with no
  password field (Principle II). See `003-account-provisioning-done`.
- **Administrator — stories & configuration** (no prototype screen) — the story list shows
  every story with published/unpublished status conveyed as text, not color alone, and is
  one of the two required entry points for publish/unpublish (`005-story-publishing`
  FR-010), enforcing the same preconditions and confirmation as the wizard's publish step by
  rendering the same shared control rather than a screen-specific reimplementation. Each row
  reaches that story's read-only configuration viewer in one action. The list is also the
  entry point for uploading a story configuration file (`011-story-import` FR-001,
  `012-story-editing-and-review` FR-005): the upload control confirms the named overwrite
  target for a file carrying a story id, and prompts for a title for one that does not. The
  viewer renders the story's complete configuration exactly as the download produces it,
  with the download action alongside, and is read-only — every edit goes through the
  authoring wizard or a re-upload. Introduced by `012-story-editing-and-review`, whose
  FR-012 defers these two screens' visual design; that deferral is recorded as an explicit
  exception in that feature's plan and covers styling only.
- **Administrator — sessions** (no prototype screen) — a read-only list of every gameplay
  session (real player and admin test play), each row showing its story, a session
  identifier, its cumulative token total, and the email of whoever played it. Reachable as
  its own admin navigation item alongside Stories and People. Introduced by
  `026-token-usage`, whose spec defers this screen's visual design; that deferral is
  recorded as an explicit exception in that feature's plan and covers styling only.

### Save and session behaviour

1. Autosave after every turn is the default and is stated to the player in the UI.
2. A manual save creates a named checkpoint and confirms visibly and briefly.
3. Exiting never loses a turn already taken; the pause/exit screen states where the game was
   saved.
4. Session length is configurable per adventure, and the game offers a natural stopping
   point rather than cutting a player off abruptly.

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
agreement for this project. Every pull request and review MUST verify compliance with the
principles and requirements above, and any added complexity — a new service, new
infrastructure, a deviation from the defined stack — MUST be explicitly justified in the
pull request description.

Amendments MUST be made through a pull request that updates this file, states the rationale
for the change, and passes the review gate in Development Workflow & Quality Gates before
merge. Versioning is semantic: MAJOR for backward-incompatible
governance or principle removals and redefinitions, MINOR for a new principle or section or
materially expanded guidance, PATCH for clarifications and wording fixes. The Last Amended
date MUST be updated on every change to this file's content, and the amendment's Sync Impact
Report replaces its predecessor at the top of this file.

Every implementation plan (`plan.md`) MUST include a Constitution Check stating how each UI
Design System requirement is satisfied or requesting an explicit, justified exception. A
cross-artifact consistency analysis MUST treat a contradiction with the design-token,
visual-rules, interaction-state, or layout and scroll requirements as a blocking finding. No
feature may ship a screen that is not traceable to a screen contract above or to a
documented amendment extending one.

**Version**: 9.0.0 | **Ratified**: 2026-08-28 | **Last Amended**: 2026-09-12
