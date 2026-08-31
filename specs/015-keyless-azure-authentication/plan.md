# Implementation Plan: Keyless Azure Authentication

**Branch**: `015-keyless-azure-authentication` | **Date**: 2026-08-31 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/015-keyless-azure-authentication/spec.md`

## Summary

This spec was split out of `007-azure-infrastructure-provisioning` on 2026-08-29 (see
spec.md's Split note) to isolate the "no stored Azure credentials, ever" requirement —
GitHub-to-Azure via federated OIDC (FR-003/FR-003a) and Function-App-to-backend-resources
via Managed Identity over Private Link (FR-001/FR-002/FR-004) — from resource provisioning
mechanics. **The split moved a spec boundary, not code**: every requirement in this spec's
FR-001 through FR-005 was already implemented and tested as part of 007's build, before the
split occurred. This plan therefore documents the existing implementation and its test
coverage rather than designing new work; no new source changes are anticipated from this
plan.

Verified implementation locations:

- **FR-001 (Private Link, public access disabled)**: `infrastructure/terraform/network.tf`
  (`azurerm_private_endpoint.storage/cosmos/openai`) and `infrastructure/terraform/main.tf`
  (`public_network_access_enabled = false` on Storage, Cosmos DB, and the AI Foundry/Cognitive
  Services account; `= true` only on the Function App per the documented FR-004 exception).
- **FR-002 (Function App Managed Identity, no keys/connection strings)**:
  `infrastructure/terraform/identity.tf` (role assignments for the Function App's
  system-assigned identity onto Storage, Cosmos DB SQL RBAC, and Cognitive Services).
- **FR-003 / FR-003a (GitHub OIDC on a dedicated user-assigned Managed Identity, scoped
  role)**: `infrastructure/scripts/bootstrap.sh` (creates
  `llmdungeon-github-oidc-identity-prod`, four federated credentials for GitHub's OIDC
  subject-claim shapes, and a Resource-Group-scoped role assignment via `az role assignment
  create` — outside Terraform, since Terraform itself authenticates as this identity).
- **FR-004 (SWA-to-Function-App public HTTPS exception)**: `infrastructure/terraform/main.tf`
  line 218 (Function App `public_network_access_enabled = true`, commented as the documented
  exception).
- **FR-005 (automated check per keyless-auth outcome)**:
  `infrastructure/tests/test_oidc_authentication.py` (success path, and the
  misconfigured-credential failure path) and
  `infrastructure/tests/test_private_connectivity.py` (private-endpoint-approved connections,
  and public-network-access-denied for Storage/Cosmos/AI Foundry), run nightly and on-demand
  by `.github/workflows/infrastructure-tests.yml`.

## Technical Context

**Language/Version**: HCL (Terraform ~> 1.x via `infrastructure/terraform/versions.tf`),
Python 3.11 (test suite), Bash (bootstrap script), YAML (GitHub Actions)

**Primary Dependencies**: `azurerm`/`azuread` Terraform providers, `azure-identity` /
`azure-mgmt-network` (Python), `azure/login@v2` GitHub Action

**Storage**: N/A (this spec governs authentication/connectivity to Storage/Cosmos/AI Foundry,
not their data)

**Testing**: pytest (`infrastructure/tests/`), `terraform validate`/`plan` in CI

**Target Platform**: Azure (Resource Group-scoped resources), GitHub Actions runners

**Project Type**: Infrastructure-as-code + CI/CD pipeline (no application UI surface)

**Performance Goals**: N/A — no throughput/latency requirement in this spec

**Constraints**: Zero long-lived Azure credentials anywhere in GitHub or application
configuration (constitution Principle VII); public network access disabled on every backend
Azure resource except the one documented FR-004 exception

**Scale/Scope**: Single Resource Group, single environment (prod) per `007`'s scope; three
private-endpoint-connected resources (Storage, Cosmos DB, AI Foundry) plus one GitHub OIDC
identity

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle VII (Zero-Trust Azure Resource Communication, NON-NEGOTIABLE)**: This spec
  *is* the direct implementation of this principle for the Function App's backend
  dependencies and for GitHub's deployment path. Status: **PASS** — Managed Identity +
  Private Endpoint everywhere a private path exists (FR-001/FR-002), with the one
  documented, justified exception (FR-004) matching the principle's own escape hatch.
- **Principle I (Meaningful, Automated Testing, NON-NEGOTIABLE)**: FR-005 requires a check
  per keyless-auth outcome; `test_oidc_authentication.py` and
  `test_private_connectivity.py` already cover the success path, the failure path (bad
  federated credential), the approved-private-connection path, and the
  denied-public-access path. Status: **PASS**.
- **Principle V (Continuous Integration Gate)**: These tests need a live Azure OIDC context
  (`id-token: write`) and deployed infra, so they run on `infrastructure-tests.yml`'s nightly
  schedule / `workflow_dispatch`, not on every PR (a PR runner has no federated trust
  established yet). This mirrors 007's existing, already-accepted CI structure for
  infra-specific tests. Status: **PASS**, no new deviation introduced by this spec.
- No other principle (II, III, IV, VI, VIII, IX) imposes a gate specific to this spec's
  scope beyond what 007 already satisfied; IX (user-verified acceptance) is addressed by
  this plan's quickstart.md, to be re-run as a verification pass rather than a first-time
  validation.

No violations requiring Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/015-keyless-azure-authentication/
├── plan.md              # This file
├── research.md          # Phase 0 output — confirms prior 007 research still applies
├── data-model.md        # Phase 1 output — the three entities, as already implemented
├── quickstart.md        # Phase 1 output — verification/re-validation guide
├── contracts/           # Phase 1 output — automated-check contract (FR-005)
└── tasks.md             # Phase 2 output (/speckit-tasks) — expected to be verification-only
```

### Source Code (repository root)

```text
infrastructure/
├── terraform/
│   ├── identity.tf       # Function App Managed Identity role assignments (FR-002)
│   ├── network.tf        # Private endpoints + subnet (FR-001)
│   └── main.tf            # public_network_access_enabled flags (FR-001, FR-004)
├── scripts/
│   └── bootstrap.sh       # GitHub OIDC Managed Identity + federated credentials (FR-003/FR-003a)
└── tests/
    ├── test_oidc_authentication.py     # FR-003/FR-005 (success + failure paths)
    └── test_private_connectivity.py    # FR-001/FR-002/FR-005 (approved + denied paths)

.github/workflows/
├── terraform-apply.yml            # Uses GitHub OIDC MI to deploy (FR-003)
├── backend-deploy.yml             # Uses GitHub OIDC MI to deploy (FR-003)
└── infrastructure-tests.yml       # Runs FR-005's automated checks nightly/on-demand
```

**Structure Decision**: No new directories. This spec's requirements live entirely inside
the existing `infrastructure/` IaC tree and `.github/workflows/` CI tree established by
`007-azure-infrastructure-provisioning`; this plan treats that as the target structure and
verifies it against 015's own acceptance criteria rather than proposing an alternative
layout.

## Complexity Tracking

*No violations — table not needed.*
