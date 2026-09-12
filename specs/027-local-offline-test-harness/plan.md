# Implementation Plan: Local Offline Test Harness

**Branch**: `027-local-offline-test-harness` | **Date**: 2026-09-12 | **Spec**: [`spec.md`](./spec.md)

**Input**: Feature specification from `specs/027-local-offline-test-harness/spec.md`

## Summary

Stand up local substitutes for every Azure dependency the test suite currently mocks at the
Python object level, so that Cosmos SQL, token validation, the Functions host, the LLM
client's failure mapping and the SPA's HTTP layer are actually executed rather than
stubbed over. The approach: the **GA vNext Cosmos emulator in HTTP mode** for data
(arm64-native, no TLS to manage), an **in-process JWKS issuer** driving the unmodified
`AuthService` for identity, a **scripted OpenAI-compatible endpoint** for the LLM, and
**Core Tools + Azurite + the SWA CLI** for a full offline stack — all reachable from the
devcontainer via **sibling containers** on the host Docker daemon. Three production seams
(FR-016 credential injection, FR-017 Graph base URL, FR-018 local settings) are the only
changes to shipped code. Phase 0 decisions and their evidence are in
[`research.md`](./research.md).

## Technical Context

**Language/Version**: Python 3.11 (production and CI target) — note the devcontainer
currently ships **3.14.7**; aligning it is a deliverable of this plan, not an assumption
(research.md D3). JavaScript / Node 24, React 19.

**Primary Dependencies**: *Existing* — `azure-functions`, `azure-cosmos`, `azure-identity`,
`agent-framework-openai`, `openai`, `PyJWT[crypto]`, `pytest`; `axios`, `@azure/msal-react`,
`vitest`. *Added by this feature (test/dev only)* — `msw` 2.x (npm, dev), Azurite (npm,
global), Azure Functions Core Tools v4 linux-arm64, `@azure/static-web-apps-cli` 2.x,
the Cosmos vNext emulator image. No new production runtime dependency.

**Storage**: Azure Cosmos DB (NoSQL), six containers named in `backend/config.py`
(`provisionedAccountEntries`, `storyDrafts`, `stories`, `playSessions`, `testPlaySessions`,
`playerContentSafetyStandings`). Locally: the vNext emulator, gateway over HTTP.

**Testing**: `pytest` (rooted at `pytest.ini`, `pythonpath = src`) in three tiers — the
existing object-level unit tier (retained unchanged, FR-007), a new emulator-backed
integration tier, and a new full-stack tier. `vitest` + `msw` for the SPA.

**Target Platform**: Linux containers on an **arm64** host (`aarch64` confirmed); the
devcontainer per worktree, plus sibling containers on the host daemon. Production is Azure
Functions Flex Consumption + Static Web Apps.

**Project Type**: Web application — Python Azure Functions backend, React SPA frontend.

**Performance Goals**: the existing object-level unit tier stays the inner loop and MUST
not slow down. The emulator tier targets a one-time session-scoped startup rather than
per-test container churn; no per-test wall-clock target is set, as none is a requirement.

**Constraints**: fully offline — no outbound network, no Azure credential, no `az login`
(FR-001/SC-002). arm64-only host. Concurrent worktree containers share the host's port
space (research.md D8). No new persistent environment (Principle XII).

**Scale/Scope**: ~25 registered HTTP routes, 6 Cosmos containers, 43 frontend test files,
10 duplicated `FakeContainer`/`FakeCosmosService` definitions to consolidate (FR-008).

## Constitution Check

*GATE: evaluated before Phase 0, re-evaluated after Phase 1 design (both recorded below).*

| Constitution requirement | Assessment | Status |
|---|---|---|
| **I — Meaningful, Automated Testing**; *Environments*: integration tests run against local stubs/emulators, and any dependency with no viable stub is named in the plan with a fallback | This feature is the direct discharge of that obligation. Every unsubstitutable dependency is named in *Live-only fallbacks* below, with its fallback. | ✅ PASS |
| **II — Secure-by-Default Access**; *Security*: the local bypass MUST be gated structurally, never by a runtime env var or header; live sign-in MUST have no disable path | There is **no bypass**. `AuthService.validate_token` is unmodified and always validates in full; tests point its existing `jwks_uri`/`issuer`/`audience` constructor overrides at a local issuer. The issuer module lives in `src/backend/tests/harness/`, which the deployed package does not contain and `function_app.py` never imports — a structural gate (research.md D6). | ✅ PASS |
| *Security*: the automation identity carries no real credentials and is not on the live allow-list | Synthetic principal uses an RFC 2606 `@invalid.` address, which cannot be a real Microsoft account (FR-003). | ✅ PASS |
| **III — Defined Technology Stack** | No stack change. Every addition is a test/dev dependency; the one version move (Python 3.14 → 3.11 locally) brings local *into* line with the declared production runtime. | ✅ PASS |
| **IV / XII — Simplicity, Right-Sized Scope** | First-party emulators throughout; no Testcontainers, no local LLM runtime, no orchestration framework. The full-stack tier stays local before it earns CI (research.md D9). | ✅ PASS |
| **VII — Zero-Trust Azure Communication** | Untouched. The credential seam (FR-016) *adds* an injection point; `shared_credential()` remains the production default. No key or connection string is introduced into production code. | ✅ PASS |
| **X — PII Protection** | The seed fixture (FR-020) uses synthetic personas only; no real address reaches a fixture, a log, or this plan. | ✅ PASS |
| **XII — No additional persistent environment** | Everything runs on a contributor's machine or an ephemeral CI service container. | ✅ PASS |
| **XIII — AI agent division of labor** | Claude implements and opens PRs per phase; the user reviews and merges. | ✅ PASS |
| *Dependency & Supply Chain*: official registries, pinned by committed lockfile | All additions come from npm / PyPI / MCR. Image tags and CLI versions pinned explicitly, not floating (see *Known limits*). | ✅ PASS |
| *Workflow*: deepest review tier for auth, CI/CD, `bin/`, `.claude/`, infrastructure | `/code-review ultra` is the plan's recommended tier for every phase that touches identity or the devcontainer (see below). | ✅ PASS |

**Post-Phase-1 re-evaluation**: no new violation introduced by the Phase 1 design. The
contracts in [`contracts/`](./contracts/) are test-harness interfaces only — none is an
endpoint the deployed application serves, and none alters an existing contract. The one
item requiring a decision from the user is a **spec deviation, not a constitution
violation** (SC-005, below). **Gate: PASS.**

## Project Structure

### Documentation (this feature)

```text
specs/027-local-offline-test-harness/
├── plan.md              # This file
├── research.md          # Phase 0 — the ten decisions and their evidence
├── data-model.md        # Phase 1 — harness entities and the seed fixture
├── quickstart.md        # Phase 1 — runnable validation scenarios
├── contracts/           # Phase 1 — harness interface contracts
│   ├── local-token-issuer.md
│   ├── llm-stub.md
│   └── local-stack.md
└── tasks.md             # Phase 2 — NOT created by /speckit-plan
```

### Source Code (repository root)

```text
.devcontainer/
├── devcontainer.json           # + docker-outside-of-docker feature, forwarded ports
└── post-create.sh              # + uv python 3.11, Core Tools, Azurite, SWA CLI

src/
├── host.json                   # existing — Functions host config at the package root
├── function_app.py             # existing — 25+ @app.route registrations
├── local.settings.json.example # NEW (FR-018) — committed template
├── local.settings.json         # NEW (FR-018) — gitignored working copy
├── backend/
│   ├── config.py               # + GRAPH_BASE_URL (FR-017)
│   ├── services/
│   │   ├── llm_service.py      # + injected credential, credential-aware cache (FR-016)
│   │   └── entra_directory_service.py  # _GRAPH_BASE_URL -> config (FR-017)
│   └── tests/
│       ├── conftest.py         # existing OTel/`_story` fixtures — extended, not replaced
│       ├── harness/            # NEW — the substitutes themselves
│       │   ├── identity.py     #   keypair, JWKS server, token minting (US1)
│       │   ├── cosmos.py       #   emulator readiness, provisioning, isolation (US2)
│       │   ├── llm_stub.py     #   scenario-keyed OpenAI-compatible server (US3)
│       │   ├── credentials.py  #   the fake TokenCredential (FR-016)
│       │   └── fakes.py        #   the ONE consolidated FakeContainer/FakeCosmosService (FR-008)
│       ├── unit/               # existing tier — retained unchanged (FR-007)
│       └── integration/        # existing tier — migrated onto the emulator behind a marker
└── frontend/
    ├── tests/
    │   ├── setup.js            # + MSW setupServer lifecycle
    │   └── msw/handlers.js     # NEW — network-boundary handlers (US5)
    └── ...

tools/local-stack/              # NEW — the offline stack (US4)
├── docker-compose.yml          #   cosmos emulator + azurite, per-worktree project name
├── ports.sh                    #   branch-derived port offsets (research.md D8)
├── seed.py                     #   deterministic fixture dataset (FR-020)
└── README.md

pytest.ini                      # + `emulator` / `live` markers, default deselection (FR-014)
.github/workflows/test.yml      # + emulator service container (research.md D9)
```

**Structure Decision**: the existing web-application layout is kept exactly as it is. Test
substitutes are additive under `src/backend/tests/harness/`, deliberately *inside* the test
package so that FR-004's structural gate is a property of the directory layout rather than
of a runtime check. The local stack lives in `tools/local-stack/` rather than `bin/`,
because `bin/` is the worktree-lifecycle entrypoint surface and adding a second, unrelated
concern to it widens a blast-radius directory for no benefit.

## Sequencing

Phases follow the spec's *Suggested sequencing*; each is independently mergeable. Two spikes
gate the phases whose viability is unverified (research.md D1, D3) — **their purpose is to
fail cheaply before the phase is built, so neither may be folded into the phase it guards.**

| Phase | Delivers | Gated by | Review tier |
|---|---|---|---|
| **0** | **Spike T001** — ETag-conditional replace and cross-partition query against the emulator | — | none (throwaway) |
| **0** | **Spike T002** — `func start` with a Python 3.11 worker on linux-arm64 | — | none (throwaway) |
| **1** | Devcontainer: Docker access, Python 3.11, Core Tools, Azurite, SWA CLI (FR-012) | — | `ultra` — `.devcontainer/`, blast radius |
| **2** | Synthetic identity, fake credential, FR-016 seam, `live`/`emulator` markers (US1, FR-014) | — | `ultra` — authentication |
| **3** | Emulator fixture, `fakes.py` consolidation, integration tests migrated (US2, FR-008) | T001, ph. 1 | `high` |
| **4** | Scripted LLM endpoint and the failure-mode tests (US3) | ph. 2 | `high` |
| **5** | Functions host + Azurite + SWA CLI + seed fixture (US4, FR-017–020) | T002, ph. 1–4 | `ultra` — CI/infra-adjacent |
| **6** | MSW network-boundary frontend tests (US5) | — (independent) | `/code-review` |

Phase 6 depends on nothing and may be taken at any point.

## Live-only fallbacks

Required by **FR-015** and by the constitution's *Environments & Deployment Pipeline*.
Carried from the spec, plus four rows this plan adds.

| Not substitutable locally | Covered instead by |
|---|---|
| Terraform apply and ARM resource shape | Existing `infrastructure/tests`; offline `fmt`/`validate` and provider-mocked unit tests |
| Private endpoints and VNet reachability | `test_private_connectivity.py`. Unobservable locally by construction — every local substitute is reachable on purpose |
| RBAC role assignments for Managed Identity | A named deploy smoke check. The local fake credential always succeeds, so a missing data-plane role stays invisible until deploy |
| The app registration's `aud` form (#212) | The existing deploy smoke test against `/api/auth/me` — note the *validation* of both forms is now covered locally (US1 scenario 4); what stays live-only is which form Entra actually stamps |
| Flex Consumption cold start, always-ready scheduling, Oryx remote build | Live observation; out of scope |
| Real LLM output quality and prompt behaviour | Post-ship playtesting — correctly not an automated test |
| **Microsoft Graph guest invite/remove** (added) | FR-017 makes the base URL configurable so a local substitute is *reachable*, but Graph's own invitation semantics are not reproduced. Existing `test_entra_directory_service.py` covers request shaping; real invitation flow stays live-only |
| **Azure Monitor / Application Insights export** (added) | Already covered locally by the in-memory OTel exporters in `tests/conftest.py`. The exporter's wire behaviour to Azure Monitor stays live-only |
| **Cosmos cross-partition parallel query** (added, *conditional*) | Emulator lists this as "not yet implemented". If T001 confirms, those assertions stay on the object-level fakes and are named here permanently |
| **Cosmos ETag-conditional replace** (added, *conditional*) | Not listed in the emulator's feature matrix either way. If T001 shows it unsupported, US2 scenario 2 — the #281 defect class — stays on the object-level fakes, and this becomes a permanent row |

## Known limits and follow-ups

- **Two decisions are unverified** (research.md D1, D3) because neither Docker nor `func`
  exists in this container yet. Both carry a named fallback and a gating spike. They are
  stated as risks, not as working solutions.
- **Version pinning**: the emulator image tag, Core Tools version and SWA CLI version must
  be pinned at implementation time (supply-chain requirement). `vnext-latest` is the
  documented tag but is floating; pin the digest or a dated tag.
- **`installTokenInterceptor` is dead code** — see the deviation below. Filed as
  [#313](https://github.com/RezaMahmood/llm-dungeon/issues/313); not fixed under this feature.
- **Python 3.14 → 3.11 locally** is a side effect of D3 with independent value (local now
  matches CI and production), but it *is* a change to every contributor's environment and
  could surface latent 3.11-vs-3.14 differences in the existing suite. Phase 1 should run
  the full existing suite on 3.11 before anything else lands.

## Spec deviation (decided)

**SC-005** — "The bearer-token interceptor and HTTP error mapping in the SPA are covered by
tests that execute the real HTTP client" — cannot be satisfied as written.
`installTokenInterceptor` is **never called anywhere in `src/frontend/src`**; the services
attach `X-Custom-Authorization` by hand instead, and the uninstalled interceptor sets the
plain `Authorization` header that Static Web Apps is documented to overwrite
(`src/backend/api/auth/middleware.py:16`). Testing it would be testing dead code.

**Decision**: SC-005 is read as covering the header attachment and error mapping that
actually ship. Phase 6 covers those through MSW; the dead code and the header-name
discrepancy are tracked separately as **[#313](https://github.com/RezaMahmood/llm-dungeon/issues/313)**
and are **out of scope here**, since installing or deleting the interceptor would change
deployed runtime behaviour — which this feature's spec excludes beyond FR-016–FR-018.

## Complexity Tracking

No constitution violation requires justification. The table is intentionally empty.
