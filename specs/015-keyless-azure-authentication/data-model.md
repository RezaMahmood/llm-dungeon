# Phase 1 Data Model: Keyless Azure Authentication

This spec has no application data entities (no database rows, no request/response DTOs).
Its "entities" are Azure identity and networking constructs, as defined in spec.md's Key
Entities section. Each is documented here with its concrete, already-implemented shape.

## Managed Identity (Function App)

- **Type**: System-assigned Managed Identity, attached to
  `azurerm_function_app_flex_consumption.functions`.
- **Fields**: `principal_id` (used as the target of role assignments), implicit
  `client_id`/`tenant_id` (not referenced directly — `DefaultAzureCredential` in the
  Function App resolves these automatically from the platform).
- **Relationships / role assignments** (`infrastructure/terraform/identity.tf`):
  - `Storage Blob Data Contributor` on `azurerm_storage_account.app_storage` (FR-002).
  - Cosmos DB built-in Data Contributor via `azurerm_cosmosdb_sql_role_assignment` (Cosmos
    RBAC is a separate system from Azure RBAC — a plain `azurerm_role_assignment` only
    grants control-plane access) (FR-002).
  - `Cognitive Services User` on `azurerm_cognitive_account.openai` (FR-002).
  - `Monitoring Metrics Publisher` on Application Insights (adjacent to this spec's scope,
    supports Principle VI observability, not itself an FR-001–005 requirement).
  - Microsoft Graph application role assignments (`User.Invite.All`, `User.ReadWrite.All`)
    — belong to `002-login-and-access-control`'s guest-user lifecycle, not this spec; listed
    here only because they share the same identity resource.
- **Validation rule**: No corresponding access key, connection string, or API key may exist
  in Function App configuration for Storage/Cosmos/AI Foundry (FR-002) — enforced by
  `test_private_connectivity.py`'s absence of any such setting in
  `infrastructure/terraform/main.tf`'s `app_settings` block, and by code review convention.

## GitHub OIDC Managed Identity

- **Type**: User-assigned Managed Identity (`llmdungeon-github-oidc-identity-prod`),
  created by `infrastructure/scripts/bootstrap.sh`, *outside* Terraform (Terraform
  authenticates as this identity, so it cannot provision its own prerequisite).
- **Fields**: `client_id`, `tenant_id` (published as GitHub Actions repository/environment
  variables `AZURE_CLIENT_ID` / `AZURE_TENANT_ID`, consumed by `azure/login@v2`); four
  `federated_credential` sub-resources, one per GitHub OIDC subject-claim shape (branch,
  environment, pull-request, and a fourth per research.md R2).
- **Relationships**: Distinct from the Function App's Managed Identity (different Managed
  Identity resource entirely) — role assignment: `Contributor`, scoped to the Resource
  Group only (not subscription-level), granted via `az role assignment create` in
  `bootstrap.sh` (FR-003a).
- **Validation rule**: No client secret, certificate, or access key may exist for this
  identity or be stored in GitHub (FR-003) — enforced by
  `test_oidc_authentication.py::test_no_stored_azure_credentials_in_environment`.
- **State/failure behavior**: An unrecognized/misconfigured federated credential MUST fail
  authentication explicitly (`ClientAuthenticationError`), never fall back to a stored
  secret or proceed unauthenticated — enforced by
  `test_oidc_authentication.py::test_misconfigured_federated_credential_fails_clearly`.

## Private Endpoint

- **Type**: `azurerm_private_endpoint`, one each for Storage, Cosmos DB, and the AI
  Foundry/Cognitive Services account, all attached to the `private_endpoints` subnet
  (`infrastructure/terraform/network.tf`).
- **Fields**: `private_link_service_connection` (state, expected `Approved`), target
  resource ID, subresource (`blob`, `Sql`, `account` per resource type).
- **Relationships**: Each pairs one Private Endpoint to exactly one backend resource; all
  three sit in the same Function-App-reachable subnet.
- **Validation rules**:
  - Connection state MUST be `Approved` (FR-001) — enforced by
    `test_private_connectivity.py::test_private_endpoint_connection_approved`.
  - The paired resource MUST have `public_network_access_enabled = false` (FR-001), except
    the Function App itself (FR-004's documented exception) — enforced by
    `test_private_connectivity.py::test_public_data_plane_access_denied`.

## State Transitions

None of these entities have an application-level lifecycle/state machine — they are
static infrastructure configuration, reconciled by `terraform apply` (identity/network
resources) and by one-time `bootstrap.sh` execution (GitHub OIDC identity). The only
"transition" of note is the pass/fail outcome of the FR-005 automated checks, which is a
test result, not an entity state.
