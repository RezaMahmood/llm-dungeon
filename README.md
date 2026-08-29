# LLM Dungeon Adventure

A private, LLM-driven text adventure game. Backend: Python on Azure
Functions. Frontend: ReactJS. Access is restricted to an explicit allow-list
of Microsoft accounts (see [Constitution](.specify/memory/constitution.md)).

## Features

- [`001-ci-cd-foundation`](specs/001-ci-cd-foundation-done/spec.md) — CI test gate on every PR
- [`002-login-and-access-control`](specs/002-login-and-access-control-done/spec.md) — Microsoft Entra ID sign-in, allow-list, and Player/Administrator capabilities
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

- Backend: see [src/backend/README.md](src/backend/README.md)
- Frontend: see [src/frontend/README.md](src/frontend/README.md)
- Infrastructure (Terraform, CI/CD, bootstrap): see [docs/INFRASTRUCTURE.md](docs/INFRASTRUCTURE.md)
- Login/access-control setup: see [docs/ADMIN_SETUP.md](docs/ADMIN_SETUP.md) and [docs/LOGIN_INSTRUCTIONS.md](docs/LOGIN_INSTRUCTIONS.md)

`002-login-and-access-control` depends on infrastructure provisioned by
`007-azure-infrastructure-provisioning` (Cosmos DB account, Function App,
Static Web App, Managed Identity). Features that depend on
`002-login-and-access-control` include `008-core-gameplay`,
`005-story-publishing`, and `012-story-editing-and-review`.

## CI/CD Governance & Branch Protection

Per the project [Constitution](.specify/memory/constitution.md) and [`001-ci-cd-foundation`](specs/001-ci-cd-foundation-done/spec.md):
- **Pull Request Only**: Direct pushes to `main` are prohibited. All modifications must be submitted via pull requests.
- **Automated CI Test Gating**: Every PR automatically triggers the full automated test suite ([`.github/workflows/test.yml`](.github/workflows/test.yml)). PR merge is mechanically blocked until all status checks pass.
- **Code Review**: Pull requests require at least 1 approval before merging.
- **Contributing & Workflows**: See [CONTRIBUTING.md](CONTRIBUTING.md) and [CI/CD Troubleshooting Guide](docs/CI_CD_TROUBLESHOOTING.md).

