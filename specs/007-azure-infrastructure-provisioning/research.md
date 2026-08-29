# Research: Azure Infrastructure Provisioning

**Date**: 2026-08-28 | **Status**: Research Phase Complete

## 1. Terraform & Azure Provider Versioning

**Unknown**: Minimum Terraform version, Azure Provider constraints

**Decision**: 
- **Terraform**: >= 1.5.0 (LTS release line, stable, modern language features)
- **Azure Provider**: >= 3.80.0 (supports all required resources: Functions, Storage, Cosmos DB, Static Web App, AI Foundry, Private Endpoints, Managed Identity)
- **State Lock**: Native to Azure Storage backend (no additional locking mechanism needed)

**Rationale**:
- Terraform 1.5+ is the current stable LTS line with broad Azure Provider compatibility
- Azure Provider 3.80+ includes full support for Private Endpoints, Managed Identity role assignments, and Azure AI Foundry provisioning (required for FR-015)
- Azure Storage backend provides native state locking via blob leases (prevents concurrent applies)

**Alternatives Considered**:
- Terraform 1.4: Supports all needed resources but lacks some modern UX features; 1.5+ is more current
- Azure Provider pinning to exact version (e.g., 3.85.0): Pinning to minor version (>= 3.80.0) allows security patches while ensuring stability

**Validation**: Use terraform version constraints in required_version and required_providers blocks in Terraform configuration.

---

## 2. Infrastructure Testing & Validation Framework

**Unknown**: Testing tools/framework for infrastructure correctness, connectivity, OIDC, private endpoints

**Decision**: 
- **Terraform Validation**: `terraform validate` + `terraform fmt` (built-in, no dependencies)
- **Terraform Plan Review**: PR workflows export `terraform plan` as artifact for human review
- **Custom Python Tests**: Use pytest (already in project per `001-ci-cd-foundation`)
  - `tests/infrastructure/test_private_connectivity.py`: Verify private endpoints exist, public access disabled
  - `tests/infrastructure/test_oidc_authentication.py`: Verify federated OIDC trust is configured, authenticate via OIDC
  - `tests/infrastructure/test_resource_creation.py`: Verify all required resources exist post-apply

**Rationale**:
- Terraform's built-in validation catches syntax/schema errors early
- Plan review as artifact keeps infrastructure changes auditable in PR workflow
- Python pytest tests leverage existing project infrastructure (001-ci-cd-foundation uses pytest)
- Custom tests verify behavioral correctness (connectivity, auth) beyond syntax validation
- Avoids additional dependencies (terratest, Azure policy) that would need separate CI/CD setup

**Alternatives Considered**:
- Terratest (Go-based): Powerful for integration testing but requires Go toolchain; adds maintenance burden
- Azure Policy: Governance tool for compliance but overkill for PR-gated validation; better for runtime audit
- Ansible: Playbook-based testing but adds complexity for what Python+pytest can do

**Validation**: Test suite runs in GitHub Actions on PR and main branch, blocking merge on failure per Principle V.

---

## 3. Expected Scale & Throughput

**Unknown**: User count, requests/sec, Cosmos DB transactions, concurrent Functions

**Decision**: 
- **User Base**: Private application, ~5-10 named Microsoft accounts (confirmed from Principle II requirements)
- **Request Volume**: Startup-phase scale (~100-1000 requests/day initially); auto-scaling to handle growth without manual tuning
- **Cosmos DB**: Serverless mode (auto-scale RUs), initial targeting ~1000 RU/s max (auto-scaling up to 40,000 RU/s if needed), `Session` consistency, `Periodic` backup policy (confirmed)
- **Functions**: **Flex Consumption plan** (confirmed) — pay-per-execution with native VNet integration support, avoiding the cold-start-into-VNet limitations of the classic Consumption plan while still auto-scaling without reserved capacity
- **Storage**: Standard LRS (locally redundant, confirmed) for the application assets account; can scale to GRS later if needed

**Rationale**:
- Small, private user base (~5-10 accounts) matches spec's secure-by-default, allow-list requirement (Principle II)
- Serverless Cosmos DB and Flex Consumption Functions auto-scaling aligns with Principle IV (simplicity, no over-provisioning)
- Flex Consumption specifically resolves the tension between "no reserved capacity" (cost) and "must reach private endpoints via VNet integration" (FR-007/FR-008) that the classic Consumption plan handles less reliably
- Storage LRS is cost-efficient for startup phase; geo-redundancy can be added later if durability becomes a concern
- Configuration allows growth without architectural redesign (Flex Consumption scales automatically)

**Alternatives Considered**:
- Classic Consumption plan: Supports regional VNet integration in most regions, but has known cold-start/reliability edge cases when the app must resolve private DNS on every scale-out; Flex Consumption addresses this while keeping pay-per-execution pricing
- Reserved capacity (Functions Premium/Elastic Premium): Higher baseline cost, not justified for current user base; Flex Consumption auto-scales adequately with VNet integration built in
- Cosmos DB provisioned throughput: Requires manual tuning; serverless auto-scaling is simpler and more cost-effective for variable load
- Cosmos DB Continuous backup: Point-in-time restore to any second, but higher cost than Periodic; not justified for this project's data-loss tolerance
- Premium Storage (SSD-backed): Not needed for startup; standard tier acceptable for story configuration and asset storage

**Validation**: Performance load tests conducted post-deployment to validate assumptions. Auto-scaling alerts configured to monitor actual vs. expected usage.

---

## 4. Terraform State Backend Bootstrap

**Unknown**: Bootstrap procedure for Terraform remote state storage (chicken-and-egg problem)

**Decision**: 
- **Two-Phase Approach**:
  1. **Phase 1 (One-Time Manual)**: Create Azure Storage account for Terraform state manually or via minimal script (using Azure CLI)
  2. **Phase 2 (Automated)**: Terraform configuration uses that backend storage; all subsequent infrastructure managed via Terraform

- **Bootstrap Script**: Minimal Azure CLI commands to create (all within the pre-existing `llm-dungeon` Resource Group — see §8):
  - Storage account (dedicated for Terraform state, separate from application storage)
  - Container within the storage account (terraform-state)
  - Storage account key retrieval (for backend configuration)

- **Backend Configuration File** (`backend.tf`):
  - Parameterized for environment (e.g., `backend-prod.hcl`)
  - Passed to `terraform init -backend-config=backend-prod.hcl`
  - No hardcoded credentials; Terraform CLI authenticates using the GitHub OIDC Managed Identity context (see §7)

**Rationale**:
- Avoids circular dependency: state storage must exist before Terraform can use it as a backend
- Manual bootstrap is a one-time operation; subsequent deployments are fully automated
- Minimal bootstrap (only storage account + container) keeps operations simple
- Backend configuration file externalizes storage account details from main Terraform code

**Alternatives Considered**:
- Local state initially, then migrate: Feasible but adds complexity; bootstrap approach is cleaner
- Terraform Cloud/Enterprise backend: Shifts state management out of Azure; adds external dependency and cost
- Environment variables for backend config: Works but harder to version control; HCL file is more maintainable

**Validation**: Bootstrap script tested independently, documented in quickstart.md with step-by-step instructions and expected outputs.

---

## 5. Azure AI Foundry Resource & Model Deployment

**Unknown**: AI Foundry provisioning via Terraform, available models, deployment configuration, private endpoint support

**Decision**:
- **Terraform Support**: Azure Provider >= 3.80.0 supports `azurerm_ai_services` and `azurerm_cognitive_account` resources
  - Use `azurerm_ai_services` for modern AI Foundry resource (vs. legacy Cognitive Services)
  - Resource type: `azurerm_ai_services` with kind = "OpenAI" or provider-specific model

- **Model Deployment**:
  - Provision Azure OpenAI Service (subset of AI Foundry offering)
  - Deploy `gpt-4o-mini` (confirmed) via Terraform `azurerm_cognitive_deployment` resource — strong quality-per-cost tradeoff for narrative generation at this project's scale; can add/change models later without architectural change
  - Initial deployment: Single region (Production region), single model

- **Private Endpoint**:
  - Configure private endpoint for AI Foundry service
  - Private DNS zone for `openai.azure.com` → private IP resolution
  - Functions authenticate to private endpoint via Managed Identity (bearer token)

- **Capacity & Scaling**:
  - Provisioned throughput: 1,000 TPM (1K TPM) initially (confirmed) — the smallest usable Azure OpenAI capacity unit; sufficient for the ~5-10 user scale assumed in this spec, can scale up later without redesign
  - No token-level rate limiting configured initially; rely on Azure defaults

**Rationale**:
- Azure OpenAI is the modern, recommended AI service (vs. legacy Cognitive Services)
- Terraform support exists for all required resources (services, model deployments, private endpoints)
- Managed Identity authentication (via bearer tokens) aligns with Principle VII (zero-trust)
- Serverless scaling (auto-scaling based on demand) matches Principle IV
- Single model covers core LLM needs; additional models can be added later without architectural change

**Alternatives Considered**:
- Azure Cognitive Services (legacy): Deprecated in favor of AI Foundry; not recommended for new projects
- Third-party LLM (OpenAI, Anthropic): Would violate Principle III (defined stack: exclusive Azure hosting) and require separate API key management (violates Principle VII)
- Multiple models per region: Not necessary for initial deployment; can be added if performance/cost optimization needed later

**Validation**: Terraform plan includes AI Foundry resource and model deployment; connectivity test verifies private endpoint reaches service.

---

## 6. Private Endpoints & DNS Configuration

**Unknown**: DNS strategy for private endpoints (Azure Private DNS Zones vs. host-file approaches); and, until confirmed, the Virtual Network itself that Functions integrate into and DNS zones link to

**Decision**:
- **Virtual Network** (confirmed, see also research.md §8-adjacent Resource Group decision): Terraform creates a new VNet `10.0.0.0/16` inside the `llm-dungeon` Resource Group, with two subnets — a Functions-integration subnet (`10.0.1.0/24`, delegated for Flex Consumption VNet integration) and a private-endpoints subnet (`10.0.2.0/24`)
- **Private DNS Zones**: Use Azure Private DNS Zone resources (provisioned by Terraform)
  - Create Private DNS Zones for each service needing private endpoints:
    - `privatelink.blob.core.windows.net` (Storage)
    - `privatelink.documents.azure.com` (Cosmos DB)
    - `privatelink.openai.azure.com` (AI Foundry/Azure OpenAI)
  - Link each Private DNS Zone to the VNet above (via `azurerm_private_dns_zone_virtual_network_link`)
  - Each private endpoint creates A records pointing to the private IP

- **DNS Resolution Flow**:
  1. Functions backend resolves `storageaccount.blob.core.windows.net` (standard Azure DNS name)
  2. Azure Private DNS intercepts query → returns private IP
  3. Connection to private endpoint → no public internet traversal

- **Public Access Disabled**:
  - Storage: Set `default_action = "Deny"` in network rules, white-list Functions' private endpoint
  - Cosmos DB: Set `public_network_access_enabled = false`, use private endpoint only
  - AI Foundry: Set `public_network_access_enabled = false`, use private endpoint only

**Rationale**:
- Azure Private DNS Zones are the Azure-native solution (no manual host file management)
- Provisioned by Terraform → fully version-controlled, auditable, reproducible
- Aligns with Principle VII (zero-trust): backend resources only reachable over private network
- Standard Azure naming conventions work transparently; no application code changes needed

**Alternatives Considered**:
- Manual host file (`/etc/hosts`) configuration: Not scalable, not version-controlled, error-prone; not suitable for production
- Azure Firewall DNS proxy: Over-complicated for current scope; Private DNS Zones are sufficient
- Custom DNS server (BIND): Unnecessary operational overhead; Azure Private DNS is managed and built-in

**Validation**: 
- Terraform plan includes Private DNS Zone resources and virtual network links
- Connectivity test resolves DNS names to private IPs, verifies public access is blocked
- Network trace confirms traffic uses private IP addresses, not public endpoints

---

## 7. GitHub OIDC Identity Type: Managed Identity vs. App Registration

**Unknown**: Whether the GitHub Actions federated OIDC credential should be configured on a traditional Microsoft Entra App Registration (service principal) or on an Azure user-assigned Managed Identity.

**Decision**:
- Use a dedicated Azure user-assigned **Managed Identity** as the subject of the GitHub OIDC federated credential (`az identity create` + `az identity federated-credential create`), not an App Registration (`az ad app federated-credential create`).
- This identity is created during the same bootstrap step as the Terraform backend storage account (see §4), since Terraform itself authenticates as this identity to run `plan`/`apply` — the identity must exist before Terraform can use it.
- The identity is granted only the role assignments deployment and Terraform-apply workflows require (e.g., `Contributor` scoped to the project's resource group), not a broad subscription-level role.
- It is kept distinct from the Azure Functions app's own (system-assigned) Managed Identity used for Storage/Cosmos DB/AI Foundry access (FR-008) — the two identities serve different purposes (control-plane deployment vs. data-plane resource access) and should not share role assignments.

**Rationale**:
- Managed Identities are Azure-native, requiring no separate Entra App Registration lifecycle to manage (no client secrets to rotate, no app manifest to maintain), consistent with the project's existing Managed Identity usage for Functions (Principle VII: zero stored credentials).
- Keeps the entire project's Azure authentication model uniform: every non-human identity (Functions runtime, GitHub Actions) is a Managed Identity with a federated or system-assigned trust, rather than mixing Managed Identities and App Registrations.
- Narrower blast radius: a compromised or misconfigured GitHub OIDC identity is scoped to deployment permissions on one resource group, not the broader surface an App Registration's service principal can accumulate over time.

**Alternatives Considered**:
- Microsoft Entra App Registration with federated credential: The traditional/most-documented approach, but introduces a second identity type to manage (App Registration vs. Managed Identity) and a separate Entra lifecycle outside Azure resource management.
- Reusing the Functions app's Managed Identity for GitHub Actions: Rejected — conflates data-plane resource access with control-plane deployment/Terraform-apply permissions, violating least-privilege separation.

**Validation**: Bootstrap script creates the Managed Identity and federated credential before first Terraform run; `az identity federated-credential create` (not `az ad app federated-credential create`) is used; GitHub Actions workflow authenticates successfully via `azure/login@v1` using the identity's client ID.

---

## 8. Resource Group Strategy: Single Pre-Existing Group vs. Terraform-Managed

**Unknown**: Whether Terraform should create its own Resource Group(s) per environment, or provision into an existing, externally-managed one.

**Decision**:
- All Azure resources for this project — application resources (Functions, Storage, Cosmos DB, Static Web App, AI Foundry, etc.) and the Terraform backend state storage account alike — are provisioned into a single, pre-existing Resource Group named `llm-dungeon`.
- This Resource Group is created out-of-band (e.g., manually by a subscription owner) before the bootstrap script or any Terraform run. Terraform references it via a `data "azurerm_resource_group"` data source (read-only lookup) rather than an `azurerm_resource_group` managed resource; Terraform never creates, renames, or deletes it.
- Both the bootstrap script and `terraform plan`/`apply` fail fast with a clear error if `llm-dungeon` does not already exist.

**Rationale**:
- Matches the constraint that the Resource Group already exists in the target subscription; treating it as Terraform-managed would make Terraform attempt to "adopt" or recreate a resource it doesn't own, risking accidental deletion on `terraform destroy` of unrelated resources someone else placed there.
- A single group simplifies RBAC: the GitHub OIDC Managed Identity's `Contributor` role assignment (§7) is scoped once, to this one group, rather than per-resource-group-per-environment.
- Consistent with the single-Production-environment scope (FR-013): one environment, one Resource Group. If further environments are added later, this decision would need revisiting (e.g., additional groups or a naming convention within the same group) — noted as a forward-compatibility consideration, not a blocker now.

**Alternatives Considered**:
- Terraform-created Resource Group (`azurerm_resource_group` managed resource): The more common Terraform pattern, but doesn't fit here since the group already exists; would require either an import step or resource conflict on first apply.
- One Resource Group per environment (Terraform-managed): Cleaner isolation for multi-environment setups, but not applicable given the single pre-existing `llm-dungeon` group requirement and the single-environment scope.

**Validation**: `terraform plan` against a subscription where `llm-dungeon` does not exist fails clearly at the data source lookup, before attempting any resource creation; all resource blocks reference `data.azurerm_resource_group.rg.name`/`.location`, none define their own resource group.

---

## 9. Cosmos DB Region: West Europe Capacity Shortage

**Unknown**: None at design time — this was discovered during implementation (`terraform apply` against the live subscription), not during planning.

**Decision**:
- The Cosmos DB account is provisioned in `uksouth`, via a dedicated `cosmos_region` variable, independent of `azure_region` (`westeurope`) which every other resource uses.
- Single region, single write region, no Availability Zone redundancy (`automatic_failover_enabled = false`, `multiple_write_locations_enabled = false`, one `geo_location` block with `zone_redundant = false`) — this project's scale (~5-10 users) needs none of Cosmos DB's multi-region/AZ features, so there's no reason to accept the added complexity of a second region's AZ capacity constraints on top of the first.
- The VNet, both subnets, and every other resource stay in `westeurope`; Cosmos's private endpoint connects cross-region (Azure Private Link supports this natively over the Microsoft backbone — no additional peering or gateway required).

**Rationale**:
- Every `terraform apply` attempt against `westeurope` failed identically: `ServiceUnavailable`/"Sorry, we are currently experiencing high demand in West Europe region for the zonal redundant (Availability Zones) accounts, and cannot fulfill your request at this time." This was confirmed as a genuine regional platform capacity issue — not a Terraform/config problem — via a direct `az cosmosdb create` probe using a different account name and bypassing Terraform entirely, which failed with the identical message.
- `uksouth` was chosen as a nearby region — region selection for this project is based on proximity to the user, not a data-residency/compliance requirement (confirmed: none exists), so any nearby region with available capacity is an acceptable substitute — and validated by provisioning (then deleting) a real test Cosmos account there before committing to the change; it succeeded on the first attempt.
- Moving only Cosmos DB (not the whole stack) to a second region keeps the blast radius of this workaround minimal and avoids re-litigating every other resource's region.

**Alternatives Considered**:
- Wait and retry `westeurope` periodically: tried first (multiple attempts over several minutes, plus a 2-minute backoff) — Azure's capacity message didn't clear; no way to predict when/if it would.
- Move the entire stack to a different region: unnecessary — only Cosmos DB was capacity-constrained; every other resource provisioned successfully in `westeurope` on the first attempt.
- Request a region access/quota increase (the `aka.ms/cosmosdbquota` link Azure's error message provides): a real option for the future if `uksouth` also becomes constrained, but not pursued here since a working nearby region was available immediately.

**Validation**: `az cosmosdb create` succeeded in `uksouth` (probed, then deleted, before the real Terraform-managed account was created); `terraform apply` subsequently created the real Cosmos DB account, database, container, and its Cosmos-native RBAC role assignment without error.

---

## Summary of Resolutions

| Unknown | Decision | Impact |
|---------|----------|--------|
| Terraform Versioning | >= 1.5.0, Azure Provider >= 3.80.0 | Ensures all required resources available, native state locking |
| Testing Framework | pytest + terraform validate | Leverages existing project setup, no new dependencies |
| Scale Assumptions | ~5-10 users, serverless Cosmos/Functions | Aligns with Principle IV, no over-provisioning |
| State Bootstrap | One-time Azure CLI bootstrap, then Terraform | Breaks circular dependency cleanly |
| AI Foundry | Azure OpenAI via Terraform, private endpoints | Modern, supported, aligned with stack constraints |
| Private DNS | Private DNS Zones (Terraform-provisioned) | Fully version-controlled, Azure-native, secure |
| GitHub OIDC Identity | Dedicated user-assigned Managed Identity, not App Registration | Uniform Managed-Identity-only auth model, narrower blast radius, no App Registration lifecycle |
| Resource Group Strategy | Single pre-existing `llm-dungeon` group, referenced via data source | Matches externally-managed group constraint, simplifies RBAC scope, avoids accidental adoption/deletion |
| Cosmos DB Region | `uksouth` (not `westeurope`), single-region/no-AZ | Works around a real West Europe Cosmos DB capacity shortage discovered during implementation; every other resource stays in `westeurope` |

All NEEDS CLARIFICATION items from Technical Context resolved. Proceed to Phase 1 design (data-model.md, contracts/, quickstart.md).
