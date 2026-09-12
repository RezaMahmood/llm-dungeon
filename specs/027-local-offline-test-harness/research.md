# Phase 0 Research: Local Offline Test Harness

**Branch**: `027-local-offline-test-harness` | **Date**: 2026-09-12

**Input**: [`spec.md`](./spec.md) — the spec records candidate substitutes as *inputs*;
this document selects and justifies. Every "Assumptions" bullet and every Edge Case in
the spec that says "decided in `plan.md`" is resolved here.

Verified against the repository at `04388ab` and against vendor documentation retrieved
2026-09-12. Where a decision could not be verified by execution inside this container
(no Docker socket, no `func`, no `swa` — see D2), it is marked **unverified** and carries
a spike task and a named fallback rather than an assertion.

---

## D1 — Cosmos DB substitute: the vNext Linux emulator, HTTP mode

**Decision**: `mcr.microsoft.com/cosmosdb/linux/azure-cosmos-emulator:vnext-latest`,
started with `--protocol http`, gateway on `:8081`, readiness gated on the health probe
at `:8080/ready`.

**Rationale**:

- The vNext emulator reached **general availability in June 2026** and ships as a Docker
  image running on **both x64 and ARM64**. This closes the spec's first Edge Case — the
  arm64 host (`uname -m` reports `aarch64` here) needs no fallback, no VM, and no
  emulation layer.
- **HTTP mode dissolves the TLS Edge Case entirely.** The emulator's default protocol is
  HTTP; only the .NET and Java SDKs require HTTPS against it. This project's data access
  is the Python SDK (`azure-cosmos`), which is unaffected. Choosing HTTP means no
  self-signed certificate, no trust-store manipulation, and no `verify=False` anywhere —
  the spec's requirement that TLS handling be "deliberate and confined to test
  configuration" is met by having no TLS to handle.
- The health probe (`/alive`, `/ready`, `/status` on `:8080`) is a first-class readiness
  signal, which is what makes FR-013's "skip with an actionable message, never hang"
  implementable without polling heuristics.
- `ENABLE_INIT_DATA` + `.csh` seed scripts mounted at `/init` give a container-native
  seeding path, and a bind-mounted `/data` volume makes re-seeding to a known state a
  matter of deleting a directory (FR-020).

**Alternatives considered**:

- *Legacy Windows/Linux emulator* — x64 only, and the Linux build is unmaintained relative
  to vNext. Rejected on the arm64 constraint alone.
- *Testcontainers-managed lifecycle* — adds a dependency and a documented friction point
  (`Azure/azure-cosmos-db-emulator-docker#160`). A plain Compose service plus a readiness
  fixture is simpler and is what CI will use anyway (D9). Rejected per Principle XII.
- *Keeping the in-process dictionary fakes* — the status quo the spec exists to fix.

**Verified by the T001 spike** ([#315](https://github.com/RezaMahmood/llm-dungeon/issues/315)).
Two entries in the emulator's published feature matrix bore directly on US2's two headline
acceptance scenarios, and both were exercised against
`azure-cosmos-emulator:vnext-latest` (build `EN20260907`, image digest
`sha256:2db1f9e7…`, native arm64) in `--protocol http` mode with `azure-cosmos` 4.17.0,
on a container partitioned on `/id` — the shape `infrastructure/terraform/main.tf`
actually provisions.

| Emulator feature matrix entry | Bears on | Result |
|---|---|---|
| **Query partitioned collection in parallel — ⚠️ "Not yet implemented"** | US2 scenario 3 (cross-partition query) | ✅ **Works.** A `WHERE c.playerId = @p` filter on a non-partition-key field returned all 12 matches spread across 40 logical partitions, exactly; unchanged under `max_item_count=5` (forced paging), and `COUNT(1)` and `ORDER BY … DESC` are also correct cross-partition. The matrix entry is pessimistic for this workload |
| *(ETag-conditional replace is not listed either way; "Replace document" is ✅ Supported)* | US2 scenario 2 (ETag conflict), #281 | ✅ **Works.** A stale ETag with `MatchConditions.IfNotModified` raises `CosmosAccessConditionFailedError` (HTTP 412) — the exact exception `play_session_service.py` catches — while the current ETag is accepted. The full claim/release sequence behind #281 reproduces: the second concurrent claim gets 412 and the claim-holder's follow-up write still lands |

ETag-conditional writes were the single highest-value reason for this tier — scenario 2 is
the defect class behind #281 — so **T001 ran as a spike before any test was migrated onto
the emulator**. Both answers came back positive, so no fallback is taken and neither
becomes a permanent row in `plan.md`'s live-only table.

The spike also confirmed the two properties the tier is worth having for independently of
those scenarios: partition-key enforcement is real (a read with the wrong partition key
404s rather than succeeding) and SQL is genuinely parsed (malformed SQL is rejected 400).

**One fidelity difference found**: the emulator returns `_etag` as a bare GUID, where real
Cosmos returns a quoted string. The backend round-trips the value opaquely so nothing
breaks, but it is recorded in the live-only table because no local test may assert on an
ETag's *shape*.

**Fallback had the spike failed** (FR-015), retained for the record: ETag-conflict and/or
cross-partition coverage would have stayed on the object-level fakes for those specific
assertions, the gap recorded in the live-only table in `plan.md`, and the emulator tier
would still have taken everything else. The tier was not to be abandoned for a partial
gap.

---

## D2 — Docker access from the devcontainer: docker-outside-of-docker

**Decision**: add the `ghcr.io/devcontainers/features/docker-outside-of-docker:1` feature
to `.devcontainer/devcontainer.json`.

**Rationale**: confirmed absent today — `command -v docker` returns nothing inside this
container, which is the spec's last Edge Case. The outside-of-docker feature mounts the
host's Docker socket, so the emulator and Azurite start as **siblings** of the devcontainer
on the host daemon. `bin/wt` already requires a reachable host Docker daemon (it calls
`docker info` and `docker ps` before `devcontainer up`), so the daemon this feature talks
to is the one already in play — no new infrastructure, and no change to `bin/wt` itself.

**Alternatives considered**:

- *docker-in-docker* — requires a privileged container, nests a second storage driver, and
  pulls the ~1GB emulator image separately per worktree container. Sibling containers share
  the host's image cache across every worktree, which matters directly given one container
  per worktree.
- *Running the emulator on the host by hand* — fails FR-012 ("installed at build time, so a
  fresh container can run the full local suite with no manual setup step").

**Consequence**: port collisions between concurrently running worktree containers are now
possible, since siblings publish onto the *host's* port space. Addressed in D8.

---

## D3 — The Functions host on arm64: Core Tools v4 with a pinned Python 3.11

**Decision**: install Azure Functions Core Tools v4 (linux-arm64) plus a **Python 3.11**
interpreter via `uv python install 3.11`, and run `func start` against that interpreter.

**Rationale and the two constraints that shape it**:

1. **Architecture.** Core Tools `4.14.0` publishes `Azure.Functions.Cli.linux-arm64.zip`
   as a release asset, and the long-standing "package linux arm64" request against the
   Python worker (`Azure/azure-functions-python-worker#1643`) is **closed**, resolved by
   PR #1677. The current *Develop Azure Functions Locally* documentation carries no ARM64
   caveat. Older guidance (and several blog posts) still says Python function development
   is unsupported on ARM64; that guidance appears to predate the worker's arm64 build.
2. **Python version.** This is the constraint that actually bites, and it is not in the
   spec. The devcontainer image is `python:3-3.14-trixie` — **Python 3.14.7** — while
   production runs Python **3.11** (`infrastructure/terraform/terraform.tfvars`:
   `functions_python_version = "3.11"`) and CI pins **3.11**
   (`.github/workflows/test.yml`). The Functions Python worker supports a fixed set of
   versions; 3.14 is not among them. So "run the real host locally" requires a 3.11
   interpreter in the container regardless of architecture.

   `uv` is already installed by `.devcontainer/post-create.sh` and its cache is already a
   shared volume, so `uv python install 3.11` is a one-line, cached addition — and it has
   a second payoff the spec doesn't claim: **it aligns local test runs with the version CI
   and production actually use**, closing a gap where a 3.14-only failure (or a
   3.11-only failure) is invisible locally today.

**Unverified**: that `func start` successfully launches a Python 3.11 worker on linux-arm64
in this image. Neither `func` nor Docker is present to test it now. **T002 is a spike.**

**Fallback if the spike fails** (FR-015), in order of preference:

1. **In-process route-table harness** — drive the registered `FunctionApp` route table
   (`src/function_app.py` declares 25+ `@app.route(...)` registrations) through a thin
   WSGI adapter that builds `func.HttpRequest` objects from real HTTP requests. This keeps
   US4 acceptance scenarios 1, 2, 4 and 5 (route/method contract, 404 on unregistered
   paths, real token validation, seeded views) genuinely covered over real HTTP, and gives
   up only the host process itself — app-settings loading and worker startup. It is
   strictly more coverage than today, where handlers are called as plain functions.
2. **x86_64 Core Tools under QEMU emulation** in a sibling container. Real host, real
   worker, materially slower; acceptable for a pre-merge check, not for the inner loop.

Option 1 is the one to build if the spike fails, because it preserves the *daily* workflow;
option 2 exists so the host's own behaviour is not permanently unreachable.

---

## D4 — Storage for the Functions host: Azurite

**Decision**: Azurite (`npm i -g azurite`, or the `mcr.microsoft.com/azure-storage/azurite`
image alongside the emulator in Compose), providing `AzureWebJobsStorage`.

**Rationale**: the Functions host requires a storage connection even for an HTTP-only app.
Azurite is the first-party emulator, is pure Node (so architecture-independent — no arm64
question arises), and `UseDevelopmentStorage=true` is the documented connection string.
Nothing in this application's own code touches Blob/Queue/Table, so Azurite is host
scaffolding only and needs no fixtures.

---

## D5 — Hosting and API proxying: Static Web Apps CLI 2.x

**Decision**: `@azure/static-web-apps-cli` (2.0.10 at time of writing), run as
`swa start` fronting the Vite dev server and proxying `/api/*` to the Functions host.

**Rationale**: the SWA CLI is actively maintained (latest release ~2 months old; no
deprecation notice) and, critically, it **reads `staticwebapp.config.json`** — the very
file whose behaviour US4 acceptance scenarios 2 and 3 assert. `src/frontend/public/staticwebapp.config.json`
declares `navigationFallback.rewrite` with `/api/*`, `/redirect.html` and a static-asset
glob excluded. Any hand-rolled proxy would be asserting against a re-implementation of
that file's semantics rather than against the implementation the deployed hosting uses,
which would make those two scenarios worthless.

**Alternatives considered**: Vite's own `server.proxy` — proxies `/api` but implements no
`navigationFallback` exclusion semantics, so scenarios 2 and 3 would be untestable.
Rejected.

---

## D6 — Synthetic identity: an in-process issuer, and why this is not a bypass

**Decision**: a test-only module generates an RSA keypair per session, serves a JWKS
document over `http://127.0.0.1:<port>/keys` from a stdlib `http.server` thread, and mints
tokens with caller-chosen claims. Tests construct
`AuthService(jwks_uri=..., issuer=..., audience=...)` — the constructor overrides that
already exist (`src/backend/services/auth_service.py`).

**Rationale — this is the part a reviewer will scrutinise, so it is stated plainly**:

- **No production code changes, and nothing is disabled.** `AuthService.validate_token`
  runs unmodified: real signature verification, real `exp`, real issuer and audience
  checks. What changes is *which issuer's keys* a test points it at. There is no branch,
  flag, header, or environment variable that weakens validation — satisfying **FR-005**
  and the constitution's "live sign-in and server-side authorization MUST have no disable
  path, flag, or override of any kind."
- **The gate is structural** (**FR-004**). The issuer lives under
  `src/backend/tests/harness/`, which the deployed package does not contain and
  `function_app.py` never imports. There is no code path from a deployed module to it.
  For the US4 local stack, the pointer to the local issuer comes from
  `local.settings.json` — a gitignored file that the deploy pipeline never produces
  (FR-018) — not from a setting the live Function App could be misconfigured into.
- **No real credentials** (**FR-003**). The synthetic principal's email uses an
  `@invalid.` address per RFC 2606, which cannot be a real Microsoft account and therefore
  cannot appear on the live allow-list.
- `_shared_jwk_client` is already keyed by URI with the comment "so a test pointing at its
  own endpoint cannot poison the real one" — the design this decision needs was
  anticipated.
- **Coverage this unlocks, from the spec's own acceptance scenarios**: `config.valid_issuers()`
  (organizational *and* the `9188040d-…` consumers tenant) and `config.valid_audiences()`
  (bare client id *and* the `api://` form — the #212 regression). Both are pure functions
  today with no test that drives a real token through them.

**Alternatives considered**: patching `jwt.decode`, or a fixture returning a canned claims
dict. Both bypass the code under test, which is precisely the failure mode this feature
exists to end.

---

## D7 — LLM substitute: a scripted OpenAI-compatible endpoint, and the FR-016 seam

**Decision**: a stdlib HTTP server speaking the OpenAI chat-completions wire format,
selecting its behaviour from a scenario key supplied per request (via the model name or a
request header), so a test names the behaviour it wants. Scenarios: `ok`, `rate_limit_then_ok`,
`rate_limit_always`, `content_filter`, `malformed_json`, `missing_key`, `usage:<in>,<out>`.

**Rationale**: `llm_service.py` holds retry-with-backoff (`_get_response_with_retry`),
`openai.RateLimitError` mapping with `Retry-After` handling (`_retry_after_seconds`),
content-filter mapping (`_as_content_filter_error` → `LLMContentFilteredError`), output
parsing (`LLMOutputError`), cost computation, and a shared-event-loop mechanism
(`_shared_loop`). None of it is reachable through an object-level mock of the service. A
wire-level stub drives the **real** `OpenAIChatCompletionClient`, which is the only way
those paths execute.

**The required seam (FR-016)**: `_shared_client(endpoint)` calls `shared_credential()`
internally and caches on `endpoint` alone:

```python
def _shared_client(endpoint: str) -> OpenAIChatCompletionClient:
    client = _clients.get(endpoint)          # cache key: endpoint only
    ...  credential=shared_credential(), ...  # credential acquired internally
```

Two changes, mirroring the seam `CosmosService.__init__(endpoint=..., client=...)` already
provides: accept an injected credential, and include the credential's identity in the cache
key so an injected fake credential cannot be served a cached real-credential client (or
vice versa) for the same endpoint. `LLMService.__init__` already accepts `client` and
`endpoint`, so the public seam is nearly there; the gap is the module-level cache.

**Alternatives considered**: a local LLM runtime (Ollama or equivalent) — explicitly out of
scope per the spec, and correctly so: nondeterministic output, none of the failure modes in
FR-009, and a heavyweight dependency for no coverage gain.

---

## D8 — Isolation between concurrent worktrees

**Decision**: derive every published host port from the worktree's branch name (a short
hash → offset), and give the Compose project a per-worktree name.

**Rationale**: D2's sibling containers publish onto the host's port space, and this repo
runs **one container per worktree with several active at once** (constitution: *Development
Workflow & Quality Gates*). Two worktrees each hard-coding `:8081` collide — which the spec
lists as an Edge Case ("its port is already taken"), and which under the worktree workflow
is the *normal* case rather than an unlucky one. A derived offset plus a Compose project
name keeps each worktree's stack independently startable and independently disposable.

**Per-test isolation** (the "state leaks between tests, making them order-dependent" Edge
Case) is separate and handled in the fixture layer: a session-scoped fixture provisions the
database and the six containers once; a function-scoped fixture gives each test a unique
partition-key value, so tests never observe each other's documents without paying container
re-creation per test.

---

## D9 — CI topology: the emulator tier runs in GitHub Actions; the host tier does not (yet)

**Decision**: add the emulator as a **service container** to `.github/workflows/test.yml`
and run the emulator-backed tier there. The Core Tools / SWA / browser end-to-end tier stays
local-only for now.

**Rationale**: the spec leaves this open as "a `plan.md` question". Microsoft publishes a
reference repository demonstrating the emulator as a GitHub Actions service container for
Python on both x64 and ARM64 runners, and GitHub manages the container's lifecycle — so the
emulator tier costs one `services:` block and gains PR-gated enforcement, which Principle I
requires of tests that exist. The full-stack tier involves three long-lived processes plus a
browser and would materially change CI runtime for a workflow that currently just runs
pytest; it earns its place locally first (Principle XII — right-sized), and moving it to CI
later is additive.

---

## D10 — Frontend network-boundary stubbing: MSW 2.x

**Decision**: `msw` 2.x with `setupServer` wired into `src/frontend/tests/setup.js`
(`server.listen()` in `beforeAll`, `resetHandlers()` in `afterEach`, `close()` in `afterAll`).

**Rationale**: MSW intercepts at Node's `http` layer via `@mswjs/interceptors`, so axios,
its interceptors and its error mapping all execute for real — which is the whole point of
US5. It needs no service-worker file under Node/jsdom, and the existing `setup.js` is a
single line, so the wiring is additive and no existing test changes behaviour.

**A finding that changes US5's scope — `installTokenInterceptor` is dead code.**
`grep -rn "installTokenInterceptor" src/frontend/src src/frontend/tests` returns exactly one
hit: its own definition. It is **never installed on any axios instance**. Meanwhile every
service attaches the header by hand, and to a *different* header name:

```js
// src/frontend/src/services/tokenInterceptor.js — never called
requestConfig.headers.Authorization = `Bearer ${token}`;

// src/frontend/src/services/gameService.js — what actually ships
headers: { "X-Custom-Authorization": `Bearer ${token}` }
```

The difference is not cosmetic: `src/backend/api/auth/middleware.py:16` reads
`X-Custom-Authorization` precisely because "Static Web Apps overwrites the standard
`Authorization` header itself". So the uninstalled interceptor also attaches the header the
platform would clobber, and its 401-refresh-and-retry logic has never run in production.

This makes **SC-005 as written unsatisfiable** — "the bearer-token interceptor … covered by
tests that execute the real HTTP client" describes testing a function nothing calls. Three
options, and the plan takes the third:

1. *Wire the interceptor in* — changes deployed runtime behaviour, which the spec's Out of
   scope section forbids beyond FR-016–FR-018, and would need the header name fixed first.
2. *Test it in isolation* — satisfies the letter of SC-005 and none of its intent.
3. **Target SC-005 at the header attachment that actually ships**, cover the real 401 and
   5xx paths through MSW, and **raise the dead code and the header-name discrepancy as a
   separate issue** rather than fixing it under this feature.

Confirmed by the maintainer and recorded in `plan.md` as a settled deviation; the dead
code and header-name discrepancy are filed as
[#313](https://github.com/RezaMahmood/llm-dungeon/issues/313).
