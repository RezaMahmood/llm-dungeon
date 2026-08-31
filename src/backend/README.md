# Backend — LLM Dungeon Adventure

Python Azure Functions backend implementing authentication, account
provisioning, and guided story creation (features `002-login-and-access-control`,
`003-account-provisioning-done`, `004-story-creation`).

## Structure

```
src/backend/
├── api/            # HTTP route handlers (auth, admin, game)
├── models/         # ProvisionedAccountEntry, Story, StoryDraft, CharacterType,
│                   # CompletionCriteria, StoryCreationExchange
├── services/       # Cosmos DB, token validation, account provisioning,
│                   # LLM client (Azure AI Foundry), story draft/story persistence
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
| `AZURE_AI_FOUNDRY_ENDPOINT` | Azure OpenAI resource endpoint (Managed Identity auth, no keys) — `004-story-creation`'s `llm_service.py`, via `agent_framework.openai.OpenAIChatCompletionClient` |
| `AZURE_AI_FOUNDRY_DEPLOYMENT_NAME` | Deployed model name on that resource (e.g. `gpt-5-nano`) — passed as `OpenAIChatCompletionClient`'s `model` |
| `LLM_INPUT_TOKEN_PRICE_USD` | USD price per input token, used to compute `gen_ai.cost_usd` on every LLM call span (Constitution Principle VI) |
| `LLM_OUTPUT_TOKEN_PRICE_USD` | USD price per output token, same purpose |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | Application Insights connection string; when set, `configure_azure_monitor()` exports OpenTelemetry spans (incl. `gen_ai.*` LLM call spans) on startup — unset locally, this step is skipped |

## Deployment

Deployed to the Azure Functions app provisioned by
[007-azure-infrastructure-provisioning](../../specs/007-azure-infrastructure-provisioning/spec.md)
via the GitHub Actions workflow, on merge to `main`.

## API endpoints

See [002's contracts/api.md](../../specs/002-login-and-access-control-done/contracts/api.md),
[003's contracts/api.md](../../specs/003-account-provisioning-done/contracts/api.md), and
[004's contracts/api.md](../../specs/004-story-creation/contracts/api.md) for full
request/response contracts.

| Endpoint | Method | Requires |
|---|---|---|
| `/api/auth/login` | POST | Valid bearer token |
| `/api/auth/me` | GET | Valid bearer token |
| `/api/auth/logout` | POST | Valid bearer token |
| `/api/manage/accounts` | POST | Administrator role |
| `/api/manage/accounts` | GET | Administrator role |
| `/api/manage/stories/drafts` | POST | Administrator role |
| `/api/manage/stories/drafts/{draftId}` | GET | Administrator role |
| `/api/manage/stories/drafts/{draftId}` | PATCH | Administrator role |
| `/api/manage/stories/drafts/{draftId}/messages` | POST | Administrator role |
| `/api/manage/stories` | GET | Administrator role |
| `/api/manage/stories/{storyId}` | GET | Administrator role |
| `/api/game/start` | POST | Player role |

`manage/*`, not `admin/*`: Azure Functions reserves any function route starting
with the literal segment `admin` for its own internal management API,
regardless of `routePrefix` — a route named `admin/...` fails to register at
all ("route conflicts with one or more built in routes").
