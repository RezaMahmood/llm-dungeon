# Research: Terraform Apply Gating

**Date**: 2026-08-30 | **Feature**: 020-terraform-apply-gating

## Current State (as-built, not the stale 007 contract doc)

Three independent GitHub Actions workflows currently exist, all triggered on
`push: branches: [main]` with the same `infrastructure/terraform/**` path filter, with
no dependency between them:

- `terraform-validate.yml` — also triggers on `pull_request`; runs `terraform fmt`/`validate`
  and `terraform plan` (upload plan artifact on PR only).
- `infrastructure-tests.yml` — also triggers on nightly `schedule` and `workflow_dispatch`;
  runs `pytest infrastructure/tests/`.
- `terraform-apply.yml` — also triggers on `workflow_dispatch`; runs `terraform apply
  -auto-approve`, gated only by the `production-infra` GitHub environment's
  required-reviewer rule.

Because all three fire independently off the same push event, `terraform-apply.yml` can
reach its approval prompt (and, if manually re-dispatched, run `terraform apply` itself)
without any regard for whether validate or the test suite passed, failed, or even
finished — this is the gap FR-001–FR-004 close.

## Decision: Consolidate into one workflow with job-level `needs:` chaining

**Decision**: Fold validate → test → apply into a single workflow
(`terraform-apply.yml`, keeping the filename) as three jobs — `validate`, `test`,
`apply` — chained with `needs:`, so `apply` only becomes eligible to run (and only then
hits its `production-infra` environment approval gate) when `test` reports
`result == 'success'`, which itself requires `validate`'s success.

**Rationale**:
- A single workflow run checks out one commit SHA for every job in it (via
  `actions/checkout@v4` in each job, all resolving the same triggering `ref`/`sha`), so
  the gate is inherently scoped to "this push's commit" (FR-007) with no extra
  bookkeeping — this is the property that most directly satisfies the spec's Edge Cases
  around quick-succession pushes.
- `needs:` + job `if:` conditions on `result` are native GitHub Actions primitives —
  no polling, no cross-workflow GitHub API calls, no artifact hand-off to correlate runs.
  This is the simplest mechanism that satisfies FR-001–FR-004 (Constitution Principle IV,
  Simplicity Over Premature Scale).
- `workflow_dispatch` on this same file re-runs the full `validate → test → apply` chain
  (not an apply-only job), so manually re-triggering cannot skip the gate — this
  directly satisfies FR-009 without a separate anti-bypass mechanism.
- The `apply` job keeps its existing `environment: production-infra` required-reviewer
  gate untouched, satisfying FR-005/FR-006/User Story 2 with zero change to the approval
  mechanism itself.
- GitHub's Actions UI already renders a `skipped` job distinctly from a job `Waiting`
  on an environment review — so "blocked by the automated gate" and "blocked on manual
  approval" are visibly different states with no new status reporting to build
  (FR-008, SC-003).

**Alternatives considered**:
- **`workflow_run` trigger, apply listens for both upstream workflows' completion**:
  Rejected. `infrastructure-tests.yml` and `terraform-validate.yml` run in parallel, so
  `apply` would need to fire on completion of *either* upstream workflow and then query
  the GitHub API for the other's conclusion on the same `head_sha` — doubling the trigger
  surface, adding a live API dependency inside the gate itself, and introducing a race
  window (the second upstream workflow's run for this SHA may not exist yet in the API
  response at the moment the first one's completion fires the check). The single-workflow
  `needs:` approach gets the same guarantee for free from the scheduler.
- **A dedicated "gate" job that polls both other workflows' status via `gh run list`**:
  Rejected for the same reasons — it re-implements what `needs:` already does natively,
  and adds a runtime dependency on `GITHUB_TOKEN` permissions/API rate limits for
  something that doesn't need to leave the current workflow run.
- **Leave three separate workflows, add a required status check in branch protection**:
  Rejected — branch protection required-checks block *merging a PR*, not a workflow
  dispatched by a push already on `main`; it has no effect on this pipeline's push-to-main
  triggers and cannot gate `terraform-apply.yml` at all.

## Decision: Trim the now-redundant `push` triggers off the two source workflows

**Decision**: Remove `push: branches: [main]` from `terraform-validate.yml` (keep its
`pull_request` trigger, for PR-time fmt/validate/plan feedback) and from
`infrastructure-tests.yml` (keep its nightly `schedule` and standalone
`workflow_dispatch`, for ops/monitoring use uninvolved with a specific pending apply).

**Rationale**: Once the combined `terraform-apply.yml` workflow runs its own
`validate` and `test` jobs on every push to main, leaving the old `push` triggers on the
standalone workflows would run `terraform fmt`/`validate` and the pytest suite a second,
redundant time per push — wasted CI minutes with no behavioral benefit, and two
differently-named workflow runs reporting on the same commit that could confuse "which
one is the real gate" (working against FR-008/SC-003 rather than for it).

**Alternatives considered**:
- **Leave the redundant triggers in place**: Rejected — pure waste, and a source of
  confusion about which run is authoritative for the gate.
- **Delete `terraform-validate.yml`/`infrastructure-tests.yml` entirely, folding PR and
  nightly/manual behavior into the combined workflow with `if:` conditions on
  `github.event_name`**: Considered, but rejected as a larger, riskier diff than
  necessary — PR-time validation and nightly ops health-checks are unrelated concerns to
  the apply gate (Assumptions section of spec.md) and already work correctly today;
  trimming just the overlapping trigger keeps each workflow's remaining purpose obvious
  and touches the fewest lines.

## Accepted (unchanged) behavior: approved-but-superseded runs

**Decision**: No new mechanism is introduced to detect or cancel an already-approved
`apply` run if a newer push lands on `main` before it executes.

**Rationale**: `actions/checkout@v4` in the `apply` job checks out the specific commit
SHA that triggered *that* workflow run, not "whatever `main` currently is" — so an
approved run applies the change it was gated and approved for, never a newer,
ungated one. This satisfies the spec's edge case ("the running or already-approved apply
is not silently redirected to apply the newer, ungated change") as an inherent property
of how GitHub Actions resolves a workflow run's ref, with no extra code required.
