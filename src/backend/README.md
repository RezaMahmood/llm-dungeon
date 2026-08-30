# Backend — LLM Dungeon Adventure

Python Azure Functions backend implementing authentication and account
provisioning (features `002-login-and-access-control`, `003-account-provisioning`).

## Structure

```
src/backend/
├── api/            # HTTP route handlers (auth, admin, game)
├── models/         # ProvisionedAccountEntry
├── services/       # Cosmos DB, token validation, account provisioning
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

Requires the [Azure Functions Core Tools](https://learn.microsoft.com/azure/azure-functions/functions-run-local).
Run from `src/` (not `src/backend/`) — `src/function_app.py` is the entry
point Azure Functions loads, matching how `backend-deploy.yml` deploys
`package: "src"`; it just re-exports the real `app` from
`backend/function_app.py`:

```bash
cd src
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

See [002's contracts/api.md](../../specs/002-login-and-access-control-done/contracts/api.md) and
[003's contracts/api.md](../../specs/003-account-provisioning/contracts/api.md) for full
request/response contracts.

| Endpoint | Method | Requires |
|---|---|---|
| `/api/auth/login` | POST | Valid bearer token |
| `/api/auth/me` | GET | Valid bearer token |
| `/api/auth/logout` | POST | Valid bearer token |
| `/api/manage/accounts` | POST | Administrator role |
| `/api/manage/accounts` | GET | Administrator role |
| `/api/manage/stories` | GET | Administrator role |
| `/api/manage/stories/create` | POST | Administrator role |

`manage/*`, not `admin/*`: Azure Functions reserves any function route starting
with the literal segment `admin` for its own internal management API,
regardless of `routePrefix` — a route named `admin/...` fails to register at
all ("route conflicts with one or more built in routes").
| `/api/game/start` | POST | Player role |
