# Feature Specification: Terraform Apply Gating on Validate and Infrastructure Tests

**Feature Branch**: `020-terraform-apply-gating`

**Created**: 2026-08-30

**Status**: Draft

**Input**: User description: "the terraform apply step in the GitHub workflow should be gated such that it can only be allowed to run after terraform validate and infrastructure tests have successfully completed. Manual approval should still be required"

## User Scenarios & Testing *(mandatory)*

<!--
  This is an infrastructure/platform feature rather than a player- or admin-facing one.
  The "users" here are the engineering team and the automated pipelines acting on their
  behalf; the value delivered is a safer, more trustworthy deployment gate for changes
  to production Azure infrastructure.
-->

### User Story 1 - Apply Is Blocked Until Validate and Infrastructure Tests Pass (Priority: P1)

An engineer pushes a Terraform change to the main branch. Before any reviewer is ever asked to approve applying that change to production, the pipeline first confirms the configuration passes `terraform validate`/format checks and the infrastructure test suite. If either check fails or hasn't finished, the apply step never becomes available to approve or run.

**Why this priority**: This is the core problem being fixed — today, apply is triggered by the same push event as validate and tests but runs as an independent workflow, so it is possible for apply to start (and a reviewer to be prompted to approve it) before validation or testing has finished, or even when they have failed. Closing this gap is the entire point of the feature.

**Independent Test**: Push a Terraform change to main that fails `terraform validate` (or that fails an infrastructure test), and verify the apply step/workflow never reaches the point of prompting for manual approval and never runs `terraform apply`. Then push a change that passes both checks and verify apply becomes available for approval only after both checks complete successfully.

**Acceptance Scenarios**:

1. **Given** a Terraform change is pushed to main, **When** `terraform validate` (including format checks) fails, **Then** the apply step is not run and no manual approval prompt is issued for it.
2. **Given** a Terraform change is pushed to main, **When** `terraform validate` passes but the infrastructure test suite fails, **Then** the apply step is not run and no manual approval prompt is issued for it.
3. **Given** a Terraform change is pushed to main, **When** both `terraform validate` and the infrastructure test suite complete successfully, **Then** the apply step becomes available and awaits manual approval before running `terraform apply`.
4. **Given** validate and infrastructure tests are still running for a pushed change, **When** an engineer checks the apply step's status, **Then** it is shown as waiting/not yet started rather than already running or already awaiting approval.

---

### User Story 2 - Manual Approval Remains Required Before Apply Runs (Priority: P1)

Even after validate and infrastructure tests both succeed, a designated reviewer must still explicitly approve the run before `terraform apply` executes against production Azure resources.

**Why this priority**: Manual approval is the existing safety control that prevents unreviewed infrastructure changes from reaching production automatically. The feature must not weaken or remove this control while adding the new automated gate — both protections need to hold at once.

**Independent Test**: Push a Terraform change that passes validate and infrastructure tests, and verify `terraform apply` does not execute until a designated reviewer approves the pending run; verify that rejecting the run prevents apply from executing.

**Acceptance Scenarios**:

1. **Given** validate and infrastructure tests have both succeeded for a change, **When** the apply step becomes available, **Then** it pauses and waits for a designated reviewer's approval before executing `terraform apply`.
2. **Given** an apply run is awaiting approval, **When** a designated reviewer approves it, **Then** `terraform apply` proceeds.
3. **Given** an apply run is awaiting approval, **When** a designated reviewer rejects it, **Then** `terraform apply` does not execute and the change is not applied to production.

---

### Edge Cases

- A Terraform change is pushed to main, but the infrastructure test run for that exact change fails to start or errors out (e.g., infrastructure outage) rather than passing or failing on assertions: apply must not be treated as gated-open — it stays blocked until a successful test run for that change exists.
- Two Terraform changes are pushed to main in quick succession: each apply run is gated on the validate/test results for its own change, not on a different push's results.
- A reviewer approves an apply run, but by the time it executes, a newer push to main has landed with different (possibly failing) validate/test results: the running or already-approved apply is not silently redirected to apply the newer, ungated change.
- Someone manually re-triggers only the apply workflow (bypassing the normal push trigger) without a corresponding successful validate/test run for the same commit: this must not be a way to skip the gate.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The pipeline MUST run `terraform validate` (including format checks) and the infrastructure test suite for every Terraform change pushed to main before the apply step is permitted to start.
- **FR-002**: The apply step MUST NOT execute `terraform apply`, and MUST NOT prompt for manual approval, unless both `terraform validate` and the infrastructure test suite have completed successfully for the same pushed change.
- **FR-003**: If `terraform validate` fails for a pushed change, the pipeline MUST prevent the apply step from running for that change.
- **FR-004**: If the infrastructure test suite fails for a pushed change, the pipeline MUST prevent the apply step from running for that change.
- **FR-005**: The apply step MUST continue to require explicit manual approval from a designated reviewer before `terraform apply` executes, even after the automated gate (validate + infrastructure tests) has passed.
- **FR-006**: Rejecting the manual approval MUST prevent `terraform apply` from executing, consistent with current behavior.
- **FR-007**: The gate MUST evaluate the validate and infrastructure-test results for the specific commit/change being applied, not a prior or unrelated push.
- **FR-008**: The pipeline MUST make it clear (e.g., via status/state visible to engineers) when the apply step is blocked because the automated gate has not yet passed, as distinct from being blocked on manual approval.
- **FR-009**: Manually re-running or re-triggering the apply step outside of the normal push-triggered flow MUST NOT bypass the requirement that validate and infrastructure tests have already passed for that same change.

### Key Entities

- **Terraform Change**: A set of Terraform configuration modifications pushed to main, identified by its commit, that must pass through validate, infrastructure tests, and manual approval before being applied.
- **Automated Gate Result**: The pass/fail outcome of `terraform validate` and the infrastructure test suite for a given Terraform Change; must be a success for both before apply becomes eligible to run.
- **Apply Approval**: The manual reviewer decision (approve/reject) required before `terraform apply` executes, evaluated only after the Automated Gate Result is a success.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of pushes to main containing Terraform changes that fail `terraform validate` or the infrastructure test suite result in zero `terraform apply` executions and zero manual-approval prompts for that change.
- **SC-002**: 100% of pushes to main containing Terraform changes that pass both `terraform validate` and the infrastructure test suite still require an explicit manual approval before `terraform apply` executes.
- **SC-003**: Engineers can determine, without cross-referencing multiple unrelated workflow runs, whether an apply is blocked due to failing/incomplete automated checks versus blocked on pending manual approval.
- **SC-004**: No change to production infrastructure occurs without both a successful automated gate and an explicit manual approval recorded for that same change.

## Assumptions

- "Infrastructure tests" refers to the existing automated infrastructure test suite that already runs in this project's pipeline; this feature reorders/gates its relationship to apply rather than introducing a new test suite.
- The existing manual-approval control (a required-reviewer gate in front of applying to production) is being preserved as-is in terms of who can approve; this feature only changes when that approval prompt becomes available, not who can grant it.
- Gating is scoped to the pipeline path that applies Terraform changes to the production environment; other environments or manually-run local applies are out of scope unless they share the same pipeline.
- It is acceptable for validate and infrastructure tests to run in whatever order or parallelism they currently use, as long as both must reach a successful outcome before apply is eligible to start.
- Rejected or failed automated-gate runs do not need a separate notification mechanism beyond the pipeline's existing failure reporting; this feature does not introduce new alerting.
