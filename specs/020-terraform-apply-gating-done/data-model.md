# Data Model: Terraform Apply Gating

**Date**: 2026-08-30 | **Feature**: 020-terraform-apply-gating

This feature has no application data model (no database entities, no API payloads). Its
"entities" from spec.md map directly onto GitHub Actions constructs:

## Terraform Change

**Spec definition**: A set of Terraform configuration modifications pushed to main,
identified by its commit, that must pass through validate, infrastructure tests, and
manual approval before being applied.

**Concrete representation**: A single workflow run of `.github/workflows/terraform-apply.yml`,
triggered by a `push` event to `main` (or a `workflow_dispatch` re-run of the same file).
Its identity is `github.sha` — every job (`validate`, `test`, `apply`) within that one
run checks out that same commit via `actions/checkout@v4`, so "the same pushed change"
is enforced by the workflow run boundary itself, not by any field the workflow has to
track or compare.

**Lifecycle**: created when the triggering push/dispatch event fires → resolved when the
`apply` job reaches a terminal state (`success`, `failure`, `cancelled`, or `skipped`).

## Automated Gate Result

**Spec definition**: The pass/fail outcome of `terraform validate` and the infrastructure
test suite for a given Terraform Change; must be a success for both before apply becomes
eligible to run.

**Concrete representation**: The `result` of the `validate` job combined with the
`result` of the `test` job (which itself only runs `if: needs.validate.result ==
'success'`), within the same workflow run. The `apply` job's `if: needs.test.result ==
'success'` condition is the gate check — there is no separate stored "gate result"
record; the two upstream jobs' native GitHub Actions job-conclusion values *are* the
Automated Gate Result, queryable at any time via the workflow run's own Actions UI/API
(`gh run view <run-id>`).

**States**: `success` (both jobs succeeded — gate open), `failure` (either job failed —
gate closed, `apply` shows `skipped`), `cancelled` (either job cancelled — gate closed,
same as failure for `apply`'s purposes).

## Apply Approval

**Spec definition**: The manual reviewer decision (approve/reject) required before
`terraform apply` executes, evaluated only after the Automated Gate Result is a success.

**Concrete representation**: The existing `production-infra` GitHub environment's
required-reviewer protection rule, attached via `environment: production-infra` on the
`apply` job — unchanged by this feature. GitHub itself only surfaces this review prompt
once the job's `needs`/`if` conditions (the Automated Gate Result) have already been
satisfied and the job is otherwise ready to start, which is what gives User Story 1's
"no approval prompt before the gate passes" behavior for free.

**States**: `pending` (job waiting, environment review requested), `approved` (reviewer
approved — `terraform apply` step runs), `rejected` (reviewer rejected — job ends,
`terraform apply` never runs).
