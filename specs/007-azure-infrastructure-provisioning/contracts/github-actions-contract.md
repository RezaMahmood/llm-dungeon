# GitHub Actions Workflow Contract

**Date**: 2026-08-28 | **Status**: Phase 1

This contract defines the GitHub Actions workflows for infrastructure provisioning, deployment, and validation.

## Workflow: Infrastructure Validation (terraform-validate.yml)

**Trigger**: Pull request (any branch), push to main

**Purpose**: Validate Terraform syntax, formatting, and plan changes

**Steps**:

1. **Checkout Code**
   - Action: `actions/checkout@v4`
   - Use: Fetch repository code and Terraform configuration

2. **Setup Terraform**
   - Action: `hashicorp/setup-terraform@v2`
   - Input: `terraform_version`: From environment variable (e.g., 1.16.0)
   - Use: Install Terraform CLI

3. **Terraform Format Check**
   - Command: `terraform fmt -check -recursive infrastructure/terraform/`
   - Purpose: Ensure code follows Terraform formatting standards
   - Fail condition: Any files not formatted correctly

4. **Terraform Validate**
   - Command: `terraform validate -json`
   - Purpose: Validate Terraform configuration syntax and schema
   - Output: JSON-formatted errors (if any)
   - Fail condition: Validation error (e.g., missing required variables, invalid resource names)

5. **Terraform Plan** (on PR only)
   - Command: `terraform plan -out=tfplan -json > tfplan.json`
   - Use: Generate and serialize plan for review
   - Output artifacts: Upload plan file and JSON summary as PR comment
   - Fail condition: Plan error (e.g., permission denied, resource conflict)

**Success Criteria**:
- Terraform format check passes (no formatting errors)
- Terraform validate passes (no syntax/schema errors)
- Terraform plan succeeds (resources can be applied)

**Failure Handling**:
- PR blocked from merge while validation fails (branch protection rule)
- Comment with error details for troubleshooting

---

## Workflow: Infrastructure Provisioning (terraform-apply.yml)

**Trigger**: Push to main branch (after terraform-validate.yml passes)

**Purpose**: Apply Terraform changes to Azure (actual resource provisioning/updates)

**Environment**: `production-infra` (confirmed) — a separate GitHub environment from `production`, used only by this workflow, so its required-reviewer approval gate covers infrastructure changes exclusively and never blocks application code deployments (FR-010/SC-006 require those to run with no manual step)

**Permissions**: 
- `contents: read` (checkout code)
- `id-token: write` (OIDC federated authentication)

**Steps**:

1. **Checkout Code**
   - Action: `actions/checkout@v4`

2. **Setup Terraform**
   - Action: `hashicorp/setup-terraform@v2`
   - Input: `terraform_version`: From environment variable

3. **Azure Login** (via Federated OIDC)
   - Action: `azure/login@v1`
   - Inputs:
     - `client-id`: `${{ secrets.AZURE_CLIENT_ID }}` (actually from GitHub environment, not secrets)
     - `tenant-id`: `${{ secrets.AZURE_TENANT_ID }}`
     - `subscription-id`: `${{ secrets.AZURE_SUBSCRIPTION_ID }}`
   - Note: Despite `secrets.*` notation, these are GitHub environment variables (not stored secrets), passed to the action
   - Output: Authenticated Azure CLI context

4. **Terraform Init**
   - Command: `terraform init -backend-config=backend-prod.hcl`
   - Use: Initialize Terraform workspace and download providers
   - State: Stored in Azure Storage backend (from bootstrap)

5. **Terraform Apply**
   - Command: `terraform apply -auto-approve tfplan`
   - Use: Apply planned changes (if plan was successful in terraform-validate.yml)
   - Or: `terraform apply -auto-approve` if using latest plan
   - Duration: ~5-15 minutes (depending on resource count and Azure API latency)
   - Output: Resource creation/update summary

6. **Capture Terraform Outputs**
   - Command: `terraform output -json > outputs.json`
   - Use: Export resource names and endpoints for downstream workflows
   - Store: Available as workflow artifact or variable

7. **Post-Apply Validation** (optional)
   - Script: `infrastructure/tests/test_resource_creation.py`
   - Purpose: Verify all resources exist with expected configuration
   - Fail condition: Resource missing or misconfigured (e.g., public access enabled when it should be disabled)

**Success Criteria**:
- Terraform apply completes without error
- All resources created or updated as expected
- Outputs captured for downstream workflows

**Failure Handling**:
- Rollback: No automatic rollback (manual `terraform destroy` or `terraform apply` with corrected config required)
- Notification: Slack/email alert (if configured) on failure
- Manual Review: Post-apply validation fails → investigate and correct configuration

**Approval**: Required (confirmed) — the `production-infra` GitHub environment has a required reviewer rule, so this workflow pauses for manual approval before `terraform apply` executes. `backend-deploy.yml` and `frontend-deploy.yml` target the separate `production` environment, which has no approval requirement, so application code deployments remain fully automatic.

---

## Workflow: Backend Deployment (backend-deploy.yml)

**Trigger**: 
- Push to main branch (after infrastructure-apply.yml confirms infrastructure exists)
- Manual trigger (workflow_dispatch)
- Path filter: `src/backend/**` (only if backend code changes)

**Purpose**: Build and deploy Python Azure Functions backend

**Environment**: `production`

**Permissions**:
- `contents: read`
- `id-token: write` (OIDC federated authentication)

**Steps**:

1. **Checkout Code**
   - Action: `actions/checkout@v4`

2. **Setup Python**
   - Action: `actions/setup-python@v4`
   - Input: `python-version: 3.11`

3. **Install Dependencies**
   - Command: `pip install -r src/backend/requirements.txt` (and `requirements-dev.txt` for testing)
   - Purpose: Install Python packages and tools

4. **Run Tests** (per Principle I - Meaningful Testing)
   - Command: `pytest src/backend/tests/ -v --cov=src/backend/src`
   - Fail condition: Test failure blocks deployment
   - Purpose: Ensure backend code changes don't introduce regressions

5. **Azure Login** (via Federated OIDC)
   - Action: `azure/login@v1`
   - Inputs: (as above in terraform-apply.yml)

6. **Build Deployment Package**
   - Command: `func pack --build remote` (or equivalent)
   - Purpose: Create Azure Functions deployment package (Python runtime + dependencies)
   - Output: ZIP file ready for Functions app deployment

7. **Deploy to Azure Functions**
   - Action: `azure/functions-action@v1` (or equivalent)
   - Inputs:
     - `app-name`: `${{ vars.FUNCTIONS_APP_NAME }}` (from GitHub environment)
     - `package`: Path to deployment package
   - Purpose: Upload and deploy to Functions app
   - Duration: ~2-5 minutes

8. **Smoke Test** (post-deployment)
   - Script: `infrastructure/tests/test_oidc_authentication.py`
   - Purpose: Verify backend is responding to authenticated requests
   - Fail condition: Backend endpoint unreachable or returning errors

**Success Criteria**:
- Python tests pass
- Functions app deployment succeeds
- Smoke test confirms backend is live

**Failure Handling**:
- PR blocked if tests fail (pre-deployment)
- Deployment fails: Previous version remains live; investigate and revert/fix

---

## Workflow: Frontend Deployment (frontend-deploy.yml)

**Trigger**: 
- Push to main branch (after infrastructure-apply.yml confirms infrastructure exists)
- Manual trigger (workflow_dispatch)
- Path filter: `src/frontend/**` (only if frontend code changes)

**Purpose**: Build and deploy ReactJS frontend to Azure Static Web App

**Environment**: `production`

**Permissions**:
- `contents: read`
- `pull-requests: read` (for PR deployments)
- `id-token: write` (OIDC federated authentication)

**Steps**:

1. **Checkout Code**
   - Action: `actions/checkout@v4`

2. **Setup Node.js**
   - Action: `actions/setup-node@v4`
   - Input: `node-version: 18` (or current LTS)

3. **Install Dependencies**
   - Command: `npm ci` (in `src/frontend/` directory)
   - Purpose: Install React and build tools

4. **Run Tests** (per Principle I)
   - Command: `npm run test -- --coverage`
   - Fail condition: Test failure blocks deployment

5. **Build Static Site**
   - Command: `npm run build` (outputs to `src/frontend/dist/` or configured directory)
   - Purpose: Compile React to static HTML/CSS/JS

6. **Azure Login** (via Federated OIDC)
   - Action: `azure/login@v1`

7. **Deploy to Static Web App**
   - Action: `azure/static-web-apps-deploy@v1` (or manual az CLI)
   - Inputs:
     - `azure_static_web_apps_api_token`: From repository secret (configured once by repo admin)
     - `app-location`: `src/frontend/dist/`
     - `api-location`: (empty, APIs are Functions app)
     - `output-location`: `src/frontend/dist/`
   - Purpose: Upload static assets to Static Web App CDN

**Success Criteria**:
- React tests pass
- Build succeeds (no TypeScript errors, etc.)
- Static Web App deployment succeeds
- Frontend is live at Static Web App URL

**Failure Handling**:
- Deployment fails: Previous version remains live

---

## Workflow: Infrastructure Testing (infrastructure-tests.yml)

**Trigger**:
- Push to main branch (after terraform-apply.yml)
- Scheduled nightly (e.g., 2 AM UTC) for continuous validation
- Manual trigger (workflow_dispatch)

**Purpose**: Validate infrastructure connectivity, authentication, and resource configuration (post-deployment tests)

**Environment**: `production`

**Permissions**:
- `id-token: write` (OIDC federated authentication)

**Steps**:

1. **Checkout Code**
   - Action: `actions/checkout@v4`

2. **Setup Python**
   - Action: `actions/setup-python@v4`
   - Input: `python-version: 3.11`

3. **Install Test Dependencies**
   - Command: `pip install pytest azure-identity azure-storage-blob azure-cosmos openai`

4. **Azure Login** (via Federated OIDC)
   - Action: `azure/login@v1`

5. **Run Private Connectivity Tests**
   - Script: `infrastructure/tests/test_private_connectivity.py`
   - Purpose: Verify backend resources are reachable over private endpoints
   - Assertions:
     - DNS resolves storage/cosmos/openai names to private IPs (not public)
     - Connections to resources succeed (authenticated via Managed Identity)
   - Fail condition: Any DNS or connection failure indicates misconfiguration

6. **Run OIDC Authentication Test**
   - Script: `infrastructure/tests/test_oidc_authentication.py`
   - Purpose: Verify GitHub Actions can authenticate to Azure via federated OIDC
   - Assertions:
     - No error accessing Azure resources
     - No stored credentials used (OIDC only)
   - Fail condition: OIDC authentication fails or falls back to stored credentials

7. **Run Resource Creation Tests**
   - Script: `infrastructure/tests/test_resource_creation.py`
   - Purpose: Verify all required resources exist and are configured correctly
   - Assertions:
     - Functions app exists, Managed Identity is enabled
     - Storage account has public network access disabled
     - Cosmos DB has public network access disabled
     - Private endpoints exist and are linked to DNS zones
   - Fail condition: Resource missing or misconfigured

**Success Criteria**:
- All connectivity tests pass
- OIDC authentication succeeds
- All resources validated

**Failure Handling**:
- Alert/notification (Slack, email, GitHub issue)
- Investigation required: configuration drift or Azure API change

---

## GitHub Environments (production and production-infra)

Two GitHub environments are used (confirmed), so the required-reviewer approval gate covers infrastructure changes only, never application code deployments:

| Environment | Used by | Required Reviewers |
|---|---|---|
| `production` | `backend-deploy.yml`, `frontend-deploy.yml`, `infrastructure-tests.yml` | None — application deploys stay fully automatic per FR-010/SC-006 |
| `production-infra` | `terraform-apply.yml` only | Required — at least one reviewer must approve before `terraform apply` runs against Azure |

**Deployment Branches** (both environments): `main` only (branch protection rule)

**Environment Secrets** (both environments): (none required — OIDC is used instead)

**Environment Variables** — defined once at the **repository** level (not duplicated per-environment, since both environments' workflows need the same identity/resource values and none of these are secrets):
```yaml
AZURE_SUBSCRIPTION_ID: <subscription-id>
AZURE_TENANT_ID: <entra-id-tenant-id>
AZURE_CLIENT_ID: <github-oidc-managed-identity-client-id>
RESOURCE_GROUP_NAME: llm-dungeon  # Pre-existing; single Resource Group for all project resources
FUNCTIONS_APP_NAME: llmdungeon-func-prod
STORAGE_ACCOUNT_NAME: llmdungeonassetsprod
COSMOS_ACCOUNT_NAME: llmdungeon-cosmos-prod
STATIC_WEB_APP_NAME: llmdungeon-web-prod
TERRAFORM_VERSION: 1.16.0
AZURE_PROVIDER_VERSION: 3.80.0
```

**Federated OIDC Trust** (configured on the dedicated GitHub OIDC Managed Identity, not an app registration) — **four** federated credentials. GitHub's OIDC subject claim shape depends on how a job is triggered and scoped, and critically: **a job's `environment:` key overrides the branch/event-based subject entirely** — every workflow here that calls `azure/login` also sets `environment:`, so each needed its own credential, found one `AADSTS700213` at a time by actually running them. This repo also issues subjects in the newer immutable-ID format (`repo:OWNER@ownerID/REPO@repoID:...`), not the classic name-only format — `infrastructure/scripts/bootstrap.sh` fetches the numeric IDs via `gh api` rather than hardcoding them:
- **`github-actions-main`**: `Subject: repo:OWNER@ownerID/REPO@repoID:ref:refs/heads/main`. Would cover a `push`-triggered job with no `environment:` key set — unused by any current workflow, kept for future ones.
- **`github-actions-pull-request`**: `Subject: repo:OWNER@ownerID/REPO@repoID:pull_request`. Covers `terraform-validate.yml`'s Azure-login-requiring `terraform plan` step on PRs.
- **`github-actions-env-production`**: `Subject: repo:OWNER@ownerID/REPO@repoID:environment:production`. Covers every job with `environment: production` — `backend-deploy.yml`, `frontend-deploy.yml`, `infrastructure-tests.yml`.
- **`github-actions-env-production-infra`**: `Subject: repo:OWNER@ownerID/REPO@repoID:environment:production-infra`. Covers `terraform-apply.yml`'s job (`environment: production-infra`).
- **Issuer** (all four): `https://token.actions.githubusercontent.com`
- **Audience** (all four): `api://AzureADTokenExchange` (default GitHub Actions audience)

---

## Workflow Dependencies & Execution Order

```
PR submitted (any branch)
  ↓
  ├→ terraform-validate.yml
  │   ├→ terraform fmt, validate
  │   ├→ terraform plan
  │   └→ Success = PR can be reviewed

PR merged to main
  ↓
  ├→ terraform-apply.yml (infrastructure update)
  │   ├→ terraform init
  │   ├→ terraform apply
  │   └→ Success = infrastructure ready
  │
  ├→ backend-deploy.yml (after terraform-apply.yml confirms infrastructure)
  │   ├→ Python tests
  │   ├→ Build Functions package
  │   ├→ Deploy to Functions app
  │   └→ Success = backend live
  │
  ├→ frontend-deploy.yml (after terraform-apply.yml confirms infrastructure)
  │   ├→ React tests
  │   ├→ Build static site
  │   ├→ Deploy to Static Web App
  │   └→ Success = frontend live
  │
  └→ infrastructure-tests.yml (nightly + after apply)
      ├→ Connectivity tests
      ├→ OIDC authentication test
      ├→ Resource validation tests
      └→ Success = infrastructure validated

```

**Parallel Execution**: `terraform-apply.yml`, `backend-deploy.yml`, and `frontend-deploy.yml` can run in parallel if they both depend on terraform-apply completing first (use GitHub Actions job dependencies or sequential workflow_run triggers).

---

## Error Handling & Notifications

**Failure Scenarios**:

1. **terraform-validate.yml fails**
   - PR shows ❌ check; merge blocked
   - Comment: Terraform error details
   - Action: Fix configuration and push

2. **terraform-apply.yml fails**
   - Alert: Slack / email / GitHub issue (if configured)
   - State: Infrastructure may be partially applied; manual investigation needed
   - Action: Review Azure portal, fix configuration, re-run

3. **backend-deploy.yml fails**
   - Alert: Deployment failed; previous version remains live
   - Action: Fix backend code/tests, push again

4. **frontend-deploy.yml fails**
   - Alert: Deployment failed; previous version remains live
   - Action: Fix frontend code/tests, push again

5. **infrastructure-tests.yml fails**
   - Alert: Infrastructure configuration drift detected
   - Action: Investigate (manual Azure changes?), correct, re-run Terraform

**Retry Policy**:
- Transient failures (Azure API throttling): Automatic retry with exponential backoff (optional, configure in workflow)
- Persistent failures: Manual review and fix required
