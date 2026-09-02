# Contracts: Workflow Interfaces

This feature has no application API. Its "interfaces" are the trigger/input contracts of the GitHub Actions workflows themselves — what other tooling, branch protection rules, human maintainers, and AI agents rely on to interact with CI and CD correctly. These are the contracts implementation and `/speckit-tasks` must honor exactly.

## CI workflows (automatic — test-on-push, build/version/cache-on-merge for frontend/backend)

| Workflow | Trigger | Path scope | Contract |
|---|---|---|---|
| `test.yml` | `push` (any branch) **and** `pull_request` (opened, synchronize, reopened) | none (runs both suites; component-level skip handled by the `changes` job below) | MUST run the standard backend (pytest) and frontend (npm test) suites automatically on every push, per FR-001. MUST NOT run either suite if the "all changed files are non-testable" check (below) is true. `frontend-test` additionally skips its real work when no `src/frontend/**` paths changed (job still always runs, so it remains a viable required-check candidate). |
| `frontend-build.yml` | `push` to `main`, paths: `src/frontend/**` | `src/frontend/**` | On a qualifying merge: run `semantic-release` (path-scoped) to compute next version → build `dist/` → attach as release asset (FR-004/FR-005/FR-006/FR-007). MUST NOT include a `deploy` job. |
| `backend-build.yml` | `push` to `main`, paths: `src/backend/**`, `src/function_app.py`, `src/requirements.txt` | as listed | Same contract as `frontend-build.yml`, for backend's artifact shape. MUST NOT include a `deploy` job. |

**Infrastructure has no CI build workflow** — no versioning, no persistent artifact (post-merge amendment; see research.md Decision 9). Its existing `terraform-validate.yml` (PR-time) and `infrastructure-tests.yml` (scheduled) are unchanged and outside this feature's scope. Infrastructure's own validation/testing happens inside `infrastructure-deploy.yml` itself (below), fresh on every deploy trigger.

### Non-testable-artifact skip contract (FR-019/FR-020)

Every CI workflow above (via a shared `changes` job pattern) MUST expose a boolean output — e.g. `all-non-testable` — computed as: `true` if and only if every file in the push/PR's changed-file list matches the non-testable glob set (`**/*.md`, `specs/**`, `docs/**`, `LICENSE`, `CONTRIBUTING.md`, and equivalents); `false` otherwise (including when the change set is empty of any files, which cannot occur for a real push).

- When `all-non-testable == true`: every downstream test/build job in that workflow run MUST be skipped (via `if: needs.changes.outputs.all-non-testable != 'true'` or equivalent) — no test suite runs, no build/version/cache pipeline runs, for any component.
- When `all-non-testable == false`: the normal per-component path-scoped pipeline runs exactly as it does today, with no reduction — including for any non-testable files bundled in the same change.

## CD workflows (manual — deploy)

| Workflow | Trigger | Approval gate | Contract |
|---|---|---|---|
| `frontend-deploy.yml` | `workflow_dispatch` **only**, `version` input | none | See shared frontend/backend CD contract below. Deploy job runs immediately once triggered (FR-011b). |
| `backend-deploy.yml` | `workflow_dispatch` **only**, `version` input | none | Same. |
| `infrastructure-deploy.yml` | `workflow_dispatch` **only**, no inputs | Target environment (e.g. `production-infra`) has a required-reviewer protection rule | No version — see infrastructure CD contract below. The `apply` job MUST target that environment, and MUST NOT run until a human approves the pending deployment in the GitHub UI/API (FR-011a). An AI agent MAY trigger the workflow and MAY complete validation/planning, but MUST NOT be the entity that supplies the approval. |

**None of the three CD workflows may declare a `push` or `pull_request` trigger** (FR-010) — this is the single most important structural assertion `workflow-structure-test.yml` must enforce for this feature.

### Frontend/backend `workflow_dispatch` input contract

```yaml
on:
  workflow_dispatch:
    inputs:
      version:
        description: "Exact <component>-v<version> to deploy. Leave blank to deploy the latest available version at execution time."
        required: false
        type: string
        default: ""
```

### Frontend/backend CD job-graph contract

1. **`resolve-version`**: if `version` input is non-blank, use it verbatim. If blank, query that component's release tags and select the highest SemVer (evaluated now, at run time — FR-013). Output: `resolved_version`.
2. **`ensure-artifact`**: check whether a release/tag `<component>-v<resolved_version>` exists with the expected asset attached.
   - **Cache hit**: download the asset unchanged. Proceed to deploy.
   - **Cache miss, and `resolved_version` is the latest tag that would exist if built from current `main`** (the "latest, not yet built" case — User Story 5 / FR-015): invoke the shared `workflow_call` build workflow (research.md Decision 5) to produce and cache it, then proceed to deploy.
   - **Cache miss, explicit version requested that doesn't correspond to any tagged/buildable state**: fail the run with a clear error (FR-016) — no fallback substitution, no unrequested build.
3. **`deploy`**: deploy the artifact obtained in step 2 as-is — no install, build, or re-plan step (FR-009).

### Infrastructure CD job-graph contract (no versioning — FR-021/FR-022)

`infrastructure-deploy.yml` declares `workflow_dispatch` with **no inputs**. Its job graph:

1. **`validate-and-test`**: `terraform fmt`/`validate` plus the infrastructure test suite, against the current state of `main` at execution time.
2. **`plan`**: `terraform plan`, uploaded as a same-run artifact (`actions/upload-artifact`) — never a persistent GitHub Release.
3. **`apply`**: downloads that same-run plan and applies it exactly (no re-plan step) — this is the job gated by the required-reviewer environment (FR-011a).

### AI-agent usage contract (informational — realized entirely through the CLI, not a new API)

An AI agent (e.g., Claude) satisfies User Story 5 by using the standard GitHub CLI against the interfaces above — no bespoke endpoint is introduced:

```bash
# Frontend/backend: check for a cached "latest" artifact before deciding
# whether a build is implied, then trigger — explicit version, or blank
gh release list --repo <owner>/<repo> | grep '^frontend-v'
gh workflow run frontend-deploy.yml -f version=1.4.0
gh workflow run frontend-deploy.yml -f version=""

# Infrastructure: no version to resolve — just dispatch. apply pauses for
# the requesting human's approval; the agent cannot supply it.
gh workflow run infrastructure-deploy.yml
```

For frontend/backend, the `ensure-artifact` job (above) performs the authoritative cache-check/build-if-missing logic server-side regardless of what the agent checked beforehand — the agent's own `gh release list` check is an optimization/explanation step, not a trust boundary.

## Required status checks (branch protection surface)

| Check name (job) | Workflow | Contract |
|---|---|---|
| PR title format | `pr-title-check.yml` | Unchanged from the existing implementation — MUST fail if the PR title doesn't parse as Conventional Commits `type(scope): description`. The `scope` word remains descriptive only; versioning eligibility is path-diff-based (per this repo's existing `semantic-release-monorepo` setup), not scope-gated. |
| `test` / `frontend-test` | `test.yml` | MUST run on every push and PR (FR-001), except when `all-non-testable == true` (FR-019). |
| Workflow lint (`actionlint`) | `workflow-lint.yml` | Unchanged — syntax/schema only. |
| Workflow structure assertion | `workflow-structure-test.yml` | MUST assert: no CD workflow has a `push`/`pull_request` trigger; frontend/backend's `workflow_dispatch` each declare a `version` input, infrastructure's declares none; infrastructure's deploy job targets the approval-gated environment and frontend/backend's do not; no CI workflow contains a `deploy`/`apply` job; infrastructure's `validate-and-test → plan → apply` order and never-re-plans-in-apply invariant. |
| Release fixture test | `release-fixtures-test.yml` | MUST cover frontend/backend's path-diff filtering fixtures, including the vertical-slice (both-component) commit case. Infrastructure is not covered — it isn't versioned. |
