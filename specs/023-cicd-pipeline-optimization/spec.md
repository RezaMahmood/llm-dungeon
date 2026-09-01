# Feature Specification: CI/CD Pipeline Optimization

**Feature Branch**: `023-cicd-pipeline-optimization`

**Created**: 2026-09-01

**Status**: Draft

**Input**: User description: "Optimize CI/CD workflows for speed and correctness across the frontend and backend components (infrastructure/Terraform is explicitly out of scope for versioning, though its apply-should-use-the-validated-plan fix is in scope). Backend and frontend deploy workflows currently mix install/test/build/deploy as one pass, the backend deploy step rebuilds via Azure Oryx remote-build instead of shipping the tested artifact, there is no dependency caching, no concurrency guard against out-of-order deploys, and no versioning of what's actually deployed. Required: caching, build-once-deploy-that-artifact restructuring per component, a concurrency guard so a newer push cancels a stale in-flight deploy, independent automated SemVer for frontend and backend only (via semantic-release with path scoping, git tag + GitHub Release per component, version stamped into the artifact), Conventional Commits enforced via a required commitlint PR check, and a fix so Terraform apply uses the exact plan validate already produced instead of re-planning. Out of scope: infrastructure SemVer, cross-workflow artifact promotion via workflow_run, rollback/redeploy of an older version, changing test.yml's triggers/scope beyond adding caching."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Backend/frontend changes deploy from the exact artifact that was tested (Priority: P1)

A maintainer merges a change to the backend or frontend into `main`. The change is tested, a version is computed and tagged, a deployable artifact is built exactly once from that tested code, and that same artifact — not a fresh rebuild — is what gets deployed to production.

**Why this priority**: This is the core correctness guarantee the feature exists to deliver: what was tested is what ships, bit-for-bit. Without it, a rebuild-at-deploy-time step (e.g. the backend's current remote build) can silently ship different code/dependencies than what passed tests, and every deploy pays a redundant build cost.

**Independent Test**: Merge a backend-only change to `main`, inspect the workflow run, and confirm the deploy job downloads and deploys the artifact the build job produced rather than re-running install/build steps. Repeat for a frontend-only change.

**Acceptance Scenarios**:

1. **Given** a backend change is merged to `main`, **When** the workflow runs, **Then** tests run once, a single backend artifact is built from the tested code, and the deploy step deploys that artifact without triggering any further remote build or reinstall step.
2. **Given** a frontend change is merged to `main`, **When** the workflow runs, **Then** tests run once, a single frontend artifact is built from the tested code, and the deploy step deploys that same built artifact without re-running the build.
3. **Given** a change touches only backend paths, **When** the workflow runs, **Then** the frontend workflow is not triggered and vice versa (existing path-scoping behavior is preserved).

---

### User Story 2 - Deploys never ship out of commit order (Priority: P1)

Two changes to the same component land on `main` in quick succession. Only the deploy corresponding to the newer commit reaches production; a deploy already in progress for an older commit is stopped before it can complete.

**Why this priority**: Without this, whichever deploy run happens to finish last wins, regardless of which commit is actually newer — so production can end up running older code than what the commit history shows, with no record that this happened. This directly delivers the "abort on conflict/newer version" requirement.

**Independent Test**: Push two commits to `main` touching the same component within a short window (or simulate by triggering two runs back to back) and confirm the earlier run is cancelled before its deploy step executes, while the later run proceeds and completes.

**Acceptance Scenarios**:

1. **Given** a deploy for commit A is in progress for a component, **When** a newer commit B for the same component is pushed to `main`, **Then** the in-progress run for commit A is cancelled before it deploys, and the run for commit B proceeds to deploy.
2. **Given** two components (frontend and backend) each receive a rapid pair of commits at the same time, **When** both workflows run, **Then** each component's cancellation is evaluated independently — a race in one component's workflow does not cancel or block the other component's deploy.

---

### User Story 3 - Every deployed frontend/backend build has a discoverable version (Priority: P2)

A maintainer investigating an incident or writing release notes wants to know what version of the frontend or backend is running in production, and can trace that version back to the exact commits it contains.

**Why this priority**: Today, deployed code is traceable only by commit SHA, with no human-readable version and no changelog. This is valuable but secondary to the correctness and ordering guarantees above — a well-versioned pipeline that still ships the wrong artifact or ships out of order is a worse outcome than an unversioned pipeline that never does.

**Independent Test**: Merge a `fix(backend): ...` commit and a `feat(frontend): ...` commit and confirm that, after the workflows run, a new backend patch version tag/release and a new frontend minor version tag/release each exist, each attributable only to the commits touching that component's paths, and each traceable to the artifact that was deployed.

**Acceptance Scenarios**:

1. **Given** a commit with a `fix` type and a `backend` scope is merged to `main`, **When** the backend workflow runs, **Then** the backend's patch version number increases, a new git tag and GitHub Release are created for that version, and no frontend version changes.
2. **Given** a commit with a `feat` type and a `frontend` scope is merged to `main`, **When** the frontend workflow runs, **Then** the frontend's minor version number increases, a new git tag and GitHub Release are created for that version, and no backend version changes.
3. **Given** a released version's artifact, **When** a maintainer inspects it, **Then** the version number is discoverable from the artifact/deployment itself, not only from the CI logs.
4. **Given** a commit touches only documentation or infrastructure paths, **When** the workflows run, **Then** neither the frontend nor backend version changes.

---

### User Story 4 - Malformed commit messages are caught before merge, not after (Priority: P2)

A contributor opens a pull request with a commit message that doesn't follow the Conventional Commits format or is missing a component scope. The pull request check fails with a clear reason before merge, rather than silently producing a wrong or skipped version bump later.

**Why this priority**: Automated versioning (User Story 3) is only trustworthy if the commit history it reads is well-formed. Catching this at PR time is cheaper to fix than debugging a missed or misattributed release after the fact, but the feature still delivers most of its value even if this check is briefly noisy while the team adapts.

**Independent Test**: Open a PR with a commit message that has no type/scope prefix and confirm the required check fails with an explanatory message; fix the message and confirm the check passes.

**Acceptance Scenarios**:

1. **Given** a PR contains a commit message that does not follow the Conventional Commits format, **When** the PR's checks run, **Then** the commit-format check fails and blocks merge, with a message explaining the expected format.
2. **Given** a PR contains only well-formed Conventional Commit messages with a valid component scope, **When** the PR's checks run, **Then** the commit-format check passes.

---

### User Story 5 - Terraform apply runs exactly the plan that was reviewed (Priority: P3)

When infrastructure changes are approved for deployment, the apply step applies the exact plan that was already generated and gated, rather than silently generating and applying a new plan at apply time.

**Why this priority**: This closes a build-once/no-rebuild gap analogous to the frontend/backend fix, and removes a window where the applied changes could differ from what was reviewed — but it's scoped to a single existing workflow step and carries no versioning requirement, so it's the smallest and lowest-risk piece of this feature.

**Independent Test**: Trigger the infrastructure apply workflow and confirm, from the run logs, that the apply step consumes the plan artifact produced by the earlier validation step rather than invoking a fresh plan.

**Acceptance Scenarios**:

1. **Given** the infrastructure validation step has produced a plan, **When** the apply step runs, **Then** it applies that exact plan file rather than computing a new one.
2. **Given** infrastructure state has drifted since the plan was produced such that the saved plan can no longer be applied cleanly, **When** the apply step runs, **Then** it fails clearly rather than silently falling back to re-planning and applying different changes than were reviewed.

---

### Edge Cases

- What happens when a component's build succeeds but the subsequent deploy step fails (e.g. transient cloud outage)? The version tag/release for that build already exists; a re-run must reuse that same version and artifact rather than computing a new version for an unchanged commit.
- What happens when a pull request contains a mix of well-formed and malformed commit messages? The commit-format check fails the PR until every commit (or the merged commit, depending on merge strategy) conforms.
- What happens when a merged commit touches both frontend and backend paths with a single scope (e.g. only `fix(backend): ...`)? Only the scoped component's version changes; the other component's workflow may still run its tests but must not cut a release for unscoped changes to its paths.
- What happens when no commits since the last release for a component match a releasable type (e.g. only `chore`/`docs` commits touching that component)? No new version, tag, or release is created for that component.
- What happens when two components' deploys race independently at the same time? Each component's cancellation and versioning logic is fully independent — no cross-component blocking.
- What happens the very first time this pipeline runs, before any component has a version tag? Each component starts from an initial baseline version (e.g. 1.0.0 or the version already recorded in its manifest) rather than failing for lack of a prior tag.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The backend workflow MUST separate testing, versioning, building, and deploying into distinct stages such that a deploy always uses the artifact produced by that same workflow run's build stage, never a fresh rebuild performed at deploy time.
- **FR-002**: The frontend workflow MUST separate testing, versioning, building, and deploying into distinct stages such that a deploy always uses the artifact produced by that same workflow run's build stage, never a fresh rebuild performed at deploy time.
- **FR-003**: Both the backend and frontend workflows MUST cache dependency installation so that unchanged dependencies are not re-downloaded/re-resolved on every run.
- **FR-004**: The frontend build MUST be reproducible from a committed dependency lockfile rather than an unlocked dependency resolution.
- **FR-005**: For each component (frontend, backend) independently, a newer push to `main` affecting that component MUST cause any still-in-progress deploy for an older commit of that same component to be stopped before it deploys.
- **FR-006**: A stopped/cancelled deploy MUST NOT be treated as a deploy failure requiring investigation — it is expected behavior when superseded by a newer commit.
- **FR-007**: Each of the frontend and backend components MUST have an independently computed Semantic Version, incremented only by changes attributable to that component's own paths.
- **FR-008**: The system MUST compute each component's next version automatically from its commit history since its last release, using the type of change indicated by each commit (e.g. bug fix vs. new feature vs. breaking change) to decide whether the increment is a patch, minor, or major version.
- **FR-009**: Each new version for a component MUST be recorded as a discoverable, permanent marker in the project's history (a tag and release note), distinguishable per component.
- **FR-010**: The version assigned to a build MUST be identifiable from the resulting deployed artifact/component itself, not solely from CI run logs.
- **FR-011**: Commit messages merged into `main` MUST follow a consistent, machine-parseable format that identifies both the type of change and which component it applies to.
- **FR-012**: A pull request containing one or more commit messages that do not follow the required format MUST be blocked from merging via a required, automated check, with feedback identifying the problem.
- **FR-013**: A commit that does not touch a given component's paths, or that is not a releasable change type (e.g. a non-functional housekeeping change), MUST NOT trigger a version change for that component.
- **FR-014**: Infrastructure changes remain entirely out of scope for automated versioning — no version, tag, or release is required or produced for infrastructure changes as part of this feature.
- **FR-015**: The infrastructure apply stage MUST apply the exact plan produced and gated earlier in the same pipeline run, rather than independently generating a new plan immediately before applying.
- **FR-016**: If the previously generated infrastructure plan can no longer be applied as-is (e.g. due to drift), the apply stage MUST fail with a clear explanation rather than silently substituting a freshly generated plan.
- **FR-017**: Existing pull-request-time testing behavior (what triggers it, what paths it covers) MUST be preserved, with dependency caching added but no change to its triggering scope.

### Key Entities

- **Component**: An independently versioned, tested, built, and deployed part of the system — specifically the frontend application and the backend application. Each has its own version history and pipeline stages, unaffected by changes to the other component or to infrastructure.
- **Release**: A named, versioned point in a component's history, tied to a specific set of commits and a specific built artifact, recorded permanently and discoverable after the fact.
- **Build Artifact**: The single deployable output produced once per pipeline run for a component, carrying its assigned version, and consumed as-is by the deploy stage without modification or rebuilding.
- **Infrastructure Plan**: The reviewed, gated description of infrastructure changes produced during validation, which the apply stage must execute unmodified.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: End-to-end time from merging a backend or frontend change to that change being live in production decreases measurably compared to the current pipeline (baseline measured before implementation).
- **SC-002**: 100% of production deploys for frontend and backend can be traced back to a single specific build artifact that also passed that run's tests — zero deploys are the product of a separate, independent rebuild step.
- **SC-003**: When two commits to the same component land within a short window, the older commit's deploy never reaches production after the newer commit's deploy — verified across repeated test cases with zero exceptions.
- **SC-004**: 100% of releasable changes to frontend or backend result in a correctly-scoped, discoverable version increment within one pipeline run of merging, with no manual version bookkeeping required.
- **SC-005**: A maintainer can determine the exact version of frontend or backend currently in production without consulting CI run history.
- **SC-006**: Malformed commit messages are caught and blocked at the pull request stage in 100% of cases, before reaching `main`.
- **SC-007**: Infrastructure apply runs execute the previously reviewed plan unchanged in 100% of successful runs, with zero instances of an apply silently using a different plan than was gated.

## Assumptions

- "Component" in this feature means the frontend application and the backend application only; infrastructure is explicitly excluded from versioning per the feature input, though it is still in scope for the build-once/apply-the-reviewed-plan correctness fix.
- The project adopts Conventional Commits (with a required component scope) as its commit message standard going forward; historical commits before this feature are not retroactively reformatted.
- "Automated Semantic Versioning" means version numbers are computed by the pipeline from commit history, not chosen manually by a maintainer per release.
- Each component starts its automated versioning from a reasonable baseline (e.g. its current manifest version or 1.0.0) the first time this pipeline runs, since no prior component-scoped version tags exist today.
- A cancelled/superseded deploy run is acceptable operational behavior and does not require alerting as a failure, distinct from a deploy that fails due to an actual error.
- Rollback to a previously deployed version, and any cross-workflow artifact promotion mechanism, are explicitly out of scope for this feature.
- Pull-request-time testing keeps its current triggers and path scope; only dependency caching is added to it.
