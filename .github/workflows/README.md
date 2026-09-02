# GitHub Actions Workflows

This directory contains the automated workflows and CI/CD pipelines for the **LLM Dungeon Adventure** repository.

CI (test, build, version, cache) and CD (deploy) are fully separated
(`specs/023-cicd-pipeline-optimization`): CI runs automatically on push and
on merge to `main`; CD (deploy) is **always** a separate, explicitly
triggered action — for all three components, including infrastructure.
Merging to `main` never deploys anything by itself.

---

## Workflows Overview

| Workflow File | Name | Trigger | Description |
| :--- | :--- | :--- | :--- |
| [`test.yml`](test.yml) | **Test Suite** | `push` (any branch) and `pull_request` | CI test gate. Runs Python backend tests (pytest) and React frontend tests (npm test) on every push and PR. Skipped entirely when every changed file is non-testable content (docs/specs/markdown — see below). Merge gate required status checks: `test`, `frontend-test`. |
| [`frontend-build.yml`](frontend-build.yml) | **Frontend Build** | `push` to `main` (paths: `src/frontend/**`) | CI. Computes the next version, builds `dist/`, attaches it as a `frontend-v<version>` GitHub Release asset. No deploy job. |
| [`backend-build.yml`](backend-build.yml) | **Backend Build** | `push` to `main` (paths: `src/backend/**`, `src/function_app.py`, `src/requirements.txt`) | CI. Computes the next version, vendors dependencies, attaches a `backend-v<version>` GitHub Release asset. No deploy job. |
| [`infrastructure-build.yml`](infrastructure-build.yml) | **Infrastructure Build** | `push` to `main` (paths: `infrastructure/**`) | CI. Validates and plans Terraform, computes the next version, attaches the saved plan as an `infrastructure-v<version>` GitHub Release asset. No apply job. |
| [`_build-frontend.yml`](_build-frontend.yml), [`_build-backend.yml`](_build-backend.yml), [`_build-infrastructure.yml`](_build-infrastructure.yml) | **Build (reusable)** | `workflow_call` only | The single implementation each `*-build.yml` above calls, and that each `*-deploy.yml` below calls on a cache-miss-on-latest. Never triggered directly. Idempotent: skips its own build/package steps if the target version's artifact is already cached. |
| [`frontend-deploy.yml`](frontend-deploy.yml) | **Frontend Deploy** | `workflow_dispatch` only (`version` input) | CD. Resolves the requested (or latest-at-execution-time) version, deploys its cached artifact as-is — building it first only if it isn't cached yet. No approval gate. |
| [`backend-deploy.yml`](backend-deploy.yml) | **Backend Deploy** | `workflow_dispatch` only (`version` input) | CD. Same pattern as frontend, for the Azure Functions backend. No approval gate. |
| [`infrastructure-deploy.yml`](infrastructure-deploy.yml) | **Infrastructure Deploy** | `workflow_dispatch` only (`version` input) | CD. Same pattern, but the `apply` job targets the `production-infra` environment, which requires human approval before it applies (see below). |
| [`pr-title-check.yml`](pr-title-check.yml) | **PR Title Check** | `pull_request_target` (opened, edited, synchronize, reopened) | Required check. Validates the PR title follows `type(scope): description` (Conventional Commits) — this repo merges by squash, so the PR title is the sole commit message that reaches `main` and the one `semantic-release` reads. |
| [`workflow-lint.yml`](workflow-lint.yml) | **Workflow Lint** | `pull_request` (paths: `.github/workflows/**`) | Required check. Runs `actionlint` against changed workflow files — syntax/schema only. |
| [`workflow-structure-test.yml`](workflow-structure-test.yml) | **Workflow Structure Test** | `pull_request` (paths: build/deploy workflows, the shared build/detect-non-testable-changes actions, `scripts/test-workflow-structure.js`, `scripts/test-non-testable-detection.js`) | Required check. Asserts the job/step *shape* `actionlint` can't check — see `scripts/test-workflow-structure.js` for the full assertion list (no deploy job in any `*-build.yml`; no push/PR trigger on any `*-deploy.yml`; idempotent build-skip; no rebuild in `deploy`/`apply`; approval-gate asymmetry; `resolve-version` before `ensure-artifact`; the not-found failure path; the build-on-demand fallback). |
| [`release-fixtures-test.yml`](release-fixtures-test.yml) | **Release Fixtures Test** | `pull_request` (paths: `.releaserc.json` files, the reusable build workflows, `scripts/test-release-fixtures.js`) | Required check. Exercises `semantic-release-monorepo`'s path-diff commit filtering combined with `@semantic-release/commit-analyzer`'s bump-type logic against synthetic commits for all three components, including vertical-slice cases (a single commit touching two or all three components) — the regression guard for a cross-component version-bump bug found during this feature's `/speckit-analyze` review. |
| [`infrastructure-tests.yml`](infrastructure-tests.yml) | **Infrastructure Tests** | `schedule` (nightly), `workflow_dispatch` | Live drift/regression check against the real deployed Azure infrastructure. Independent of the build/deploy pipeline above. |
| [`terraform-validate.yml`](terraform-validate.yml) | **Terraform Validate** | `pull_request` (paths: `infrastructure/**`) | Runs `terraform validate` and format checks at PR time. |

---

## CI: build/version/cache on merge to `main`

For each of frontend, backend, and infrastructure, merging a tested change
to `main` runs that component's `*-build.yml` workflow, which calls its
matching `_build-*.yml` reusable workflow:

1. Computes the next version via `semantic-release` (`semantic-release-monorepo`,
   so eligibility is gated by which paths a commit's diff actually
   touched, not by the PR title's scope word), creating a git tag
   (`frontend-v*` / `backend-v*` / `infrastructure-v*`) and GitHub Release
   when a qualifying commit exists. Never pushes a commit to `main` — only
   tags/releases.
2. Checks whether that version's artifact is already attached to the
   release (idempotency: a second build request for an already-cached
   version reuses it rather than re-building).
3. If not cached: builds the artifact (frontend: zipped `dist/`; backend:
   zipped `src` deploy root with dependencies vendored into
   `.python_packages`; infrastructure: the saved Terraform plan + a
   human-readable rendering), stamps it with the version, and attaches it
   to the release as a single file — the durable, immutable, indefinitely
   retained cache (not `actions/upload-artifact`, which expires).

None of `frontend-build.yml`/`backend-build.yml`/`infrastructure-build.yml`
contains a deploy or apply job — CI's job ends at a cached, ready-to-ship
artifact.

## Non-testable-change skip (docs/specs-only pushes)

`.github/actions/detect-non-testable-changes` computes whether **every**
file changed in a push/PR is non-testable content (`**/*.md`, `specs/**`,
`docs/**`, `LICENSE`, `CONTRIBUTING.md`) — by content type, regardless of
which directory the files live in. `test.yml` and every `*-build.yml`
wire this in: if the entire change set is non-testable, no test or build
job runs. The moment even one changed file is testable/buildable, the
full pipeline runs normally for every affected component, including for
any docs files bundled in that same change.

## CD: deploy is always a separate, manual action

Deploying is never a side effect of a push or merge — `frontend-deploy.yml`,
`backend-deploy.yml`, and `infrastructure-deploy.yml` are each triggered
**only** by `workflow_dispatch`, accepting one input:

| Input | Required | Default | Meaning |
|---|---|---|---|
| `version` | no | `""` (blank) | The exact `<component>-v<version>` to deploy. Blank means "resolve to the latest available version at execution time." |

Each deploy workflow's job graph:

1. **`resolve-version`** — if `version` was supplied, verifies a matching
   tag exists (failing clearly, with no fallback, if it doesn't — a
   version that was never built cannot be deployed). If blank, defers
   resolution to `build-on-demand` below, evaluated fresh at execution
   time so a version that lands between trigger and execution is picked
   up correctly.
2. **`build-on-demand`** — calls the matching `_build-*.yml` reusable
   workflow whenever the requested version isn't confirmed cached yet.
   Cheap when nothing changed (the reusable workflow's own idempotency
   check short-circuits it); this is what lets "deploy latest" build the
   artifact first, in the same request, the first time a component has
   never been built at all.
3. **`ensure-artifact`** — downloads the resolved version's cached
   artifact.
4. **`deploy`** / **`apply`** — deploys/applies that artifact exactly as
   downloaded. No install, build, or re-plan step anywhere in this job.

Frontend and backend's `deploy` job runs straight through once triggered
— no approval step. Infrastructure's `apply` job targets the
`production-infra` GitHub Environment, which **must** be configured (in
GitHub's UI, not in this YAML) with a required-reviewer protection rule
that has **"Prevent self-review" enabled**, with the requesting human set
as the required reviewer. An AI agent can dispatch
`infrastructure-deploy.yml` and complete validation, but only that human
can supply the approval — never the agent, and never the identity that
dispatched the run.

### Deploying via an AI agent (e.g. Claude)

An AI agent uses the standard GitHub CLI against the same
`workflow_dispatch` interface a human would use — no bespoke API:

```bash
# Check whether a cached "latest" artifact already exists, for context
gh release list --repo <owner>/<repo> | grep '^frontend-v'

# Trigger the deploy — explicit version, or blank for latest
gh workflow run frontend-deploy.yml -f version=1.4.0
gh workflow run frontend-deploy.yml -f version=""
```

The workflow's own `resolve-version`/`build-on-demand`/`ensure-artifact`
jobs perform the authoritative cache-check/build-if-missing logic
server-side regardless of what the agent checked beforehand — the agent's
`gh release list` check is an optimization/explanation step for the user,
not a trust boundary. For infrastructure, the agent can run the same
`gh workflow run infrastructure-deploy.yml -f version=...` command, but
the run will pause awaiting the requesting human's approval before it
applies — the agent cannot supply that approval itself.

### One-time rollout step: seed the version baseline

`semantic-release` computes `1.0.0` for a component's first-ever release
when no prior tag exists. This project's baseline is `0.1.0` instead
(frontend continuing its existing manifest version; backend and
infrastructure starting at the same baseline for consistency — see
`spec.md`'s Clarifications and `research.md` Decision 9). Each
`_build-*.yml` workflow refuses to run until this exists, so **once this
feature has merged to `main`**, a repo admin must run, once:

```bash
git tag backend-v0.1.0 <commit-sha-on-main>
git tag frontend-v0.1.0 <commit-sha-on-main>
git tag infrastructure-v0.1.0 <commit-sha-on-main>
git push origin backend-v0.1.0 frontend-v0.1.0 infrastructure-v0.1.0
```

(`<commit-sha-on-main>` — any commit on `main`, typically its current HEAD
at rollout time.)

### One-time rollout step: configure the `production-infra` environment

In the repository's Settings → Environments → `production-infra`, enable
"Required reviewers", add the requesting human as the reviewer, and
enable "Prevent self-review". Without this, `infrastructure-deploy.yml`'s
approval gate does not actually prevent the dispatching identity from
approving its own run (FR-011a).

### One-time rollout step: require the new checks

Add these job names to `main`'s required-status-checks branch protection
list (they won't block merges until they exist as real check runs, and
won't exist until this feature's PR has merged and run at least once):

- `PR Title Check / check-title`
- `Workflow Lint / actionlint`
- `Workflow Structure Test / structure-test`
- `Release Fixtures Test / release-fixtures-test`

---

## Test Suite Workflow (`test.yml`)

### Job Details

1. **`changes`**: runs `.github/actions/detect-non-testable-changes` to
   decide whether `test`/`frontend-test` should run at all (see above).
2. **`test` (Backend Test Suite)**:
   - **Runner**: `ubuntu-latest`
   - **Timeout**: 30 minutes
   - **Environment**: Python 3.11, with `pip` dependency caching
   - **Steps**: checkout, setup Python, install dependencies from
     `requirements*.txt` files, run `pytest -v`.
   - **Required Status Check**: registers the `test` check required by
     repository branch rulesets.
3. **`frontend-test` (Frontend Test Suite)**:
   - **Runner**: `ubuntu-latest`
   - **Timeout**: 30 minutes
   - **Environment**: Node.js 24, with `npm` dependency caching
   - **Steps**: checkout, install dependencies, dependency audit, run
     `npm test`.

---

## Local Verification

Before pushing, you can execute the same checks locally:

```bash
# Backend pytest suite
pytest -v

# Frontend suite
cd src/frontend && npm test

# Workflow lint (requires actionlint on PATH; see
# https://github.com/rhysd/actionlint/blob/main/docs/install.md)
actionlint .github/workflows/*.yml

# Workflow structure / release fixture / non-testable-detection / PR-title tests
cd scripts && npm ci
npm run test:workflow-structure
npm run test:release-fixtures
npm run test:non-testable-detection
npm run test:pr-title
```
