# Implementation Plan: CI/CD Pipeline Optimization — Test-on-Push, Build-on-Merge, Manual Deploy

**Branch**: `023-cicd-pipeline-optimization` | **Date**: 2026-09-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/023-cicd-pipeline-optimization/spec.md`

**Note**: This plan supersedes an earlier plan written against a materially different, now-replaced version of `spec.md` (auto-deploy-on-merge with concurrency cancellation). The current codebase's `.github/workflows/*` were built against that earlier spec and are the starting point this plan restructures, not a green-field build.

## Summary

Separate CI from CD across all three components (frontend, backend, infrastructure): CI (test-on-push, build+version+cache-on-merge-to-`main`) stays fully automatic and identical in shape across components; CD (deploy) becomes a distinct, explicitly-triggered `workflow_dispatch` action per component that is never a side effect of a push or merge. Each deploy action accepts an optional `version` input (blank = latest-at-execution-time), deploys the matching cached, immutable artifact as-is if one exists, and builds that exact version on demand if it doesn't. Frontend and backend deploys execute directly once triggered; infrastructure's deploy additionally requires a human to approve the validated change before it applies. A push/PR whose changed files are *entirely* non-testable content (docs/specs/markdown) triggers no component's pipeline at all; the moment any testable file is included, the full pipeline runs as normal for the affected component(s), non-testable files included.

This restructures (rather than replaces from scratch) the existing `.github/workflows/` implementation: `test.yml`, `backend-deploy.yml`, `frontend-deploy.yml`, and `terraform-apply.yml` currently conflate CI and CD into one push-triggered chain per component (`test → release → build → deploy`) with a `concurrency`-group cancellation guard. That auto-deploy-on-merge behavior is exactly what the current spec forbids (FR-010); the concurrency-cancellation mechanism it used is now moot once deploy is no longer triggered by push at all.

## Technical Context

**Language/Version**: GitHub Actions workflow YAML (orchestration layer); Python 3.11 (backend, unchanged), Node.js 24 (frontend build tooling, unchanged), HCL/Terraform (infrastructure, unchanged). This feature's own deliverable is pipeline configuration and small helper scripts (Node/Bash), not application code.

**Primary Dependencies**: GitHub Actions (`workflow_dispatch`, `workflow_call`, `environments`), `semantic-release` via `semantic-release-monorepo` (path-scoped independent versioning, already in use for frontend/backend — extended to infrastructure), GitHub CLI (`gh`) for both human and AI-agent-driven manual deploy triggering, GitHub Releases (tags + release assets) as the artifact cache, Terraform CLI, `actionlint`, existing custom Node test scripts (`scripts/test-workflow-structure.js`, `scripts/test-release-fixtures.js`).

**Storage**: GitHub Releases (git tag + release, one per component per version) as the immutable, versioned, indefinitely-retained build-artifact cache — reusing frontend/backend's existing `semantic-release`-driven tag/release mechanism and extending the same pattern to infrastructure. `actions/upload-artifact` alone is insufficient as the cache (default ~90-day retention does not satisfy the spec's immutable/indefinitely-retrievable requirement, FR-006/FR-007) and is used only for same-run job-to-job artifact passing, never as the durable cache.

**Testing**: pytest (backend), `npm test`/vitest (frontend), Terraform validate + existing infrastructure unit tests, `actionlint` (workflow syntax), and the existing custom structure/fixture test scripts under `scripts/` — extended to assert the new CI/CD separation (no `push`-triggered deploy job anywhere; every deploy workflow requires `workflow_dispatch` with a `version` input; infrastructure's deploy job targets an approval-gated environment; frontend/backend's does not; the changed-files-are-all-non-testable skip logic).

**Target Platform**: GitHub Actions runners (`ubuntu-latest`); deploy targets remain Azure Functions (backend), Azure Static Web Apps (frontend), and Azure resources managed by Terraform (infrastructure) — unchanged from the existing implementation.

**Project Type**: CI/CD pipeline configuration for an existing web application (frontend + backend + infrastructure-as-code), not a new application feature — no new runtime service or UI surface is introduced.

**Performance Goals**: Directional only, per spec SC-007 — independent components' test/build pipelines run in parallel rather than serially blocking each other, and no deploy or build step performs a rebuild a cache lookup could have served instead. No fixed numeric time budget is set by this feature.

**Constraints**: Deploy MUST NOT be triggered by `push` or `pull_request` events, only `workflow_dispatch` (FR-010). Every deploy workflow MUST accept a `version` input. Infrastructure's deploy job MUST target a GitHub Environment with required-reviewer protection (FR-011a); frontend/backend's MUST NOT have an equivalent approval step (FR-011b). A push/PR whose entire diff is non-testable content MUST trigger no pipeline (FR-019); one testable file in the same diff MUST trigger the full pipeline (FR-020). Artifacts MUST be immutable and idempotently re-servable from cache (FR-007/FR-008).

**Scale/Scope**: Three components (frontend, backend, infrastructure), each with its own independent CI workflow(s) and its own independent CD (deploy) workflow, one Azure deploy target per component (no multi-environment/staging matrix introduced by this feature).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Meaningful, Automated Testing (NON-NEGOTIABLE)** — Satisfied. FR-001/FR-002/FR-003 keep the existing PR-gated pytest/vitest suites as the merge-blocking requirement; this feature does not narrow test scope, only reorganizes when build/deploy happen relative to it.
- **II. Secure-by-Default Access** — N/A. This feature does not touch application authentication/authorization surfaces.
- **III. Defined Technology Stack** — Satisfied. Backend stays Python/Azure Functions, frontend stays ReactJS; this feature only reorganizes the GitHub Actions/Terraform delivery pipeline around that existing stack, introducing no new language or hosting model.
- **IV. Simplicity Over Premature Scale (YAGNI)** — Satisfied. Reuses the existing `semantic-release-monorepo` + GitHub Releases mechanism already proven for frontend/backend rather than introducing a new artifact-storage system (e.g., a container registry or blob store) for infrastructure's artifact.
- **V. Continuous Integration Gate** — Satisfied and strengthened. Every PR still runs the full required test suite and is blocked from merging while it fails; this feature does not change that gate's presence, only clarifies (FR-019/FR-020) that a docs-only PR isn't required to invoke a pipeline that has nothing to test.
- **VI. Observability & AI Cost Transparency** — N/A. No LLM interaction is introduced by this feature.
- **VII. Zero-Trust Azure Resource Communication (NON-NEGOTIABLE)** — Satisfied, unchanged. Deploy jobs continue to authenticate to Azure via OIDC/federated credentials (`permissions: id-token: write`, already present in the existing deploy workflows) rather than long-lived secrets; this feature does not alter that mechanism.
- **VIII. UI Design System & Accessibility Compliance** — N/A. No user-facing UI is introduced or changed by this feature.
- **IX. User-Verified Acceptance Before Completion (NON-NEGOTIABLE)** — Applies. `tasks.md` MUST end with an explicit user-verified acceptance task: a human triggers each of the three deploy workflows (including an AI-agent-driven "deploy latest" request) against the real repository/environment and confirms the behavior described in spec.md's user stories, not merely that automated workflow-structure tests pass.
- **X. PII Protection by Design** — N/A. No PII is handled by this feature.
- **XI. UI Design Pre-Agreement Before Implementation** — N/A. No UI surface.
- **Development Workflow & Quality Gates** — Satisfied. Changes go through a PR on this feature's own branch/worktree; CI (Principle V) still gates merge; no direct push to `main`.

No violations requiring justification — Complexity Tracking is not needed.

**Post-Design Re-check** (after Phase 1: research.md, data-model.md, contracts/, quickstart.md): No new violations introduced. Design decisions reinforce rather than strain the gates above — notably Decision 3/research.md (reusing GitHub Releases instead of adding a new Azure storage resource) and Decision 5 (a single shared build implementation instead of duplicated YAML) both directly serve Principle IV (YAGNI); Decision 6 reuses the existing `production-infra` environment/approval mechanism rather than inventing one. Constitution Check gates remain satisfied as stated above.

## Project Structure

### Documentation (this feature)

```text
specs/023-cicd-pipeline-optimization/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── workflow-interfaces.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
.github/workflows/
├── test.yml                      # CI: test-on-push (extended: push trigger + all-non-testable-files skip)
├── frontend-build.yml            # CI: build+version+cache on merge to main (renamed from frontend-deploy.yml, deploy job removed)
├── backend-build.yml             # CI: build+version+cache on merge to main (renamed from backend-deploy.yml, deploy job removed)
├── infrastructure-build.yml      # CI: validate+plan+version+cache on merge to main (new; versioning extended to infra)
├── frontend-deploy.yml           # CD: workflow_dispatch only, version input, no approval gate
├── backend-deploy.yml            # CD: workflow_dispatch only, version input, no approval gate
├── infrastructure-deploy.yml     # CD: workflow_dispatch only, version input, required-reviewer environment (renamed/split from terraform-apply.yml)
├── pr-title-check.yml            # unchanged
├── workflow-lint.yml             # unchanged
├── workflow-structure-test.yml   # extended: asserts CI/CD separation, version inputs, approval-gate asymmetry, docs-skip logic
├── release-fixtures-test.yml     # extended: infrastructure path scope added to release-fixture matrix
├── infrastructure-tests.yml      # unchanged (PR-time Terraform validation)
└── terraform-validate.yml        # unchanged (PR-time Terraform validation)

src/backend/                      # unchanged application code; .releaserc.json path scope unchanged
src/frontend/                     # unchanged application code; .releaserc.json path scope unchanged
infrastructure/terraform/         # unchanged Terraform configuration; new infrastructure/.releaserc.json added

scripts/
├── test-workflow-structure.js    # extended with new assertions (see above)
└── test-release-fixtures.js      # extended with infrastructure path scope
```

**Structure Decision**: Existing repository layout (`src/backend`, `src/frontend`, `infrastructure/terraform`, `.github/workflows`, `scripts`) is reused as-is — this feature restructures the workflow layer only. The core change is splitting each component's single push-triggered `test → release → build → deploy` workflow into two: a CI workflow (auto, ends at build+version+cache) and a CD workflow (manual `workflow_dispatch` only, starts from version resolution). Infrastructure gains a CI/CD split mirroring frontend/backend's, plus its own `semantic-release` path scope, where today it has only a single push-triggered `validate → test → apply` workflow.

## Complexity Tracking

*No Constitution Check violations — this section is not needed.*
