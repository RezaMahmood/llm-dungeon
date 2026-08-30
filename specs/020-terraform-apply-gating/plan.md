# Implementation Plan: Terraform Apply Gating on Validate and Infrastructure Tests

**Branch**: `020-terraform-apply-gating` | **Date**: 2026-08-30 | **Spec**: `specs/020-terraform-apply-gating/spec.md`

**Input**: Feature specification from `/specs/020-terraform-apply-gating/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

`terraform-validate.yml`, `infrastructure-tests.yml`, and `terraform-apply.yml` currently
run as three independent GitHub Actions workflows, all triggered by the same push-to-main
event, with no dependency between them — so the `production-infra` approval prompt (and,
via `workflow_dispatch`, `terraform apply` itself) can be reached without validate or the
infrastructure test suite having passed for that commit. The fix consolidates all three
into a single workflow (kept as `terraform-apply.yml`) with three jobs — `validate` →
`test` → `apply` — chained with native `needs:`/`if:` conditions, so `apply` (and its
existing `production-infra` required-reviewer gate) only becomes reachable once both
upstream jobs report success for that same commit. `terraform-validate.yml` and
`infrastructure-tests.yml` keep their PR-time and nightly/manual purposes respectively,
just without a now-redundant push-to-main trigger.

## Technical Context

**Language/Version**: YAML (GitHub Actions workflow syntax); Bash and Python 3.11 in the
existing steps being relocated/reused (`infrastructure/tests/test_terraform_validate.sh`,
`pytest`).

**Primary Dependencies**: GitHub Actions (`actions/checkout@v4`,
`hashicorp/setup-terraform@v3`, `actions/setup-python@v5`, `azure/login@v2`), the
project's existing `infrastructure/terraform/` configuration and
`infrastructure/tests/` suite — all unchanged, only re-sequenced.

**Storage**: N/A.

**Testing**: No new automated tests are introduced by this feature — it re-sequences
existing CI steps. Verification is functional/behavioral against real GitHub Actions
runs, per `quickstart.md`'s six scenarios plus the Constitution Principle IX final
acceptance task.

**Target Platform**: GitHub Actions (`ubuntu-latest` runners), gating access to Azure via
the existing `production-infra` GitHub environment.

**Project Type**: CI/CD pipeline configuration change (single project; no
frontend/backend/mobile split applies here).

**Performance Goals**: N/A — this is a correctness/ordering gate, not a throughput or
latency concern.

**Constraints**: Must not weaken or remove the existing `production-infra`
required-reviewer approval gate (Constitution Principle II's least-access posture and
this feature's User Story 2); must not introduce a way to run `terraform apply` for a
commit whose validate/test results are not both successes (FR-002, FR-009); must not
duplicate CI compute by leaving redundant triggers on the source workflows (research.md).

**Scale/Scope**: Three existing workflow files; net change is one workflow's jobs
restructured (`terraform-apply.yml`) plus a one-line trigger removal in each of the other
two (`terraform-validate.yml`, `infrastructure-tests.yml`). No new Azure resources, no new
secrets/variables, no application code changes.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle I (Meaningful, Automated Testing)**: N/A change to test content — this
  feature re-sequences when the existing `terraform fmt`/`validate` and
  `infrastructure/tests/` pytest suite run relative to apply; it adds no new
  functionality requiring new tests. Verification is via the real-run scenarios in
  `quickstart.md`. **Pass.**
- **Principle II (Secure-by-Default Access)**: Unaffected — no user-facing page or API
  endpoint is touched. **Pass / N/A.**
- **Principle III (Defined Technology Stack)**: Unaffected — no language/framework/hosting
  change; still Python backend / GitHub Actions CI, unchanged. **Pass.**
- **Principle IV (Simplicity Over Premature Scale)**: Directly drives the chosen design —
  native `needs:`/`if:` job chaining inside one workflow run, rejecting cross-workflow
  polling/API correlation as unnecessary complexity (see research.md). **Pass.**
- **Principle V (Continuous Integration Gate)**: Unaffected for PR merges —
  `terraform-validate.yml` keeps its `pull_request` trigger and PR merges are still
  blocked on it exactly as today; this feature only touches the separate push-to-main
  apply path. **Pass.**
- **Principle VI (Observability & AI Cost Transparency)**: N/A — no LLM interaction
  involved in this feature. **N/A.**
- **Principle VII (Zero-Trust Azure Resource Communication)**: Unaffected — Azure Login
  steps keep using the existing OIDC Managed Identity federated credentials; no shared
  keys/secrets introduced, no network topology changed. **Pass.**
- **Principle VIII (UI Design System & Accessibility) / XI (UI Design Pre-Agreement)**:
  N/A — this feature has no user-facing UI; there is no screen to design or agree.
  **N/A.**
- **Principle IX (User-Verified Acceptance Before Completion)**: Applies — `tasks.md`
  (next phase) MUST end with an explicit final acceptance task where the requesting user
  or product owner observes a real pipeline run (per `quickstart.md`'s Scenarios 1, 3,
  and 4) against the actual GitHub repository, not merely a passing automated check.
  **Carried forward as a required task in Phase 2.**
- **Principle X (PII Protection by Design)**: N/A — no PII is involved in workflow
  configuration. **N/A.**

No violations requiring justification — Complexity Tracking table below is empty.

## Project Structure

### Documentation (this feature)

```text
specs/020-terraform-apply-gating/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/
│   └── terraform-apply-pipeline-contract.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
.github/workflows/
├── terraform-apply.yml         # MODIFIED: becomes the 3-job (validate → test → apply)
│                                  gated pipeline; trigger stays push-to-main + workflow_dispatch
├── terraform-validate.yml      # MODIFIED: drop the now-redundant push-to-main trigger;
│                                  keep pull_request trigger for PR-time feedback
├── infrastructure-tests.yml    # MODIFIED: drop the now-redundant push-to-main trigger;
│                                  keep schedule (nightly) + workflow_dispatch for ops use
├── backend-deploy.yml          # UNCHANGED — out of scope (src/** paths, not terraform)
└── frontend-deploy.yml         # UNCHANGED — out of scope (src/** paths, not terraform)

infrastructure/
├── terraform/                  # UNCHANGED — no .tf configuration changes
└── tests/                      # UNCHANGED — existing validate script and pytest suite
                                   reused as-is inside the new `validate`/`test` jobs
```

**Structure Decision**: No new directories or projects. This is a targeted edit to three
existing GitHub Actions workflow files under `.github/workflows/`; no application source,
Terraform configuration, or test content changes.

## Complexity Tracking

*No violations — table intentionally empty.*
