#!/usr/bin/env bash
# Populates the repository-level GitHub Actions variables shared by both the
# `production` and `production-infra` environments, sourced from `terraform
# output -json` (contracts/deployment-config-contract.md's GitHub Environment
# Variables section).
#
# T014 (Foundational) already created the `production`/`production-infra`
# environments and the `production-infra` required-reviewer protection rule —
# this script only sets variable values, it does not create environments.
#
# Usage: ./scripts/configure-github-environment.sh
# Requires: gh CLI (authenticated), terraform CLI, run from repo root with
# terraform/ already applied (state readable via `terraform output`).

set -euo pipefail

REPO="RezaMahmood/llm-dungeon"
TERRAFORM_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../terraform" && pwd)"

outputs=$(terraform -chdir="$TERRAFORM_DIR" output -json)
json_get() { echo "$outputs" | python3 -c "import json,sys; print(json.load(sys.stdin)['$1']['value'])"; }

SUBSCRIPTION_ID=$(az account show --query id -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)
IDENTITY_CLIENT_ID=$(az identity show \
  --resource-group llm-dungeon \
  --name llmdungeon-github-oidc-identity-prod \
  --query clientId -o tsv)

declare -A vars=(
  [AZURE_SUBSCRIPTION_ID]="$SUBSCRIPTION_ID"
  [AZURE_TENANT_ID]="$TENANT_ID"
  [AZURE_CLIENT_ID]="$IDENTITY_CLIENT_ID"
  [RESOURCE_GROUP_NAME]="$(json_get resource_group_name)"
  [FUNCTIONS_APP_NAME]="$(json_get functions_app_name)"
  [STORAGE_ACCOUNT_NAME]="$(json_get storage_account_name)"
  [COSMOS_ACCOUNT_NAME]="$(json_get cosmos_db_account_name)"
  [STATIC_WEB_APP_NAME]="$(json_get static_web_app_name)"
  # 1.16.0, not the originally-planned 1.6.0: CI failed with "error checking
  # signature: openpgp: key expired" installing the azurerm provider under
  # 1.6.0's stale embedded trust data (1.16.0 — validated locally throughout
  # this feature's implementation — installs it without issue).
  [TERRAFORM_VERSION]="1.16.0"
  [AZURE_PROVIDER_VERSION]="5.3.0"
)

for name in "${!vars[@]}"; do
  gh variable set "$name" --repo "$REPO" --body "${vars[$name]}"
  echo "✓ Set repository variable: $name"
done

echo
echo "== Done =="
echo "Repository variables set on $REPO (shared by 'production' and 'production-infra')."
echo "Remaining manual step: set the 'AZURE_STATIC_WEB_APPS_API_TOKEN' repository secret"
echo "  gh secret set AZURE_STATIC_WEB_APPS_API_TOKEN --repo $REPO --body \"\$(terraform -chdir=$TERRAFORM_DIR output -raw static_web_app_deployment_token)\""
