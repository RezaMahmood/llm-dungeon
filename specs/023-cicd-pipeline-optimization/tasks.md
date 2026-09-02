---

description: "Task list for CI/CD Pipeline Optimization — Test-on-Push, Build-on-Merge, Manual Deploy"
---

# Tasks: CI/CD Pipeline Optimization — Test-on-Push, Build-on-Merge, Manual Deploy

**Input**: Design documents from `/specs/023-cicd-pipeline-optimization/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/workflow-interfaces.md, quickstart.md (all present)

**Tests**: This feature's "tests" are the existing project convention for pipeline config — structure-assertion scripts (`scripts/test-workflow-structure.js`, `scripts/test-release-fixtures.js`) run as required PR checks, per Constitution Principle I (NON-NEGOTIABLE automated testing) and Principle V (CI gate). They are included as implementation tasks below, alongside the workflow changes they assert, matching this repo's existing convention.

**Organization**: Tasks are grouped by user story (spec.md) to enable independent implementation and testing of each story. This restructures the existing `.github/workflows/` implementation (built for a now-superseded, auto-deploy-on-merge design) rather than building from scratch — see plan.md's Summary.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: Which user story this task belongs to (US1-US5)
- File paths are exact and relative to the repository root

## Path Conventions

- Workflows: `.github/workflows/`
- Reusable/composite building blocks: `.github/actions/`, `.github/workflows/_*.yml` (`workflow_call`, leading underscore marks "not directly triggerable")
- Scripts/tests: `scripts/`
- Release configs: `src/frontend/.releaserc.json`, `src/backend/.releaserc.json`, `infrastructure/.releaserc.json`

---

## Phase 1: Setup

**Purpose**: Initialize the one new piece of static configuration the rest of this feature depends on.

- [X] T001 [P] Create `infrastructure/.releaserc.json`: a `semantic-release` config path-scoped to `infrastructure/**`, tag prefix `infrastructure-v`, starting baseline `0.1.0` — mirrors `src/frontend/.releaserc.json` and `src/backend/.releaserc.json` exactly, per research.md Decision 9.

**Checkpoint**: Infrastructure has its own release-config identity, ready for the build/version/cache work in US2.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The one mechanism shared by more than one user story (US1's test gate and US2's build gate both need it) — must exist before either is complete.

**⚠️ CRITICAL**: US1 and US2 both depend on this.

- [X] T002 Create composite action `.github/actions/detect-non-testable-changes/action.yml`: computes the full changed-file list for the triggering push/PR and outputs `all-non-testable` (`"true"`/`"false"`) — `true` iff every changed file matches the non-testable glob set (`**/*.md`, `specs/**`, `docs/**`, `LICENSE`, `CONTRIBUTING.md`, and equivalents), regardless of which directory those files live in. Implements the "Non-testable-artifact skip contract" in `contracts/workflow-interfaces.md` (FR-019/FR-020).
- [X] T003 [P] Add `scripts/test-non-testable-detection.js`, registered in an existing/adjacent required workflow-lint-style check, asserting T002's glob logic against fixture file-list cases: all-docs → `true`; all-code → `false`; mixed docs+code → `false`; a docs file sitting *inside* a component directory (e.g. `src/frontend/README.md`) alone → still `true` (content-type based, not location-based, per the clarification session).

**Checkpoint**: Foundation ready — US1 and US2 can now both wire in the shared skip mechanism.

---

## Phase 3: User Story 1 - No untested code reaches main (Priority: P1) 🎯 MVP

**Goal**: The standard test suite runs automatically on every push (not just PR events), a merge is blocked while tests fail, and a push whose entire diff is non-testable content triggers no test run at all.

**Independent Test**: Push a change that breaks a test and confirm the test-on-push run fails and merge is blocked; push a change that passes and confirm merge is allowed; push a docs-only change and confirm no test run occurs.

### Implementation for User Story 1

- [X] T004 [US1] Add a `push` trigger (any branch) to `.github/workflows/test.yml`, alongside its existing `pull_request` trigger, per FR-001 and the CI workflow contract in `contracts/workflow-interfaces.md`.
- [X] T005 [US1] Wire `.github/actions/detect-non-testable-changes` (T002) into `test.yml`'s existing `changes` job, and condition the `test` and `frontend-test` jobs on `if: needs.changes.outputs.all-non-testable != 'true'`.
- [X] T006 [P] [US1] Extend `scripts/test-workflow-structure.js` with an assertion that `test.yml` declares both `push` and `pull_request` triggers, and that its test jobs are conditioned on the `all-non-testable` output from T005.
- [ ] T007 [US1] Confirm (record in the PR description — this is a GitHub repository setting, not YAML) that branch protection on `main` still lists `test` and `frontend-test` as required status checks, so FR-002/FR-003 ("no path for untested code to enter `main`") remain enforced after T004/T005's changes.

**Checkpoint**: User Story 1 is fully functional and independently testable — the test gate now covers pushes generally, and non-testable-only pushes are pipeline-silent.

---

## Phase 4: User Story 2 - Merging to main produces one immutable, versioned, cached build (Priority: P1)

**Goal**: A tested merge to `main` builds exactly one deployable artifact per affected component, assigns it a version, and stores it immutably and idempotently in the cache — usable as-is, with no CD/deploy job in the same workflow.

**Independent Test**: Merge a tested, frontend-only change to `main`; confirm exactly one `frontend-v<version>` GitHub Release is created with the built artifact attached, and backend/infrastructure are untouched. Re-request a build for that same version and confirm the existing artifact is reused, not rebuilt.

### Implementation for User Story 2

- [X] T008 [P] [US2] Create reusable build workflow `.github/workflows/_build-frontend.yml` (`workflow_call` only): runs `semantic-release` (via `semantic-release-monorepo`, path-scoped to `src/frontend/**`) to compute the next version, builds `dist/`, and attaches it as a `frontend-v<version>` GitHub Release asset — reusing/skipping the build if that release already exists (idempotency, FR-007/FR-008). Extracted from the current `frontend-deploy.yml`'s `release`/`build` jobs.
- [X] T009 [P] [US2] Create reusable build workflow `.github/workflows/_build-backend.yml` (`workflow_call` only): same contract as T008, for backend's zip-with-vendored-dependencies artifact and `backend-v<version>` releases. Extracted from the current `backend-deploy.yml`'s `release`/`build` jobs.
- [X] T010 [P] [US2] Create reusable build workflow `.github/workflows/_build-infrastructure.yml` (`workflow_call` only): runs `terraform validate`/`plan`, then `semantic-release` using T001's config, then saves the `tfplan` binary + a human-readable plan-text rendering + a `VERSION` file as an `infrastructure-v<version>` GitHub Release asset — "usable as-is" here means the exact validated plan, not a re-plan (research.md Decision 3).
- [X] T011 [P] [US2] Create `.github/workflows/frontend-build.yml`: triggered on `push` to `main`, paths `src/frontend/**`; wires in `detect-non-testable-changes` (T002) the same way `test.yml` does; on a qualifying push, calls `_build-frontend.yml` (T008) via `workflow_call`. **No** `deploy` job.
- [X] T012 [P] [US2] Create `.github/workflows/backend-build.yml`: same pattern as T011, paths `src/backend/**`, `src/function_app.py`, `src/requirements.txt`, calling `_build-backend.yml` (T009). **No** `deploy` job.
- [X] T013 [P] [US2] Create `.github/workflows/infrastructure-build.yml`: `push` to `main`, paths `infrastructure/**`, calling `_build-infrastructure.yml` (T010). **No** `apply` job.
- [X] T014 [P] [US2] Extend `scripts/test-workflow-structure.js`: assert none of `frontend-build.yml`/`backend-build.yml`/`infrastructure-build.yml` contains a `deploy`/`apply` job, and that each `_build-*.yml` declares `workflow_call` as its only trigger; **assert each `_build-*.yml` checks for an existing release/tag for the target version before running its build steps, and skips/short-circuits those steps when one already exists — so a second build request for an already-released version cannot produce a second, differing artifact (FR-008/SC-006).**
- [X] T015 [P] [US2] Extend `scripts/test-release-fixtures.js` to cover `infrastructure/.releaserc.json`'s path scope (T001) alongside the existing frontend/backend fixtures, including the vertical-slice (single commit touching multiple components) case.

**Checkpoint**: User Stories 1 AND 2 both work independently — CI (test, build, version, cache) is now fully automatic and produces immutable, idempotent, per-component artifacts, with no deploy anywhere in this phase.

---

## Phase 5: User Story 3 - Deploy is always a separate, explicitly-triggered action; infrastructure additionally requires human approval (Priority: P1)

**Goal**: Each component's deploy is its own `workflow_dispatch`-only workflow, never triggered by push/merge. Frontend and backend deploy directly once triggered; infrastructure's apply step waits for human approval on a protected environment.

**Independent Test**: Merge a change for each component (from US2) and confirm no deploy occurs; manually dispatch each deploy workflow with an already-cached explicit version and confirm frontend/backend deploy immediately while infrastructure pauses for a reviewer's approval before applying.

### Implementation for User Story 3

- [X] T016 [US3] Rewrite `.github/workflows/frontend-deploy.yml` as the CD workflow: `workflow_dispatch` only (remove the existing `push`/`pull_request` triggers and the `concurrency` cancel-in-progress block per research.md Decisions 1-2), a `version` input per the shared input contract in `contracts/workflow-interfaces.md`, an `ensure-artifact` job that downloads the release asset for the given version, and a `deploy` job that deploys it as-is with no approval step (FR-011b).
- [X] T017 [US3] Rewrite `.github/workflows/backend-deploy.yml` the same way as T016, for backend.
- [X] T018 [US3] Rename `.github/workflows/terraform-apply.yml` to `.github/workflows/infrastructure-deploy.yml` and rewrite it as the CD workflow: `workflow_dispatch` only, `version` input, an `ensure-artifact` job that downloads the `infrastructure-v<version>` plan asset, and an `apply` job that targets the `production-infra` GitHub Environment (FR-011a, research.md Decision 6).
- [ ] T019 [US3] Confirm (record in the PR description — a GitHub repository/environment setting, not YAML) that the `production-infra` environment has a required-reviewer protection rule configured **with "Prevent self-review" enabled, and that the requesting user (the sole human in the loop for this repository) is the one who enables that checkbox and is listed as the required reviewer** — so an AI agent can dispatch `infrastructure-deploy.yml` and complete validation, but only that human can supply the approval, never the agent or the dispatching identity itself (FR-011a). Confirm frontend/backend deploy jobs' targets have no equivalent protection.
- [X] T020 [P] [US3] Extend `scripts/test-workflow-structure.js`: assert none of `frontend-deploy.yml`/`backend-deploy.yml`/`infrastructure-deploy.yml` declares a `push` or `pull_request` trigger; assert all three declare a `workflow_dispatch` `version` input; assert `infrastructure-deploy.yml`'s apply job sets `environment: production-infra` and neither app-deploy workflow's job sets an equivalent `environment`; **assert each workflow's `deploy`/`apply` job contains no dependency-install, build/compile (`npm run build`, packaging), or `terraform plan` step — only artifact-download (`ensure-artifact`) and deploy/apply steps — so a rebuild between cache-check and deploy is structurally impossible (FR-009/SC-002).**
- [X] T021 [US3] Update `.github/workflows/README.md`: replace the stale description of the old combined `test → release → build → deploy` graph with the new CI (`*-build.yml`)/CD (`*-deploy.yml`) split.

**Checkpoint**: User Stories 1-3 all work independently — deploy is now always a distinct, explicit action for all three components, with infrastructure's added human-approval asymmetry.

---

## Phase 6: User Story 4 - Deploy targets a specific version, defaulting to latest (Priority: P2)

**Goal**: An unspecified `version` input resolves, at execution time, to whichever version is truly latest at that moment; an explicit version deploys exactly that version; an explicit version with no matching build fails clearly rather than substituting something else.

**Independent Test**: Dispatch a deploy with an explicit older version and confirm exactly that version deploys; dispatch with a blank version while multiple versions exist and confirm the newest deploys; dispatch a version that was never built and confirm a clear failure.

### Implementation for User Story 4

- [X] T022 [P] [US4] In `frontend-deploy.yml`'s `ensure-artifact` job (T016): add a `resolve-version` step — if the `version` input is blank, query frontend's release tags (`gh release list` / `git tag --list 'frontend-v*' --sort=-v:refname`) and select the highest SemVer, evaluated at run time (FR-013); otherwise pass the input through unchanged. Add the explicit-version-not-found failure path: if a supplied version has no matching release/tag, fail the run with a clear error (FR-016) rather than deploying a substitute.
- [X] T023 [P] [US4] Apply the same `resolve-version` + not-found-failure logic to `backend-deploy.yml` (T017).
- [X] T024 [P] [US4] Apply the same `resolve-version` + not-found-failure logic to `infrastructure-deploy.yml` (T018).
- [X] T025 [P] [US4] Extend `scripts/test-workflow-structure.js`: assert a `resolve-version` step/job exists in all three deploy workflows, runs before `ensure-artifact`'s download step, and that an explicit not-found version has an assertable failure path (no silent fallback).
- [ ] T026 [US4] Run `quickstart.md` Scenario 4 (specific-version and latest-resolution) and Scenario 7 (invalid-version failure) against the real repository; record results in the PR description.

**Checkpoint**: User Stories 1-4 all work independently — version targeting is precise and predictable, with latest correctly resolved at the moment of execution.

---

## Phase 7: User Story 5 - An AI agent can resolve and deploy "latest" on request (Priority: P2)

**Goal**: When "latest" resolves to a version with no cached artifact yet, the deploy workflow builds it on demand (via the shared build workflows from US2) and deploys the result — all from one trigger — and the `gh` CLI pattern an agent uses is documented.

**Independent Test**: With a cached artifact already present for the latest version, trigger a deploy and confirm no rebuild occurs. With the latest version not yet built, trigger a deploy and confirm exactly one build occurs, followed by deploy of that same artifact.

### Implementation for User Story 5

- [X] T027 [P] [US5] In `frontend-deploy.yml`'s `ensure-artifact` job (T022): on a cache miss where `resolved_version` is genuinely the latest version derivable from current `main` (not yet built) — as opposed to an explicit not-found version (T022's failure path) — invoke `_build-frontend.yml` (T008) via `workflow_call` within the same run, then proceed to `deploy` with the resulting artifact (FR-015).
- [X] T028 [P] [US5] Apply the same cache-miss-on-latest build fallback to `backend-deploy.yml` (T023), calling `_build-backend.yml` (T009).
- [X] T029 [P] [US5] Apply the same cache-miss-on-latest build fallback to `infrastructure-deploy.yml` (T024), calling `_build-infrastructure.yml` (T010).
- [X] T030 [P] [US5] Extend `scripts/test-workflow-structure.js`: assert each deploy workflow's `ensure-artifact` job conditionally invokes its matching `_build-*.yml` workflow only on the latest-and-not-yet-built path, and that this path is distinct from (never triggered by) an explicit not-found version.
- [X] T031 [US5] Add an "AI agent deploy" subsection to `.github/workflows/README.md`, documenting the `gh release list` / `gh workflow run <component>-deploy.yml -f version=...` usage pattern from `contracts/workflow-interfaces.md`, so a human maintainer or an instructed AI agent can follow it verbatim (FR-018).
- [ ] T032 [US5] Run `quickstart.md` Scenario 5 (both the cache-hit and cache-miss/cold-start paths) against the real repository via an actual AI agent session; record results in the PR description.

**Checkpoint**: All five user stories are independently functional — the full CI/CD separation described in spec.md is implemented.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Repository-wide consistency and the feature's final acceptance gate.

- [X] T033 [P] Run `actionlint` across every new/modified file under `.github/workflows/`; fix any findings.
- [X] T034 [P] Search the repository (`CLAUDE.md`, `docs/`, any other workflow docs) for remaining references to the old combined `test → release → build → deploy` graph or the old push-triggered-deploy/concurrency-cancellation behavior, and update them to describe the new CI/CD split.
- [ ] T035 Run the full `quickstart.md` validation suite (Scenarios 1-7) end-to-end against the real repository, with the requesting user or product owner confirming each scenario's outcome directly — per Constitution Principle IX (User-Verified Acceptance Before Completion), this is the feature's final, distinct acceptance gate and is not satisfied by the automated `scripts/test-workflow-structure.js`/`scripts/test-release-fixtures.js` checks alone.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately.
- **Foundational (Phase 2)**: No dependency on Setup's T001 (different concern); BLOCKS User Story 1 (T005) and User Story 2 (T011-T013).
- **User Story 1 (Phase 3)**: Depends on Foundational (T002). Independent of US2-US5.
- **User Story 2 (Phase 4)**: Depends on Foundational (T002) and Setup (T001, for infrastructure's build). Independent of US1, US3, US4, US5.
- **User Story 3 (Phase 5)**: Depends on User Story 2's build workflows existing (T008-T010, so `ensure-artifact` has something to download) — not strictly on US2's workflow-trigger tasks, but practically sequenced after US2 for a working end-to-end deploy.
- **User Story 4 (Phase 6)**: Depends on User Story 3's deploy workflows (T016-T018) existing — extends their `ensure-artifact` job.
- **User Story 5 (Phase 7)**: Depends on User Story 4's `resolve-version`/failure-path logic (T022-T024) and User Story 2's build workflows (T008-T010) — extends the same `ensure-artifact` job further.
- **Polish (Phase 8)**: Depends on all desired user stories being complete.

### User Story Dependencies

- US1 and US2 are both independently testable and deliverable once Foundational is done — they can proceed in parallel.
- US3 builds on US2's artifacts existing to have something to deploy, but its own acceptance criteria (no auto-deploy, explicit trigger, approval asymmetry) are testable independently of US4/US5's version-resolution refinements.
- US4 and US5 both extend US3's `ensure-artifact` job incrementally — US4's default-to-latest logic, then US5's build-on-miss logic — so within a single deploy workflow file they are sequential, but the three components' files (frontend/backend/infrastructure) remain parallelizable within each phase.

### Within Each User Story

- Composite/reusable building blocks before the workflows that call them (e.g., T008-T010 before T011-T013).
- Workflow content before its structure-test assertion (e.g., T016-T018 before T020).
- Structure/fixture-test extensions before the quickstart validation run that exercises them end-to-end.

### Parallel Opportunities

- T001 (Setup) can run alongside T002-T003 (Foundational) — different concerns, different files.
- Once Foundational (T002) is done, US1 (Phase 3) and US2 (Phase 4) can proceed in parallel.
- Within US2: T008, T009, T010 (the three reusable build workflows) are mutually parallel; T011, T012, T013 (the three CI trigger workflows) are mutually parallel once their respective T008/T009/T010 and T002 are done.
- Within US3: T016, T017, T018 (the three CD workflows) are mutually parallel.
- Within US4: T022, T023, T024 (per-component `resolve-version`) are mutually parallel.
- Within US5: T027, T028, T029 (per-component build-on-miss) are mutually parallel.
- T033 and T034 (Polish) are mutually parallel.

---

## Parallel Example: User Story 2

```bash
# Launch the three reusable build workflows together (different files, no cross-dependency):
Task: "Create .github/workflows/_build-frontend.yml per T008"
Task: "Create .github/workflows/_build-backend.yml per T009"
Task: "Create .github/workflows/_build-infrastructure.yml per T010"

# Once those land, launch the three CI trigger workflows together:
Task: "Create .github/workflows/frontend-build.yml per T011"
Task: "Create .github/workflows/backend-build.yml per T012"
Task: "Create .github/workflows/infrastructure-build.yml per T013"
```

---

## Implementation Strategy

### MVP First (User Story 1 + User Story 2)

Together, US1 and US2 deliver the full CI half of this feature (test-on-push, block-untested-merge, build/version/cache-on-merge) with zero deploy-behavior change yet — a safe, independently valuable increment that doesn't touch how deploys currently happen.

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (blocks US1 and US2)
3. Complete Phase 3: User Story 1
4. Complete Phase 4: User Story 2
5. **STOP and VALIDATE**: run `quickstart.md` Scenarios 1, 2, and 6 against the real repository

### Incremental Delivery

1. Setup + Foundational → shared mechanisms ready
2. US1 + US2 (parallel) → CI fully automatic, no deploy behavior changed yet (MVP)
3. US3 → deploy becomes manual-only for all three components (this is the point at which the *old* auto-deploy-on-merge behavior is actually removed — sequence this deliberately, not casually, since it changes how production gets updated)
4. US4 → precise version targeting and correct latest-resolution
5. US5 → AI-agent-driven cache-aware deploy, the feature's headline capability
6. Polish → lint, stale-doc cleanup, full end-to-end user-verified acceptance (Constitution Principle IX)

### Parallel Team Strategy

With multiple contributors: one completes Setup + Foundational; then one takes US1 while another starts US2's three reusable build workflows in parallel with each other; US3 (and its sequential dependents US4/US5) should land as one coordinated change per component, since splitting an individual deploy workflow's incremental logic (T016→T022→T027, etc.) across people risks merge conflicts within the same file.

---

## Notes

- [P] tasks touch different files and have no incomplete-task dependency within their batch.
- [Story] labels map every Phase 3+ task to its user story for traceability back to spec.md.
- T016-T018, T022-T024, and T027-T029 each incrementally extend the *same* three files (one deploy workflow per component) across US3/US4/US5 — implement them in that order per file; do not attempt to parallelize across phases within a single component's deploy workflow.
- Commit after each task or logical group.
- Constitution Principle IX (T035) is the feature's true completion gate — automated checks passing is necessary but not sufficient.
