# Contract: `.github/workflows/terraform-apply.yml` (consolidated pipeline)

**Date**: 2026-08-30 | **Status**: Phase 1

This supersedes, for the push-to-main apply path only, the stale multi-workflow
description of `terraform-apply.yml` in
`specs/007-azure-infrastructure-provisioning/contracts/github-actions-contract.md`.
`terraform-validate.yml` (PR-only after this change) and `infrastructure-tests.yml`
(nightly/manual-only after this change) keep their own separate, unchanged contracts for
those remaining purposes.

## Triggers

- `push` to `main`, path-filtered to `infrastructure/terraform/**` and this workflow
  file itself — the normal path that must be gated.
- `workflow_dispatch` — manual re-run; runs the full `validate → test → apply` chain
  below, not `apply` in isolation (FR-009: this is what prevents a manual re-trigger
  from bypassing the gate).

No `pull_request` or `schedule` trigger — those remain the concern of
`terraform-validate.yml` and `infrastructure-tests.yml` respectively.

## Jobs

### `validate`

- Same steps as today's `terraform-validate.yml` push path: `terraform fmt`/`validate`
  via `infrastructure/tests/test_terraform_validate.sh`, Azure Login (OIDC), `terraform
  init -backend-config=backend-prod.hcl`, `terraform plan`.
- No `needs:` — always runs first for this workflow's triggers.

### `test`

- `needs: validate`
- `if: needs.validate.result == 'success'`
- Same steps as today's `infrastructure-tests.yml`: setup Python, setup Terraform, Azure
  Login (OIDC), `terraform init` (read-only), `pytest infrastructure/tests/ -v`.
- `environment: production` (unchanged — no required reviewer; matches the existing
  `production` environment's automatic-deploy posture).

### `apply`

- `needs: test`
- `if: needs.test.result == 'success'`
- `environment: production-infra` (unchanged — required-reviewer protection rule is the
  Apply Approval gate; see data-model.md).
- Same steps as today's `terraform-apply.yml`: Azure Login (OIDC), `terraform init`,
  `terraform apply -auto-approve -var-file=terraform.tfvars`, capture/upload outputs.

## Observable states (FR-008 / SC-003)

| Scenario | `validate` | `test` | `apply` |
|---|---|---|---|
| `terraform validate`/fmt fails | `failure` | `skipped` | `skipped` |
| validate passes, infra tests fail | `success` | `failure` | `skipped` |
| both pass, awaiting reviewer | `success` | `success` | `waiting` (environment review requested) |
| both pass, reviewer approves | `success` | `success` | `success` |
| both pass, reviewer rejects | `success` | `success` | `failure`/`cancelled` (no `terraform apply` executed) |

A `skipped` `apply` job (gate not passed) is visibly distinct in the Actions UI from a
`waiting` `apply` job (gate passed, pending human approval) — this distinction is the
mechanism satisfying FR-008, with no additional status reporting to build.

## Unaffected workflows

- `terraform-validate.yml`: keep only its `pull_request` trigger; drop
  `push: branches: [main]` (now redundant — see research.md).
- `infrastructure-tests.yml`: keep its `schedule` (nightly) and standalone
  `workflow_dispatch` triggers; drop `push: branches: [main]` (now redundant).
- `backend-deploy.yml` / `frontend-deploy.yml`: untouched; they trigger off
  `src/**` paths, not `infrastructure/terraform/**`, and are out of this feature's scope.
