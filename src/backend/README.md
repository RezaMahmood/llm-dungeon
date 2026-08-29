# Backend — LLM Dungeon Adventure

Python Azure Functions backend implementing authentication, allow-list, and
capability-based authorization (feature `002-login-and-access-control`).

## Structure

```
src/backend/
├── api/            # HTTP route handlers (auth, admin, game)
├── models/         # AllowListEntry, CapabilityAssignment
├── services/       # Cosmos DB, token validation, allow-list, capabilities
├── db/             # Seed data script
├── config.py       # Environment-driven configuration
└── function_app.py # Azure Functions entry point (route registration)
```

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env   # fill in AZURE_TENANT_ID, AZURE_APP_ID, COSMOS_ENDPOINT
```

## Running tests

```bash
pytest src/backend/tests/ -v --cov=backend
```

Tests mock Cosmos DB and Azure AD's JWKS endpoint — no live Azure resources
are required to run the suite.

## Running locally

Requires the [Azure Functions Core Tools](https://learn.microsoft.com/azure/azure-functions/functions-run-local):

```bash
func start
```

## Environment variables

| Variable | Description |
|---|---|
| `AZURE_TENANT_ID` | Azure AD tenant ID |
| `AZURE_APP_ID` | Azure AD app registration ID (token audience) |
| `COSMOS_ENDPOINT` | Cosmos DB account endpoint (Managed Identity auth, no keys) |

## Deployment

Deployed to the Azure Functions app provisioned by
[007-azure-infrastructure-provisioning](../../specs/007-azure-infrastructure-provisioning/spec.md)
via the GitHub Actions workflow, on merge to `main`.

## API endpoints

See [contracts/api.md](../../specs/002-login-and-access-control/contracts/api.md) for full
request/response contracts.

| Endpoint | Method | Requires |
|---|---|---|
| `/api/auth/login` | POST | Valid bearer token |
| `/api/auth/me` | GET | Valid bearer token |
| `/api/auth/logout` | POST | Valid bearer token |
| `/api/admin/stories` | GET | Administrator capability |
| `/api/admin/stories/create` | POST | Administrator capability |
| `/api/game/start` | POST | Player capability |
