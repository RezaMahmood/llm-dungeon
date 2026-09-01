# GitHub Actions Workflows

This directory contains the automated workflows and CI/CD pipelines for the **LLM Dungeon Adventure** repository.

---

## Workflows Overview

| Workflow File | Name | Trigger | Description |
| :--- | :--- | :--- | :--- |
| [`test.yml`](test.yml) | **Test Suite** | `pull_request` (opened, synchronize, reopened) | Primary CI test gate. Runs Python backend tests (pytest) and React frontend tests (npm test) on pull requests. Merge gate required status checks: `test`, `frontend-test`. |
| [`backend-deploy.yml`](backend-deploy.yml) | **Backend Deploy** | `push` to `main` (paths: `src/backend/**`, `src/function_app.py`, `src/requirements.txt`) | `test` → `release` → `build` → `deploy`. Packages and deploys the Azure Functions backend from the exact artifact `build` produced — `deploy` never reinstalls dependencies or triggers Azure's Oryx remote build. |
| [`frontend-deploy.yml`](frontend-deploy.yml) | **Frontend Deploy** | `push` to `main` (paths: `src/frontend/**`) | `test` → `release` → `build` → `deploy`. Builds once and deploys the exact `dist/` artifact `build` produced to Azure Static Web Apps — `deploy` never re-runs `npm install`/`npm run build`. |
| [`pr-title-check.yml`](pr-title-check.yml) | **PR Title Check** | `pull_request_target` (opened, edited, synchronize, reopened) | Required check. Validates the PR title follows `type(scope): description` (Conventional Commits) — this repo merges by squash, so the PR title is the sole commit message that reaches `main` and the one `semantic-release` reads. |
| [`workflow-lint.yml`](workflow-lint.yml) | **Workflow Lint** | `pull_request` (paths: `.github/workflows/**`) | Required check. Runs `actionlint` against changed workflow files — syntax/schema only. |
| [`workflow-structure-test.yml`](workflow-structure-test.yml) | **Workflow Structure Test** | `pull_request` (paths: deploy/terraform-apply workflows, `scripts/test-workflow-structure.js`) | Required check. Asserts the job/step *shape* `actionlint` can't check: no rebuild in `deploy` (US1), the `concurrency` block (US2), and `terraform-apply.yml` applying the saved plan (US5). |
| [`release-fixtures-test.yml`](release-fixtures-test.yml) | **Release Fixtures Test** | `pull_request` (paths: `.releaserc.json` files, deploy workflows, `scripts/test-release-fixtures.js`) | Required check. Exercises `semantic-release-monorepo`'s path-diff commit filtering combined with `@semantic-release/commit-analyzer`'s bump-type logic against synthetic commits, including the vertical-slice case — the regression guard for a cross-component version-bump bug found during this feature's `/speckit-analyze` review. |
| [`infrastructure-tests.yml`](infrastructure-tests.yml) | **Infrastructure Tests** | `pull_request` (paths: `infrastructure/**`) | Validates Terraform configuration and executes infrastructure unit tests. |
| [`terraform-validate.yml`](terraform-validate.yml) | **Terraform Validate** | `pull_request` (paths: `infrastructure/**`) | Runs `terraform validate` and format checks. |
| [`terraform-apply.yml`](terraform-apply.yml) | **Terraform Apply** | `push` to `main` (paths: `infrastructure/**`) | `validate` → `test` → `apply`. `apply` applies the exact plan `validate` generated and gated, rather than re-planning immediately before applying. |

---

## Backend/Frontend Deploy Job Graph

Both `backend-deploy.yml` and `frontend-deploy.yml` follow the same four-job graph (`specs/023-cicd-pipeline-optimization`):

1. **`test`** — runs the existing test suite (pytest / vitest) with dependency caching. Blocks the rest of the chain on failure.
2. **`release`** — runs `semantic-release` (via `semantic-release-monorepo`, so eligibility is gated by which paths a commit's diff actually touched, not by the PR title's scope word) to compute this component's next SemVer, creating a git tag (`backend-v*` / `frontend-v*`) and GitHub Release when a qualifying commit exists. Never pushes a commit to `main` — only tags/releases. Exposes a `version` output for `build` to consume.
3. **`build`** — produces the exact deployable artifact (backend: a zip of the `src` deploy root with dependencies vendored into `.python_packages`; frontend: the built `dist/`), stamped with `release`'s version (`VERSION` file / `dist/version.json`), uploaded once via `actions/upload-artifact`.
4. **`deploy`** — downloads that same artifact and deploys it as-is. No install/build step of its own.

Each workflow also declares a literal, per-component `concurrency` group (`deploy-backend` / `deploy-frontend`) with `cancel-in-progress: true`, so a newer push to `main` cancels an in-flight older run for that component before it deploys.

### One-time rollout step: seed the version baseline

`semantic-release` computes `1.0.0` for a component's first-ever release when no prior tag exists. This project's baseline is `0.1.0` instead (frontend continuing its existing manifest version; backend starting at the same baseline for consistency — see `spec.md`'s Clarifications). The `release` job in each workflow refuses to run until this exists, so **once this feature has merged to `main`**, a repo admin must run, once:

```bash
git tag backend-v0.1.0 <commit-sha-on-main>
git tag frontend-v0.1.0 <commit-sha-on-main>
git push origin backend-v0.1.0 frontend-v0.1.0
```

(`<commit-sha-on-main>` — any commit on `main`, typically its current HEAD at rollout time.)

### One-time rollout step: require the new checks

Add these job names to `main`'s required-status-checks branch protection list (they won't block merges until they exist as real check runs, and won't exist until this feature's PR — including this workflow-lint/-structure-test/-release-fixtures-test infrastructure — has merged and run at least once):

- `PR Title Check / check-title`
- `Workflow Lint / actionlint`
- `Workflow Structure Test / structure-test`
- `Release Fixtures Test / release-fixtures-test`

---

## Test Suite Workflow (`test.yml`)

### Job Details
1. **`test` (Backend Test Suite)**:
   - **Runner**: `ubuntu-latest`
   - **Timeout**: 30 minutes (per FR-004a)
   - **Environment**: Python 3.11, with `pip` dependency caching
   - **Steps**:
     - Checkout code (`actions/checkout@v4`)
     - Setup Python runtime (`actions/setup-python@v5`)
     - Upgrade pip and install dependencies from `requirements*.txt` files
     - Execute `pytest -v` across all test suites
   - **Required Status Check**: This job registers the `test` check required by repository branch rulesets.

2. **`frontend-test` (Frontend Test Suite)**:
   - **Runner**: `ubuntu-latest`
   - **Timeout**: 30 minutes
   - **Environment**: Node.js 24, with `npm` dependency caching
   - **Steps**:
     - Check if `src/frontend/package.json` exists
     - Install dependencies (`npm install`)
     - Execute frontend tests (`npm test`)

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

# Workflow structure / release fixture / PR-title tests
cd scripts && npm ci
npm run test:workflow-structure
npm run test:release-fixtures
npm run test:pr-title
```
