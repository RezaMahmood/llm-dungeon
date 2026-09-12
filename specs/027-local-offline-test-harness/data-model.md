# Phase 1 Data Model: Local Offline Test Harness

**Branch**: `027-local-offline-test-harness` | **Date**: 2026-09-12

The entities here are **test-harness constructs and fixture data**, not application domain
models. This feature adds no persisted schema and changes no existing model — the
application's entities (`Story`, `PlaySession`, `TestPlaySession`,
`PlayerContentSafetyStanding`, `StoryDraft`, `ProvisionedAccountEntry`) are untouched,
and their definitions stay authoritative in `src/backend/models/`.

Three of the four entities below are named in the spec's *Key Entities*; the fourth
(**Fake credential**) is required by the FR-016 seam.

---

## 1. Synthetic identity

*Spec: "a test-only principal with an email, object id and role set… Carries no real
credentials."*

| Field | Type | Rules |
|---|---|---|
| `oid` | str (UUID) | Stable per persona, so a document written by one call is readable by the next |
| `email` | str | **MUST** end in a reserved non-resolvable domain (RFC 2606 `.invalid`). Enforced by an assertion in the harness, not by convention — FR-003 |
| `name` | str | Display name; synthetic persona only (Principle X) |
| `roles` | tuple[str, …] | Drawn from the roles the app already recognises (admin / player) |
| `tid` | str | Either `config.AZURE_TENANT_ID` or `config.MICROSOFT_CONSUMERS_TENANT_ID` — selecting between them is what exercises `config.valid_issuers()` (US1 scenario 3) |

**Validation rule (FR-003, enforced)**: constructing a synthetic identity whose `email`
does not end in `.invalid` raises. This is the mechanism that makes "MUST NOT correspond to
any address on the live allow-list" a property of the code rather than a promise.

**Standard personas**: `ADMIN` (admin role, organizational `tid`), `PLAYER` (player role,
organizational `tid`), `CONSUMER_PLAYER` (player role, consumers `tid`), `UNKNOWN` (valid
token, no allow-list entry — drives the existing `test_unauthorized_user.py` path against a
real token for the first time).

---

## 2. Local token issuer

*Spec: "holds a keypair generated per session, publishes the corresponding public key
document, and mints tokens with caller-chosen claims."*

| Field | Type | Notes |
|---|---|---|
| `private_key` / `public_key` | RSA 2048 keypair | Generated **per session**, never written to disk, never committed |
| `kid` | str | Key id; published in the JWKS and stamped into every minted token's header |
| `jwks_uri` | str | `http://127.0.0.1:<port>/keys` — passed to `AuthService(jwks_uri=…)` |
| `issuer` | str | Mirrors the real issuer shape, `…/{tid}/v2.0` |

**State transition** — the only one in this document, and it is what US1 scenario 2 turns on:

```
[keypair A generated] → tokens signed by A  → JWKS publishes A → validation SUCCEEDS
        │
        └─ rotate() → keypair B, JWKS publishes B only
                    → a token still signed by A → validation FAILS (unknown kid)
```

`rotate()` is how "a token signed by a key absent from the local JWKS document is rejected"
is tested without hand-forging a bad signature. Note that `AuthService` caches signing keys
process-wide for `JWKS_CACHE_SECONDS` (24h) keyed by URI — so a rotation test **must** use a
fresh `jwks_uri` (a new port or path) rather than expecting the cache to notice. This is a
real constraint on the fixture design, not an incidental detail.

**Minting parameters** (all defaulted, all overridable — each maps to a US1 acceptance
scenario): `identity`, `audience` (bare client id *or* `api://…` — scenario 4),
`issuer` (organizational *or* consumers — scenario 3), `expires_in` (negative for an expired
token — scenario 5), `key` (a foreign key — scenario 2).

---

## 3. Scenario-keyed LLM stub

*Spec: "maps a requested scenario to a canned response or failure, so a test names the
behaviour it wants rather than reaching into client internals."*

| Field | Type | Notes |
|---|---|---|
| `scenario` | enum | The key a caller names — see the table below |
| `remaining_failures` | int | Mutable per scenario instance; how `rate_limit_then_ok` stops failing |
| `input_tokens` / `output_tokens` | int | Echoed in the response's `usage` block, so the span's `gen_ai.usage.*` and `gen_ai.cost_usd` are computed from a value the test chose (US3 scenario 5) |
| `body` | str \| dict | The completion payload — valid JSON, invalid JSON, or JSON missing a required key |

| Scenario | Wire behaviour | Exercises |
|---|---|---|
| `ok` | 200, well-formed completion | Happy path, cost computation |
| `rate_limit_then_ok` | 429 × N, then 200 | `_get_response_with_retry` backoff (US3-1) |
| `rate_limit_always` | 429 on every attempt | Retry exhaustion → rate-limit error (US3-2) |
| `content_filter` | 400 with the content-filter error shape | `_as_content_filter_error` → `LLMContentFilteredError` (US3-3) |
| `malformed_json` | 200, body is not JSON | `LLMOutputError` (US3-4) |
| `missing_key` | 200, valid JSON missing a required key | `LLMOutputError` (US3-4) |

The `retry_after` seconds value is settable per scenario so `_retry_after_seconds`'s
header-parsing branch is driven rather than left to its fallback.

---

## 4. Fake credential (FR-016)

Not in the spec's *Key Entities*, but the FR-016 seam has no meaning without it.

A minimal object satisfying the `TokenCredential` protocol — `get_token(*scopes, **kwargs)`
returning a static `AccessToken` with a far-future expiry. It performs **no** network call,
which is what makes SC-001 ("no outbound call attempted") true rather than merely
unobserved.

**Cache-key rule**: `llm_service._shared_client` currently caches on `endpoint` alone. Once
a credential can be injected, the cache key must include the credential's identity —
otherwise the first test to construct a client for an endpoint pins that endpoint's client
(and its credential) for every later test in the process. This is the kind of ordering bug
that presents as "passes alone, fails in the suite", so it is called out here rather than
left to implementation.

---

## 5. Emulator fixture

*Spec: "provisions the six containers and isolates state between tests."*

**Provisioning** (session-scoped, once per run): create database
`config.COSMOS_DATABASE_NAME`, then the six containers named by the `*_CONTAINER` constants
in `backend/config.py`, each with the partition key the production container uses. The
container names are read **from `config`**, never re-listed in the fixture — a fixture with
its own copy of the list drifts silently the first time a container is added.

**Isolation** (function-scoped): each test gets a unique partition-key prefix rather than a
fresh container. Re-creating six containers per test costs seconds each and would make the
tier too slow to run; a unique prefix gives the same freedom from cross-test observation.
Cross-partition query tests, which must see documents across partitions by design, instead
take a dedicated container that no other test writes to.

**Readiness and skip (FR-013)**: the fixture polls the health probe (`:8080/ready`) with a
bounded timeout. On timeout it **skips** with a message naming the dependency and the exact
command to start it — never hangs, never passes vacuously. The contract for that message is
in [`contracts/local-stack.md`](./contracts/local-stack.md).

---

## 6. Seed fixture dataset (FR-019, FR-020)

Deterministic data sufficient to populate **every principal view** — the spec is explicit
that an empty store is not sufficient.

| Content | Populates |
|---|---|
| 3 published stories, varied in length and character types | Story list; adventure browse |
| 1 unpublished draft, 1 edit draft | Admin stories list; draft editing views |
| 1 fresh play session (0 turns) | Session start view |
| 1 in-progress play session (~5 turns, prior context present) | In-progress turn view — the one whose content otherwise depends on an LLM |
| 1 completed session | Completion view |
| 1 session at a content-safety standing threshold | The content-safety error state |
| 2 provisioned accounts (admin + player, `.invalid` addresses) | Admin accounts view |

**Rules**: every id, timestamp and narrative string is fixed — no `uuid4()`, no `now()` — so
a re-seed reproduces byte-identical state and a visual diff means a real change. All
personas are synthetic (Principle X). Turn narratives are written into the fixture, so the
in-progress session renders **without the LLM stub being called at all**; the stub covers
*taking a new turn*, the fixture covers *seeing an existing one*.

**Re-seeding**: one documented command restores this exact state (FR-020). Implemented as
drop-and-recreate of the database rather than an upsert pass — an upsert leaves behind
anything a manual play session created, which defeats "back to a known state".
