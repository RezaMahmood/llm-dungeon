<!--
Sync Impact Report
Version change: 3.0.0 -> 3.1.0
Modified principles: none
Added principles: XIV. Spec Artifacts and Code Stay Clean — Git Is the History
Removed principles: none
Added sections: none
Modified sections: none
Source: direct user instruction (2026-09-07) — spec artifacts (spec/plan/research/
  tasks/etc.) and source code comments must rely on git history rather than in-file
  narrative; a short line of current rationale is fine, but multi-line narrative
  explaining why a decision was made or reversed is not, and a superseding decision
  overwrites the old one with a very short note instead of retaining the old
  explanation. Extends the same restraint to code comments: no narrating what code
  does, no restating spec-documented behavior, no changelog-in-comments. Additive-only
  new principle, hence MINOR. This amendment was authored in parallel with the
  2.3.0 -> 3.0.0 amendment below on a separate branch and is folded in here, on top of
  3.0.0, now that this branch has caught up with `origin/main`.
Templates requiring follow-up: none - dependent templates read this file at runtime and
  are not modified by this command.
Deferred/TODO placeholders: none.

Previous report (2.3.0 -> 3.0.0)
Modified principles:
  - XIII. AI Agent Division of Labor: Local LLM Pushes & Opens PRs, GitHub Copilot
    Reviews, Human Merges (NON-NEGOTIABLE) - removed the requirement that GitHub issue
    resolution (bug reports, dependency-update issues, and fixes) MUST be performed via
    GitHub Copilot. A local AI agent MAY now resolve an issue end-to-end - writing the
    fix, pushing the branch, and opening the pull request - the same as any other local
    development work; GitHub Copilot's role is the PR review pass, not a required
    intermediary for issue resolution. The narrower prohibition on a local AI agent
    itself merging a pull request or closing a GitHub issue (a GitHub-side action,
    distinct from writing the fix) is unchanged. Backward-incompatible: this withdraws a
    previously NON-NEGOTIABLE restriction, hence MAJOR.
Added principles: none
Removed principles: none
Added sections: none
Modified sections:
  - AI Agent / GitHub Handoff Requirements - removed the bullet requiring GitHub issue
    resolution to be assigned to or driven by GitHub Copilot; clarified the remaining
    "MUST NOT merge a pull request or close a GitHub issue" bullet to state that
    resolving the issue (fix, push, PR) is ordinary local work and not restricted by it.
  - Development Workflow & Quality Gates - removed the clause requiring GitHub issue
    resolution to go via GitHub Copilot from the bullet summarizing the AI agent
    push/PR/review/merge flow.
Removed sections: none
Source: direct user instruction (2026-09-07). The user asked to resolve issue #260,
  which itself (correctly, per the then-current constitution) declined to be resolved by
  a local agent and named GitHub Copilot as the required path for issue resolution. On
  review the user judged that restriction wrong - GitHub Copilot's role in this project
  is PR code review, not issue resolution - and directed that it be removed so a local
  AI agent can resolve issues (including #260 itself) the same way it does any other
  local development work, subject to the unchanged no-merge/no-auto-merge/labelling
  rules.
Templates requiring follow-up: CLAUDE.md carried a mirrored copy of the old
  Copilot-only issue-resolution rule (Git / PR workflow section); that edit landed in the
  same pull request as this amendment (#272), so there is no outstanding follow-up here.
Deferred/TODO placeholders: none.

Previous report (2.2.0 -> 2.3.0)
Version change: 2.2.0 -> 2.3.0
Modified principles: none
Added principles: none
Removed principles: none
Added sections: none
Modified sections:
  - Screen contracts - added a sixth contract, "Administrator - stories &
    configuration", covering the administrator story list (published status, publish/
    unpublish entry point per 005-story-publishing FR-010, and the entry point for
    uploading a story configuration file per 011-story-import FR-001) and the read-only
    story configuration viewer introduced by 012-story-editing-and-review. Also
    corrected the stale "five screens" count in the section preamble to six (06-game-setup.html has
    been in specs/designs/ since 006-adventure-and-character-setup), and stated
    explicitly that a screen contract MAY exist without a prototype screen when a spec
    defers visual design, in which case the contract text is the sole acceptance
    reference for that screen.
Removed sections: none
Source: 012-story-editing-and-review's cross-artifact analysis (2026-09-07) found its
  read-only configuration viewer to be a new screen traceable to no screen contract,
  which Governance forbids shipping. The requesting user chose to extend the screen
  contracts rather than take an exception. This is additive guidance only - no existing
  contract, principle, or requirement changes meaning, hence MINOR. This amendment was
  authored in parallel with the 2.1.0 -> 2.2.0 amendment below on a separate branch and
  is folded in here, on top of 2.2.0, when that branch caught up with `origin/main`.
Templates requiring follow-up: none - dependent templates read this file at runtime and
  are not modified by this command.
Deferred/TODO placeholders: none.

Previous report (2.1.0 -> 2.2.0)
Modified principles:
  - XIII. AI Agent Division of Labor: Local LLM Pushes & Opens PRs, GitHub Copilot
    Reviews, Human Merges (NON-NEGOTIABLE) - materially expanded, not redefined. Added a
    sync-before-work rule: before any development or spec-related work begins on a feature
    branch - planning (plan, tasks, clarify, analyze) included, not implementation alone -
    that branch MUST be brought up to date with `origin/main`, and a divergence MUST be
    resolved or reported rather than worked around. Where an artifact then states that
    code already exists, that statement MUST match the synced tree or `origin/main`, never
    an unmerged local branch, another worktree, or a stale local `main`. Identifiers an
    artifact proposes to create are expressly exempt - a plan is expected to name code
    that does not exist yet - and a dependency on unmerged work MUST be named as such.
    Backward-compatible: nothing previously permitted is withdrawn, and the existing
    push/open-PR authorization, no-auto-merge and no-merge rules, the merged/closed-PR
    push prohibition, the Copilot review pass, and the manual human merge are all
    unchanged.
Added principles: none
Removed principles: none
Added sections: none
Modified sections:
  - AI Agent / GitHub Handoff Requirements - added a bullet stating the rule operationally
    (fetch and fast-forward/merge `origin/main` before spec-related work; read existing
    code from the synced tree or `git show origin/main:<path>`, never from another branch
    or worktree).
  - Development Workflow & Quality Gates - added a bullet making a claim that code already
    exists, where it is absent from `origin/main` and not declared as a named unmerged
    dependency, a blocking cross-artifact consistency analysis finding. Proposed
    identifiers are explicitly not findings.
Removed sections: none
Source: direct user instruction (2026-09-06), prompted by a concrete failure during
  010-story-test-play planning. The plan was written by reading the then-unmerged local
  `008-core-gameplay` branch, and asserted a service method `list_saved_games()` that does
  not exist; the real method on `origin/main` is `list_player_sessions()`. The error was
  caught only when the artifacts were re-verified against `origin/main` after that work
  merged. The project's existing `speckit.git.pull` hook did not prevent it: it runs only
  on `before_implement`, fast-forwards a feature branch from its own upstream rather than
  from the trunk, and skips silently when a branch has no upstream - which was the case
  here. Nothing in the constitution required syncing before planning.
Templates requiring follow-up: `.specify/extensions.yml` registers `speckit.git.pull` on
  `before_implement` only, and `.claude/skills/speckit-git-pull/SKILL.md` fast-forwards
  from the branch's own upstream rather than from `origin/main`. Bringing that tooling in
  line with this rule (running before the planning commands, and syncing the trunk) is
  tracked as issue #260, deliberately not bundled into this governance amendment. Until
  that lands, this rule is enforced by convention rather than by tooling.
Deferred/TODO placeholders: none.
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
Automated integration tests MUST run locally against stubbed/emulated external cloud
dependencies (e.g., a CosmosDB emulator or an equivalent local stub, per Dependency &
Supply Chain Security Requirements) rather than requiring the live Azure environment,
since this project maintains only the two environments defined in Environments &
Deployment Pipeline — local and live — with no dedicated test-only cloud environment to
run against. As much automated testing as practical MUST run locally for speed and
tight feedback; the live environment is not a substitute for local automated testing.

Rationale: The team explicitly wants confidence from tests that verify real behavior,
not a coverage metric. Automating tests in the PR pipeline is the only way to enforce
this consistently as the game's dungeon logic, LLM interactions, and API surface grow.
Because Principle XII deliberately rules out a dedicated test/staging cloud environment,
local stubs of cloud dependencies are the only way to keep integration tests both fast
and fully automated.

### II. Secure-by-Default Access (NON-NEGOTIABLE)
The application MUST require sign-in via Microsoft Entra ID for every user-facing page
and every API endpoint — there is no public or anonymous access to any part of the
system, including status/health endpoints that reveal application details. Access MUST
be restricted to an explicit allow-list of specific Microsoft accounts; there is no
open sign-up or tenant-wide access by default. Authorization checks MUST be enforced
server-side in the Azure Functions backend; a client-side (ReactJS) check alone is never
sufficient, since it can be bypassed. The one narrow exception is local automated
testing: a dedicated automation identity MAY bypass interactive Entra ID sign-in when
running locally, strictly under the guardrails in Security & Access Control
Requirements below — this exception MUST NOT be reachable, configurable, or present as
live code/config in the deployed live environment.

Rationale: The project is explicitly scoped as a private application for a specific,
named set of Microsoft accounts, not a public product. Server-side enforcement is
required because client-side gating is trivially bypassable. Requiring an interactive
Entra ID sign-in for every local automated test run would make the fast, frequent local
testing this project relies on (Principle I) impractical, so a strictly local-only,
non-deployable bypass is permitted instead of weakening production auth.

### III. Defined Technology Stack
The backend MUST be implemented in Python and deployed as Azure Functions. The frontend
MUST be implemented in ReactJS and run in a standard web browser. Any deviation from
this stack (a different language, framework, or hosting model) requires a documented
justification and an amendment to this constitution before adoption. New code MUST
target the latest long-term-support (LTS) major version of each runtime in the stack
(Node.js for frontend tooling, Python for the backend) and the latest stable major
version of each core framework (e.g., React) at the time the code is written; the
project MUST NOT knowingly adopt or remain pinned to a runtime/framework major version
that is approaching end-of-support when a current LTS/stable major is available. Detailed
rules are in the Dependency & Supply Chain Security Requirements section below.

Rationale: A fixed, agreed stack keeps the small initial build focused and avoids
architectural churn while the game's core mechanics are still being established.
Deliberately starting on the current LTS/stable major of each runtime and framework —
rather than an older one — avoids accumulating a forced, disruptive major-version
migration later; the project explicitly wants to avoid regularly refactoring for newer
majors (e.g., a React major upgrade) that a more current starting point would have
avoided.

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

### IX. Playtesting-Driven Quality (Post-Ship Verification, Non-Blocking)
A feature is complete once its automated tests (Principle I) pass and it merges through
the CI gate (Principle V) — human verification against the real deployed environment is
NOT a precondition for completion or merge, and MUST NOT be used to block a pull request
or hold a feature open. Human playtesting against the deployed environment still
happens, but as an ongoing, post-ship activity: issues it surfaces are captured (e.g., as
GitHub issues) and fixed in follow-up work, not treated as proof the original work was
incomplete. A feature's task list MAY include a playtesting/acceptance task, but it is
informational and non-blocking, not a required gate, unless a specific feature's plan
explicitly opts back into a blocking check for a named, high-risk area.

Rationale: The team has explicitly deprioritized getting every feature right on first
delivery in favor of development speed and shipping an MVP; issues are expected to be
found and fixed through live play rather than prevented upfront by a human sign-off gate.
This principle previously required human verification before completion specifically
because automated tests missed real deployment-wiring failures (e.g., during
003-account-provisioning-done, where all 82 backend and 31 frontend tests passed while
sign-in was broken in production for five separate reasons). That risk has not
disappeared, but the team has decided the cost of a mandatory pre-completion human gate
now outweighs it for MVP velocity — automated tests (Principle I) remain the safety net,
and issues that slip through are expected to be caught and fixed via playtesting after
the fact instead of before merge.

### X. PII Protection by Design (NON-NEGOTIABLE)
Personally identifiable information (PII) — a real person's email address, name, phone
number, physical address, or any other data that identifies a specific individual — MUST
live only in a secure, access-controlled, purpose-built data store: the application's
database, Azure Key Vault, or an equivalent managed secret/credential store. PII MUST NOT
be committed to the GitHub repository, written into commit messages, or posted into GitHub
issues, pull request descriptions, or comments, and MUST NOT be written to application
logs, traces, or telemetry. Where an issue, PR, commit, or log entry must discuss a record
that involves PII, it MUST reference that record indirectly (e.g., a role, an internal
identifier, or "the seed administrator's entry") rather than including the PII itself. The
detailed rules are in the PII & Data Protection Requirements section below.

Rationale: GitHub issues, pull requests, comments, and commit history are effectively
public or broadly-accessible-forever records for this project — indexed, cached, and
retained indefinitely — and are not access-controlled the way the application's own data
stores are. Including a real person's PII on any of these surfaces defeats the purpose of
restricting where that data is allowed to live, and cannot be reliably un-published once
posted.

### XI. Implementer Design Latitude (Non-Blocking)
For a feature that includes a user-facing UI, the implementing agent or team MAY proceed
directly to implementation using its own design judgment, guided by the existing design
system and screen contracts (Principle VIII, UI Design System Requirements) — a
pre-implementation design mockup/sign-off from the requesting user or product owner is
NOT required to start implementation, and MUST NOT be used to block or delay it. A
feature's task list MAY include a design walkthrough or mockup review, but only as an
optional, non-blocking checkpoint at the author's discretion, not a required gate.
Design issues (a layout that doesn't fit, a flow that confuses players) are expected to
surface through playtesting (Principle IX) and are fixed as follow-up work rather than
prevented upfront through mandatory pre-approval.

Rationale: The team has explicitly deprioritized getting the design right on the first
attempt in favor of development speed toward an MVP, accepting that some design rework
will be discovered and fixed via playtesting instead of avoided by an upfront sign-off
gate. Principle VIII still enforces that any UI built stays inside this project's design
system, token layer, and accessibility bar regardless of who approved the specific
layout — that constraint is unaffected and remains NON-NEGOTIABLE; only the requirement
that the requesting user pre-approve the specific screen design before coding starts is
removed.

### XII. Right-Sized Scope — Not Enterprise-Grade (NON-NEGOTIABLE)
This project is a small application for a specific, named set of users, not an
enterprise product, and MUST NOT be designed or specified as if it were one. A spec,
plan, or task MUST NOT introduce an enterprise-grade pattern — including, but not
limited to, single sign-on or federated identity beyond the already-mandated Entra ID
allow-list (Principle II), multi-tenant architecture, additional non-production
environments beyond local development and the single live environment (see
Environments & Deployment Pipeline below), elaborate role/permission hierarchies beyond
the allow-list's roles, or dedicated scaling/high-availability infrastructure — unless a
concrete, stated requirement calls for it. Whenever work on a spec, plan, or task starts
trending toward an enterprise-grade pattern, the author (human or AI) MUST stop and
explicitly ask the requesting user whether it is actually needed, rather than assuming
it is or silently including it. For example, SSO beyond the mandated Entra ID sign-in is
out of scope by default and MUST be confirmed with the user before being specified.

Rationale: "Enterprise-grade" defaults (extra environments, broader identity
federation, elaborate RBAC, scale-out infrastructure) are easy to reach for out of habit
and quietly inflate scope, cost, and complexity for a project that has neither the user
base nor the stated requirements to justify them. This principle extends Principle IV's
general YAGNI stance into an explicit, enforced process check specifically for
enterprise-shaped patterns, since those are the ones most likely to be assumed rather
than requested.

### XIII. AI Agent Division of Labor: Local LLM Pushes & Opens PRs, GitHub Copilot Reviews, Human Merges (NON-NEGOTIABLE)
Local AI agent development — writing code, running local tests, and spec-related work
(intake, specify, clarify, plan, tasks, analyze) — MAY be performed by Claude Code or
another local LLM-based coding assistant (e.g., Cursor or an equivalent). Spec-related
work MUST stay local: it MUST be performed by the local AI agent and MUST NOT be
delegated to GitHub Copilot. Once that local work is ready, the local AI agent MUST
push the branch and open the pull request itself (e.g., `gh pr create`), labelled per
the AI Agent / GitHub Handoff Requirements below. The local AI agent MUST NOT enable
auto-merge and MUST NOT merge the pull request itself. From there, GitHub Copilot
reviews the pull request and posts its findings as review comments/recommendations —
Copilot code review does not produce a formal approving review or perform the merge on
a clean pass. The requesting user or product owner MUST review Copilot's
recommendations together with the required CI/status checks and code-quality gate, and
then merge the pull request manually. A local AI agent MAY resolve a GitHub issue
end-to-end — writing the fix, pushing the branch, and opening the pull request itself —
the same as any other local development work; GitHub Copilot's role is the PR review
pass described above, not a required intermediary for issue resolution. A local AI agent
MUST NOT merge a pull request or close a GitHub issue directly itself (e.g., via `gh
issue close`), even where the tool has the technical means to do so — an issue is closed
by its resolving pull request merging, or manually by the requesting user. Work MUST
start from a synced tree: before any development or
spec-related work begins on a feature branch — planning (plan, tasks, clarify, analyze)
included, not implementation alone — that branch MUST be brought up to date with
`origin/main`, and a divergence MUST be resolved or reported rather than worked around.
Where an artifact then states that code already exists — a module path, a class or
function name, a constant, a field, an endpoint, or a configuration value — that statement
MUST match the synced tree or `origin/main` itself, never an unmerged local branch,
another worktree's checkout, or a stale local `main`. Identifiers an artifact proposes to
create are expressly exempt: a plan is expected to name files, symbols, and fields that do
not exist yet, and MUST simply make clear which it proposes and which it claims already
exist. A dependency on work that has not yet merged MUST be named explicitly rather than
described as if it had already landed. Every push of new work MUST be visible as its own
open pull request: a local AI agent MUST NOT push follow-up commits onto the branch of a
pull request that has already been merged or closed, even where that branch still exists
and the push would technically succeed. Such work MUST go onto a fresh branch behind a new
pull request. Detailed rules are in the AI Agent / GitHub Handoff Requirements
section below.

Rationale: A bot-authored pull request (one opened by an automation identity via a
GitHub Actions workflow) is treated by GitHub the same way as an outside contributor's
PR — its required checks sit pending a manual "approve and run workflows" click every
time, which defeats a hands-off pipeline. Having the local AI agent open the PR as the
developer's own authenticated action avoids that gate, while GitHub Copilot still
provides a consistent, GitHub-side review pass regardless of which local LLM tool
pushed the branch. Auto-completing the merge once Copilot finishes was dropped because
Copilot's code review is relatively slow and does not produce a formal approving review
before merge — wiring auto-merge to it would let a pull request merge without anyone
actually having weighed Copilot's findings. Requiring the requesting user to read
Copilot's recommendations and merge manually keeps a real decision point in the loop
while still using Copilot for the GitHub-side review pass. Reusing the branch of an
already-merged or closed pull request hides the new work: the merged PR is no longer
part of anyone's review queue, Copilot does not re-review it, and the commits reach
the repository without ever appearing as something a human was asked to look at.

Rationale for the sync-before-work rule: a local AI agent can read any branch or
worktree the machine happens to hold, and code read from an unmerged branch looks exactly
like code that already exists. A plan built that way asserts identifiers that are not on
the trunk — a defect that survives review precisely because the artifact reads as
authoritative. Syncing first is the root prevention: once the branch carries `origin/main`,
reading the working tree *is* reading the trunk, and the failure cannot arise. The project
already had a pull step, but only as a pre-implementation hook that fast-forwards a
feature branch from its own upstream — it does not run before planning, does not sync with
the trunk, and skips silently on a branch with no upstream, so it did not prevent this.
Exempting proposed identifiers keeps the rule from blocking the ordinary business of a
plan, which is to describe code that does not exist yet; naming an unmerged dependency
keeps that legitimate case available without disguising it as fact.

### XIV. Spec Artifacts and Code Stay Clean — Git Is the History
A feature's spec-related artifacts (`spec.md`, `plan.md`, `research.md`, `data-model.md`,
`quickstart.md`, `tasks.md`, and any other file under that feature's `specs/` folder,
excluding this constitution's own Sync Impact Report) rely on git history, not narrative
prose, to record why a decision was made or later changed. A line or two of rationale
next to a decision is fine. Multiple lines of narrative explaining why a decision was
made or reversed are NOT permitted in these files — that belongs in the commit message
or PR description, not the artifact. When a decision supersedes an earlier one, the
artifact MUST be edited in place to reflect the new decision, with only a very short
note marking the change (e.g. "Supersedes: <old approach>, in <15 words> why") — not a
retained explanation of the old decision alongside the new.

The same restraint applies to source code comments. A comment MAY note a short,
non-obvious reason for a line of code (e.g. a workaround for a specific external
constraint) but MUST NOT narrate what the code does, restate implementation detail the
governing spec already documents, or explain the history of how the implementation
arrived at its current form — no changelog-in-comments, no "previously this did X,
changed to Y because Z". That detail belongs in the feature's spec/plan (current
behavior) and git history (why it changed), not in a block comment at the call site.

Rationale: Spec artifacts are working documents read repeatedly during a feature's life;
narrative justifying past reversals bloats them and makes the current, authoritative
decision harder to find. Git history already preserves that reasoning at the commit
that made it, so the artifact itself should show only what is true now, briefly why.
The same applies to code: a spec is the intended place to document what a feature does
and why, so a comment repeating that or narrating its edit history is duplicated,
drifts out of sync with the spec as the code evolves, and clutters the code itself.

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
- Application code and design MUST follow OWASP Top 10 practices appropriate to the
  stack in use (e.g., input validation and output encoding, parameterized data access,
  proper authentication/session handling, access-control checks on every server-side
  entry point, secure default configuration, and safe handling of dependencies known to
  carry vulnerabilities). This is a baseline practice expectation proportionate to this
  project's size, not a request for enterprise-grade security tooling or process
  (Principle XII).
- A local-only automation identity/bypass for automated integration tests (Principle I,
  Principle II) MUST be gated by a build-time or deploy-time condition that is
  structurally absent from the live environment's build/deploy configuration (e.g., a
  code path compiled or wired in only for local test runs) — never a runtime
  environment-variable or request-header check alone, since either could be
  misconfigured or spoofed against the live deployment. The live environment's Entra ID
  sign-in and server-side authorization checks (this section, above) MUST have no
  disable path, flag, or override of any kind.
- The automation identity used for local bypass MUST carry no real user's credentials
  and MUST NOT correspond to a real Microsoft account on the production allow-list; it
  exists only to let local automated tests exercise authorized-user code paths without
  an interactive sign-in.
- Any change that touches the local automation bypass or the Entra ID sign-in/
  authorization path MUST be reviewed with this section in mind (Development Workflow &
  Quality Gates) — the reviewer explicitly confirms the bypass remains unreachable from
  the live environment.

## Dependency & Supply Chain Security Requirements

- Dependencies (Python packages, npm packages, GitHub Actions, container base images)
  MUST be pulled only from official, public package registries/marketplaces; MUST use a
  committed lockfile (e.g., `requirements.txt`/`poetry.lock`, `package-lock.json`) so
  builds are reproducible; and MUST NOT pin to a package version already flagged with a
  known, unpatched critical or high-severity vulnerability when an updated version
  exists.
- Automated dependency vulnerability scanning (e.g., GitHub Dependabot alerts or
  equivalent) MUST be enabled on the repository, and a critical or high-severity
  advisory affecting a dependency in use MUST be remediated (upgrade, patch, or
  documented accepted-risk exception) rather than silently ignored.
- New code MUST target the latest LTS major version of each runtime (Node.js, Python)
  and the latest stable major version of each core framework (e.g., React) at the time
  it is written, per Principle III — this keeps the project off soon-to-be-outdated
  majors and avoids a disruptive forced migration later.
- This is a proportionate, best-practices baseline for a small application's supply
  chain — not an enterprise-grade software-supply-chain program (e.g., no SBOM
  generation, no third-party vendor security review process) unless a concrete,
  stated requirement calls for it (Principle XII).

## PII & Data Protection Requirements

- Personally identifiable information (PII) MUST only be stored in a secure,
  access-controlled data store: the application's database (e.g., Cosmos DB), Azure Key
  Vault, or an equivalent managed secret/credential store.
- PII MUST NOT be committed to the GitHub repository in any form — source code,
  configuration, fixtures, seed data, or documentation. Test and fixture data MUST use
  synthetic values, never a real person's actual information.
- PII MUST NOT be included in GitHub issues, pull request descriptions, or comments, nor
  in commit messages. Where an issue, PR, or commit legitimately needs to discuss a
  record that involves PII, it MUST reference that record indirectly (e.g., a role, an
  internal identifier, or a redacted form) rather than including the PII itself.
- PII MUST NOT be written to application logs, traces, or telemetry (see Observability &
  Telemetry Requirements below) beyond what a feature's specification explicitly requires
  and secures within an access-controlled data store — general-purpose logs and traces
  MUST NOT capture a user's email, name, or other identifying data.
- This requirement applies everywhere the project's output could become publicly
  accessible or durably retained beyond the team's direct control (issue trackers, CI
  logs, published artifacts, external documentation) — not solely the repository's own
  commit history.

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

## AI Agent / GitHub Handoff Requirements

- Local AI agent tools (Claude Code or another local LLM-based coding assistant, e.g.
  Cursor or an equivalent) are authorized for: writing and editing code, running local
  and automated tests, all spec-related work (intake, specify, clarify, plan, tasks,
  analyze) via this project's Spec Kit workflow, and — once that work is ready — pushing
  the branch and opening the pull request for it.
- Before a local AI agent begins spec-related work on a branch — writing or updating
  `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`, or `tasks.md`,
  not only implementing — it MUST sync that branch with `origin/main` (e.g. `git fetch
  origin`, then fast-forward or merge `origin/main` into the branch), and MUST report a
  divergence it cannot fast-forward rather than forcing or working around it. Existing
  code an artifact describes MUST then be read from that synced tree, or from
  `origin/main` directly (e.g. `git show origin/main:<path>`) — never from a different
  local branch or another worktree's checkout. This applies to identifiers the artifact
  says already exist; identifiers it proposes to create are exempt, and a dependency on
  unmerged work MUST be named as such.
- When a local AI agent opens a pull request, it MUST label it `AI Generated` and
  `Claude` (both labels already exist in this repository), MUST NOT include a link to
  the local agent's own session/transcript in the PR description, and MUST NOT enable
  auto-merge on the PR or merge it directly.
- Before pushing to a remote branch, a local AI agent MUST confirm the state of any
  pull request associated with that branch (e.g., `gh pr view <branch> --json state`).
  If the associated pull request is merged or closed, the agent MUST NOT push to that
  branch; it MUST create a new branch off the current main branch and open a new pull
  request for the work, labelled as above. Pushing to a branch whose pull request is
  still open is permitted and is the normal way to address review feedback.
- Local AI agent tools MUST NOT directly perform any other GitHub-hosted operation: they
  MUST NOT merge a pull request or close a GitHub issue directly on their own behalf,
  even where the tool has the technical means to do so (e.g., a `gh` CLI or GitHub API
  credential). Resolving the issue — writing the fix, pushing the branch, and opening
  the pull request — is ordinary local development work and is not restricted by this
  bullet; only the GitHub-side close/merge action is.
- Once a local AI agent has pushed a branch and opened its pull request, GitHub Copilot
  reviews the pull request and posts its findings as review comments/recommendations;
  its required CI/status checks and code-quality gate run as usual, mirroring the
  required checks already established in Development Workflow & Quality
  Gates and Continuous Integration Gate (Principle V). Copilot code review does not
  produce a formal approving review or perform the merge. The requesting user or
  product owner MUST read Copilot's recommendations and the status of the required
  checks, then merge the pull request manually once satisfied.
- This division applies to GitHub-hosted actions only. It does not change where code is
  written or tested (Principle I, Environments & Deployment Pipeline) — only who is
  authorized to create and monitor the GitHub-side artifacts (PRs and issues) that carry
  that work, and it makes clear that merging a pull request is a manual action for the
  requesting user or product owner, not something either AI agent performs.
- Any exception (e.g., an emergency fix where GitHub Copilot is unavailable) MUST be
  explicitly called out by the person directing the work and is not a default local AI
  agent behavior.

## Development Workflow & Quality Gates

- All changes MUST go through a pull request on GitHub; direct pushes to the main branch
  are not permitted.
- This repository merges exclusively by squash, so the PR title — not any individual
  commit message — becomes the sole commit on `main` and is what semantic-release reads
  to compute the next version. Every PR title MUST therefore follow Conventional
  Commits format, `type(scope): description`, and MUST pass the repository's required
  `check-title` status check before merge. The allowed `type` and `scope` values are the
  single source of truth in `scripts/pr-title-config.js` (mirrored into
  `.github/workflows/pr-title-check.yml`); scope is required on every PR title, even for
  a scope (e.g., `docs`, `chore`) that never gates a version bump.
- Every pull request MUST include automated tests for the functionality and edge cases
  it introduces or changes, per Principle I.
- CI MUST run the full automated test suite on every pull request, per Principle V; a
  failing run blocks merge.
- Code review by at least one other contributor is required before merge, focused on
  correctness, adherence to this constitution, and meaningful test quality (not just
  presence of tests).
- A passing automated test suite (Principle I) and a green CI run (Principle V) are
  sufficient for a feature to be considered complete and mergeable; human playtesting
  against the deployed environment happens afterward, on an ongoing basis, per
  Principle IX, and MUST NOT be used to block merge or hold a feature open.
- Spec-related work MUST begin from a branch synced with `origin/main`, not from an
  unmerged local branch, another worktree, or a stale local `main`, per Principle XIII.
  A cross-artifact consistency analysis MUST treat as a blocking finding any statement
  that code already exists — a module path, symbol, constant, field, or endpoint — where
  that code is absent from `origin/main` and is not declared as a named, not-yet-merged
  dependency. Identifiers the artifact proposes to create are not findings; a plan naming
  code it intends to add is doing its job.
- Issues, pull request descriptions/comments, and commit messages MUST NOT include PII
  (Principle X, PII & Data Protection Requirements) — reference affected records
  indirectly instead.
- A feature with a user-facing UI is NOT required to have a pre-implementation UI design
  agreement/sign-off task; per Principle XI, the implementer MAY proceed on its own
  design judgment within the constraints of Principle VIII and the UI Design System
  Requirements below. A task list MAY still include an optional, non-blocking design
  walkthrough at the author's discretion.
- A local AI agent completing local work — including resolving a GitHub issue —
  pushes the branch and opens its own pull request (labelled, auto-merge NOT enabled),
  per Principle XIII and the AI Agent / GitHub Handoff Requirements above. GitHub
  Copilot reviews the PR and posts its findings as recommendations. Merging is a manual
  step: the requesting user or product owner reviews Copilot's recommendations and the
  required checks, then merges the pull request themselves.
- Feature work MUST happen inside that feature's own git worktree, running inside that
  worktree's own isolated devcontainer (started via `bin/wt <branch>`) — never directly in
  the primary checkout, and a worktree's container MUST NOT be shared with another
  worktree. This keeps concurrent specs from cross-contaminating: a session for one spec
  has no filesystem access to any other spec's worktree. See
  `docs/WORKTREE_CONTAINER_WORKFLOW.md` for the full workflow.

## Environments & Deployment Pipeline

- There are exactly two places code is built and tested: a contributor's local machine
  (including a worktree's isolated devcontainer, per Development Workflow above) and the
  single live/production environment in Azure. The project MUST NOT stand up an
  additional persistent environment (e.g., a separate staging, UAT, or QA deployment)
  without a documented requirement and a constitution amendment — this is a deliberate,
  non-enterprise-grade choice (Principle XII).
- The only path from a merged change to the live environment is through GitHub Actions
  workflows; there is no manual/portal deployment path for application code.
- Credentials and configuration needed by deployment workflows MUST be stored as GitHub
  Actions secrets (or GitHub environment secrets/variables), never committed to the
  repository, consistent with the Security & Access Control Requirements above.
- CI (build/test, per Principle V) and CD (deploy to the live environment) both run as
  GitHub Actions workflows; a deployment workflow run MUST NOT deploy a change that has
  not passed the required CI checks.
- Because no dedicated cloud test environment exists, automated integration tests MUST
  run against a local stub or emulator of each external cloud dependency they exercise
  (e.g., the Azure Cosmos DB emulator, or an equivalent local/in-memory stub) instead of
  a live Azure resource, per Principle I. A dependency without a viable local stub or
  emulator MUST be called out explicitly in that feature's plan, with a documented
  fallback (e.g., a narrowly-scoped contract test against the real live-environment
  resource, run only where unavoidable).

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
   `008-core-gameplay-done`), which remain a legitimate, narratively-framed part of gameplay.

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
and copy; this constitution wins on rules where the two disagree. It contains six
screens, a shared vendored stylesheet, and a README mapping each screen to the spec(s)
that govern its behavior (see `specs/designs/README.md`).

A screen contract MAY exist without a corresponding prototype screen where the governing
spec explicitly defers visual design (recording that deferral as an exception in its
plan's Constitution Check). For such a screen the contract text below is the sole
acceptance reference: it fixes the screen's purpose, its required affordances, and its
entry points, while layout and copy are the implementer's within the design-token,
interaction-state, and accessibility requirements above — none of which the deferral
relaxes.

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
  fields. A story MUST NOT be publishable (see `005-story-publishing-done`) until it has
  completed a test play.
- **Administrator — people** (`specs/designs/05-admin-users.html`) — add a new Player or
  Administrator by email; existing accounts are listed with their role(s), and removed
  one at a time, always behind a confirmation dialog (no bulk removal). Accounts are
  Microsoft identities only — no password field, consistent with Principle II. See
  `003-account-provisioning-done`.
- **Administrator — stories & configuration** (no prototype screen; see the paragraph
  above) — the administrator's story list shows every story with its published/
  unpublished status conveyed as text, not color alone, and is one of the two required
  entry points for publish/unpublish (`005-story-publishing` FR-010), enforcing the same
  preconditions and confirmation as the authoring wizard's publish step by rendering the
  same shared control, never a screen-specific reimplementation. Each row reaches that
  story's read-only configuration viewer in one action. The list is also the entry point
  for uploading a story configuration file (`011-story-import` FR-001,
  `012-story-editing-and-review` FR-005): the upload control confirms the named overwrite
  target for a file that carries a story id, and prompts for a title for one that does
  not. The viewer renders the story's complete configuration file exactly as the download
  produces it, with the download action alongside it, and it is read-only — every edit
  goes through the authoring wizard (04) or a re-upload. Introduced by
  `012-story-editing-and-review`, whose FR-012 defers these two screens' visual design
  to follow-up work; that deferral is recorded as an explicit exception in that
  feature's plan and covers styling only.

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

**Version**: 3.1.0 | **Ratified**: 2026-08-28 | **Last Amended**: 2026-09-07
