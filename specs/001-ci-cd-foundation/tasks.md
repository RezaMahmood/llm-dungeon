# Tasks: CI/CD Foundation & PR Governance

**Input**: Design documents from `/specs/001-ci-cd-foundation/`

**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, quickstart.md ✓

**Feature Type**: Repository governance & CI/CD configuration (not application code)

**Tests**: Not applicable — this feature is configuration-driven. Validation is performed via the scenarios in quickstart.md, which test GitHub's native features.

**Organization**: Tasks are grouped by user story to enable independent configuration and validation.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)
- Include exact file paths in descriptions

## Important Note on "Testing"

This feature gates our test suite via CI, but the tests themselves are user story dependencies — they must already exist before this feature can validate them. The quickstart.md document provides manual validation scenarios that confirm GitHub's native branch protection and Actions features work as configured.

---

## Phase 1: GitHub Actions Workflow Setup

**Purpose**: Create the GitHub Actions workflow that runs the project's test suite on every pull request

**⚠️ CRITICAL**: The project must have a working test suite before this workflow can be deployed. If tests don't exist yet, create them in a separate feature before completing this phase.

### GitHub Actions Workflow Configuration

- [x] T001 Create `.github/workflows/test.yml` with trigger on pull_request (opened, synchronize, reopened) events
- [x] T002 [P] Add checkout step to GitHub Actions workflow
- [x] T003 [P] Add runtime setup step (Python/Node.js/etc.) to match project's test framework
- [x] T004 [P] Add dependency installation step to GitHub Actions workflow
- [x] T005 Add test execution step that runs the project's full test suite (pytest/npm test/etc.)
- [x] T006 Configure 30-minute job timeout in `.github/workflows/test.yml` per FR-004a
- [x] T007 [P] Add GitHub Actions status reporting so results appear as a required status check on PRs
- [x] T008 Commit and push the workflow file to main branch (this enables it for all future PRs)

**Checkpoint**: GitHub Actions workflow is deployed and active. It will run on all pull requests going forward.

---

## Phase 2: Branch Protection Rule Configuration

**Purpose**: Configure GitHub branch protection on the main branch to enforce PR-only access and test-gated merge

### User Story 1 (P1): Repository Enforces Pull-Request-Only Changes

**Goal**: No one can push a commit directly to the main branch — all changes must enter via pull request.

**Independent Test**: 
- Attempt to push a commit directly to main → verify rejection
- Create a pull request with the same change → verify it can proceed through review/merge flow

#### Configuration Tasks for User Story 1

- [x] T009 [US1] Configure GitHub branch protection rule on main branch (via GitHub UI or API)
- [x] T010 [US1] Set "Require a pull request before merging" = true in branch protection rule
- [x] T011 [US1] Set "Dismiss stale pull request approvals when new commits are pushed" = true (best practice)
- [x] T012 [US1] Set "Allow force pushes" = false and "Allow deletions" = false in branch protection rule
- [x] T013 [US1] Verify rule applies uniformly to all users (no admin bypass) per FR-002
- [x] T014 [US1] Test: Attempt direct push to main branch, verify rejection with error message

**Checkpoint**: User Story 1 complete. Branch protection enforces PR-only access to main branch.

---

## Phase 3: CI Test Gating

**Purpose**: Integrate the GitHub Actions workflow with branch protection to gate merge on passing tests

### User Story 2 (P2): Automated Test Suite Runs on Every Pull Request

**Goal**: Every pull request triggers the test suite; merge is blocked if tests fail.

**Independent Test**:
- Open PR with failing test → verify merge is blocked
- Fix the test and push → verify merge becomes available once tests pass
- Verify PR with passing tests can be merged (given reviewer approval is satisfied)

#### Configuration Tasks for User Story 2

- [x] T015 [US2] Add GitHub Actions workflow ("test" job) as a required status check in branch protection rule
- [x] T016 [US2] Set "Require status checks to pass before merging" = true in branch protection rule
- [x] T017 [US2] Configure "Require 1 approval" in branch protection rule per clarified requirement (FR-005)
- [x] T018 [US2] Verify author can approve their own change (single developer policy)
- [x] T019 [US2] Test: Open PR with a deliberate test failure, verify merge is blocked
- [x] T020 [US2] Test: Fix failing test in PR, verify merge becomes available once tests pass

**Checkpoint**: User Story 2 complete. CI test suite gates PR merge; tests must pass before merge is allowed.

---

## Phase 4: Validation & Documentation

**Purpose**: Run comprehensive validation scenarios and document the configuration

### Validation Tasks

- [x] T021 Run Validation Scenario 1 (Direct Push Rejection) from quickstart.md
- [x] T022 Run Validation Scenario 2 (GitHub Actions Workflow Runs on PR) from quickstart.md
- [x] T023 Run Validation Scenario 3 (PR Merge Blocked on Failed Tests) from quickstart.md
- [x] T024 Run Validation Scenario 4 (PR Merge Allowed on Passing Tests) from quickstart.md
- [x] T025 Run Validation Scenario 5 (Merge Blocked Without Reviewer Approval) from quickstart.md
- [x] T026 Run Validation Scenario 6 (Workflow Reruns on New Commits) from quickstart.md
- [x] T027 Run Validation Scenario 7 (Manual Branch Protection Rule Verification) from quickstart.md
- [x] T028 Document any issues found and verify all scenarios pass before marking feature complete

**Checkpoint**: All validation scenarios pass. Feature is ready for use by the team.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Documentation and knowledge transfer for the team

### Documentation & Knowledge Transfer

- [x] T029 Update project README with CI/CD governance model and branch protection policy
- [x] T030 Add documentation to CONTRIBUTING.md or equivalent about PR workflow and CI gating
- [x] T031 [P] Document the GitHub Actions workflow in a README within `.github/workflows/`
- [x] T032 Create a troubleshooting guide for common CI/CD issues (see quickstart.md Troubleshooting section)
- [x] T033 Share the quickstart.md validation guide with the team for reference

**Checkpoint**: Feature is documented. Team understands the CI/CD governance model.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (GitHub Actions Workflow Setup)**: No dependencies - can start immediately
- **Phase 2 (Branch Protection Configuration)**: Depends on Phase 1 (workflow must exist before being used as a required status check)
- **Phase 3 (CI Test Gating)**: Depends on Phase 2 (branch protection rule must exist before integrating tests as a status check)
- **Phase 4 (Validation)**: Depends on Phase 3 (everything must be configured before validation)
- **Phase 5 (Polish & Documentation)**: Depends on Phase 4 (validation must pass before finalizing documentation)

### User Story Dependencies

**Within User Story 1 (PR-Only Access)**:
- Configuration tasks (T009–T013) must complete before test task (T014)
- Test task (T014) confirms User Story 1 is working

**Within User Story 2 (Test Gating)**:
- Configuration tasks (T015–T018) must complete before test tasks (T019–T020)
- Test tasks verify User Story 2 is working

**Between User Stories**:
- User Story 1 and 2 are not strictly sequential but logically follow in priority order
- User Story 1 MUST be complete before User Story 2 tests can be meaningful (can't test merge gating without PR-only access)

### Prerequisite: Working Test Suite

**BLOCKING**: This feature assumes the project already has a working test suite (per project Constitution Principle I). If tests do not exist:
1. Create tests in a separate feature/PR
2. Ensure tests run locally and pass
3. Then deploy this CI/CD feature

---

## Parallel Opportunities

### Within Phase 1 (GitHub Actions Workflow)

Tasks marked [P] can run in parallel:
- T002 (checkout step) and T003 (runtime setup) and T004 (dependencies) can be added to the workflow concurrently

### Within Phase 2 & 3 (Branch Protection Configuration)

Since branch protection is a single configuration object, tasks here must be done sequentially:
- T009 (create rule) → T010–T013 (configure properties) → T014 (test)
- T015–T018 (add status check and reviewer requirement) → T019–T020 (test)

### Phase 4 (Validation)

All validation scenarios (T021–T027) can be run in parallel (they test the same feature from different angles):
- T021–T027 can be executed concurrently
- Results must be collected and verified before marking complete

### Phase 5 (Documentation)

Documentation tasks marked [P] can run in parallel:
- T031 (workflow README) is independent of T029–T030, T032–T033

---

## Parallel Example: Full Validation Suite

```bash
# Run all validation scenarios in parallel (they test the same configured feature):
- T021: Direct Push Rejection test
- T022: GitHub Actions Execution test
- T023: Merge Blocked on Failed Tests test
- T024: Merge Allowed on Passing Tests test
- T025: Reviewer Approval Required test
- T026: Workflow Rerun test
- T027: Manual Branch Protection Verification test

# Collect results → T028: Document and verify all pass
```

---

## Implementation Strategy

### Single Developer (Current Scenario)

1. **Phase 1**: Create GitHub Actions workflow (T001–T008)
   - Create `.github/workflows/test.yml` with all necessary steps
   - Commit and push to main
   
2. **Phase 2 & 3**: Configure branch protection (T009–T020)
   - Create branch protection rule via GitHub UI or API
   - Add required status check and reviewer requirement
   - Test both features work together
   
3. **Phase 4**: Run full validation suite (T021–T028)
   - Execute all scenarios from quickstart.md
   - Verify each one passes
   
4. **Phase 5**: Document and finalize (T029–T033)
   - Update project documentation
   - Share quickstart.md with team

### Team Expansion (Future)

When additional developers join:
- Provide them with the quickstart.md validation guide
- Explain the CI/CD governance model
- Point them to contributing guidelines with PR workflow

---

## MVP Scope (Minimum Viable Product)

For an MVP, complete only **User Story 1**:

1. ✅ Complete Phase 1: GitHub Actions Workflow Setup (T001–T008)
2. ✅ Complete Phase 2: Branch Protection for PR-Only Access (T009–T014)
3. ✅ Run Phase 4 Validation for User Story 1 (T021–T027, focusing on direct push rejection)
4. ❌ SKIP Phase 3 (Test Gating) until tests exist and are stable

**Result**: Repository enforces PR-only access. CI workflow exists but is not yet gated as a required check.

---

## Incremental Delivery

### Increment 1: PR-Only Access (User Story 1)
- Phases 1, 2, 4 (partial), 5 (minimal)
- **Value**: Repository enforces PR-based workflow
- **Validation**: Direct push rejection works

### Increment 2: Test Gating (User Story 2)
- Phase 3, 4 (remaining), 5 (complete)
- **Value**: Tests gate PR merge; quality enforcement active
- **Validation**: All quickstart.md scenarios pass
- **Dependency**: Assumes tests exist and pass

---

## Task Checklist Summary

**Total Tasks**: 33

**Phase Breakdown**:
- Phase 1 (Workflow Setup): T001–T008 (8 tasks)
- Phase 2 (User Story 1 - PR-Only): T009–T014 (6 tasks)
- Phase 3 (User Story 2 - Test Gating): T015–T020 (6 tasks)
- Phase 4 (Validation): T021–T028 (8 tasks)
- Phase 5 (Documentation): T029–T033 (5 tasks)

**By Story**:
- User Story 1 (P1): T009–T014, T021, T023–T027 (9 tasks total)
- User Story 2 (P2): T015–T020, T022, T024, T028 (9 tasks total)
- Setup/Support: T001–T008, T029–T033 (13 tasks)

**Parallelizable Tasks**: T002–T004, T031, T021–T027

---

## Notes

- This feature is configuration-driven; no traditional application code to write
- Tasks focus on GitHub configuration (via UI or API) and validation
- The workflow file (`.github/workflows/test.yml`) is the primary artifact
- Branch protection rule is configured via GitHub (stored in repository settings, not version-controlled as a separate file)
- Quickstart.md provides the validation strategy; tasks reference it for testing
- Each user story is independently testable and can be deployed separately
- Documentation (Phase 5) helps team understand and maintain the CI/CD governance
