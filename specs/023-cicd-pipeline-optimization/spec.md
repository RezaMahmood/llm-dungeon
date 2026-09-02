# Feature Specification: CI/CD Pipeline Optimization — Test-on-Push, Build-on-Merge, Manual Deploy

**Feature Branch**: `023-cicd-pipeline-optimization`

**Created**: 2026-09-02

**Status**: Draft

**Input**: User description: "Start again. I want a pipeline that does the following: on push, run standard tests. On merge, do a build, version it, and cache the assets. The deploy step should be a manually triggered workflow. Front end, backend and infrastructure should follow the same pattern - deploy is always manual. when doing the deploy, the user should be asked to provide the specific version - which can be retrieved from the last build if this is being triggered from AI (e.g. claude). So if I tell claude to deploy latest, it should see if there's a cached version of the asset - if not then build a new artifact for that same version and deploy. basically, no code can enter the github main unless it's been tested. once tested, the resulting build should be idempotent and immutable and versioned and it should be usable as is. if a newer version of frontend/backend/infrastructure lands before a deploy occurs and a version hasn't been specified, then latest should be assumed. this should effectively separate CI from CD - CD will always be manual. CI will happen at push and merge"

## Clarifications

### Session 2026-09-02

- Q: Should frontend and backend deploys become fully automatic on a successful merge to `main`, while infrastructure keeps a required manual approval/validation gate before apply? → A: No — "automatable" is not "automated." Deploy stays a distinct, explicitly-triggered action for all three components (never a side effect of merge); an AI agent can chain push→build→deploy as one requested sequence, but that is the agent invoking the same manual trigger, not the pipeline auto-cascading into deploy on its own. The real difference is what happens *after* that trigger fires: frontend/backend deploys execute directly, while infrastructure's trigger must additionally pass a validation/approval gate before it applies.
- Q: For infrastructure's validation gate, does it require a human to explicitly approve the change before it applies, or is an automated check sufficient? → A: Human approval required — an AI agent (or automation) may trigger validation and prepare the plan, but cannot itself approve/apply it. All validation and testing MUST be complete before that final human approval/apply step; the gate is the last step in the sequence, not interleaved with earlier checks.
- Q: Should the spec commit to specific numeric performance targets for CI feedback/build-cache latency, or stay directional? → A: Directional only — no fixed numeric target. The pipeline must avoid unnecessary serial delay (e.g., independent components test/build in parallel, cache lookups never trigger an avoidable rebuild), but no specific time budget is set since nothing has been measured yet for this pipeline shape.
- Q: If someone bypasses the normal merge gate (e.g., an admin force-pushes to `main` or overrides a required check), should the build/version/cache step independently re-verify a passing test result before building, or is preventing bypass entirely a repository-permissions concern outside this feature's scope? → A: Rely on the merge gate (FR-002/FR-003) plus standard branch-protection settings as the sole enforcement mechanism — no separate in-pipeline re-verification step. An admin bypassing branch protection is an out-of-scope governance/permissions issue, not something this feature's build pipeline is required to independently detect or refuse.
- Q: Should non-testable artifacts (documentation, specs, markdown) be excluded from triggering test/build/version by content type wherever they live, or only when they live outside all component directories? → A: By content type, but only when the *entire* change set is non-testable content — exclude a push/PR from triggering any component's test/build/version/cache pipeline only if every changed file is a non-testable artifact (docs, specs, markdown, comments-only), regardless of directory. The moment even one changed file in that same push/PR is a testable/buildable artifact, the full test/build pipeline for the affected component(s) MUST run as normal — including for the non-testable files bundled in that same change.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - No untested code reaches main (Priority: P1)

A contributor pushes a change to a branch or opens a pull request. The standard automated test suite for the affected component(s) runs automatically. The change can only be merged into `main` once its tests have passed — there is no path for untested code to enter `main`.

**Why this priority**: This is the foundational guarantee everything else depends on. If untested code can reach `main`, then "the resulting build is usable as-is" (User Story 2) has no basis, since a build could be made from broken code.

**Independent Test**: Push a change that breaks a test and confirm the merge is blocked; push a change that passes and confirm it can merge.

**Acceptance Scenarios**:

1. **Given** a change is pushed to a branch touching frontend, backend, or infrastructure paths, **When** the push occurs, **Then** the standard test suite for that component runs automatically without any manual step.
2. **Given** a pushed change's tests fail, **When** a merge into `main` is attempted, **Then** the merge is blocked.
3. **Given** a pushed change's tests pass, **When** a merge into `main` is attempted, **Then** the merge is allowed to proceed.

---

### User Story 2 - Merging to main produces one immutable, versioned, cached build (Priority: P1)

When a tested change merges into `main`, the system builds a deployable artifact for each affected component exactly once, assigns it a version, and stores it in a cache. That artifact is complete and usable as-is — no further build or modification step is needed before it can be deployed.

**Why this priority**: This is the core deliverable that separates CI from CD: CI's job ends with a trustworthy, ready-to-ship artifact. Without this, "deploy" would still require a build step, defeating the separation.

**Independent Test**: Merge a tested change to `main` and confirm exactly one artifact is built for each affected component, that it is tagged with a version, and that it is retrievable from the cache afterward without rebuilding.

**Acceptance Scenarios**:

1. **Given** a tested change merges into `main` and only touches frontend paths, **When** the merge completes, **Then** a single frontend artifact is built, assigned a version, and stored in the cache; backend and infrastructure are untouched.
2. **Given** a tested change merges into `main` and touches both frontend and backend paths, **When** the merge completes, **Then** each affected component independently receives its own build, version, and cache entry.
3. **Given** an artifact has been built and cached for a version, **When** that same version is requested again, **Then** the existing cached artifact is returned rather than a new build being produced (idempotent, immutable).

---

### User Story 3 - Deploy is always a separate, explicitly-triggered action; infrastructure additionally requires human approval (Priority: P1)

For each of frontend, backend, and infrastructure, deploying to an environment is a distinct action that a person (or an AI agent acting on their instruction) must explicitly trigger — merging to `main` never causes an automatic deploy for any of them. Frontend and backend deploys execute directly once triggered. Infrastructure's deploy trigger additionally requires a human to review and approve the validated change before it applies; an AI agent may trigger validation and prepare the change, but cannot itself approve or apply it.

**Why this priority**: This is the other half of the CI/CD separation: CI (test + build + version + cache) is automatic, CD (deploy) is never a side effect of merge. Uniform explicit-trigger behavior across all three components keeps the pipeline predictable to operate; infrastructure's added human-approval gate reflects that its changes can affect live, often-irreversible cloud resources, unlike a frontend/backend redeploy of a previously tested artifact.

**Independent Test**: Merge a change to `main` for each component and confirm no deploy occurs; then manually trigger each component's deploy action and confirm frontend/backend deploy directly while infrastructure stops for approval before applying.

**Acceptance Scenarios**:

1. **Given** a change merges into `main` for any component, **When** the merge completes, **Then** no deploy of that component occurs automatically.
2. **Given** a maintainer or AI agent wants to deploy frontend or backend, **When** they explicitly trigger that component's deploy action, **Then** the deploy proceeds directly as a result of that trigger, with no additional approval step.
3. **Given** a maintainer or AI agent wants to deploy infrastructure, **When** they explicitly trigger the infrastructure deploy action, **Then** the system validates the change and then waits for a human to review and approve it before applying — an AI-triggered request cannot itself supply that approval.
4. **Given** the three components' deploy actions, **When** compared, **Then** each follows the same explicit-trigger, version-accepting, deploy-cached-artifact-as-is pattern, differing only in that infrastructure inserts a mandatory human approval step between trigger and apply.

---

### User Story 4 - Deploy targets a specific version, defaulting to latest (Priority: P2)

When triggering a deploy, the person (or AI agent) provides which version of the component to deploy. If no version is given, the system deploys whichever version is the most recently built one for that component at the moment the deploy actually runs — even if a newer version landed after the deploy was requested but before it executed.

**Why this priority**: This makes deploys precise and predictable rather than ambiguous, while still supporting the common "just ship whatever is newest" case without forcing every deploy trigger to look up a version number by hand.

**Independent Test**: Trigger a deploy with an explicit older version and confirm that exact version is deployed; trigger a deploy with no version specified while multiple versions exist and confirm the most recently built one is deployed.

**Acceptance Scenarios**:

1. **Given** multiple versions of a component have been built and cached, **When** a deploy is triggered with a specific version, **Then** exactly that version's cached artifact is deployed.
2. **Given** a deploy is triggered without specifying a version, **When** the deploy runs, **Then** the most recently built version available for that component at that moment is deployed.
3. **Given** a deploy was requested without a version, **and** a newer version finishes building before the deploy actually executes, **When** the deploy runs, **Then** the newer version is deployed, not whatever was latest at request time.

---

### User Story 5 - An AI agent can resolve and deploy "latest" on request (Priority: P2)

A user asks an AI agent (e.g., Claude) to deploy the latest version of a component. The agent determines whether a cached artifact already exists for that version; if it does, the agent deploys it as-is. If no cached artifact exists yet for that version, the agent causes it to be built first, then deploys the resulting artifact — without the user having to manually look up version numbers or trigger a separate build step.

**Why this priority**: This is the concrete, user-facing payoff of Stories 1-4 working together, and it's the specific workflow the request calls out by name. It depends on the version/cache/manual-deploy mechanics already existing, so it is ordered after them.

**Independent Test**: With a cached artifact already present for the latest version, ask an AI agent to deploy latest and confirm it deploys the cached artifact without rebuilding. Then, in a state where the latest version has no cached artifact, repeat the request and confirm a build occurs first and the resulting artifact is deployed.

**Acceptance Scenarios**:

1. **Given** the latest version of a component already has a cached artifact, **When** an AI agent is asked to deploy "latest", **Then** it deploys the cached artifact without triggering a new build.
2. **Given** the latest version of a component has no cached artifact, **When** an AI agent is asked to deploy "latest", **Then** it builds the artifact for that exact version first, then deploys it.
3. **Given** an AI agent is resolving "latest", **When** it checks for a cached artifact, **Then** it identifies the version to check by the same "most recently built version" rule used for any other unspecified-version deploy (User Story 4).

---

### Edge Cases

- Deploy is triggered with an explicit version that was never built (e.g., a typo, or a version number that doesn't exist for that component): the deploy MUST fail with a clear error rather than silently falling back to another version or building an unrequested one.
- Deploy is triggered for "latest" on a component that has never been built at all (no merge to `main` has ever happened for it): the system builds an artifact from the current tested state of `main` for that component, versions it, caches it, and deploys it.
- Two deploys for the same component and same version are triggered close together: both MUST result in the same artifact being deployed (no duplicate or divergent builds), consistent with idempotency.
- A push happens to a non-`main` branch (e.g., a feature branch or PR): only the test phase runs; no build, version, or cache entry is created.
- A merge to `main` touches only one component's paths: only that component's build/version/cache pipeline runs; the other components are unaffected and their "latest version" stays whatever it already was.
- A requested build for a version that already has a cached artifact: the existing artifact is reused as-is; no new build is produced and no existing cache entry is overwritten.
- Someone bypasses the merge gate itself (e.g., an admin force-pushes directly to `main`, or overrides a required status check): this is a repository-permissions/governance concern outside this feature's scope — the build pipeline relies on the merge gate (FR-002/FR-003) and standard branch protection as its sole enforcement mechanism and is not required to independently re-verify test results before building.
- A push or PR changes only documentation/spec/markdown files (including refining specs under `specs/`, wherever they're committed): no component's test, build, version, or cache pipeline is triggered, and merging is not blocked waiting on a check that has nothing to test.
- A push or PR changes documentation/spec files together with even one testable/buildable file: the full test pipeline (and, on merge, build/version/cache) runs for every affected component exactly as normal — the presence of docs/spec files in the same change does not narrow or skip any of it.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST automatically run the standard automated test suite for a component whenever a change affecting that component's paths is pushed, on any branch.
- **FR-002**: The system MUST block a change from being merged into `main` while its required tests have not passed.
- **FR-003**: The system MUST NOT provide any path by which untested code can be merged into `main`.
- **FR-004**: Upon a change merging into `main`, the system MUST build a deployable artifact for each component whose paths were affected by that change, and MUST NOT rebuild components whose paths were unaffected.
- **FR-005**: The system MUST assign each built artifact a unique version, distinct per component, so that frontend, backend, and infrastructure each have their own independent version history.
- **FR-006**: The system MUST store each built artifact in a cache keyed by component and version, so it can be retrieved later without rebuilding.
- **FR-007**: Built artifacts MUST be immutable — once a version's artifact has been built and cached, its contents MUST NOT be altered.
- **FR-008**: Building MUST be idempotent — requesting a build for a version that already has a cached artifact MUST reuse that cached artifact rather than producing a new one.
- **FR-009**: A built, cached artifact MUST be usable as-is for deployment, with no further build, install, or modification step required at deploy time.
- **FR-010**: Deployment for each of frontend, backend, and infrastructure MUST be a distinct action that requires an explicit trigger (by a person, or by an AI agent acting on a person's instruction); none of them may be initiated automatically as a result of a push or a merge to `main`.
- **FR-011**: All three components' deploy actions MUST follow the same operational pattern — explicitly triggered, accepts a version, deploys that version's cached artifact as-is — differing only in that infrastructure inserts a mandatory human-approval step (FR-011a) between trigger and apply.
- **FR-011a**: Infrastructure's deploy action MUST require a human to review and approve the validated change before it is applied; an AI agent MAY trigger validation and prepare the change, but MUST NOT be able to supply that approval itself. All validation and testing for the change MUST be complete before this approval step — the approval is the final step in the sequence, not interleaved with earlier checks.
- **FR-011b**: Frontend and backend deploy actions MUST execute directly once explicitly triggered, with no additional approval step required between trigger and deploy.
- **FR-012**: A deploy action MUST accept a version identifying which artifact of that component to deploy.
- **FR-013**: When a deploy is triggered without a version specified, the system MUST deploy the most recently built version available for that component at the time the deploy actually executes.
- **FR-014**: When a deploy is triggered for a version that has a cached artifact, the system MUST deploy that cached artifact without rebuilding it.
- **FR-015**: When a deploy is triggered for a version that has no cached artifact (including "latest" resolving to a version that hasn't been built yet), the system MUST build that exact version's artifact first, then deploy it.
- **FR-016**: When a deploy is triggered for an explicit version that does not exist and cannot be built (e.g., it does not correspond to any tested state that ever merged to `main`), the system MUST fail the deploy with a clear error rather than deploying a different version.
- **FR-017**: The system MUST make it possible to determine, for each component, which version was most recently built, so that "latest" can be resolved by a person or an AI agent without inspecting build logs.
- **FR-018**: The system MUST support an AI agent initiating a deploy on a user's behalf, including resolving an unspecified or "latest" version request to a concrete version and determining whether that version already has a cached artifact before deciding whether to build.
- **FR-019**: If every file changed in a push or pull request is a non-testable artifact (documentation, specs, markdown, comments-only content), the system MUST NOT trigger any component's test, build, version, or cache pipeline for that change, regardless of which directory the files live in.
- **FR-020**: If a push or pull request changes at least one testable/buildable file, the system MUST run the full test (and, on merge, build/version/cache) pipeline for every component whose paths were affected — including for any non-testable files bundled in that same change — exactly as it would if no non-testable files were present.

### Key Entities

- **Component**: One of Frontend, Backend, or Infrastructure — an independently tested, built, versioned, and deployed unit of the system.
- **Build Artifact**: The immutable, versioned output of a successful build for one component; complete and usable as-is for deployment.
- **Version**: A unique identifier assigned to a build artifact, scoped to its component, used to reference exactly which tested change the artifact was built from.
- **Cache**: The store of build artifacts, keyed by component and version, consulted before any new build and used to serve deploys without rebuilding.
- **Deploy Action**: A manually triggered operation, one per component, that takes an optional version (defaulting to latest-at-execution-time) and results in that version's cached artifact being deployed.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of changes merged into `main` have their tests pass beforehand — there is no recorded instance of untested code merging.
- **SC-002**: Every deploy delivers the exact same artifact that was built and cached at merge time — zero rebuilds occur between build and deploy for a given version.
- **SC-003**: A maintainer or AI agent can deploy any previously built, still-cached version of a component in a single manual action, without waiting for a new build.
- **SC-004**: Requesting a deploy of "latest" when no cached artifact yet exists for that version results in a completed deploy from a single trigger, with the build happening automatically as part of that same request.
- **SC-005**: Across frontend, backend, and infrastructure, zero deploys occur as an automatic consequence of a merge to `main`; every deploy has a corresponding explicit trigger, and every infrastructure deploy additionally has a recorded human approval before it applied.
- **SC-006**: Re-requesting a build for an already-cached version returns the identical artifact rather than producing a new one, in 100% of observed cases.
- **SC-007**: The pipeline introduces no unnecessary serial delay: independent components' tests and builds proceed in parallel rather than waiting on each other, and no deploy or build step rebuilds an artifact that a cache lookup could have served instead. (Directional — no fixed numeric time budget is set by this feature.)

## Assumptions

- "Standard tests" on push means the same automated test suite this project already requires as its merge-blocking CI gate — this feature does not narrow or expand what counts as "tested," only when and how the resulting build is produced and deployed.
- Versions are assigned using a semantic, change-driven scheme (e.g., derived from the nature of each change — fix, feature, breaking change) consistent with this project's existing versioning practice; the exact mechanics of how a version number is computed are an implementation detail, not a product requirement.
- "Merge" means a pull request merging into `main`. Pushes to any other branch (including open pull requests) trigger only the test phase — never a build, version bump, or cache entry.
- Each component's test/build/version/cache pipeline is scoped to that component's own paths, consistent with this project's existing per-component (frontend/backend/infrastructure) workflow separation — a change to one component's paths does not trigger another component's pipeline.
- Manually triggering a deploy (by a person or by an AI agent acting for them) requires the same repository permissions already in place for this project; this feature does not introduce a new authorization model.
- The artifact cache has no expiry policy driven by this feature — artifacts remain retrievable indefinitely, consistent with the immutability requirement. Only a genuinely lost/evicted artifact would need to be rebuilt, which FR-015's build-on-demand behavior already covers.
- Deploying an explicitly specified older version is a supported way to redeploy a previous release (functions as a rollback) because the identical, previously tested artifact is simply reused — no separate "rollback" mechanism is required.
- Infrastructure participates in the same test-on-push, build/version/cache-on-merge, explicitly-triggered-deploy pattern as frontend and backend; its "build artifact" is whatever validated, deployable output infrastructure changes produce (e.g., a validated plan) rather than a compiled application bundle. It differs from frontend/backend only in requiring a human-approval gate between trigger and apply (FR-011a).
- "No code can enter `main` unless it's been tested" is enforced by the merge gate and this project's existing branch-protection settings (FR-002/FR-003); the build pipeline does not perform its own independent re-verification of test results. A bypass of branch protection (e.g., an admin override) is a repository-permissions/governance matter outside this feature's scope.
