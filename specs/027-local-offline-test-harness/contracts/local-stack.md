# Contract: The Local Offline Stack

**Consumers**: a contributor running the app offline (US4), the seed/visual workflow
(FR-019, FR-020), emulator-backed tests (US2).
**Implementation**: `tools/local-stack/`.

## Components and ports

Published host ports are **derived from the branch name** (`ports.sh`), because sibling
containers share the host's port space and this repo runs several worktree containers at
once (research.md D2, D8). The numbers below are the base; each worktree adds its offset.

| Component | Base port | Protocol | Started by |
|---|---|---|---|
| Cosmos emulator — gateway | 8081 | **HTTP** (`--protocol http`) | Compose |
| Cosmos emulator — health probe | 8080 | HTTP | Compose |
| Cosmos emulator — Data Explorer | 1234 | HTTP | Compose |
| Azurite — blob / queue / table | 10000–10002 | HTTP | Compose |
| Functions host (`func start`) | 7071 | HTTP | `func` |
| Vite dev server | 5173 | HTTP | `npm run dev` |
| SWA CLI (**the entry point**) | 4280 | HTTP | `swa start` |
| Local token issuer | ephemeral | HTTP (loopback) | in-process |
| LLM stub | ephemeral | HTTP (loopback) | in-process |

**Use `:4280`, not `:5173`.** Only the SWA CLI applies `staticwebapp.config.json`; going
direct to Vite bypasses both the `/api` proxy and the navigation-fallback rules, and would
make US4 scenarios 2 and 3 untestable.

## Readiness and skip contract (FR-013)

A test or command that needs a component it cannot reach **skips with an actionable
message** — it never hangs, and it never passes vacuously.

```
SKIPPED - Cosmos emulator not reachable at http://127.0.0.1:8081 (health probe
http://127.0.0.1:8080/ready timed out after 30s).
Start it with:  tools/local-stack/up.sh
```

Rules:

1. Readiness is the **health probe**, not a TCP connect and not a log-line grep — a socket
   that accepts before the emulator is initialised is exactly how "still starting" becomes
   a flaky failure.
2. Bounded timeout, always. No unbounded wait anywhere in the fixture.
3. The message names **both** the missing dependency and the command that starts it.
4. Skipping is only ever for an **absent dependency**. A test that reaches the emulator and
   then fails must fail — never degrade into a skip.

## Marker contract (FR-014)

Registered in `pytest.ini`:

| Marker | Meaning | Default local run |
|---|---|---|
| *(none)* | Object-level unit tier, no external dependency | runs |
| `emulator` | Needs the Cosmos emulator | runs; skips with the message above if absent |
| `live` | Needs a real Azure resource | **deselected by default** |

`live` is deselected by an explicit `addopts` deselection, not left to fail-and-skip on its
own. A test that requires live Azure and is not marked `live` is a defect.

## Settings contract (FR-018)

`src/local.settings.json.example` is committed; `src/local.settings.json` is gitignored.
The example carries every key the host needs with empty or local values, and **no secret**.

The stale-settings Edge Case: startup validates that every key present in the example is
present in the working copy, and on a mismatch reports **the missing key by name** —

```
local.settings.json is missing: AZURE_AI_FOUNDRY_ENDPOINT, COSMOS_ENDPOINT
Copy the new keys from src/local.settings.json.example
```

— rather than failing later inside the host with an obscure error.

## Seeding contract (FR-020)

| Command | Effect |
|---|---|
| `tools/local-stack/up.sh` | Starts the sibling containers, waits for readiness |
| `python tools/local-stack/seed.py` | Drops and recreates the database, writes the fixture dataset |
| `python tools/local-stack/seed.py --verify` | Asserts current state matches the fixture exactly |
| `tools/local-stack/down.sh` | Stops the containers; `--volumes` also discards data |

Seeding is **drop-and-recreate**, not upsert — an upsert leaves behind whatever a manual
play session wrote, which defeats "re-seedable back to a known state".

## Offline invariant (FR-001, SC-001)

With the stack running and networking disabled, no component attempts an outbound
connection. The fake credential returns a static token without a network call; the issuer
and LLM stub are loopback; the emulator and Azurite are local containers. `login.microsoftonline.com`
and `graph.microsoft.com` are reached by **nothing** in a default local run — FR-017 exists
precisely so the Graph base URL is redirectable rather than hard-coded.
