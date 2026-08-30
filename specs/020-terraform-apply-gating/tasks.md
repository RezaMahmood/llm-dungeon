---

description: "Task list for Terraform Apply Gating on Validate and Infrastructure Tests"
---

# Tasks: Terraform Apply Gating on Validate and Infrastructure Tests

**Input**: Design documents from `/specs/020-terraform-apply-gating/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/terraform-apply-pipeline-contract.md, quickstart.md

**Tests**: No automated test suite applies to this feature — it restructures GitHub Actions
workflow YAML, which cannot be meaningfully unit-tested. Verification instead uses the
explicit, real-run scenarios from `quickstart.md`, tasked below as their own checklist
items per Constitution Principle IX (user-verified acceptance).

**Organization**: Both user stories in spec.md are Priority P1. US1 (the automated gate)
is implemented first since US2 (manual approval survives the gate) requires no code
change of its own — it is a property of the unmodified `production-infra` environment
protection rule — and so is expressed here entirely as verification tasks that depend on
US1's implementation.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)

## Path Conventions

Single project; the only paths touched are under `.github/workflows/`. No `src/`/`tests/`
scaffolding applies — see plan.md's Project Structure section.

---

## Phase 1: Setup

**Not applicable.** This feature edits three existing GitHub Actions workflow files; no
project scaffolding, dependency installation, or tooling configuration is needed.

---

## Phase 2: Foundational

**Not applicable.** There is no shared prerequisite infrastructure beyond what already
exists (the `production` and `production-infra` GitHub environments, OIDC federated
credentials, and the existing Terraform/test scripts — all provisioned by
`007-azure-infrastructure-provisioning` and unchanged here). The workflow restructuring
in Phase 3 is not blocked on anything new.

---

## Phase 3: User Story 1 - Apply Is Blocked Until Validate and Infrastructure Tests Pass (Priority: P1) 🎯 MVP

**Goal**: `terraform-apply.yml`'s `apply` job becomes reachable (including its approval
prompt) only after `terraform validate`/fmt and the infrastructure test suite have both
succeeded for the same pushed commit.

**Independent Test**: Push a Terraform change that fails `terraform validate` (or that
fails an infrastructure test) to `main`, and confirm the `apply` job in that run shows
`skipped` with no pending environment review — per `quickstart.md` Scenarios 1 and 2.

### Implementation for User Story 1

- [X] T001 [US1] In `.github/workflows/terraform-apply.yml`, replace the single `apply`
  job with three jobs — `validate`, `test`, `apply` — per
  `contracts/terraform-apply-pipeline-contract.md`: (a) `validate` runs the existing
  `terraform-validate.yml` push-path steps (checkout, setup Terraform, run
  `infrastructure/tests/test_terraform_validate.sh`, Azure Login via OIDC, `terraform
  init -backend-config=backend-prod.hcl`, `terraform plan -var-file=terraform.tfvars`),
  with no `needs:`; (b) `test` has `needs: validate` and `if: needs.validate.result ==
  'success'`, and runs the existing `infrastructure-tests.yml` steps (checkout, setup
  Python 3.11, setup Terraform, Azure Login via OIDC, `terraform init`
  read-only, `pytest infrastructure/tests/ -v`), keeping `environment: production`; (c)
  `apply` has `needs: test` and `if: needs.test.result == 'success'`, keeps its existing
  `environment: production-infra` and all of its current steps (Azure Login, `terraform
  init`, `terraform apply -auto-approve -var-file=terraform.tfvars`, capture/upload
  outputs) unchanged. Keep the workflow's `push`/`workflow_dispatch` triggers and path
  filters as they are today. Omit the PR-only `Upload plan artifact` step (conditioned on
  `github.event_name == 'pull_request'`) from the new `validate` job, since that condition
  can never be true on a `push`/`workflow_dispatch` trigger.

- [X] T002 [P] [US1] In `.github/workflows/terraform-validate.yml`, remove the
  `push: branches: [main]` trigger entry (now redundant with the `validate` job added in
  T001), keeping only the `pull_request` trigger so PR-time fmt/validate/plan feedback is
  unaffected.

- [X] T003 [P] [US1] In `.github/workflows/infrastructure-tests.yml`, remove the
  `push: branches: [main]` trigger entry (now redundant with the `test` job added in
  T001), keeping only the nightly `schedule` and standalone `workflow_dispatch` triggers
  for ops/monitoring use.

- [X] T004 [US1] Push a Terraform change to a branch that deliberately fails
  `terraform fmt`/`validate` (e.g., an unformatted `.tf` file) and merge to `main`.
  Confirm, per `quickstart.md` Scenario 1: `validate` job = `failure`; `test` and `apply`
  jobs = `skipped`; no pending review request appears on the `production-infra`
  environment. Depends on: T001.

- [X] T005 [US1] Push a Terraform change that passes validate but fails an
  `infrastructure/tests/` assertion, and merge to `main`. Confirm, per `quickstart.md`
  Scenario 2: `validate` = `success`; `test` = `failure`; `apply` = `skipped`; no pending
  review request. Depends on: T001.

- [X] T006 [US1] With the commit from T004 (or any commit whose gate has not passed)
  still at the tip of `main`, run `gh workflow run terraform-apply.yml` and confirm, per
  `quickstart.md` Scenario 5: the dispatched run re-executes `validate` (and `test` only
  if `validate` passes) from scratch rather than jumping straight to `apply` or an
  approval prompt. Depends on: T001.

- [X] T006a [US1] Push two Terraform changes to `main` in quick succession — one that
  fails `terraform validate` (or infra tests), one right behind it that passes both —
  and confirm, per `quickstart.md` Scenario 7, that each run's `apply` gate reflects only
  its own commit's `validate`/`test` results, independent of the other push's outcome.
  Depends on: T001.

- [X] T007 [US1] Confirm the runs from T004 and T005 both show `apply` = `skipped` with
  no pending environment review requested against `production-infra` — the
  automated-gate-blocked half of `quickstart.md` Scenario 6. Depends on: T004, T005.

**Checkpoint**: `apply` is now provably unreachable for any commit whose validate/test
results are not both successes, with no change yet required to demonstrate the manual
approval gate itself (Phase 4).

---

## Phase 4: User Story 2 - Manual Approval Remains Required Before Apply Runs (Priority: P1)

**Goal**: Confirm that once the automated gate from User Story 1 passes, `terraform
apply` still pauses for a designated reviewer's explicit approval (or rejection) before
executing — unchanged from today's `production-infra` environment protection rule.

**Independent Test**: Push a Terraform change that passes both `terraform validate` and
the infrastructure tests, and confirm `terraform apply` does not execute until a
designated reviewer approves the pending run; confirm rejecting the run prevents apply
from executing — per `quickstart.md` Scenarios 3 and 4.

### Verification for User Story 2

- [X] T008 [US2] Merge a valid, passing Terraform change to `main`. Watch the run:
  `validate` → `success`, `test` → `success`. Confirm, per `quickstart.md` Scenario 3,
  that the `apply` job's status becomes `waiting` with a pending deployment review
  requested against the `production-infra` environment, and that `terraform apply` has
  not executed yet. Depends on: T001 (no separate implementation task — this exercises
  the unmodified environment protection rule reached through the new gate).

- [X] T009 [US2] Approve the pending review from T008 (via `gh run view` or the Actions
  UI "Review deployments"). Confirm `apply` proceeds, `terraform apply` completes, and
  the outputs artifact is uploaded. Depends on: T008.

- [X] T010 [US2] Repeat T008 on a separate passing change, but reject the pending review
  instead of approving. Confirm, per `quickstart.md` Scenario 4, that the `apply` job
  ends without running `terraform apply` and no changes reach Azure. Depends on: T001.

- [X] T010a [US1][US2] Compare the `skipped` run from T007 against the `waiting` run from
  T008 (before approval) and confirm, per `quickstart.md` Scenario 6, that an engineer
  can tell "blocked by the automated gate" apart from "blocked on manual approval"
  without opening any other workflow's run. Depends on: T007, T008.

**Checkpoint**: Both the automated gate (Phase 3) and the pre-existing manual approval
control (Phase 4) are now confirmed to hold together on the same pipeline run.

---

## Phase 5: Polish & Cross-Cutting Concerns

- [X] T011 [P] In
  `specs/007-azure-infrastructure-provisioning/contracts/github-actions-contract.md`,
  add a short note above the "Workflow: Infrastructure Provisioning (terraform-apply.yml)"
  and "Workflow: Infrastructure Testing (infrastructure-tests.yml)" sections pointing
  readers to `specs/020-terraform-apply-gating/contracts/terraform-apply-pipeline-contract.md`
  as the current, accurate description of these workflows' triggers and job structure
  (that document was already stale relative to the as-built workflows before this
  feature; this avoids compounding the drift).

- [ ] T012 Final user-verified acceptance (Constitution Principle IX): the requesting
  user or product owner reviews the real GitHub Actions runs produced by T004, T006a,
  T008, and T010 (or an equivalent live run they trigger themselves) directly in the
  repository's Actions tab, and confirms the gate and approval behavior match spec.md's
  acceptance scenarios before this feature is considered done. The approved-but-
  superseded-push edge case (spec.md Edge Cases) does not need its own live
  demonstration — it is guaranteed by GitHub Actions' per-run commit checkout (see
  research.md), not custom logic this feature adds — but the reviewer should be aware
  this is the guarantee being relied upon. This task is not complete until that
  confirmation is given — not merely on the strength of T004–T010a having been executed
  by the implementing agent. Depends on: T004, T006a, T008, T010.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup / Foundational**: N/A — nothing to complete first.
- **User Story 1 (Phase 3)**: No dependency on other stories; T001 is the sole
  implementation task and everything else in this feature (Phase 4's verification,
  Phase 5) depends on it.
- **User Story 2 (Phase 4)**: Depends on T001 (the gate must exist for there to be
  anything to verify the approval step is reached through). No implementation task of
  its own — the `production-infra` environment rule is unchanged.
- **Polish (Phase 5)**: T011 has no dependency; T012 depends on both stories' verification
  tasks completing.

### Within Phase 3

- T001 must land before T002/T003 are meaningful to verify end-to-end (though T002/T003
  are textually independent edits to different files and can be made in parallel with
  T001).
- T004, T005, T006, T006a each depend only on T001.
- T007 depends on T004 and T005 (compares their outcomes) but, unlike the full
  skipped-vs-waiting contrast, needs no `waiting` run to exist yet.

### Within Phase 4

- T010a depends on T007 (Phase 3) and T008 — it is the skipped-vs-waiting half of
  `quickstart.md` Scenario 6 that T007 alone can't complete, since it needs T008's
  `waiting` run to contrast against.

### Parallel Opportunities

- T002 and T003 touch different files from T001 and from each other — can be done in
  parallel with T001 and with each other.
- T004, T005, T006, T006a can be run in parallel with each other (independent
  pushes/dispatches) once T001 has landed.

---

## Parallel Example: User Story 1

```bash
# T002 and T003 are independent one-line trigger edits in different files;
# can be done alongside T001's terraform-apply.yml restructuring:
Task: "Remove push trigger from .github/workflows/terraform-validate.yml"
Task: "Remove push trigger from .github/workflows/infrastructure-tests.yml"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete T001–T003 (the actual workflow restructuring).
2. Run T004–T006 to prove the gate blocks apply on failure and can't be bypassed by
   manual re-dispatch.
3. **STOP and VALIDATE**: this alone closes the security gap the feature exists to fix.

### Incremental Delivery

1. T001–T003 → gate exists.
2. T004–T007, T006a → gate proven to block correctly on failure, independently per
   pushed commit, and re-dispatch-proof (User Story 1's own behavior fully verified).
3. T008–T010 → manual approval proven to still hold once the gate passes (User Story 2
   complete).
4. T010a → the skipped-vs-waiting contrast (SC-003/FR-008) is finalized once T008's
   `waiting` run exists.
5. T011–T012 → documentation pointer updated, final human sign-off recorded.
