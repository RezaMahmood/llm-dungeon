# Quickstart: Validating Terraform Apply Gating

**Feature**: 020-terraform-apply-gating | See `contracts/terraform-apply-pipeline-contract.md` for the full job/trigger contract and `data-model.md` for what each state means.

## Prerequisites

- Repo admin access (to inspect Actions runs and the `production-infra` environment's
  pending-approval queue).
- A throwaway branch off `main` for producing test pushes; merges into `main` are what
  actually fire the pipeline (path-filtered to `infrastructure/terraform/**`).

## Scenario 1 — Failing `terraform validate` blocks apply (FR-001, FR-003, Acceptance Scenario 1)

1. On a branch, introduce a deliberately malformed/unformatted `.tf` file under
   `infrastructure/terraform/`.
2. Merge to `main`.
3. `gh run list --workflow=terraform-apply.yml --limit=1` → open the run.
4. **Expected**: `validate` job = `failure`; `test` and `apply` jobs = `skipped`; no
   pending review request appears against the `production-infra` environment.

## Scenario 2 — Passing validate, failing infrastructure tests blocks apply (FR-002, FR-004, Acceptance Scenario 2)

1. On a branch, make a valid Terraform change that nonetheless fails an assertion in
   `infrastructure/tests/` (e.g., temporarily tighten a test's expected value).
2. Merge to `main`.
3. Inspect the run as above.
4. **Expected**: `validate` = `success`; `test` = `failure`; `apply` = `skipped`; no
   pending review request.

## Scenario 3 — Gate passes, apply still waits for manual approval (FR-005, Acceptance Scenario 3, User Story 2)

1. Merge a valid, passing Terraform change to `main`.
2. Watch the run: `validate` → `success`, `test` → `success`.
3. **Expected**: `apply` job status becomes `waiting` and the `production-infra`
   environment shows a pending deployment review — `terraform apply` has not executed
   yet.
4. Approve the pending review (`gh run view` or the Actions UI "Review deployments").
5. **Expected**: `apply` proceeds and completes `terraform apply`; outputs artifact is
   uploaded.

## Scenario 4 — Rejecting approval prevents apply (FR-006, Acceptance Scenario in US2)

1. Repeat Scenario 3 through step 3.
2. Reject the pending review instead of approving.
3. **Expected**: `apply` job ends without running `terraform apply`; no changes reach
   Azure.

## Scenario 5 — Manual re-dispatch cannot bypass the gate (FR-009, Edge Case)

1. On the same commit as Scenario 1 (failing validate) still at the tip of `main`,
   or any commit whose gate has not passed, run `gh workflow run terraform-apply.yml`.
2. **Expected**: the dispatched run re-executes `validate` (and `test` if validate
   passes) from scratch — it does not go straight to an `apply` job or an approval
   prompt. If validate/test fail again, `apply` is `skipped` exactly as in Scenario 1/2.

## Scenario 6 — Status distinguishes gate-blocked from approval-pending (FR-008, SC-003)

1. Compare a run from Scenario 1/2 (`apply` = `skipped`) against a run from Scenario 3
   before approval (`apply` = `waiting`, environment review pending).
2. **Expected**: an engineer looking at the Actions run list (or `gh run list`) can tell
   the two states apart without opening any other workflow's run — `skipped` vs
   `waiting`/pending-review are visually and textually distinct in the GitHub UI and in
   `gh run view` output.

## Scenario 7 — Quick-succession pushes gate independently (FR-007, Edge Case 2)

1. Push two independent Terraform changes to `main` in quick succession: change A
   deliberately fails `terraform validate` (as in Scenario 1); change B, pushed right
   behind it, is valid and passes both checks.
2. `gh run list --workflow=terraform-apply.yml --limit=2` → open both runs.
3. **Expected**: A's run shows `validate = failure`, `test`/`apply` = `skipped`. B's run
   independently shows `validate = success`, `test = success`, `apply = waiting`
   (pending review) — unaffected by A's failure.

## Final acceptance (Constitution Principle IX)

Per this project's constitution, this feature is not complete on automated evidence
alone — a human (the requesting user or product owner) must observe at least one real
run of Scenarios 1, 3, and 4 against the actual GitHub repository's Actions tab (not a
local simulation) and confirm the pipeline behaves as described before this feature is
marked done. This must appear as an explicit sign-off task in `tasks.md`, sequenced
last.
