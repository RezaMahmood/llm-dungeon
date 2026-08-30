#!/usr/bin/env bash
# One-time bootstrap for the Terraform state backend and the GitHub OIDC
# Managed Identity, per contracts/deployment-config-contract.md's Bootstrap
# Procedure and research.md §4/§7.
#
# This script never creates the `llm-dungeon` Resource Group — it must
# already exist. It creates:
#   1. A Storage Account + container for Terraform's own remote state
#      (separate from application storage — spec.md FR-002).
#   2. A dedicated user-assigned Managed Identity carrying the GitHub OIDC
#      federated credential (not an App Registration — FR-011a), with a
#      Contributor role assignment scoped to the Resource Group only.
#   3. Microsoft Graph application permissions on that same Managed
#      Identity (003-account-provisioning, T058) — a Microsoft Entra ID /
#      Graph API grant, not Azure RBAC, so it is not covered by the
#      Contributor role above. Required so `terraform apply` (running as
#      this identity in CI, via identity.tf's azuread provider resources)
#      can itself read the Microsoft Graph service principal and grant the
#      Function App's managed identity the Graph permissions
#      EntraDirectoryService needs. Idempotent — safe to re-run.
#
# Usage: ./infrastructure/scripts/bootstrap.sh
# Requires: az CLI, authenticated (`az login`) with access to the target
# subscription (this environment has access to exactly one subscription,
# so no --subscription override is needed beyond `az account show`).

set -euo pipefail

RESOURCE_GROUP="llm-dungeon"
REGION="westeurope"
STORAGE_ACCOUNT="llmdungeontstateprod"
CONTAINER_NAME="terraform-state"

GITHUB_ORG="RezaMahmood"
GITHUB_REPO="llm-dungeon"
IDENTITY_NAME="llmdungeon-github-oidc-identity-prod"

SUBSCRIPTION_ID=$(az account show --query id -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)

# This GitHub org/repo issues OIDC subject claims in the newer immutable-ID
# format ("repo:OWNER@ownerID/REPO@repoID:...") rather than the classic
# name-only format ("repo:OWNER/REPO:...") — discovered via AADSTS700213
# during implementation. Fetched dynamically (not hardcoded) so this script
# stays correct if the repo is ever renamed or forked.
GITHUB_OWNER_ID=$(gh api "users/$GITHUB_ORG" --jq '.id')
GITHUB_REPO_ID=$(gh api "repos/$GITHUB_ORG/$GITHUB_REPO" --jq '.id')
GITHUB_SUBJECT_PREFIX="repo:${GITHUB_ORG}@${GITHUB_OWNER_ID}/${GITHUB_REPO}@${GITHUB_REPO_ID}"

echo "== Bootstrap target =="
echo "Subscription: $SUBSCRIPTION_ID"
echo "Tenant:       $TENANT_ID"
echo "Resource Group: $RESOURCE_GROUP"
echo

# --- Step 0: Verify the pre-existing Resource Group exists (never created here) ---
if ! az group show --name "$RESOURCE_GROUP" >/dev/null 2>&1; then
  echo "✗ Resource Group '$RESOURCE_GROUP' does not exist. It must be created out-of-band before bootstrap." >&2
  exit 1
fi
echo "✓ Resource Group '$RESOURCE_GROUP' exists"

# --- Step 1: Terraform state Storage Account ---
if az storage account show --name "$STORAGE_ACCOUNT" --resource-group "$RESOURCE_GROUP" >/dev/null 2>&1; then
  echo "✓ Storage account '$STORAGE_ACCOUNT' already exists, skipping creation"
else
  # default-action stays "Allow" (not "Deny"): this account is created before
  # any VNet exists and must be reachable from GitHub-hosted runners and
  # developer machines, none of which have a private network path to it.
  # Access is still gated by Azure AD auth (backend.tf's use_azuread_auth,
  # `--auth-mode login` below) — RBAC-authenticated, not anonymous or key-based.
  az storage account create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$STORAGE_ACCOUNT" \
    --location "$REGION" \
    --sku "Standard_LRS" \
    --access-tier "Hot" \
    --https-only true \
    --min-tls-version "TLS1_2" \
    --allow-blob-public-access false
  echo "✓ Storage account created: $STORAGE_ACCOUNT"
fi

if az storage container show --account-name "$STORAGE_ACCOUNT" --name "$CONTAINER_NAME" --auth-mode login >/dev/null 2>&1; then
  echo "✓ Container '$CONTAINER_NAME' already exists, skipping creation"
else
  az storage container create \
    --account-name "$STORAGE_ACCOUNT" \
    --name "$CONTAINER_NAME" \
    --auth-mode login
  echo "✓ Container created: $CONTAINER_NAME"
fi

az storage account blob-service-properties update \
  --account-name "$STORAGE_ACCOUNT" \
  --resource-group "$RESOURCE_GROUP" \
  --enable-versioning true >/dev/null
echo "✓ Blob versioning enabled on $STORAGE_ACCOUNT"

# --- Step 2: GitHub OIDC Managed Identity + federated credential ---
if az identity show --resource-group "$RESOURCE_GROUP" --name "$IDENTITY_NAME" >/dev/null 2>&1; then
  echo "✓ Managed Identity '$IDENTITY_NAME' already exists, skipping creation"
else
  az identity create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$IDENTITY_NAME" \
    --location "$REGION"
  echo "✓ Managed Identity created: $IDENTITY_NAME"
fi

IDENTITY_CLIENT_ID=$(az identity show --resource-group "$RESOURCE_GROUP" --name "$IDENTITY_NAME" --query clientId -o tsv)
IDENTITY_PRINCIPAL_ID=$(az identity show --resource-group "$RESOURCE_GROUP" --name "$IDENTITY_NAME" --query principalId -o tsv)

# Contributor scoped only to the Resource Group (not subscription-wide).
if az role assignment list --assignee "$IDENTITY_PRINCIPAL_ID" --role "Contributor" --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP" --query "[0].id" -o tsv | grep -q .; then
  echo "✓ Contributor role assignment already exists, skipping"
else
  az role assignment create \
    --assignee-object-id "$IDENTITY_PRINCIPAL_ID" \
    --assignee-principal-type ServicePrincipal \
    --role "Contributor" \
    --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP"
  echo "✓ Contributor role assigned, scoped to Resource Group '$RESOURCE_GROUP'"
fi

# Storage Blob Data Contributor on the state Storage Account specifically:
# Contributor (above) is an ARM control-plane role and does NOT grant blob
# data-plane access. backend.tf sets use_azuread_auth = true, so both the
# GitHub OIDC identity and (below) the human running bootstrap need this to
# actually read/write the state blob via `terraform init`/`plan`/`apply`.
STATE_STORAGE_SCOPE="/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Storage/storageAccounts/$STORAGE_ACCOUNT"

if az role assignment list --assignee "$IDENTITY_PRINCIPAL_ID" --role "Storage Blob Data Contributor" --scope "$STATE_STORAGE_SCOPE" --query "[0].id" -o tsv | grep -q .; then
  echo "✓ Storage Blob Data Contributor already assigned to Managed Identity, skipping"
else
  az role assignment create \
    --assignee-object-id "$IDENTITY_PRINCIPAL_ID" \
    --assignee-principal-type ServicePrincipal \
    --role "Storage Blob Data Contributor" \
    --scope "$STATE_STORAGE_SCOPE"
  echo "✓ Storage Blob Data Contributor assigned to Managed Identity on $STORAGE_ACCOUNT"
fi

CURRENT_USER_OID=$(az ad signed-in-user show --query id -o tsv 2>/dev/null || true)
if [ -n "$CURRENT_USER_OID" ]; then
  if az role assignment list --assignee "$CURRENT_USER_OID" --role "Storage Blob Data Contributor" --scope "$STATE_STORAGE_SCOPE" --query "[0].id" -o tsv | grep -q .; then
    echo "✓ Storage Blob Data Contributor already assigned to current user, skipping"
  else
    az role assignment create \
      --assignee-object-id "$CURRENT_USER_OID" \
      --assignee-principal-type User \
      --role "Storage Blob Data Contributor" \
      --scope "$STATE_STORAGE_SCOPE"
    echo "✓ Storage Blob Data Contributor assigned to current user on $STORAGE_ACCOUNT"
  fi
fi

# --- Step 3: Microsoft Graph application permissions on the Managed Identity ---
# Needed by identity.tf's azuread_app_role_assignment resources (T057/T058):
# this identity's own `terraform apply` run must be able to read the
# Microsoft Graph service principal and create app-role assignments on the
# Function App's managed identity. Requires the human running this script to
# already hold sufficient Entra ID privilege to grant Graph application
# permissions (e.g. Global Administrator / Privileged Role Administrator, or
# the Application.ReadWrite.All + AppRoleAssignment.ReadWrite.All Graph
# permissions themselves) — the same "someone privileged bootstraps the
# least-privilege CI identity once" pattern as the Contributor role above.
#
# AppRoleAssignment.ReadWrite.All is broad (it can assign any Graph app role
# to any principal tenant-wide, not just these two roles to this one
# identity) — there is no narrower built-in Graph permission scoped to "grant
# only these specific roles." Granting it to this identity is a deliberate,
# reviewed trade-off, not an oversight.
GRAPH_APP_ID="00000003-0000-0000-c000-000000000000"
GRAPH_SP_ID=$(az ad sp show --id "$GRAPH_APP_ID" --query id -o tsv)

grant_graph_app_role() {
  local role_value="$1"
  local role_id
  role_id=$(az ad sp show --id "$GRAPH_APP_ID" --query "appRoles[?value=='$role_value'].id | [0]" -o tsv)

  local existing
  existing=$(az rest --method GET \
    --uri "https://graph.microsoft.com/v1.0/servicePrincipals/$IDENTITY_PRINCIPAL_ID/appRoleAssignments" \
    --query "value[?appRoleId=='$role_id'].id | [0]" -o tsv 2>/dev/null || true)

  if [ -n "$existing" ]; then
    echo "✓ Graph app role '$role_value' already granted to Managed Identity, skipping"
  else
    az rest --method POST \
      --uri "https://graph.microsoft.com/v1.0/servicePrincipals/$IDENTITY_PRINCIPAL_ID/appRoleAssignments" \
      --headers "Content-Type=application/json" \
      --body "{\"principalId\": \"$IDENTITY_PRINCIPAL_ID\", \"resourceId\": \"$GRAPH_SP_ID\", \"appRoleId\": \"$role_id\"}" >/dev/null
    echo "✓ Graph app role '$role_value' granted to Managed Identity"
  fi
}

grant_graph_app_role "Application.Read.All"
grant_graph_app_role "AppRoleAssignment.ReadWrite.All"

# Federated credentials on the Managed Identity — NOT an App Registration
# (az ad app federated-credential create), per research.md §7 / FR-011a.
#
# Four, not one: GitHub's OIDC subject claim shape depends on how a job is
# triggered/scoped, discovered by actually running these workflows for the
# first time (each shape below hit AADSTS700213 in turn until added):
#   - push to main, no `environment:`          -> repo:...:ref:refs/heads/main
#   - pull_request                             -> repo:...:pull_request
#   - job with `environment: production`       -> repo:...:environment:production
#   - job with `environment: production-infra` -> repo:...:environment:production-infra
# A job's `environment:` key, when present, determines its subject — the
# ref-based credential is unused by any current workflow (every one that
# calls azure/login@v2 also sets `environment:`) but kept for any future
# push-triggered job that doesn't.
declare -A FEDERATED_CREDENTIALS=(
  ["github-actions-main"]="ref:refs/heads/main"
  ["github-actions-pull-request"]="pull_request"
  ["github-actions-env-production"]="environment:production"
  ["github-actions-env-production-infra"]="environment:production-infra"
)

for cred_name in "${!FEDERATED_CREDENTIALS[@]}"; do
  subject_suffix="${FEDERATED_CREDENTIALS[$cred_name]}"
  if az identity federated-credential show --name "$cred_name" --identity-name "$IDENTITY_NAME" --resource-group "$RESOURCE_GROUP" >/dev/null 2>&1; then
    echo "✓ Federated credential '$cred_name' already exists, skipping"
  else
    az identity federated-credential create \
      --name "$cred_name" \
      --identity-name "$IDENTITY_NAME" \
      --resource-group "$RESOURCE_GROUP" \
      --issuer "https://token.actions.githubusercontent.com" \
      --subject "${GITHUB_SUBJECT_PREFIX}:${subject_suffix}" \
      --audiences "api://AzureADTokenExchange"
    echo "✓ Federated OIDC credential '$cred_name' configured on Managed Identity: $IDENTITY_NAME"
  fi
done

echo
echo "== Bootstrap complete =="
echo "Update infrastructure/terraform/backend-prod.hcl and infrastructure/terraform/terraform.tfvars if not already set:"
echo "  resource_group_name  = \"$RESOURCE_GROUP\""
echo "  storage_account_name = \"$STORAGE_ACCOUNT\""
echo
echo "Set these as GitHub repository variables (Settings → Secrets and variables → Actions → Variables):"
echo "  AZURE_SUBSCRIPTION_ID = $SUBSCRIPTION_ID"
echo "  AZURE_TENANT_ID       = $TENANT_ID"
echo "  AZURE_CLIENT_ID       = $IDENTITY_CLIENT_ID"
