# Feature Specification: Local Offline Test Harness

**Feature Branch**: `027-local-offline-test-harness`

**Created**: 2026-09-12

**Status**: Draft

**Source**: [#308](https://github.com/RezaMahmood/llm-dungeon/issues/308)

**Input**: User description: "I want to make more use of local testing which will mean updating devcontainer to install dependencies that cannot currently be tested because they are hosted on azure."

---

## Why now

Constitution, *Environments & Deployment Pipeline*:

> Automated integration tests MUST run against a local stub or emulator of each external cloud dependency they exercise (e.g. the Azure Cosmos DB emulator) instead of a live Azure resource (Principle I). A dependency with no viable stub MUST be called out explicitly in that feature's plan, with a documented fallback.

This is an outstanding obligation, not a new proposal. Today the backend suite
substitutes its dependencies at the Python object level — ten separate hand-written
`FakeContainer` / `FakeCosmosService` classes across `src/backend/tests/unit` and
`src/backend/tests/integration`, with handler functions invoked directly rather than
through the Functions host. The frontend substitutes above the HTTP layer: 43 test files
call `vi.mock`, 31 of them replacing `@azure/msal-react`, and exactly one mocking
`axios`.

That tier is fast and worth keeping. But no current test executes a line of Cosmos SQL,
a route registration, a JWT signature check, or an axios interceptor — which is
precisely the set of things that only fail once deployed.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Authorized code paths run without an interactive sign-in (Priority: P1)

A contributor runs the backend suite on a laptop with no `az login` session and no
network. Tests that exercise authorized endpoints obtain a synthetic token from a local
issuer, and `auth_service` validates its signature, expiry, issuer and audience for
real.

**Why this priority**: Every other story depends on it — an emulator-backed or
host-backed test still needs an accepted token to reach the code under test. It is also
the smallest change here and introduces no new infrastructure.

**Independent Test**: Disable networking, run `pytest src/backend/tests`, and confirm
the suite completes with no `DefaultAzureCredential` or `login.microsoftonline.com`
traffic.

**Acceptance Scenarios**:

1. **Given** no Azure credentials are available, **When** the suite runs, **Then** every test passes and no outbound network call is attempted.
2. **Given** a token signed by a key absent from the local JWKS document, **When** it is presented to a protected endpoint, **Then** the request is rejected as unauthorized.
3. **Given** a token carrying the personal-Microsoft-account tenant id rather than the organizational one, **When** it is validated, **Then** it is accepted — covering the `config.valid_issuers()` path.
4. **Given** a token whose `aud` is the bare client id, and separately one whose `aud` is the `api://` form, **When** each is validated, **Then** both are accepted — covering `config.valid_audiences()` and the regression behind #212.
5. **Given** an expired token, **When** it is presented, **Then** the request is rejected.

---

### User Story 2 - Data-access tests run against a real database engine (Priority: P1)

Integration tests covering persistence run against a local Cosmos DB emulator rather
than an in-process dictionary, so Cosmos SQL, partition keys and ETag concurrency are
actually executed.

**Why this priority**: The highest-fidelity gain available. The object-level fakes are
least faithful exactly where the code is most subtle — optimistic-concurrency conflicts
and cross-partition queries — and #281 (unguarded read-modify-write against a concurrent
delete) is a live example of a defect class this tier would catch.

**Independent Test**: Start the emulator, run the persistence integration tests, and
confirm they exercise real query parsing and real `_etag` conflicts.

**Acceptance Scenarios**:

1. **Given** the emulator is running, **When** the integration suite runs, **Then** all six containers are provisioned by a shared fixture and the tests pass.
2. **Given** a document read at one ETag and modified by another writer, **When** a conditional replace is attempted with the stale ETag, **Then** the conflict surfaces as it would in the live account.
3. **Given** a query filtering on a non-partition-key field, **When** it executes cross-partition, **Then** it returns correct results and the SQL is genuinely parsed.
4. **Given** the emulator is not running, **When** the suite runs, **Then** emulator-backed tests are cleanly skipped with a message naming how to start it — never silently passing.

---

### User Story 3 - LLM failure modes are reproducible on demand (Priority: P2)

Tests drive the real `llm_service` client path against a local endpoint that can be told
to return a rate-limit response, a content-filter refusal, malformed JSON, or a normal
completion with a chosen token usage.

**Why this priority**: `llm_service.py` contains retry-with-backoff,
`LLMContentFilteredError` mapping, `LLMOutputError` mapping, cost computation from
reported usage, and a shared-event-loop mechanism — none of which an object-level mock of
the service exercises. These paths are currently reachable only by a live Foundry
misbehaving.

**Independent Test**: Point the client at the local endpoint, request each scenario, and
assert the mapped exception, retry count, and span attributes.

**Acceptance Scenarios**:

1. **Given** the stub returns HTTP 429 twice then succeeds, **When** a generation call is made, **Then** it retries with backoff and ultimately returns the completion.
2. **Given** the stub returns HTTP 429 on every attempt, **When** a call is made, **Then** the caller sees a rate-limit error rather than an unhandled 500.
3. **Given** the stub returns a content-filter refusal, **When** a gameplay turn is submitted, **Then** `LLMContentFilteredError` is raised and the player content-safety standing is updated.
4. **Given** the stub returns text that is not valid JSON, or JSON missing a required key, **When** the response is parsed, **Then** `LLMOutputError` is raised.
5. **Given** the stub reports specific input and output token counts, **When** the call completes, **Then** the span carries matching `gen_ai.usage.*` values and a `gen_ai.cost_usd` computed from the configured prices.

---

### User Story 4 - The whole application runs offline over HTTP (Priority: P1)

A contributor starts the SPA and the API locally and uses the app end to end — browsing
stories, starting a session, taking turns — with no Azure resource involved, and can open
every principal view in a browser to inspect and iterate on the UI.

**Why this priority**: Two distinct payoffs, and the second is a first-class goal rather
than a side effect. It is the first point at which "run the app offline" is true rather
than only "run the tests offline", and it brings the Functions host's own behaviour under
test: route registration, method handling, app-settings loading, and the
`src/`-as-package-root layout the deploy actually uses. It is also the only way to render
the real UI, with real data, for visual inspection and design iteration — including
running design tooling against the running app — without standing up an Azure resource or
hand-editing component fixtures.

**Note on ordering**: P1 states the value, not the position. This story depends on US1
for an accepted token, on a real data store for content, and on US3 for turn responses,
so it stays at phase 4 in the sequencing below. Those phases are its prerequisites, not
competing priorities.

**Independent Test**: Start the local stack, open the SPA in a browser, sign in through
the synthetic identity, complete a full play loop, and load each principal view with the
seed fixture in place.

**Acceptance Scenarios**:

1. **Given** the local stack is running, **When** a request is made to a registered route, **Then** it is served by the real host with the same path and method contract as the deployed app.
2. **Given** a request to an unregistered path, **When** it is made, **Then** the host returns 404 rather than the SPA's fallback document.
3. **Given** a deep link into a client-side route, **When** it is loaded directly, **Then** SPA fallback serves the app — and the `/api/*` and `redirect.html` exclusions in `staticwebapp.config.json` are honoured.
4. **Given** the SPA obtains a synthetic token, **When** it calls the API, **Then** the backend validates that token's signature for real and authorizes the request.
5. **Given** the local stack is seeded with the fixture dataset, **When** each principal view is opened in a browser — story list, session start, an in-progress turn, and the error states — **Then** each renders populated, representative content, with no Azure resource involved.

---

### User Story 5 - Frontend tests exercise the HTTP boundary (Priority: P3)

Component and integration tests in the SPA stub network responses rather than replacing
whole service modules, so the axios layer runs.

**Why this priority**: Of 43 mocking test files only one mocks `axios`, which leaves
`tokenInterceptor.js`, bearer-header attachment, and error-to-UI mapping effectively
untested. Cheap to close, and independent of every other story — but it changes no
production behaviour, so it ranks below the tiers that do.

**Independent Test**: Replace service-module mocks with request-level stubs in a
representative test and confirm the interceptor runs.

**Acceptance Scenarios**:

1. **Given** a stubbed API response, **When** a component fetches data, **Then** the request carried an `Authorization: Bearer` header attached by the real interceptor.
2. **Given** the API returns 401, **When** a component fetches data, **Then** the SPA surfaces the same behaviour it would against the live API.
3. **Given** the API returns a 5xx or a network failure, **When** a component fetches data, **Then** the user-facing error state matches the specified behaviour.

---

### Edge Cases

- The emulator image has no build for this host's architecture (the primary checkout and its devcontainers run on arm64). The fallback must be decided in `plan.md`, not discovered mid-implementation.
- The emulator is not running, is still starting, or its port is already taken — tests must skip or fail with an actionable message, never hang and never pass vacuously.
- The emulator presents a self-signed certificate; how TLS verification is handled must be deliberate and confined to test configuration.
- A contributor has a stale `local.settings.json` from an earlier revision — the local stack should report the missing setting by name rather than fail obscurely.
- Emulator state leaks between tests, making them order-dependent.
- The devcontainer needs to launch sibling containers; the current configuration has no Docker access.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The backend test suite MUST run to completion with no outbound network access and no Azure credentials of any kind.
- **FR-002**: Tests MUST be able to mint a synthetic identity whose token is validated by the real token-validation path — signature, expiry, issuer and audience — rather than bypassing validation.
- **FR-003**: The synthetic identity MUST carry no real credentials and MUST NOT correspond to any address on the live allow-list (Constitution, *Security & Access Control*).
- **FR-004**: The synthetic-identity path MUST be gated by a build-time or deploy-time condition structurally absent from the live build — a module the deployed package never imports, or a build mode the deploy never selects — never a runtime environment variable or request header (Constitution, *Security & Access Control*).
- **FR-005**: Live sign-in and server-side authorization MUST retain no disable path, flag or override of any kind after this work.
- **FR-006**: Integration tests covering persistence MUST execute against a local database engine that genuinely parses the queries, enforces partition keys, and implements ETag-conditional writes.
- **FR-007**: The existing object-level fakes MUST be retained for the fast unit tier; the emulator tier is additive, not a replacement.
- **FR-008**: The ten duplicated `FakeContainer` / `FakeCosmosService` definitions SHOULD be consolidated into one shared fixture as part of this work.
- **FR-009**: Tests MUST be able to reproduce, on demand and deterministically, each LLM failure mode the backend maps: rate limiting, content-filter refusal, malformed or incomplete output, and a completion reporting chosen token usage.
- **FR-010**: A contributor MUST be able to run the SPA and the API locally, over HTTP, with SPA fallback routing and API proxying behaving as the deployed hosting does.
- **FR-011**: Frontend tests MUST be able to stub at the network boundary so the real HTTP client, its interceptors and its error mapping execute.
- **FR-012**: The devcontainer MUST provide every dependency the above requires, installed at build time, so a fresh container can run the full local suite with no manual setup step.
- **FR-013**: Where a substitute is unavailable or a stub cannot be launched, the affected tests MUST skip with a message naming the missing dependency and how to start it — and MUST NOT pass vacuously.
- **FR-014**: Tests that require live Azure MUST be explicitly marked and deselected from a default local run, rather than relying on an incidental failure to skip themselves.
- **FR-015**: Every dependency with no viable local substitute MUST be named in `plan.md` with its documented fallback (Constitution, *Environments & Deployment Pipeline*).
- **FR-019**: A contributor MUST be able to render the running SPA against the local stack in a browser and reach every principal view — story list, session start, an in-progress turn, and the error states — so the UI can be inspected and iterated on visually, and design tooling pointed at it, with no Azure resource involved.
- **FR-020**: The local stack MUST be seedable with a deterministic fixture dataset sufficient to populate those views, by one documented command, and re-seedable back to a known state. An empty store is not sufficient for FR-019.

### Seams required in production code

Most substitutes plug into injection points that already exist — `CosmosService` and
`EntraDirectoryService` accept injected clients, and `AuthService` accepts `jwks_uri` /
`issuer` / `audience` overrides. The exceptions:

- **FR-016**: The LLM client factory MUST accept an injected credential and endpoint, matching the constructor seam `CosmosService` already provides. (`llm_service._shared_client()` currently calls `shared_credential()` internally and caches on endpoint alone.)
- **FR-017**: The Microsoft Graph base URL MUST be configuration-sourced rather than a module constant, so a local substitute is reachable. (`entra_directory_service._GRAPH_BASE_URL`.)
- **FR-018**: The Functions host's local settings file MUST be provided as a committed example plus a gitignored working copy, alongside the existing `src/backend/.env.example`.

### Key Entities

- **Synthetic identity**: a test-only principal with an email, object id and role set, used to obtain tokens the real validation path accepts. Carries no real credentials.
- **Local token issuer**: holds a keypair generated per session, publishes the corresponding public key document, and mints tokens with caller-chosen claims.
- **Scenario-keyed LLM stub**: maps a requested scenario to a canned response or failure, so a test names the behaviour it wants rather than reaching into client internals.
- **Emulator fixture**: provisions the six containers and isolates state between tests.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With networking disabled and no Azure credentials present, the backend suite runs to completion and passes.
- **SC-002**: No test in the default local run requires `az login`, a service principal, or any stored secret.
- **SC-003**: Every persistence integration test that today asserts against an in-process dictionary instead asserts against a real database engine, with no loss of coverage.
- **SC-004**: Each of the LLM error paths named in FR-009 is covered by at least one test that drives the real client, where today none are.
- **SC-005**: The bearer-token interceptor and HTTP error mapping in the SPA are covered by tests that execute the real HTTP client.
- **SC-006**: A contributor can complete a full play loop — browse, start a session, take a turn — against the local stack with no Azure resource involved.
- **SC-007**: A freshly built devcontainer runs the full local suite with no manual installation step.
- **SC-008**: Every dependency in the inventory is either substituted locally or named in `plan.md` with its fallback; none is left unaccounted for.
- **SC-009**: Every principal view of the SPA can be loaded and visually inspected against the local stack, populated by the seed fixture — including the views whose content depends on an LLM response — with no Azure resource involved.

## Assumptions

- Candidate substitutes are recorded here as inputs to `plan.md`, not as decisions: the Cosmos DB Emulator (Linux `vnext-preview` image) for the database; Azure Functions Core Tools v4 with Azurite for the host; the Static Web Apps CLI for hosting and API proxying; a locally generated keypair with a JWKS endpoint for tokens; a scripted OpenAI-compatible HTTP server for the LLM; MSW for the SPA. `plan.md` selects and justifies.
- The devcontainer will need Docker access to launch sibling containers. It currently has none.
- The host architecture is arm64. Any image without an arm64 build needs an explicit fallback decision in `plan.md`.
- **No local large-language-model runtime is in scope.** The scripted LLM endpoint of US3 is the only substitute, and it serves both purposes: its canned, deterministic responses drive the failure-mode tests, and they are equally sufficient for hand-play and for visual work, where reproducible prose is an advantage rather than a limitation. Ollama and equivalents are explicitly excluded — nondeterministic output, none of the failure modes in FR-009, and a further heavyweight devcontainer dependency for no coverage or design gain. Real prompt and output-quality work stays with post-ship playtesting (Constitution Principle IX).
- Existing injection points in `CosmosService`, `EntraDirectoryService` and `AuthService` are sufficient and do not need redesigning.
- No additional persistent environment is created (Constitution Principle XII). Everything here runs on a contributor's machine or in CI.

## Live-only fallbacks

Named here per FR-015; to be carried into `plan.md`.

| Not substitutable | Covered instead by |
|---|---|
| Terraform apply and ARM resource shape | Existing post-apply tests in `infrastructure/tests`; offline `fmt`/`validate`, static linting, and provider-mocked unit tests for locals and module wiring |
| Private endpoints and VNet reachability | `test_private_connectivity.py`. Unobservable locally by construction — every local substitute is reachable on purpose |
| RBAC role assignments for Managed Identity | A named deploy smoke check. The local credential always succeeds, so a missing data-plane role stays invisible until deploy |
| The app registration's token configuration (the `aud` form behind #212) | The existing deploy smoke test against `/api/auth/me` |
| Flex Consumption cold start, always-ready scheduling, Oryx remote build | Live observation; out of scope for local testing |
| Real LLM output quality and prompt behaviour | Post-ship playtesting (Constitution Principle IX) — correctly not an automated test |

## Out of scope

- Any change to deployed runtime behaviour beyond the seams in FR-016 to FR-018.
- Replacing or retiring the existing object-level unit-test tier.
- A staging or QA environment of any kind.
- CI topology changes. Whether the emulator tier also runs in GitHub Actions is a `plan.md` question, not a requirement here.
- Any local large-language-model runtime (Ollama or equivalent) — see Assumptions.
- Test coverage for features not already shipped.

## Suggested sequencing

Each phase is independently mergeable and makes the next cheaper.

1. Synthetic identity, fake credential, the `llm_service` credential seam, and the live-test marker (US1, FR-014, FR-016).
2. Cosmos emulator, shared fixture, and the highest-value integration tests moved onto it — ETag conflicts and cross-partition queries first (US2).
3. Scripted LLM endpoint covering the failure modes (US3).
4. Functions host, storage emulator and hosting emulator, plus the seed fixture, for a full local stack over HTTP (US4, FR-019, FR-020). This is the earliest phase at which the app is visualisable locally; phases 1 to 3 are hard prerequisites for it.
5. Network-boundary frontend tests, then browser end-to-end against the local stack (US5).

## Review tier

`/code-review ultra`, on the blast-radius rule: this touches authentication, the
devcontainer and `bin/`-adjacent tooling, and CI-relevant test configuration. The
constitution additionally requires that any change touching the automation bypass or the
Entra ID sign-in path receive the deepest tier, with the reviewer explicitly confirming
the bypass is unreachable from the live environment.
