---
description: "Task list for CI/CD Pipeline Optimization"
---

# Tasks: CI/CD Pipeline Optimization

**Input**: Design documents from `/specs/023-cicd-pipeline-optimization/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/workflow-interfaces.md, quickstart.md (all present)

**Tests**: Automated tests ARE included (revised post-`/speckit-analyze`, findings C1 and G1) — Principle I is NON-NEGOTIABLE and requires fully automatable tests for every user story's own behavior, not only the manual quickstart.md scenarios. Every story (US1–US5) now has a dedicated automated test: workflow-structure assertion tests for US1/US2/US5 (static YAML-shape checks) and fixture/unit tests for US3/US4 (commit-analysis and PR-title-pattern behavior). See research.md decision #8. quickstart.md's scenarios remain as the separate Principle IX human-acceptance layer.

**Organization**: Tasks are grouped by user story (spec.md) to enable independent implementation and validation of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no unmet dependency)
- **[Story]**: Which user story this task belongs to (US1–US5)

## Path Conventions

Repository root paths, per plan.md's Project Structure — this feature touches `.github/workflows/*.yml` and adds minimal tooling-only manifests and test scripts under `src/backend/`, `src/frontend/`, and a shared `scripts/` location.

---

## Phase 1: Setup

**Purpose**: Prerequisites that unlock reproducible builds and versioning tooling, with no story-specific behavior yet.

- [ ] T001 Remove `package-lock.json` from `.gitignore`, run `npm install` in `src/frontend/` to generate a lockfile matching the current `package.json`, and commit it — files: `.gitignore`, `src/frontend/package-lock.json`. Verify `npm ci` succeeds from the committed lockfile before moving on (research.md decision #5).
- [ ] T002 [P] Create a tooling-only `package.json` in `src/backend/` (`{"name": "llmdungeon-backend", "version": "0.1.0", "private": true}`) for `semantic-release` to run against — file: `src/backend/package.json`. Do not add a `main`/build/publish config; this manifest is never published (research.md decision #3).

**Checkpoint**: Frontend builds are reproducible via `npm ci`; backend has a version-tracking manifest for later stories.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Cross-cutting work that must happen before other changes are made, so later measurements are valid and every subsequent workflow edit is checked automatically.

**⚠️ CRITICAL**: T003 must run before any workflow changes in Phase 3+, since it establishes the "before" baseline SC-001 is measured against.

- [ ] T003 Record the last 5 successful `backend-deploy.yml` and `frontend-deploy.yml` run durations (from the Actions tab, pre-change) into `specs/023-cicd-pipeline-optimization/baseline-metrics.md`, so SC-001's "decreases measurably vs. baseline" has a concrete before-value to compare against later.
- [ ] T004 [P] Add `cache: pip` to the `actions/setup-python` step and `cache: npm` to the `actions/setup-node` step in `.github/workflows/test.yml` (FR-003, FR-017 — caching only, no trigger/scope change) — file: `.github/workflows/test.yml`.
- [ ] T005 [P] Create `.github/workflows/workflow-lint.yml`: a required `pull_request` check running `actionlint` (or equivalent) against every changed file under `.github/workflows/**` (research.md decision #8, addressing constitution Principle I / `/speckit-analyze` finding C1). Every workflow edit in Phases 3–7 below is covered by this check from this point forward. Note: this only catches syntax/schema errors — behavioral/structural correctness per story is covered by each story's own dedicated test below (finding G1).

**Checkpoint**: Baseline captured; PR-time test workflow already benefits from caching; every subsequent workflow YAML change in this feature is automatically linted. User story work can now begin.

---

## Phase 3: User Story 1 - Backend/frontend changes deploy from the exact artifact that was tested (Priority: P1) 🎯 MVP

**Goal**: Split each component's deploy workflow into `test` → `build` → `deploy` jobs so the artifact `deploy` ships is exactly what `build` produced from tested code — no rebuild, no remote-build, at deploy time.

**Independent Test**: Merge a backend-only change and a frontend-only change to `main`; confirm each workflow's `deploy` job only downloads and deploys an artifact, with zero install/build activity in that job (quickstart.md Scenario 1).

### Tests for User Story 1 ⚠️

> Write this test FIRST; it MUST FAIL until T008/T009 restructure the workflows.

- [ ] T006 [P] [US1] Write a workflow-structure assertion test (research.md decision #8; `/speckit-analyze` finding G1) — a YAML-parsing script (e.g. `scripts/test-workflow-structure.sh`) asserting: `backend-deploy.yml`'s `deploy` job contains no `pip install` (or equivalent install) step and `Azure/functions-action`'s `remote-build` input is `false`; `frontend-deploy.yml`'s `deploy` job contains no `npm install`/`npm run build` step and `Azure/static-web-apps-deploy`'s `skip_app_build` input is `true`; and both workflows' `build` job output is connected to `deploy` via matching `actions/upload-artifact`/`actions/download-artifact` names — file: new test script under `scripts/`.

### Implementation for User Story 1

- [ ] T007 [P] [US1] Restructure `.github/workflows/backend-deploy.yml` into `test` → `build` → `deploy` jobs: `test` runs `pytest` with `cache: pip` (FR-003); `build` zips the `src` deploy root (`function_app.py` + `backend/` package + `requirements.txt`) after a normal `pip install`, writes a placeholder `VERSION` file (e.g. the short commit SHA — User Story 3 will replace this with the real semantic version) into the artifact root, and uploads it via `actions/upload-artifact` named `backend-build-${{ github.run_id }}`; `deploy` downloads that artifact via `actions/download-artifact`, keeps the existing `AzureWebJobsStorage` key-sync step, and calls `Azure/functions-action` with `remote-build: false` against the downloaded package (no further `pip install`) — file: `.github/workflows/backend-deploy.yml`.
- [ ] T008 [P] [US1] Restructure `.github/workflows/frontend-deploy.yml` into `test` → `build` → `deploy` jobs: `test` runs `npm ci` (now unlocked by T001) with `cache: npm` and `npm test`; `build` runs `npm run build` once, writes a placeholder `version.json` (e.g. `{"version": "<short-sha>"}` — User Story 3 will replace this) into `dist/`, and uploads `dist/` via `actions/upload-artifact` named `frontend-build-${{ github.run_id }}`; `deploy` downloads that artifact and calls `Azure/static-web-apps-deploy` with `skip_app_build: true` against the downloaded `dist/`, with no `npm install`/`npm run build` of its own — file: `.github/workflows/frontend-deploy.yml`. Depends on T001 (lockfile) for `npm ci`.
- [ ] T009 [US1] Wire T006's structure test to run against the restructured workflows as a required PR check on changes to either deploy workflow; confirm it now passes. Depends on T006, T007, T008.

**Checkpoint**: Backend and frontend both deploy from a single tested build, independently of versioning/concurrency/PR-title work — this alone is a shippable, demoable increment (contracts/workflow-interfaces.md's job-graph and artifact-naming contracts now hold for both components), protected going forward by an automated structure test rather than only a manual quickstart pass.

---

## Phase 4: User Story 2 - Deploys never ship out of commit order (Priority: P1)

**Goal**: A newer push to `main` cancels an in-flight older deploy for the same component, so production never regresses to an older commit's build.

**Independent Test**: Push two rapid commits to the same component and confirm the older run is cancelled (not failed) before its `deploy` job starts, while the newer run completes (quickstart.md Scenario 2).

### Tests for User Story 2 ⚠️

> Write this test FIRST; it MUST FAIL until T011/T012 add the concurrency blocks.

- [ ] T010 [P] [US2] Write a workflow-structure assertion test (research.md decision #8; finding G1) asserting `backend-deploy.yml` and `frontend-deploy.yml` each declare a top-level `concurrency.group` of `deploy-backend`/`deploy-frontend` (literal, not templated on `github.ref`) with `cancel-in-progress: true` — file: new test script under `scripts/` (may extend T006's script).

### Implementation for User Story 2

- [ ] T011 [P] [US2] Add a top-level `concurrency: { group: deploy-backend, cancel-in-progress: true }` block to `.github/workflows/backend-deploy.yml` (FR-005, FR-006; research.md decision #2 — literal group name, not templated on ref) — file: `.github/workflows/backend-deploy.yml`.
- [ ] T012 [P] [US2] Add a top-level `concurrency: { group: deploy-frontend, cancel-in-progress: true }` block to `.github/workflows/frontend-deploy.yml` — file: `.github/workflows/frontend-deploy.yml`.
- [ ] T013 [US2] Wire T010's structure test to run against the real concurrency configuration as a required PR check; confirm it now passes. Depends on T010, T011, T012.

**Checkpoint**: Both components now independently guarantee commit-order-safe deploys, on top of (but not dependent on) User Story 1's job restructuring, protected by an automated structure test.

---

## Phase 5: User Story 3 - Every deployed frontend/backend build has a discoverable version (Priority: P2)

**Goal**: Each component gets an independently computed SemVer, gated by **path-diff filtering** (does a commit's diff touch this component's paths?) rather than the PR title's scope word — since specs here are typically vertical slices that can touch multiple components in one commit (research.md decision #3, revised post-`/speckit-analyze` finding F1). Recorded as a git tag + GitHub Release, and stamped into its build artifact — without ever pushing a commit to `main`.

**Independent Test**: Merge a `fix(backend): ...`-titled PR and a `feat(frontend): ...`-titled PR; confirm the correct component's tag/release is created (and the other's is not); then merge a vertical-slice PR touching both components' paths and confirm both release independently (quickstart.md Scenario 3, steps 1–5). Depends on User Story 1's `build`/`deploy` job split already existing (this story adds a `release` job ahead of `build` and updates `build` to consume its output).

### Tests for User Story 3 ⚠️

> Write this test FIRST; it MUST FAIL until T017/T018's path-diff filtering exists.

- [ ] T014 [P] [US3] Write a version-computation fixture test (research.md decision #8): a script (e.g. `scripts/test-release-fixtures.sh`, invoked from a new PR-triggered job) that exercises the configured commit-analyzer/`semantic-release --dry-run` against synthetic commits — a same-component `fix`, a same-component `feat`, a non-releasable `chore`, and a **vertical-slice commit touching both components' paths with a single declared scope** — and asserts each produces the expected per-component bump (or correctly no-bumps). This is the automated guard against the exact bug `/speckit-analyze` found in the original design.

### Implementation for User Story 3

- [ ] T015 [US3] Create `src/backend/.releaserc.json` configuring `semantic-release` with `tagFormat: "backend-v${version}"` and plugins `@semantic-release/commit-analyzer`, `@semantic-release/release-notes-generator`, `@semantic-release/github` only (no `@semantic-release/git`, no `@semantic-release/npm` — research.md decision #3) — file: `src/backend/.releaserc.json`. Depends on T002 (backend `package.json` must exist).
- [ ] T016 [P] [US3] Create `src/frontend/.releaserc.json` with the same plugin set and `tagFormat: "frontend-v${version}"` — file: `src/frontend/.releaserc.json`.
- [ ] T017 [US3] Insert a `release` job into `.github/workflows/backend-deploy.yml` between `test` and `build`: for every commit since `backend`'s last matching tag, filter by **path-diff** (does `git diff --name-only` for that commit include any path under `src/backend/**`?) before handing surviving commits to `semantic-release`'s commit-analyzer (working directory `src/backend`) — commits whose diff does not touch backend paths MUST be excluded regardless of their declared PR-title scope (research.md decision #3, spec.md FR-013). Exposes a job `output` named `version` (the newly cut version, or the current latest `backend-v*` tag if no qualifying commit triggered a release this run) — file: `.github/workflows/backend-deploy.yml`. Depends on T007 (job skeleton) and T015 (release config).
- [ ] T018 [P] [US3] Insert a `release` job into `.github/workflows/frontend-deploy.yml` between `test` and `build`, applying the same path-diff filter against `src/frontend/**` before the commit-analyzer (working directory `src/frontend`), exposing the same `version` output pattern — file: `.github/workflows/frontend-deploy.yml`. Depends on T008 and T016.
- [ ] T019 [US3] Update `backend-deploy.yml`'s `build` job to write `release`'s `version` output into the artifact's `VERSION` file instead of the T007 placeholder (short SHA) — file: `.github/workflows/backend-deploy.yml`. Depends on T017.
- [ ] T020 [P] [US3] Update `frontend-deploy.yml`'s `build` job to write `release`'s `version` output into `dist/version.json` instead of the T008 placeholder — file: `.github/workflows/frontend-deploy.yml`. Depends on T018.
- [ ] T021 [US3] Set each workflow's `release` job `permissions:` to include `contents: write` (required for `@semantic-release/github` to create tags/releases) while confirming neither workflow gains permission to push commits to `main` — files: `.github/workflows/backend-deploy.yml`, `.github/workflows/frontend-deploy.yml`. Depends on T017, T018.
- [ ] T022 [US3] Wire T014's fixture test to run against the real path-diff filtering implementation (T017/T018) as a required PR check on changes to either `.releaserc.json` or either workflow's `release` job; confirm it now passes, including the vertical-slice case. Depends on T014, T017, T018, T019, T020.

**Checkpoint**: Both components now have independently versioned, tagged, released, and self-describing build artifacts — correctly attributed even for vertical-slice commits touching multiple components, and protected going forward by an automated fixture test rather than only a manual quickstart pass.

---

## Phase 6: User Story 4 - Malformed commit messages are caught before merge, not after (Priority: P2)

**Goal**: A required PR check blocks merge when the PR title doesn't follow Conventional Commits with a valid component/area scope — since this repo squash-merges, the title is what `semantic-release` reads for change type and descriptive content (the scope word itself no longer gates versioning eligibility — see User Story 3).

**Independent Test**: Open a PR with a malformed title and confirm the required check fails with an explanatory message; fix the title and confirm it passes (quickstart.md Scenario 4). Fully independent of US1–US3's workflow files.

### Tests for User Story 4 ⚠️

> Write this test FIRST; it MUST FAIL until T024's checker is configured.

- [ ] T023 [P] [US4] Write a PR-title-format unit test (research.md decision #8) asserting the configured pattern accepts known-good titles (`fix(backend): ...`, `feat(frontend): ...`) and rejects known-bad ones (no type, no scope, unrecognized type) — file: alongside the checker action's config, e.g. `.github/workflows/pr-title-check.test.*` or the checker action's own fixture-test mechanism if it provides one.

### Implementation for User Story 4

- [ ] T024 [US4] Create `.github/workflows/pr-title-check.yml`: triggers on `pull_request` (`opened`, `edited`, `synchronize`), uses a PR-title Conventional Commits checker action validating `type(scope): description` with `scope` restricted to the project's known components/areas (at minimum `frontend`, `backend`), failing with an explanatory message on mismatch (FR-011, FR-012; research.md decision #4 — PR title, not per-commit, since squash-merge discards individual commits) — file: `.github/workflows/pr-title-check.yml`. Depends on T023 (test exists first, and must now pass).
- [ ] T025 [US4] Add the new check's job name to `main`'s required-status-checks branch protection list (repo admin action via GitHub settings or `gh api`), and document the requirement in `.github/workflows/README.md` — files: GitHub branch protection settings (not a repo file), `.github/workflows/README.md`. Depends on T024.

**Checkpoint**: Malformed PR titles are now blocked before merge, making User Story 3's version computation trustworthy going forward.

---

## Phase 7: User Story 5 - Terraform apply runs exactly the plan that was reviewed (Priority: P3)

**Goal**: `terraform-apply.yml`'s `apply` job applies the exact plan file `validate` produced, instead of implicitly re-planning immediately before applying.

**Independent Test**: Trigger the infrastructure apply workflow and confirm from the logs that `apply` consumes the plan artifact rather than invoking a fresh `terraform plan` (quickstart.md Scenario 5). Fully independent of US1–US4.

### Tests for User Story 5 ⚠️

> Write this test FIRST; it MUST FAIL until T027/T028 wire the plan artifact through.

- [ ] T026 [P] [US5] Write a workflow-structure assertion test (research.md decision #8; finding G1) asserting `terraform-apply.yml`'s `apply` job's `terraform apply` command references the downloaded `tfplan` file and contains neither `-auto-approve` nor `-var-file=terraform.tfvars` — file: new test script under `scripts/` (may extend T006's script).

### Implementation for User Story 5

- [ ] T027 [US5] In `.github/workflows/terraform-apply.yml`'s `validate` job, keep the existing `-out=tfplan` flag on `terraform plan` and add an `actions/upload-artifact` step uploading `infrastructure/terraform/tfplan` — file: `.github/workflows/terraform-apply.yml`.
- [ ] T028 [US5] In the same file's `apply` job, add an `actions/download-artifact` step for the `tfplan` artifact, then change the apply step to `terraform apply -input=false tfplan` (removing `-auto-approve` and `-var-file=terraform.tfvars`, which only apply to generating a new plan) — file: `.github/workflows/terraform-apply.yml`. Depends on T027.
- [ ] T029 [US5] Wire T026's structure test to run against the real apply-job configuration as a required PR check on changes to `terraform-apply.yml`; confirm it now passes. Depends on T026, T027, T028.

**Checkpoint**: Infrastructure apply now runs the exact reviewed plan; a stale plan fails outright (Terraform's native behavior) rather than silently re-planning (FR-015, FR-016), protected by an automated structure test.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, closing the loop on SC-001's before/after measurement, end-to-end operational validation, and the constitution-mandated human acceptance gate.

- [ ] T030 Update `.github/workflows/README.md` to describe the new job graphs (`test → release → build → deploy`), concurrency groups, path-diff-based version gating, tag/version-file naming conventions, and the PR-title requirement, per `contracts/workflow-interfaces.md` — file: `.github/workflows/README.md`. Depends on all of Phase 3–7 being complete.
- [ ] T031 Run through `quickstart.md` Scenarios 1–5 end-to-end against real PRs, merges, and Actions runs, including Scenario 3's vertical-slice step; record any deviations and fix before sign-off. Depends on T030.
- [ ] T032 Record post-implementation `backend-deploy.yml`/`frontend-deploy.yml` run durations and compare them against `baseline-metrics.md` (T003), recording the result against SC-001. Depends on T031.
- [ ] T033 Final acceptance (Constitution Principle IX, NON-NEGOTIABLE): the requesting user or product owner confirms Scenarios 1–5 behave as specified against the real deployed environment and real GitHub state — not merely that workflow YAML is syntactically valid or that automated tests pass. This task is not complete until that confirmation is given. Depends on T031, T032.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: T003 has no file dependency but must complete before Phase 3+ changes are made (baseline validity). T004 and T005 are independent of T001/T002 and of each other.
- **User Stories (Phase 3–7)**: All may start once Phase 1–2 are complete.
  - **US1 (T006–T009)**: No dependency on other stories. T006 (test) before T007/T008 (implementation) before T009 (wire-up).
  - **US2 (T010–T013)**: No dependency on US1 — a `concurrency:` block is independent of internal job structure — but touches the same files as US1, so sequence edits to avoid merge conflicts if worked on concurrently by different people.
  - **US3 (T014–T022)**: Depends on US1 (T007/T008) — the `release` job is inserted into the job graph US1 creates, and `build` is updated to consume its output. T014 (the fixture test) should be written before T017/T018 implement the path-diff filtering it checks.
  - **US4 (T023–T025)**: Fully independent — can be done in any order relative to US1–US3, though it delivers most value once US3 exists (well-formed titles making versioning's descriptive content trustworthy).
  - **US5 (T026–T029)**: Fully independent of US1–US4 (different workflow file entirely).
- **Polish (Phase 8)**: Depends on all prior phases being complete.

### Parallel Opportunities

- T001 and T002 (Setup) — different files.
- T003, T004, and T005 (Foundational) — different files/artifacts.
- T007 and T008 (US1 implementation) — different files.
- T011 and T012 (US2 implementation) — different files.
- T016 can run parallel to T014/T015 (different files); T018 parallel to T017; T020 parallel to T019.
- T023 (US4 test) can run at any point in parallel with any other phase's tasks — it's a wholly new, independent file.
- T026 (US5 test) can likewise run at any point in parallel with any other phase's tasks.

---

## Parallel Example: Phase 3 (User Story 1)

```bash
# Launch both component restructurings together — different files, no shared dependency:
Task: "Restructure .github/workflows/backend-deploy.yml into test/build/deploy jobs"
Task: "Restructure .github/workflows/frontend-deploy.yml into test/build/deploy jobs"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 (Setup) and Phase 2 (Foundational — baseline capture and workflow-lint are worth having even for an MVP-only rollout).
2. Complete Phase 3 (User Story 1: T006 test, then T007–T008 implementation, then T009 wire-up).
3. **STOP and VALIDATE**: run quickstart.md Scenario 1 against real merges.
4. This alone delivers the feature's core correctness guarantee (SC-002) and most of its speed benefit (SC-001), safely shippable before versioning/concurrency/PR-title/Terraform work lands.

### Incremental Delivery

1. Setup + Foundational → baseline captured, lockfile committed, workflow lint active.
2. Add US1 (test-first: T006, then T007–T009) → validate → this is the MVP.
3. Add US2 (test-first: T010, then T011–T013) → validate → commit-order safety added, still independent of versioning.
4. Add US3 (test-first: T014, then T015–T022) → validate → versioning live, including the vertical-slice fix, protected by an automated fixture test.
5. Add US4 (test-first: T023, then T024–T025) → validate → malformed titles now blocked going forward.
6. Add US5 (test-first: T026, then T027–T029) → validate → infra apply-the-plan fix live (fully independent, could also land first or anywhere in this sequence).
7. Phase 8 → document, run full quickstart pass, close out SC-001's before/after comparison, obtain final human acceptance sign-off.

---

## Notes

- Every user story (US1–US5) now has a dedicated automated test written before its implementation (T006, T010, T014, T023, T026) and wired up to pass afterward (T009, T013, T022; T024/T028 double as their own stories' implementation-and-passing step) — see the Tests header above and research.md decision #8. quickstart.md's manual scenarios remain the separate Principle IX human-acceptance layer, not a substitute for these.
- US2 and US5 touch files independently of US1/US3/US4 and could, in principle, be implemented first — the ordering above follows spec.md's priority (P1 → P2 → P3), not a hard technical dependency, except where explicitly noted (US3 depends on US1).
- Commit after each task; T007/T008, T011/T012, T015/T016, T017/T018, T019/T020 pairs touch the same two files repeatedly across phases — verify no phase's edit to a shared file accidentally reverts an earlier phase's edit to that same file.
- T006, T010, and T026's structure-assertion tests may reasonably live in a single shared script (e.g. `scripts/test-workflow-structure.sh`) with per-story assertion functions, rather than three separate files — implementer's judgment call, since the task descriptions specify behavior/assertions, not file boundaries between them.
