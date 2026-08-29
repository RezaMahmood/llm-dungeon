# Feature Specification: CI/CD Foundation & PR Governance

**Feature Branch**: `001-ci-cd-foundation`

**Created**: 2026-08-28

**Status**: Draft

**Input**: User description: "we will need some foundation work done to set up CI/CD pipelines using Github Actions. Github will also need to be configured to only allow checkins after a PR is created - AI should be validating that the PR is valid - Github Copilot Free plan should be sufficient but it all needs to be set up."

**Amendment (2026-08-28)**: The AI-assisted PR review capability (originally User Story
3 / FR-005–FR-007 below) was rolled back at the user's explicit direction — automated
Copilot PR review requires a paid GitHub Copilot subscription, which the project's
budget does not currently support. This spec now covers branch protection and the
automated test-suite CI gate only. AI PR review may be revisited as a future amendment
if budget allows.

## Clarifications

### Session 2026-08-28

- Q: What is the maximum acceptable time for the CI test suite to complete on a pull request? → A: 30 minutes (balanced approach: full test suite, reasonable feedback loop).
- Q: How many human reviewers must approve a pull request before it can merge, and can the author approve their own change? → A: 1 reviewer required; author can self-approve (single developer scenario, can be revisited as team grows).
- Q: When a CI test run fails, how should the team be notified? → A: GitHub native notifications only (built-in email/in-app via GitHub); no separate tooling initially.

## User Scenarios & Testing *(mandatory)*

<!--
  This is a repository-governance/tooling feature rather than a player- or admin-facing
  one. The "users" here are the engineering team and the automated pipelines acting on
  their behalf; the value delivered is a repository that mechanically enforces the
  project's own constitution (PR-only changes, PR-gated CI, mandatory human review)
  instead of relying on discipline alone.
-->

### User Story 1 - Repository Enforces Pull-Request-Only Changes (Priority: P1)

No one can push a commit directly to the main branch — every change, from any
contributor, must enter through a pull request.

**Why this priority**: This is the foundational governance gate everything else in this
feature depends on, and it is the direct, mechanical enforcement of a rule the project's
constitution already states as non-negotiable.

**Independent Test**: Attempt to push a commit directly to the main branch and verify it
is rejected; open a pull request with the same change and verify it can proceed through
the normal review/merge flow instead.

**Acceptance Scenarios**:

1. **Given** the main branch is protected, **When** anyone attempts to push a commit
   directly to it, **Then** the push is rejected.
2. **Given** a change is proposed via a pull request instead, **When** the pull request
   is opened, **Then** it can proceed through the required checks and review process
   toward merge.

---

### User Story 2 - Automated Test Suite Runs on Every Pull Request (Priority: P2)

Every pull request automatically triggers the project's full automated test suite; the
pull request cannot be merged while that run is failing.

**Why this priority**: This operationalizes the constitution's testing and CI-gate
principles as an actual, enforced pipeline rather than a stated policy — it is the
primary quality gate, and it depends on the pull-request mechanism from User Story 1.

**Independent Test**: Open a pull request containing a failing test and verify merge is
blocked; fix it and verify merge becomes available once the run passes.

**Acceptance Scenarios**:

1. **Given** a pull request is opened or updated, **When** the CI workflow runs,
   **Then** it executes the project's full automated test suite against the proposed
   change.
2. **Given** a pull request's test run fails, **When** someone attempts to merge it,
   **Then** the merge is blocked until the run passes.
3. **Given** a pull request's test run passes, **When** all other required checks and
   reviews are satisfied, **Then** the merge is allowed to proceed.

---

### Edge Cases

- A user with elevated repository permissions (e.g., a repository administrator)
  attempts to bypass branch protection: the protection applies uniformly, with no
  direct-push exemption for elevated permissions.
- A pull request is opened by an automated process (e.g., a dependency-update bot): the
  same required checks (tests, human approval) apply — no special exemption.
- A pull request changes only non-code content (e.g., documentation): the same
  pull-request-only and required-checks rules apply uniformly; this feature does not
  introduce a content-based exemption.
- The CI test-runner service is temporarily unavailable when a pull request is opened:
  the pull request's status reflects that the check has not yet completed — there is no
  silent bypass that lets the pull request merge as though the check succeeded.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The repository's main branch MUST be configured so that no commit can be
  pushed to it directly; every change MUST enter via a pull request.
- **FR-002**: Branch protection MUST apply uniformly, including to users with elevated
  repository permissions; no direct-push bypass MUST exist for the main branch.
- **FR-003**: Every pull request MUST automatically trigger a GitHub Actions workflow
  that runs the project's full automated test suite.
- **FR-004**: A pull request MUST be blocked from merging while its required test run
  has not passed.
- **FR-004a**: The CI test workflow MUST complete within 30 minutes; runs exceeding this
  time MUST be marked as failed and block merge.
- **FR-005**: A pull request MUST require at least 1 approval from a reviewer before it
  can merge; the author of the pull request is permitted to approve their own change
  (single developer policy, subject to revision as the team grows).
- **FR-006**: CI test failures MUST be visible through GitHub's native notification
  system (email, GitHub in-app notifications); no additional notification tooling is
  required for this feature.
- **FR-007**: This pull-request-time validation pipeline (branch protection + test CI)
  is distinct from, and MUST NOT be conflated or merged with, the application
  deployment pipeline already specified in `007-azure-infrastructure-provisioning`;
  that pipeline deploys application code to Azure, this one validates a pull request
  before merge.
- **FR-008**: Each distinct governance/CI outcome (direct push rejected, PR test run
  passing, PR test run failing and blocking merge) MUST be verified — by an automated
  check where the outcome is testable in code, or by a documented verification step
  where it is a GitHub-native repository setting that cannot be unit-tested directly.

### Key Entities

- **Branch Protection Rule**: The repository-level configuration on the main branch
  requiring a pull request, passing required status checks, and reviewer approval
  before a change can merge.
- **CI Validation Workflow**: The GitHub Actions workflow that runs the project's
  automated test suite against every pull request.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of direct-push attempts to the main branch are rejected in testing.
- **SC-002**: 100% of pull requests with a failing required test run are blocked from
  merge in testing.

## Assumptions

- AI-assisted PR review (GitHub Copilot or otherwise) is explicitly out of scope for
  this spec: it requires a paid subscription tier the project's budget does not
  currently support, per direct user decision. The project's constitution already
  requires at least one human contributor's review before merge; that requirement is
  unaffected and is not re-specified here. Automated AI review may be added later via a
  new amendment if budget allows.
- This spec covers pull-request-time validation (branch protection, test CI) only.
  Provisioning the Azure infrastructure the tests and deployments run against, and the
  deployment workflow itself, are already covered by
  `007-azure-infrastructure-provisioning` and are not re-specified here.
- The "full automated test suite" referenced here is the same one required by the
  project's constitution (Principle I); this spec does not define what tests exist, only
  that they run automatically on every pull request and gate merge.
- Review requirements are currently set to 1 reviewer (with author self-approval permitted)
  per the clarification captured above, reflecting the single-developer phase of the
  project. As the team grows, branch protection rules may be updated to require a
  second reviewer or designated code owners without this feature being re-specified.
