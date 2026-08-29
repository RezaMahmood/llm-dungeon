# Quickstart & Validation Guide

**Date**: 2026-08-28 | **Status**: Phase 1 Complete

This guide documents the steps to validate each user story and feature requirement for Azure infrastructure provisioning.

---

## Prerequisites

- Azure subscription with owner/contributor access
- Azure CLI installed and authenticated (`az login`)
- GitHub repository access (to configure actions/environments)
- Terraform >= 1.5.0 installed locally (for manual validation)

---

## Scenario 1: Bootstrap Terraform State Storage

**User Story**: Engineer sets up Terraform for the first time (one-time setup)

**Prerequisites**:
- Azure subscription ID
- The `llm-dungeon` Resource Group already exists (pre-created out-of-band; Terraform and this bootstrap script never create or delete it)

**Setup Steps**:

1. **Create Bootstrap Storage Account**

   ```bash
   SUBSCRIPTION_ID="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
   RESOURCE_GROUP="llm-dungeon"  # Pre-existing — all project resources share this one group
   STORAGE_ACCOUNT="llmdungeontstateprod"  # Must be unique, 3-24 chars
   CONTAINER="terraform-state"
   REGION="westeurope"
   
   az login --use-device-code
   az account set --subscription "$SUBSCRIPTION_ID"
   
   # Verify the pre-existing resource group exists (never created here)
   az group show --name "$RESOURCE_GROUP" >/dev/null
   
   az storage account create \
     --resource-group "$RESOURCE_GROUP" \
     --name "$STORAGE_ACCOUNT" \
     --location "$REGION" \
     --sku "Standard_LRS" \
     --access-tier "Hot" \
     --https-only true \
     --default-action "Deny"
   
   az storage container create \
     --account-name "$STORAGE_ACCOUNT" \
     --name "$CONTAINER" \
     --auth-mode login
   ```

2. **Update Backend Configuration**

   Update `infrastructure/terraform/backend-prod.hcl`:
   ```hcl
   resource_group_name  = "llm-dungeon"
   storage_account_name = "llmdungeontstateprod"
   container_name       = "terraform-state"
   key                  = "production.tfstate"
   ```

3. **Initialize Terraform**

   ```bash
   cd infrastructure/terraform/
   terraform init -backend-config=backend-prod.hcl
   ```

**Expected Output**:
```
Initializing the backend...
Successfully configured the backend "azurerm"! Terraform will automatically
use this backend in all future operations.
```

**Validation**:
- [ ] Storage account created in Azure Portal
- [ ] Container "terraform-state" exists in storage account
- [ ] `terraform init` succeeds without errors

---

## Scenario 2: Provision Complete Production Infrastructure

**User Story 1**: Infrastructure is provisioned reproducibly via Terraform

**Prerequisites**:
- Bootstrap storage account created (Scenario 1)
- Terraform variables configured (`infrastructure/terraform/terraform.tfvars`)
- Azure subscription access

**Setup Steps**:

1. **Review Terraform Configuration**

   Ensure `infrastructure/terraform/terraform.tfvars` contains:
   ```hcl
   environment     = "production"
   azure_region    = "westeurope"
   resource_prefix = "llmdungeon"
   github_repository_owner  = "RezaMahmood"
   github_repository_name   = "llm-dungeon"
   ```

2. **Plan Terraform Changes**

   ```bash
   cd infrastructure/terraform/
   terraform plan -out=tfplan
   ```

   Review output: 100+ resources will be created.

3. **Apply Terraform**

   ```bash
   terraform apply tfplan
   ```

   Duration: ~10-15 minutes (Azure API latency)

4. **Capture Outputs**

   ```bash
   terraform output -json > outputs.json
   cat outputs.json | jq '.resource_group_name.value'
   ```

**Expected Output**:
```
Apply complete! Resources added: 25 (example).

Outputs:
  resource_group_name = "llm-dungeon"
  functions_app_name = "llmdungeon-func-prod"
  static_web_app_name = "llmdungeon-web-prod"
  storage_account_name = "llmdungeonassetsprod"
  cosmos_db_account_name = "llmdungeon-cosmos-prod"
  ...
```

**Validation**:
- [ ] Azure Portal shows all resources created in resource group
- [ ] Functions app exists, Managed Identity enabled
- [ ] Storage account exists, public access disabled
- [ ] Cosmos DB account exists, public access disabled
- [ ] Static Web App exists, GitHub repo linked
- [ ] Azure AI Foundry resource exists, model deployment present
- [ ] Application Insights resource exists
- [ ] Private endpoints created for Storage, Cosmos, AI Foundry
- [ ] Private DNS zones exist and linked to VNet
- [ ] Drift detection: manually change a tag on one resource via the Azure Portal, then run `terraform plan` — the change is surfaced as a proposed update, not silently reverted or accepted (spec.md Edge Cases, FR-016)

---

## Scenario 3: Validate Infrastructure via GitHub Actions

**User Story 2**: Application code deploys automatically via GitHub Actions

**Prerequisites**:
- GitHub repository with `.github/workflows/` configured
- GitHub environments "production" (app deploys, no approval) and "production-infra" (Terraform apply, required reviewer) created, with repository variables set
- Federated OIDC trust configured in Azure

**Setup Steps**:

1. **Create GitHub OIDC Managed Identity and Configure Federated Trust**

   (Dedicated user-assigned Managed Identity — not an Azure app registration/service principal)

   ```bash
   TENANT_ID="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
   RESOURCE_GROUP="llm-dungeon"
   REGION="westeurope"
   IDENTITY_NAME="llmdungeon-github-oidc-identity-prod"
   GITHUB_ORG="RezaMahmood"
   GITHUB_REPO="llm-dungeon"

   az identity create \
     --resource-group "$RESOURCE_GROUP" \
     --name "$IDENTITY_NAME" \
     --location "$REGION"

   az identity federated-credential create \
     --name "github-actions-main" \
     --identity-name "$IDENTITY_NAME" \
     --resource-group "$RESOURCE_GROUP" \
     --issuer "https://token.actions.githubusercontent.com" \
     --subject "repo:$GITHUB_ORG/$GITHUB_REPO:ref:refs/heads/main" \
     --audiences "api://AzureADTokenExchange"

   # Grant only what deployment/Terraform-apply workflows need (not a subscription-wide role)
   IDENTITY_PRINCIPAL_ID=$(az identity show --resource-group "$RESOURCE_GROUP" --name "$IDENTITY_NAME" --query principalId -o tsv)
   az role assignment create \
     --assignee-object-id "$IDENTITY_PRINCIPAL_ID" \
     --assignee-principal-type ServicePrincipal \
     --role "Contributor" \
     --scope "/subscriptions/<subscription-id>/resourceGroups/$RESOURCE_GROUP"
   ```

2. **Set GitHub Environment Variables**

   Go to: GitHub repo → Settings → Environments → production → Environment variables
   
   ```
   AZURE_SUBSCRIPTION_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
   AZURE_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
   AZURE_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx  # GitHub OIDC Managed Identity client ID
   RESOURCE_GROUP_NAME=llm-dungeon
   FUNCTIONS_APP_NAME=llmdungeon-func-prod
   TERRAFORM_VERSION=1.16.0
   AZURE_PROVIDER_VERSION=3.80.0
   ```

3. **Trigger Terraform Validation Workflow**

   ```bash
   git add .
   git commit -m "Initial infrastructure configuration"
   git push origin feature-branch
   # Create pull request
   ```

   Check GitHub Actions → terraform-validate.yml workflow

4. **Verify Workflow Steps**

   - [ ] terraform-validate job starts
   - [ ] Terraform fmt check passes
   - [ ] Terraform validate passes
   - [ ] Terraform plan artifact generated
   - [ ] PR shows ✓ check-passed

5. **Merge PR to Main**

   ```bash
   # Merge PR via GitHub UI
   ```

   Check GitHub Actions → terraform-apply.yml workflow

6. **Verify Infrastructure Apply**

   - [ ] terraform-apply job starts
   - [ ] Azure login succeeds (OIDC authentication)
   - [ ] terraform init succeeds
   - [ ] terraform apply succeeds
   - [ ] All resources created/updated

**Validation**:
- [ ] Terraform validation workflows pass on PR
- [ ] OIDC authentication succeeds (no secrets printed in logs)
- [ ] Terraform apply runs on main branch merge
- [ ] Infrastructure updates reflected in Azure Portal

---

## Scenario 4: Verify Private Connectivity

**User Story 4**: Backend resources communicate privately without stored credentials

**Prerequisites**:
- Infrastructure provisioned (Scenario 2)
- Functions app deployed with Python backend

**Setup Steps**:

1. **Install Test Dependencies**

   ```bash
   pip install azure-identity azure-storage-blob azure-cosmos pytest
   ```

2. **Run Private Connectivity Tests**

   ```bash
   cd infrastructure/tests/
   pytest test_private_connectivity.py -v
   ```

3. **Manual Verification: DNS Resolution**

   ```bash
   # From any machine in Azure (or via bastion)
   nslookup llmdungeonassetsprod.blob.core.windows.net
   # Expected: Private IP (e.g., 10.0.1.15), not public IP
   
   nslookup llmdungeon-cosmos-prod.documents.azure.com
   # Expected: Private IP
   
   nslookup llmdungeon-openai-prod.openai.azure.com
   # Expected: Private IP
   ```

4. **Manual Verification: Connection Test**

   From Functions app (or local terminal with Azure CLI):
   
   ```bash
   # Test Storage connection (via Managed Identity)
   curl -H "Authorization: Bearer $(az account get-access-token --resource https://storage.azure.com --query accessToken -o tsv)" \
     https://llmdungeonassetsprod.blob.core.windows.net/assets?comp=list
   # Expected: 200 OK, list of blobs (if any exist)
   
   # Test Cosmos DB connection
   python3 -c "
   from azure.cosmos import CosmosClient
   from azure.identity import DefaultAzureCredential
   
   cred = DefaultAzureCredential()
   client = CosmosClient('https://llmdungeon-cosmos-prod.documents.azure.com:443/', credential=cred)
   db = client.get_database_client('llmdungeon-db-prod')
   print('✓ Connected to Cosmos DB')
   "
   ```

5. **Verify Public Access Disabled**

   ```bash
   # Attempt connection from public internet (expected to fail)
   # This should time out or return connection refused
   curl -v https://llmdungeonassetsprod.blob.core.windows.net/assets?comp=list \
     --connect-timeout 5
   # Expected: timeout or connection refused (public endpoint blocked)
   ```

**Expected Output**:
```
test_private_connectivity.py::test_storage_private_ip PASSED
test_private_connectivity.py::test_cosmos_private_ip PASSED
test_private_connectivity.py::test_openai_private_ip PASSED
test_private_connectivity.py::test_public_access_disabled PASSED
```

**Validation**:
- [ ] DNS resolves resource names to private IPs
- [ ] Connections to resources via private IPs succeed
- [ ] No stored credentials used (Managed Identity only)
- [ ] Public endpoints return connection refused/timeout
- [ ] All connectivity tests pass

---

## Scenario 5: Test GitHub → Azure OIDC Authentication

**User Story 3**: GitHub connects to Azure without stored secrets

**Prerequisites**:
- Federated OIDC trust configured (Scenario 3)
- GitHub Actions workflow using Azure login

**Setup Steps**:

1. **Run OIDC Authentication Test Workflow**

   Manually trigger (or wait for push to main):
   ```bash
   git push origin main
   # GitHub Actions → infrastructure-tests.yml
   ```

2. **Verify No Secrets Stored**

   Go to: GitHub repo → Settings → Secrets → Verify no Azure secrets present
   
   Expected: Only GitHub-managed secrets (e.g., DEPLOYMENT_TOKEN for Static Web App), no Azure credentials

3. **Review Workflow Logs**

   GitHub Actions → infrastructure-tests.yml → test_oidc_authentication job

   Look for:
   - [ ] Azure login step succeeds
   - [ ] No error: "couldn't find credentials"
   - [ ] No Azure secrets referenced in logs

4. **Verify OIDC Exchange**

   In workflow logs, look for:
   ```
   Authenticating using federated identity exchange...
   [OK] Federated token acquired
   [OK] Access token acquired
   ```

**Expected Output**:
```
✓ OIDC authentication test passed
✓ No stored credentials detected
✓ Federated identity exchange successful
```

**Validation**:
- [ ] Azure login succeeds via OIDC
- [ ] No long-lived credentials stored in GitHub
- [ ] Workflow logs show federated token exchange
- [ ] Authentication test passes

---

## Scenario 6: Verify Application Settings & Configuration

**User Story 5**: Environment configuration is externalized

**Prerequisites**:
- Infrastructure provisioned (Scenario 2)
- Functions app with backend code deployed

**Setup Steps**:

1. **Verify Terraform Outputs → App Settings**

   ```bash
   # Check Terraform outputs
   terraform output -json | jq '.github_environment_variables'
   
   # Expected output includes resource names for GitHub Actions
   ```

2. **Verify Functions App Settings**

   Azure Portal → Function App → Settings → Application Settings

   Expected settings:
   ```
   COSMOS_ENDPOINT=https://llmdungeon-cosmos-prod.documents.azure.com:443/
   COSMOS_DATABASE=llmdungeon-db-prod
   COSMOS_CONTAINER=stories
   STORAGE_ACCOUNT_URL=https://llmdungeonassetsprod.blob.core.windows.net/
   STORAGE_CONTAINER=assets
   AZURE_OPENAI_ENDPOINT=https://llmdungeon-openai-prod.openai.azure.com/
   AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o-mini
   APPLICATIONINSIGHTS_CONNECTION_STRING=...
   PYTHON_ENABLE_WORKER_EXTENSIONS=true
   ```

3. **Verify No Hardcoded Values**

   ```bash
   # Search application code for hardcoded Azure endpoints
   grep -r "blob.core.windows.net" src/backend/src/
   grep -r "documents.azure.com" src/backend/src/
   # Expected: No matches (all values come from environment variables)
   ```

4. **Modify an Application Setting**

   ```bash
   # Azure CLI
   az functionapp config appsettings set \
     --name llmdungeon-func-prod \
     --resource-group llm-dungeon \
     --settings "TEST_VALUE=hello-world"
   ```

5. **Verify Application Picks Up Change**

   ```bash
   # Call Functions endpoint (if public test available)
   curl https://llmdungeon-func-prod.azurewebsites.net/api/test-config
   # Expected: Returns TEST_VALUE=hello-world (no restart/redeploy needed)
   ```

**Expected Output**:
```
✓ All required application settings present
✓ No hardcoded resource names in application code
✓ Setting change applied without code redeploy
```

**Validation**:
- [ ] All application settings present in Functions app
- [ ] Settings match Terraform outputs
- [ ] No hardcoded values in application code
- [ ] Application reads settings at runtime
- [ ] Setting changes apply without code redeploy

---

## Scenario 7: Full Deployment Pipeline Test

**User Story 2**: Application code deploys automatically via GitHub Actions

**Prerequisites**:
- All infrastructure in place (Scenarios 1-6)
- Backend and frontend code ready
- Workflows configured

**Setup Steps**:

1. **Push Backend Code Change**

   ```bash
   git checkout -b test/backend-deploy
   # Make a change to src/backend/src/main.py (e.g., add a comment)
   git add src/backend/src/main.py
   git commit -m "test: backend deployment"
   git push origin test/backend-deploy
   ```

2. **Create PR and Merge**

   - Create pull request via GitHub UI
   - Verify CI workflows pass (tests, linting)
   - Merge to main

3. **Monitor Deployment Workflow**

   GitHub Actions → backend-deploy.yml

   Expected steps:
   - [ ] Checkout code
   - [ ] Setup Python 3.11
   - [ ] Install dependencies
   - [ ] Run pytest tests
   - [ ] Azure login (OIDC)
   - [ ] Build Functions package
   - [ ] Deploy to Functions app
   - [ ] Smoke test

4. **Verify Deployment Success**

   ```bash
   # Check Functions app deployment status
   az functionapp deployment list \
     --name llmdungeon-func-prod \
     --resource-group llm-dungeon \
     --query "[0].[status,deploymentId]"
   # Expected: status="Succeeded"
   
   # Test backend endpoint (if available)
   curl https://llmdungeon-func-prod.azurewebsites.net/api/health
   # Expected: 200 OK
   ```

5. **Test Frontend Deployment** (similar to backend)

   ```bash
   git checkout -b test/frontend-deploy
   # Make change to src/frontend/src/App.jsx
   git add src/frontend/src/App.jsx
   git commit -m "test: frontend deployment"
   git push origin test/frontend-deploy
   # Create PR, merge to main
   ```

   GitHub Actions → frontend-deploy.yml

   Expected steps:
   - [ ] Checkout code
   - [ ] Setup Node.js 18
   - [ ] Install dependencies
   - [ ] Run React tests
   - [ ] Build static site
   - [ ] Azure login (OIDC)
   - [ ] Deploy to Static Web App

**Expected Output**:
```
✓ Backend deployment workflow runs to completion
✓ Python tests pass
✓ Functions app updated
✓ Backend endpoint responds
✓ Frontend deployment workflow runs to completion
✓ React tests pass
✓ Static Web App updated
✓ Frontend URL serves updated content
```

**Validation**:
- [ ] Deployment workflows trigger on code push to main
- [ ] All workflow steps complete successfully
- [ ] No manual deployment steps required
- [ ] Updated code live in Azure

---

## Scenario 8: Infrastructure Validation Tests (Nightly)

**Purpose**: Detect infrastructure drift or configuration issues

**Setup Steps**:

1. **Schedule Validation Workflow**

   Workflow: `.github/workflows/infrastructure-tests.yml`
   
   Trigger: Nightly (2 AM UTC) + manual trigger

2. **Run Validation Tests**

   ```bash
   # Manual trigger from GitHub Actions UI
   # or execute locally:
   cd infrastructure/tests/
   pytest test_*.py -v
   ```

3. **Review Test Results**

   - [ ] test_private_connectivity.py: DNS and connection validation
   - [ ] test_oidc_authentication.py: Federated OIDC functionality
   - [ ] test_resource_creation.py: All resources exist with correct config

**Expected Output**:
```
test_private_connectivity.py::test_storage_private_endpoint_ip PASSED
test_private_connectivity.py::test_cosmos_private_endpoint_ip PASSED
test_private_connectivity.py::test_openai_private_endpoint_ip PASSED
test_oidc_authentication.py::test_github_oidc_trust PASSED
test_resource_creation.py::test_functions_app_exists PASSED
test_resource_creation.py::test_managed_identity_enabled PASSED
test_resource_creation.py::test_storage_public_access_disabled PASSED
test_resource_creation.py::test_cosmos_public_access_disabled PASSED
...
========================= 10 passed in 2.34s =========================
```

**Validation**:
- [ ] All infrastructure tests pass
- [ ] No connectivity issues detected
- [ ] OIDC trust still valid
- [ ] All resources exist as expected

---

## Rollback & Recovery

**If Deployment Fails**:

1. **Review Error Logs**
   ```bash
   # GitHub Actions logs
   # or Azure Portal → Deployments → failed deployment
   ```

2. **Identify Issue**
   - Configuration error → Fix infrastructure/terraform/terraform.tfvars, re-run Terraform
   - Permission error → Add missing role assignment, retry
   - Network error → Check private endpoint DNS, re-run validation tests

3. **Redeploy**
   ```bash
   # For infrastructure
   cd infrastructure/terraform/
   terraform apply
   
   # For application
   git push origin main  # Triggers deployment workflows
   ```

**Manual Rollback**:
```bash
# If needed, destroy infrastructure (careful!)
terraform destroy  # Interactive approval required
```

---

## Monitoring & Alerts

**Ongoing Validation**:

- Weekly: Manual smoke test of src/backend/frontend endpoints
- Daily: Nightly infrastructure validation tests (automated)
- Per-deployment: Smoke test after src/backend/frontend deployment
- Real-time: Application Insights dashboard for errors, latency, LLM cost

---

## Checklists

### Prerequisites Checklist
- [ ] Azure subscription with owner/contributor access
- [ ] Azure CLI installed and authenticated
- [ ] GitHub repository access
- [ ] Terraform >= 1.5.0 installed
- [ ] GitHub environments "production" and "production-infra" created

### Infrastructure Setup Checklist
- [ ] Bootstrap storage account created
- [ ] Terraform backend configured
- [ ] Terraform variables file filled in
- [ ] GitHub repository variables set (shared by both environments)
- [ ] Required reviewer configured on "production-infra" only
- [ ] GitHub OIDC Managed Identity created with federated credential (not an app registration)
- [ ] terraform apply succeeds
- [ ] All resources exist in Azure Portal

### Validation Checklist
- [ ] Scenario 1: Bootstrap succeeds
- [ ] Scenario 2: Full infrastructure provisioned
- [ ] Scenario 3: GitHub Actions workflows pass
- [ ] Scenario 4: Private connectivity verified
- [ ] Scenario 5: OIDC authentication works
- [ ] Scenario 6: Application settings configured
- [ ] Scenario 7: Full deployment pipeline works
- [ ] Scenario 8: Nightly validation tests pass

---

## Support & Troubleshooting

**Common Issues**:

| Issue | Cause | Fix |
|-------|-------|-----|
| `terraform init` fails | Backend storage doesn't exist | Run bootstrap procedure (Scenario 1) |
| `terraform validate` fails | Syntax error in .tf file | Review terraform fmt output |
| `terraform apply` fails | Permission denied | Verify Azure CLI authentication |
| OIDC auth fails | Federated credential misconfigured on the GitHub OIDC Managed Identity | Recreate the federated credential (`az identity federated-credential create`) with the correct subject |
| Private endpoint DNS fails | DNS zone not linked | Link Private DNS Zone to Functions VNet |
| Functions deployment fails | Code error or missing dependency | Check Functions logs, fix code, retry |
| Connectivity test fails | Network misconfiguration | Verify private endpoint exists, DNS resolves, public access disabled |

For detailed support, see:
- [Terraform Azure Provider Docs](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs)
- [Azure Functions Documentation](https://learn.microsoft.com/en-us/azure/azure-functions/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
