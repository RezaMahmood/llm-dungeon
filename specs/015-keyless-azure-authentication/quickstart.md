# Quickstart: Verifying Keyless Azure Authentication

This feature is already implemented (see plan.md Summary). This guide re-validates it
against spec.md's Independent Tests and Acceptance Scenarios, rather than standing up
something new. Run this after any change touching `infrastructure/terraform/identity.tf`,
`infrastructure/terraform/network.tf`, `infrastructure/scripts/bootstrap.sh`, or the GitHub
Actions workflows, and as this spec's Principle IX user-verified acceptance pass.

## Prerequisites

- Azure CLI (`az`) logged in with read access to the project's Resource Group.
- `infrastructure/terraform/` initialized against the `production` backend:
  `terraform init -backend-config=backend-prod.hcl -input=false`.
- Python 3.11 with `pip install -r infrastructure/tests/requirements.txt`.
- `gh` CLI (or repo web UI access) to inspect GitHub Actions secrets/variables.

## Scenario 1 — No stored Azure secret in GitHub (spec.md US1, Independent Test)

```bash
gh secret list --repo <org>/<repo>
gh variable list --repo <org>/<repo>
```

**Expected**: No `AZURE_CLIENT_SECRET` or equivalent secret is present. `AZURE_CLIENT_ID`,
`AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID` may appear as plain **variables** (not secrets) —
a client ID is not sensitive on its own without a corresponding secret/certificate.

## Scenario 2 — GitHub OIDC Managed Identity is correctly configured (spec.md US1, AS1/AS3)

```bash
az identity show --name llmdungeon-github-oidc-identity-prod --resource-group <rg>
az identity federated-credential list --identity-name llmdungeon-github-oidc-identity-prod --resource-group <rg>
az role assignment list --assignee <github-oidc-identity-client-id> --resource-group <rg> -o table
```

**Expected**: The identity exists and is a Managed Identity (not an App Registration —
`az ad app show` for the same name should find nothing). Four federated credentials are
listed (research.md R2). Role assignments are scoped to the Resource Group only — no
subscription-level or Owner/Contributor-at-subscription entries.

## Scenario 3 — A real deployment authenticates via OIDC alone (spec.md US1, AS1)

```bash
gh workflow run terraform-apply.yml --repo <org>/<repo>
gh run watch --repo <org>/<repo>
```

**Expected**: The "Azure Login (OIDC)" step succeeds with no secret input; the run
completes without any credential-related failure.

## Scenario 4 — Backend reaches Storage/Cosmos/AI Foundry privately, with Managed Identity (spec.md US2, AS1-3)

Automated (run from anywhere, verifies the public-path-is-closed half):

```bash
pip install -r infrastructure/tests/requirements.txt
pytest infrastructure/tests/test_private_connectivity.py -v
```

Manual, in-VNet DNS check (cannot be proven from outside the VNet — research.md R5):

1. Deploy a throwaway VM or use Azure Cloud Shell attached to the same VNet as the private
   endpoints subnet.
2. `nslookup <storage-account>.blob.core.windows.net` — expect a private (10.x/172.x)
   IP, not a public Azure Storage IP.
3. Repeat for the Cosmos DB and AI Foundry hostnames (from `terraform output`).

**Expected**: All three hostnames resolve to private IPs from inside the VNet.

## Scenario 5 — Public access to backend resources is rejected (spec.md US2, AS4)

```bash
pytest infrastructure/tests/test_private_connectivity.py::test_public_data_plane_access_denied -v
```

**Expected**: All three parametrized cases pass — public calls to Storage, Cosmos DB, and AI
Foundry either fail to connect or return 401/403.

## Scenario 6 — No stored keys/connection strings in Function App config (spec.md US2, Independent Test)

```bash
az functionapp config appsettings list --name <func-app-name> --resource-group <rg> \
  --query "[?contains(name, 'CONNECTION') || contains(name, 'KEY')]"
```

**Expected**: Empty result (or only non-Azure-credential settings coincidentally matching
the filter — inspect manually if anything appears).

## Scenario 7 — SWA-to-Function-App documented exception still holds (spec.md FR-004)

```bash
terraform -chdir=infrastructure/terraform output functions_app_name
az functionapp show --name <func-app-name> --resource-group <rg> --query "publicNetworkAccess"
```

**Expected**: `Enabled` — confirming the one deliberate exception is still in place and
still the *only* resource in this Resource Group with public access enabled (cross-check
against Scenario 5's list).

## Full automated suite

```bash
pytest infrastructure/tests/ -v
```

Or trigger the scheduled CI job directly: `gh workflow run infrastructure-tests.yml`.

**Expected**: All tests pass, covering every FR-005 outcome (see
`contracts/automated-check-contract.md` for the full outcome → test mapping).
