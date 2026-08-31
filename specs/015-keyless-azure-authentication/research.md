# Phase 0 Research: Keyless Azure Authentication

There are no unresolved `NEEDS CLARIFICATION` markers in this spec's Technical Context —
every decision was already made and implemented while this feature's two user stories were
still part of `007-azure-infrastructure-provisioning`, before the 2026-08-29 split. This
document records those decisions as inherited context (not re-derived) and confirms each is
still current on this branch.

## R1. GitHub OIDC identity type: dedicated user-assigned Managed Identity, not an App Registration

- **Decision**: The federated credential trusting GitHub Actions is configured on a
  standalone Azure user-assigned Managed Identity (`llmdungeon-github-oidc-identity-prod`),
  not a Microsoft Entra App Registration/service principal.
- **Rationale**: Managed Identities have no client secret to leak or rotate at all — a
  federated credential on a service principal still leaves a secret-shaped attack surface
  (the App Registration itself can have secrets added to it later). A Managed Identity
  scoped to nothing but the federated trust and an RG-level role assignment is the narrowest
  possible blast radius. This matches spec.md's Assumptions section (confirmed) and FR-003a.
- **Alternatives considered**: App Registration + federated credential (rejected — retains
  the service-principal secret-management surface this spec exists to eliminate); a single
  shared Managed Identity for both GitHub OIDC and Function App runtime (rejected — the two
  need different role assignments: deployment/Terraform-apply vs. data-plane access to
  Storage/Cosmos/Foundry, and merging them would violate least-privilege).
- **Where implemented**: `infrastructure/scripts/bootstrap.sh` — created outside Terraform
  since Terraform itself authenticates as this identity (a resource can't provision its own
  prerequisite).

## R2. GitHub's four OIDC subject-claim shapes

- **Decision**: Four separate federated credentials are registered on the same Managed
  Identity, covering GitHub's different subject-claim shapes (e.g. branch push vs.
  `environment:` deployment jobs vs. pull-request events), not just one.
- **Rationale**: A federated credential's subject claim must match exactly; GitHub emits a
  different subject string depending on how a workflow run is triggered. Registering only
  one shape would make the other trigger types fail authentication unexpectedly.
- **Where implemented**: `infrastructure/scripts/bootstrap.sh` (`az identity
  federated-credential create`, four times).

## R3. Private connectivity: Private Endpoints + `public_network_access_enabled = false`

- **Decision**: Storage, Cosmos DB, and the AI Foundry/Cognitive Services account each get a
  dedicated `azurerm_private_endpoint` into a private-endpoints subnet, plus
  `public_network_access_enabled = false` on the resource itself (both are required — a
  private endpoint alone does not close the public data-plane path).
- **Rationale**: Matches constitution Principle VII directly (Managed Identity +
  Private Endpoint wherever available, public access disabled). Disabling public access is
  what makes `test_private_connectivity.py`'s "public access denied" assertions meaningful,
  rather than merely preferring the private path.
- **Alternatives considered**: Service Endpoints (rejected — coarser-grained, and doesn't
  fully remove the public data-plane listener); leaving public access enabled with
  IP/VNet firewall rules only (rejected — still exposes a public endpoint as an attack
  surface, contrary to Principle VII's "disabled wherever a private path is available").
- **Where implemented**: `infrastructure/terraform/network.tf` (endpoints, subnet),
  `infrastructure/terraform/main.tf` (the `public_network_access_enabled` flags).

## R4. The one documented exception: Static Web App → Function App over public HTTPS

- **Decision**: The Function App keeps `public_network_access_enabled = true` (ingress),
  since the frontend Static Web App calls it over the public internet.
- **Rationale**: The Function App independently requires Entra ID-authenticated requests on
  every call (`002-login-and-access-control`), so this path is protected by identity rather
  than network isolation — an explicit, narrow, documented deviation from the private-only
  default (FR-004), not an oversight.
- **Where implemented**: `infrastructure/terraform/main.tf` line 218 (commented inline as
  the FR-014/FR-004 documented exception).

## R5. Test vantage point for private-connectivity verification

- **Decision**: `test_private_connectivity.py` runs from GitHub-hosted runners (outside the
  VNet) and asserts (a) the private endpoint connections are `Approved`, and (b) direct
  public-hostname calls to Storage/Cosmos/AI Foundry are rejected (connection
  refused/timeout, or 401/403).
- **Rationale**: This is the strongest claim provable from a vantage point outside the VNet
  without deploying a test harness inside it. It cannot prove that an in-VNet caller's DNS
  resolves to the private IP (Azure Private DNS only overrides resolution for clients using
  Azure-provided DNS within the linked VNet) — that remains a documented manual step.
- **Where implemented**: `infrastructure/tests/test_private_connectivity.py` (docstring),
  cross-referenced to `quickstart.md` Scenario 4 for the manual DNS-resolution check.

## R6. CI cadence for these tests: nightly/on-demand, not per-PR

- **Decision**: `infrastructure-tests.yml` runs on a nightly schedule and
  `workflow_dispatch`, not on every pull request.
- **Rationale**: These tests need a live federated-OIDC context (`id-token: write`) and
  already-deployed infrastructure; a PR-triggered run from a fork or an unmerged branch has
  neither. Running against the live `production` environment on every PR would also risk
  false failures from unrelated in-flight infra changes.
- **Alternatives considered**: Running against a per-PR ephemeral environment (rejected as
  out of scope — no ephemeral-environment mechanism exists in this project, and Principle IV
  (YAGNI) counsels against building one without a stated need).

## Open items

None. All decisions above are already implemented, deployed, and covered by
`infrastructure/tests/`; Phase 1 documents the resulting design rather than proposing a new
one.
