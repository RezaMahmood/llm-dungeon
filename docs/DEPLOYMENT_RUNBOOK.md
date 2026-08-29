# Deployment Runbook: Login and Access Control

**Prerequisite**: `007-azure-infrastructure-provisioning` must be complete
(Cosmos DB serverless account, Azure Functions app, Static Web App, Managed
Identity, GitHub Actions OIDC federation). This feature (`002`) does not
provision any Azure infrastructure itself.

## Steps

1. **Verify Cosmos DB collections exist**
   - `allowListEntries` (partition key `/user_oid`)
   - `capabilityAssignments` (partition key `/user_oid`)
   - Create them (via Azure Portal, CLI, or SDK) against the serverless
     account provisioned by 007 if they don't exist yet — see
     [data-model.md](../specs/002-login-and-access-control/data-model.md).

2. **Seed test data**
   ```bash
   COSMOS_ENDPOINT=<endpoint> python -m backend.db.seed_data
   ```
   Requires the caller's identity to hold `Cosmos DB Data Contributor` on the
   account.

3. **Configure Azure AD app registration**
   - Redirect URIs: `http://localhost:5173/` (dev), the deployed Static Web
     App URL (prod, from 007's output)
   - Scopes: `openid`, `profile`, `email`
   - Record the tenant ID and app (client) ID.

4. **Set Function App application settings** (in the Function App provisioned
   by 007):
   - `AZURE_TENANT_ID`
   - `AZURE_APP_ID`
   - `COSMOS_ENDPOINT`
   - Confirm the Function App's Managed Identity has `Cosmos DB Data
     Contributor` on the Cosmos DB account (provisioned by 007).

5. **Deploy backend** — merge to `main` triggers the GitHub Actions workflow
   (from 007) that deploys `backend/` to the Function App.

6. **Deploy frontend** — set `VITE_AZURE_TENANT_ID`, `VITE_AZURE_APP_ID`,
   `VITE_AZURE_REDIRECT_URI` as deployment secrets/build variables, then
   merge to `main` to trigger the Static Web App deployment.

7. **Run quickstart validation scenarios** — see
   [quickstart.md](../specs/002-login-and-access-control/quickstart.md) and
   the four scenario docs in
   [tests/e2e/](../specs/002-login-and-access-control/tests/e2e/).

8. **Verify telemetry** — confirm Application Insights receives
   authentication/authorization events from `auth_service`,
   `allow_list_service`, and `capability_service`.
