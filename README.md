# LLM Dungeon Adventure

A private, LLM-driven text adventure game. Backend: Python on Azure
Functions. Frontend: ReactJS. Access is restricted to an explicit allow-list
of Microsoft accounts (see [Constitution](.specify/memory/constitution.md)).

## Features

- [`001-ci-cd-foundation`](specs/001-ci-cd-foundation/spec.md) — CI test gate on every PR
- [`002-login-and-access-control`](specs/002-login-and-access-control/spec.md) — Microsoft Entra ID sign-in, allow-list, and Player/Administrator capabilities
- [`007-azure-infrastructure-provisioning`](specs/007-azure-infrastructure-provisioning/spec.md) — Azure infrastructure (Functions, Static Web App, Cosmos DB, Managed Identity), provisioned separately

## Architecture

```
Browser (React + MSAL)
   │  Authorization: Bearer <token>
   ▼
Azure Functions (Python)
   │  token validation → allow-list check → capability check
   ▼
Cosmos DB (allowListEntries, capabilityAssignments)
```

## Getting started

- Backend: see [backend/README.md](backend/README.md)
- Frontend: see [frontend/README.md](frontend/README.md)
- Login/access-control setup: see [docs/ADMIN_SETUP.md](docs/ADMIN_SETUP.md) and [docs/LOGIN_INSTRUCTIONS.md](docs/LOGIN_INSTRUCTIONS.md)

`002-login-and-access-control` depends on infrastructure provisioned by
`007-azure-infrastructure-provisioning` (Cosmos DB account, Function App,
Static Web App, Managed Identity). Features that depend on
`002-login-and-access-control` include `008-core-gameplay`,
`005-story-publishing`, and `012-story-editing-and-review`.
