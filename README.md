# LLM Dungeon Adventure

A private, LLM-driven text adventure game. Administrators author stories in
plain language with an LLM's help; players sign in with a Microsoft account
and play them by typing what they want to do.

Backend: Python on Azure Functions. Frontend: React SPA on Azure Static Web
Apps. Data: Cosmos DB (serverless). Narration and story generation: Azure AI
Foundry (Azure OpenAI). Access is restricted to an explicit,
admin-provisioned list of Microsoft accounts (see
[Constitution](.specify/memory/constitution.md)).

## Features

Every capability is specified before it is built, one numbered folder per
feature under [`specs/`](specs/). A folder is renamed with a `-done` suffix
once its task list is complete; the rest are in flight.

**Playing**

- [Core gameplay](specs/008-core-gameplay-done/spec.md) — the play loop: free-form natural-language turns, LLM narration, content-safety screening of player input, sessions exclusive to the player who started them, and configurable completion (time limit, success criteria, fail criteria)
- [Adventure and character setup](specs/006-adventure-and-character-setup/spec.md) — browse published stories, name a character, pick a character type, then start
- [Save and continue](specs/009-save-and-continue/spec.md) — save progress, resume a session later, and be prompted to save on sign-out
- [Persistent nav redesign](specs/022-persistent-nav-redesign-done/spec.md) — persistent top navigation and the Modernist design system ([`specs/designs/`](specs/designs/README.md))
- [SPA refresh button](specs/019-spa-refresh-button/spec.md) — in-app refresh, so a browser reload never throws a player out of the app

**Authoring (administrators)**

- [Story creation](specs/004-story-creation-done/spec.md) — guided story-creation wizard; a plain-language idea becomes a suggested world prompt, character types and completion criteria, then a persisted story
- [Story editing and review](specs/012-story-editing-and-review/spec.md) — review and edit existing stories, view and download the full story configuration
- [Story import](specs/011-story-import/spec.md) — upload a story configuration file, validated, as a new story or an overwrite
- [Story test-play](specs/010-story-test-play/spec.md) and [story publish test-play gate](specs/017-story-publish-test-play-gate/spec.md) — test-play a draft before it ships, and require that test play before publishing
- [Story publishing](specs/005-story-publishing-done/spec.md) — explicit publish/unpublish; publishing makes a story available to all players
- [Story delete](specs/025-story-delete/spec.md) — confirmed, destructive delete that also removes in-progress sessions based on that story
- [Account provisioning](specs/003-account-provisioning-done/spec.md) and [account listing](specs/014-account-listing/spec.md) — seed the first administrator, grant/revoke access by email, view provisioned accounts

**Platform**

- [Login and access control](specs/002-login-and-access-control-done/spec.md) — Entra ID sign-in and Player/Administrator roles
- [Azure infrastructure provisioning](specs/007-azure-infrastructure-provisioning/spec.md) — Terraform-provisioned Azure resources
- [Keyless Azure authentication](specs/015-keyless-azure-authentication-done/spec.md) — Managed Identity and federated OIDC everywhere; no stored credentials
- [Environment configuration externalization](specs/016-environment-configuration-externalization/spec.md) — configuration read from environment-scoped sources, never hardcoded
- [OpenTelemetry observability](specs/013-opentelemetry-observability/spec.md) and [observability resilience](specs/018-observability-resilience/spec.md) — end-to-end OpenTelemetry, including per-call LLM token counts and cost, that degrades safely when the sink is unavailable
- [Azure monitoring dashboard](specs/024-azure-monitoring-dashboard/spec.md) — source-controlled Azure dashboard for failures, performance, usage and estimated cost
- [CI/CD foundation](specs/001-ci-cd-foundation-done/spec.md), [CI/CD pipeline optimization](specs/023-cicd-pipeline-optimization/spec.md), [Terraform apply gating](specs/020-terraform-apply-gating-done/spec.md), and [npm dependency audit](specs/021-npm-dependency-audit-done/spec.md) — the pipeline, its gates, and dependency hygiene

## Architecture

```
Browser — React SPA (MSAL sign-in)  ──hosted on──►  Azure Static Web Apps
   │  Authorization: Bearer <Entra ID token>
   ▼
Azure Functions (Python, Flex Consumption, system-assigned Managed Identity)
   │  token validation → provisioned-account lookup by email → oid bind/verify
   │
   ├─ Cosmos DB (serverless) ─── private endpoint
   │     provisionedAccountEntries · stories · storyDrafts
   │     playSessions · testPlaySessions · playerContentSafetyStandings
   │
   └─ Azure AI Foundry (Azure OpenAI) ─── private endpoint
         narrative turns and story generation
                 │
                 ▼
   Application Insights / Log Analytics  ◄── OpenTelemetry from frontend and backend
```

HTTP routes are registered in
[`src/backend/function_app.py`](src/backend/function_app.py) under `/api/…`
(`auth/*`, `manage/*` for administrators, `game/*` for players) — see
[src/backend/README.md](src/backend/README.md) for the endpoint table.

## Authentication & access control

- **No anonymous access, anywhere.** Every page and every API endpoint
  requires a valid Microsoft Entra ID token (Constitution Principle II).
- **Allow-list only.** A Microsoft account can sign in only if an
  administrator has provisioned its email address. The first administrator is
  seeded from configuration (`SEED_ADMIN_EMAIL`); every other account is
  granted through the admin UI.
- **Email first, `oid` thereafter.** A provisioned entry matches on email on
  first sign-in and binds to that account's Entra object ID; later sign-ins
  are verified against the binding, so a re-used email address cannot inherit
  someone else's access.
- **Two roles — Player and Administrator** — and an account may hold both.
  Authorization is enforced server-side in the Functions backend; the React
  navigation only reflects it, it never grants it.
- **No stored credentials.** Functions reaches Cosmos DB, Storage and AI
  Foundry over private endpoints using its own system-assigned Managed
  Identity, and GitHub Actions authenticates to Azure via federated OIDC.

Setup and troubleshooting: [docs/ADMIN_SETUP.md](docs/ADMIN_SETUP.md),
[docs/LOGIN_INSTRUCTIONS.md](docs/LOGIN_INSTRUCTIONS.md).

## Infrastructure

Everything lives in one pre-existing `llm-dungeon` resource group (West
Europe) and is defined in Terraform under
[`infrastructure/terraform/`](infrastructure/terraform): VNet with private
endpoints, Functions (Flex Consumption, with always-ready instances scheduled
on only during development hours), Static Web App, Storage, Cosmos DB, AI
Foundry, Log Analytics + Application Insights, a monthly budget alert, and a
source-controlled Portal dashboard with a cost workbook. `infrastructure/tests/`
holds live drift/regression suites, and `infrastructure/scripts/bootstrap.sh`
does the one-time Terraform-backend and GitHub-OIDC setup.

Detail: [docs/INFRASTRUCTURE.md](docs/INFRASTRUCTURE.md).

## CI/CD

CI and CD are fully separated — merging to `main` never deploys anything.

- **On push / PR:** the full backend (pytest) and frontend (vitest) suites
  run and gate the merge. A change whose files are all docs/specs skips the
  test and build jobs entirely.
- **On merge to `main`:** frontend and backend are versioned by
  `semantic-release` (path-diff filtered) and built into an immutable
  artifact attached to a GitHub Release — the durable, re-usable cache. No
  deploy job exists in any build workflow.
- **Deploy is always manual** (`workflow_dispatch`) for frontend, backend and
  infrastructure, taking an explicit version or defaulting to the latest
  build. Infrastructure deploys run validate → test → plan → apply, applying
  the exact plan from that run behind a human approval gate on the
  `production-infra` environment.
- **Required checks:** `test`, `check-title`, `actionlint`,
  `structure-test`, `release-fixtures-test` — the five contexts the `main`
  ruleset requires. A branch must also be up to date with `main` to merge.

Detail: [.github/workflows/README.md](.github/workflows/README.md),
[CONTRIBUTING.md](CONTRIBUTING.md),
[CI/CD Troubleshooting Guide](docs/CI_CD_TROUBLESHOOTING.md).

## Repository conventions

- **The constitution is the top authority.**
  [`.specify/memory/constitution.md`](.specify/memory/constitution.md) governs
  testing, security, observability, stack choices, scope, UI/accessibility and
  the human/AI division of labour. Code and specs are held to it.
- **Spec-driven development.** Features are specified, planned and broken into
  tasks before implementation, using the spec-kit commands
  (`/speckit-specify` → `/speckit-plan` → `/speckit-tasks` →
  `/speckit-implement`) whose templates and scripts live in
  [`.specify/`](.specify). A spec covers at most two user stories — larger
  ones are split into their own numbered specs.
- **Pull requests only.** Direct pushes to `main` are blocked; PRs need
  passing checks and a review pass via Claude Code's `/code-review` skill
  (tier per the triage rule in
  [CONTRIBUTING.md](CONTRIBUTING.md#5-review)), and are merged by a human,
  always by squash. The ruleset requires no approving reviews — this
  project has one maintainer.
- **Conventional Commit PR titles.** `type(scope): description`, validated by
  the `check-title` gate. Because the repo squash-merges, the PR title *is*
  the commit on `main` and is what `semantic-release` reads to compute the
  next version. Allowed types and scopes:
  [`scripts/pr-title-config.js`](scripts/pr-title-config.js).
- **AI agent division of labour.** Claude Code does local development, pushes
  branches and opens PRs (labelled `AI Generated` and `Claude`); review runs
  through Claude Code's `/code-review` skill on request; a human merges.
  Claude never merges. See [CLAUDE.md](CLAUDE.md) and Constitution
  Principle XIII.
- **One worktree and devcontainer per spec.** [`bin/wt`](bin/wt) creates an
  isolated git worktree with its own container so several specs can be worked
  in parallel —
  [docs/WORKTREE_CONTAINER_WORKFLOW.md](docs/WORKTREE_CONTAINER_WORKFLOW.md).
- **Dependency hygiene.** Dependabot watches frontend npm packages weekly and
  `npm run audit:frontend` fails on high-severity advisories.

## Repository layout

| Path | What's there |
|---|---|
| [`src/backend/`](src/backend) | Python Azure Functions app — API handlers, services, models, observability |
| [`src/frontend/`](src/frontend) | React SPA — pages, components, MSAL wiring, design tokens |
| [`infrastructure/`](infrastructure) | Terraform, infrastructure tests, bootstrap scripts |
| [`.github/workflows/`](.github/workflows) | CI/CD pipelines |
| [`specs/`](specs) | One folder per feature: spec, plan, tasks, contracts, research; plus [`designs/`](specs/designs) |
| [`docs/`](docs) | Cross-cutting guides linked from this README |
| [`scripts/`](scripts) | Repo tooling (PR-title config, workflow checks, release fixtures) |
| [`utilities/`](utilities) | Human-run maintenance scripts, e.g. branch/worktree cleanup |
| [`.specify/`](.specify) | Spec-kit templates, scripts and the constitution |

## Getting started

- Backend: [src/backend/README.md](src/backend/README.md)
- Frontend: [src/frontend/README.md](src/frontend/README.md)
- Infrastructure (Terraform, CI/CD, bootstrap): [docs/INFRASTRUCTURE.md](docs/INFRASTRUCTURE.md)
- Signing in and administering access: [docs/LOGIN_INSTRUCTIONS.md](docs/LOGIN_INSTRUCTIONS.md), [docs/ADMIN_SETUP.md](docs/ADMIN_SETUP.md)
- Contributing and the PR workflow: [CONTRIBUTING.md](CONTRIBUTING.md)
- Working on a spec in its own worktree/container: [docs/WORKTREE_CONTAINER_WORKFLOW.md](docs/WORKTREE_CONTAINER_WORKFLOW.md)
- First-time login/access-control deployment steps: [docs/DEPLOYMENT_RUNBOOK.md](docs/DEPLOYMENT_RUNBOOK.md)
