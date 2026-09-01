# Implementation Plan: CI/CD Pipeline Optimization

**Branch**: `023-cicd-pipeline-optimization` | **Date**: 2026-09-01 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/023-cicd-pipeline-optimization/spec.md`

## Summary

Restructure the backend and frontend GitHub Actions workflows so each separates into distinct test → release → build → deploy jobs, with the deploy job always consuming the exact artifact the build job produced in that same run — eliminating the backend's redundant Azure Oryx remote build and any hidden rebuild risk in the frontend path. Add dependency caching and a committed frontend lockfile for speed and reproducibility. Add a per-component `concurrency` group with `cancel-in-progress: true` so a newer push to `main` cancels an in-flight older deploy for that component, which is the mechanism satisfying "abort on conflict/newer version." Add independent, automated Semantic Versioning for frontend and backend via `semantic-release`, with each component's release eligibility gated by **path-diff filtering** (does a given commit's diff actually touch this component's paths?) rather than by the PR title's scope word — since specs here are typically vertical slices that can touch multiple components in one commit, path-diff filtering is what correctly attributes each bump, while the PR title (the sole commit message reaching `main`, since this repo merges by squash) supplies the change type and descriptive content. Versioning publishes only a git tag and GitHub Release per component, deliberately never pushing a version-bump commit back to `main` so the constitution's "no direct pushes to main" rule is never at risk. Add a required PR-title format check so malformed titles are blocked before merge. Separately, fix `terraform-apply.yml` so its `apply` job applies the exact plan file `validate` already produced and had gated, instead of implicitly re-planning immediately before applying. Infrastructure versioning remains explicitly out of scope.

## Technical Context

**Language/Version**: YAML (GitHub Actions workflow definitions); Node.js 24 (frontend runtime + versioning tooling); Python 3.11 (backend runtime); Terraform (version pinned via the `TERRAFORM_VERSION` repo variable) — no application-level language changes.

**Primary Dependencies**: GitHub Actions (`actions/checkout`, `actions/setup-node`, `actions/setup-python`, `actions/upload-artifact`, `actions/download-artifact`, `azure/login`, `Azure/functions-action`, `Azure/static-web-apps-deploy`, `hashicorp/setup-terraform`); `semantic-release` plus a monorepo/path-scoping plugin, `@semantic-release/commit-analyzer`, `@semantic-release/release-notes-generator`, `@semantic-release/github` (no `@semantic-release/git` — see Research); a PR-title format-check GitHub Action.

**Storage**: N/A — no application data store is touched by this feature. Versions are persisted as git tags and GitHub Releases; build artifacts are persisted as GitHub Actions run artifacts.

**Testing**: Existing `pytest` (backend) and `vitest` (frontend) suites keep gating merges unchanged (FR-017). This feature's own new logic gets a dedicated automated test per user story (research.md decision #8): workflow-structure assertion scripts for US1 (no rebuild/install step in `deploy`), US2 (`concurrency` block present and correctly configured), and US5 (`apply` references the saved plan, no re-planning flags); a `semantic-release --dry-run` fixture test for US3 (including the vertical-slice case); and a PR-title-pattern unit test for US4 — plus an `actionlint` check across all changed workflows. quickstart.md's scenarios are a separate, additional layer: the Principle IX human-acceptance validation against the real deployed environment, not a substitute for the automated tests above.

**Target Platform**: GitHub Actions (`ubuntu-latest` runners) deploying to Azure Functions (backend) and Azure Static Web Apps (frontend); Azure via Terraform for infrastructure. No change to the deployed runtime platforms themselves.

**Project Type**: CI/CD pipeline configuration (GitHub Actions workflows + minimal versioning-tooling manifests) — not an application feature; no new user-facing surface.

**Performance Goals**: Backend and frontend deploy workflow wall-clock time decreases versus a pre-implementation baseline (directional per spec SC-001 — no fixed target, since the achievable reduction depends on unmeasured factors like Azure Oryx build time and current npm/pip install time).

**Constraints**: Constitution's "no direct pushes to main" rule (Development Workflow & Quality Gates) must not be violated by the versioning mechanism; the repo's actual merge strategy is squash-merge (confirmed from history), so per-commit linting is the wrong tool and PR-title linting is used instead (see Clarifications in spec.md); existing `production`/`production-infra` GitHub environments, required secrets/vars, and approval gates must be preserved as-is; `test.yml`'s PR-time triggers and path scope must not change beyond adding caching (FR-017).

**Scale/Scope**: Two independently versioned components (frontend, backend); one additional build-once/no-replan correctness fix for infrastructure apply (no versioning). Single environment tier (`production`) — no staging/multi-environment concerns introduced.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Meaningful, Automated Testing** — PASS (revised post-`/speckit-analyze`, findings C1 and G1). Existing backend/frontend automated test suites keep gating every PR and every deploy workflow run unchanged (FR-017). This feature's *own* new logic is covered by a dedicated automated test per user story, not only `actionlint`'s syntax checking: workflow-structure assertion tests for US1 (no rebuild/install step in `deploy`), US2 (`concurrency` block present and correctly configured), and US5 (`apply` references the saved plan, no re-planning flags); a `semantic-release --dry-run` fixture test for US3 exercising same-component, non-releasable, and vertical-slice commit scenarios; and a PR-title-pattern unit test for US4 (research.md decision #8). quickstart.md's manual scenarios remain as the Principle IX human-acceptance layer on top of all of these, not a substitute for them — the original plan's reliance on manual validation alone was corrected during two rounds of `/speckit-analyze`.
- **II. Secure-by-Default Access** — N/A. No user-facing page or API endpoint is added or changed.
- **III. Defined Technology Stack** — PASS. Backend stays Python/Azure Functions, frontend stays ReactJS/browser; `semantic-release` and its plugins are CI-only tooling dependencies (declared in per-component `package.json` files used solely for version tracking), not a change to the deployed application stack.
- **IV. Simplicity Over Premature Scale** — PASS. Design deliberately stays within each component's existing single workflow (multi-job, not multi-workflow), and explicitly excludes cross-workflow `workflow_run` orchestration and rollback/redeploy machinery per the spec's stated out-of-scope — no speculative infrastructure is added beyond what the five user stories require.
- **V. Continuous Integration Gate** — PASS. The existing PR-gated test suite requirement is preserved; the new PR-title format check is an additional required check, not a replacement.
- **VI. Observability & AI Cost Transparency** — N/A. No LLM interaction is touched by this feature.
- **VII. Zero-Trust Azure Resource Communication** — PASS. No new shared keys, connection strings, or public network paths are introduced. The backend deploy's pre-existing `AzureWebJobsStorage` key-sync step (a documented, already-justified exception for Flex Consumption) is unaffected by moving from remote-build to a pre-built artifact deploy.
- **VIII. UI Design System & Accessibility Compliance** — N/A. No UI is added or changed.
- **IX. User-Verified Acceptance Before Completion** — APPLIES. `tasks.md` must include a final acceptance task where a maintainer merges a real PR for each component and confirms, against the actual GitHub Actions run and the real Azure deployment, that the artifact-reuse, concurrency-cancellation, versioning, PR-title check, and Terraform apply-the-plan behaviors all work as specified — not merely that a workflow YAML lints correctly.
- **X. PII Protection by Design** — N/A. No PII is introduced, logged, or referenced by this feature.
- **XI. UI Design Pre-Agreement Before Implementation** — N/A. No UI is added or changed.
- **Development Workflow & Quality Gates — "no direct pushes to main"** — PASS BY DESIGN, flagged for visibility. The most likely way a semantic-versioning implementation could violate this rule is `semantic-release`'s common `@semantic-release/git` plugin, which pushes a version-bump/changelog commit directly to the release branch. This design deliberately excludes that plugin: `semantic-release` is configured to produce only a git tag and a GitHub Release (both non-branch-history writes) per component, and per-component `package.json` version fields are never bumped by automation — they exist solely so `semantic-release`'s tooling has a package manifest to run against. See Research decision on versioning tooling.

No violations requiring justification. Complexity Tracking table is not needed.

## Project Structure

### Documentation (this feature)

```text
specs/023-cicd-pipeline-optimization/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

This feature touches CI/CD configuration and adds minimal, tooling-only manifests — it does not add an application module. Existing repository layout, annotated with what this feature adds/changes:

```text
.github/workflows/
├── backend-deploy.yml        # CHANGED: split into test/release/build/deploy jobs,
│                              #   remote-build removed, concurrency group added
├── frontend-deploy.yml       # CHANGED: split into test/release/build/deploy jobs,
│                              #   deploy consumes build job's artifact, concurrency group added
├── test.yml                  # CHANGED: caching added only; triggers/scope unchanged (FR-017)
├── pr-title-check.yml         # NEW: required check validating PR title format
│                              #   (paired with a unit test, e.g. pr-title-check.test.*)
├── workflow-lint.yml          # NEW: required actionlint check on changed workflow files
├── terraform-apply.yml       # CHANGED: apply job consumes validate job's saved plan artifact
├── terraform-validate.yml    # UNCHANGED
├── infrastructure-tests.yml  # UNCHANGED
└── README.md                 # CHANGED: documents the new job graphs, concurrency groups,
                               #   path-diff-based version gating, and PR-title requirement

scripts/
├── test-workflow-structure.sh # NEW: asserts deploy/concurrency/terraform-apply job shape
│                              #   (US1, US2, US5 — one script, per-story assertion functions)
└── test-release-fixtures.sh   # NEW: asserts per-component version-bump behavior against
                               #   synthetic commits, including the vertical-slice case (US3)

src/backend/
├── package.json              # NEW: tooling-only manifest (name + version) for semantic-release;
│                              #   never published, never version-bumped by automation
├── .releaserc.json           # NEW: semantic-release config scoped to src/backend/** paths
└── ... (existing Python source, unchanged)

src/frontend/
├── package.json              # CHANGED: unchanged fields, now paired with a committed lockfile
├── package-lock.json         # NEW: committed (currently gitignored) to unlock npm ci + caching
├── .releaserc.json           # NEW: semantic-release config scoped to src/frontend/** paths
└── ... (existing React source, unchanged)

infrastructure/terraform/      # UNCHANGED (no source changes; only the apply workflow step changes)
```

**Structure Decision**: This is a CI/CD-only feature — no `src/models`, `src/services`, or similar application-layer directories are introduced. The new files are workflow YAML, per-component `package.json`/`.releaserc.json` manifests that exist purely to give `semantic-release` a scoped, tooling-only home in each component's existing directory, and a small `scripts/` directory holding the automated tests this feature's own logic needs (research.md decision #8). Both `backend-deploy.yml` and `frontend-deploy.yml` are restructured in place (same file, new job graph) rather than split into separate CI/CD workflow files, consistent with the spec's Clarifications and the constitution's Simplicity principle.

## Complexity Tracking

*No Constitution Check violations require justification — table intentionally omitted.*
