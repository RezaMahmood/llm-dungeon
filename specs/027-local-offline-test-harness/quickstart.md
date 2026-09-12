# Quickstart: Local Offline Test Harness

**Branch**: `027-local-offline-test-harness` | **Date**: 2026-09-12

Runnable validation scenarios proving the feature works end to end. Each maps to the
success criteria it evidences. **None of this works yet** — this is the guide the
implementation must make true, and the order below is the order the phases land in
([`plan.md`](./plan.md) *Sequencing*).

Interface details are in [`contracts/`](./contracts/); fixture contents in
[`data-model.md`](./data-model.md). Neither is repeated here.

---

## Prerequisites

- A rebuilt devcontainer (phase 1). Docker access, Python 3.11, Core Tools, Azurite and the
  SWA CLI are installed at **build** time — if any of these needs a manual install step,
  FR-012/SC-007 is not met and that is the bug.
- `cp src/local.settings.json.example src/local.settings.json` (gitignored working copy).
- No `az login`, no service principal, no stored secret. If any scenario below asks for
  one, SC-002 has been missed.

Verify the rebuild took:

```bash
docker info >/dev/null && echo "docker: sibling containers reachable"
python --version          # expect 3.11.x, NOT 3.14 — matches CI and production
func --version            # expect 4.x
swa --version
```

---

## Scenario 0 — the spikes (phase 0, before anything is built)

Both decisions these gate are **unverified** (research.md D1, D3). Run them first; a
failure here redirects the phase rather than wasting it.

```bash
# T001 — does the emulator support what US2 actually needs?
python tools/local-stack/spikes/etag_and_crosspartition.py
```

Expected: an ETag-conditional replace with a stale ETag **fails with a precondition
failure**, and a cross-partition query returns correct results. If either does not hold,
that assertion set stays on the object-level fakes and becomes a permanent row in
`plan.md`'s live-only table — the tier still proceeds for everything else.

```bash
# T002 — does the real Functions host run here at all?
cd src && func start --verbose
```

Expected: the host starts, loads a Python 3.11 worker on linux-arm64, and lists the
registered routes. If it does not, phase 5 builds the in-process route-table harness
instead (plan.md fallback 1) — US4 scenarios 1, 2, 4 and 5 survive; the host's own
startup does not.

---

## Scenario 1 — the suite runs with no network and no credentials

**Evidences SC-001, SC-002, FR-001.**

```bash
pytest src/backend/tests
```

Expected: passes. Then the real test — **prove** it, rather than trusting it:

```bash
unshare -rn pytest src/backend/tests        # no network namespace at all
```

Expected: still passes, identically. A pass here is the only honest evidence for SC-001; a
pass with networking available proves only that nothing happened to fail.

Then confirm the token path is genuinely executing:

```bash
pytest src/backend/tests/unit/test_auth_service.py -v
```

Expected: tests named for a foreign signing key, an expired token, the consumers-tenant
issuer, and both audience forms (bare client id and `api://…`) — all passing, all driving
`AuthService.validate_token` unmodified (US1 scenarios 2–5).

---

## Scenario 2 — data access against a real database engine

**Evidences SC-003, FR-006.**

```bash
tools/local-stack/up.sh
pytest -m emulator src/backend/tests/integration -v
```

Expected: all pass. Specifically verifiable, per US2:

- an ETag conflict surfaces from a stale conditional replace (scenario 2 — the #281 class);
- a query filtering a non-partition-key field returns correct results with the SQL really
  parsed (scenario 3);
- all six containers provisioned once by a session-scoped fixture (scenario 1).

Now check the skip path is honest (FR-013, US2 scenario 4):

```bash
tools/local-stack/down.sh
pytest -m emulator src/backend/tests/integration
```

Expected: **skipped**, with a message naming the emulator and the command that starts it —
not passed, and not hung. A silent pass here is the failure mode FR-013 exists to prevent.

---

## Scenario 3 — LLM failure modes on demand

**Evidences SC-004, FR-009.**

```bash
pytest src/backend/tests/integration/test_llm_failure_modes.py -v
```

Expected — each driving the real client against the stub, none patching `llm_service`:

| Test | Asserts |
|---|---|
| 429 twice then success | retried with backoff, returned the completion, **stub saw 3 attempts** |
| 429 always | caller sees a rate-limit error, not an unhandled 500 |
| content-filter refusal | `LLMContentFilteredError` **and** the player standing updated |
| non-JSON body | `LLMOutputError` |
| JSON missing a required key | `LLMOutputError` |
| usage 1234 in / 567 out | span carries matching `gen_ai.usage.*` and a `gen_ai.cost_usd` computed from configured prices |

---

## Scenario 4 — the whole application, offline, in a browser

**Evidences SC-006, SC-009, FR-010, FR-019, FR-020.**

```bash
tools/local-stack/up.sh
python tools/local-stack/seed.py
cd src && func start &          # terminal 2
cd src/frontend && npm run dev & # terminal 3
swa start http://localhost:5173 --api-devserver-url http://localhost:7071   # terminal 4
```

Open **`http://localhost:4280`** (not `:5173` — only the SWA CLI applies
`staticwebapp.config.json`).

Walk the play loop: browse stories → start a session → take a turn. Expected: it works end
to end with no Azure resource involved, turn responses coming from the scripted endpoint.

Then the hosting contract (US4 scenarios 1–3):

```bash
curl -i http://localhost:4280/api/version              # 200, served by the real host
curl -i http://localhost:4280/api/not-a-route          # 404 — NOT the SPA fallback document
curl -i http://localhost:4280/play/some-session-id     # 200 index.html — SPA fallback
curl -i http://localhost:4280/redirect.html            # the real file, fallback excluded
```

The second line is the one that matters: a fallback document with a 200 where a 404 belongs
is exactly the deploy-time defect this tier exists to catch.

Then every principal view, populated (SC-009): story list, session start, an in-progress
turn, the completion view, and the error states — each rendering representative content
from the seed fixture. Re-seed and confirm byte-identical state:

```bash
python tools/local-stack/seed.py && python tools/local-stack/seed.py --verify
```

---

## Scenario 5 — frontend tests at the HTTP boundary

**Evidences SC-005 (as redirected — see *Spec deviation (decided)* in `plan.md`), FR-011.**

```bash
cd src/frontend && npm test
```

Expected: the representative migrated tests stub at the network boundary via MSW, so axios
runs for real — the outgoing request carries the bearer header the services actually
attach, a 401 produces the SPA's real behaviour, and a 5xx or network failure produces the
specified error state.

Note what is **not** claimed: `installTokenInterceptor` is dead code (never called in
`src/frontend/src`), so no test here covers it. That discrepancy is tracked as
[#313](https://github.com/RezaMahmood/llm-dungeon/issues/313) and is out of scope for this
feature — see `plan.md`, *Spec deviation (decided)*.

---

## Scenario 6 — a fresh container, no manual steps

**Evidences SC-007, FR-012.**

```bash
bin/wt 027-local-offline-test-harness --rebuild     # run by the user, on the host
```

Then, inside the fresh container, scenarios 1–5 with **no** install step of any kind. Any
`pip install`, `npm i -g` or manual download needed at this point is an FR-012 failure.

---

## Scenario 7 — CI

**Evidences Principle I (tests that exist must be PR-gated).**

Push the branch and confirm `.github/workflows/test.yml` runs the emulator tier against the
emulator service container, and that it fails the run when an emulator-backed test fails.
The Core Tools / SWA / browser tier stays local-only for now (research.md D9).

---

## Coverage map

| Criterion | Scenario |
|---|---|
| SC-001, SC-002 | 1 |
| SC-003 | 2 |
| SC-004 | 3 |
| SC-005 | 5 *(redirected — see plan.md; dead code tracked as #313)* |
| SC-006, SC-009 | 4 |
| SC-007 | 6 |
| SC-008 | `plan.md` *Live-only fallbacks* |
