# Quickstart: Validating CI/CD Pipeline Optimization

This guide walks through validating the CI/CD separation end-to-end once implemented, following the acceptance scenarios in `spec.md`. It assumes repository admin access (to trigger `workflow_dispatch` runs and view Actions history) and the GitHub CLI (`gh`) authenticated against this repository. See `contracts/workflow-interfaces.md` for the exact trigger/input contracts referenced below, and `data-model.md` for what "cache", "version", and "artifact" concretely mean.

## Prerequisites

- This feature's PR has merged to `main` (so the new/renamed workflows exist there).
- `gh auth status` shows an authenticated session with write access to this repository.
- At least one prior version exists for each component (from normal development merges), or you're prepared to validate the "never built before" cold-start path explicitly (Scenario 5 below).

## Scenario 1 — No untested code reaches `main` (User Story 1)

1. Open a PR with a change that breaks an existing backend or frontend test.
2. Confirm the `test` (or `frontend-test`) required check fails and the PR's merge button is blocked.
3. Fix the change so tests pass; confirm the check goes green and merging is allowed.

**Expected outcome**: no path exists to merge while the required test check is red.

## Scenario 2 — Merge produces one immutable, versioned, cached build (User Story 2)

1. Merge a small, qualifying (`feat`/`fix`) change touching only `src/frontend/**`.
2. In the Actions tab, confirm `frontend-build.yml` ran and only it — `backend-build.yml` and `infrastructure-build.yml` did not trigger.
3. `gh release list | grep '^frontend-v'` — confirm a new `frontend-v<version>` release exists with the built artifact attached.
4. `gh workflow run frontend-build.yml` is not itself a re-triggerable path for this — instead, confirm re-running the same completed build job (e.g., via "re-run jobs" in the Actions UI) does not create a second, different release for the same version (idempotency, FR-008).

**Expected outcome**: exactly one artifact, one version, one cache entry, per affected component.

## Scenario 3 — Deploy is always a separate, manual action (User Story 3)

1. After Scenario 2's merge, check the Actions tab and Azure/Static Web App: confirm **no deploy occurred automatically** as a result of the merge.
2. `gh workflow run frontend-deploy.yml -f version=""` — confirm this explicit trigger is what causes the deploy, and it completes without any approval prompt.
3. `gh workflow run infrastructure-deploy.yml -f version=""` — confirm the run pauses awaiting a required-reviewer approval on the target environment (visible in the Actions UI's "Review deployments" prompt) before the `apply` step runs. Approve it as the reviewer and confirm apply then proceeds.

**Expected outcome**: zero automatic deploys; frontend/backend deploy directly on trigger; infrastructure additionally waits for a human approval.

## Scenario 4 — Deploy targets a specific version, defaulting to latest (User Story 4)

1. Ensure at least two versions of a component are cached (e.g., `frontend-v1.2.0` and `frontend-v1.3.0`).
2. `gh workflow run frontend-deploy.yml -f version=1.2.0` — confirm the deployed artifact matches `frontend-v1.2.0` exactly (check the deployed `dist/version.json` or equivalent).
3. `gh workflow run frontend-deploy.yml -f version=""` — confirm `1.3.0` (the latest) deploys instead.
4. Trigger a deploy with no version specified, and — before it finishes resolving — merge a change that produces `frontend-v1.4.0`. Confirm the run deploys `1.4.0`, not `1.3.0` (execution-time resolution, FR-013). (This step is timing-sensitive; if the resolve step completes before the new merge lands, re-run with tighter timing or treat Scenario 2 + immediate re-check as sufficient evidence the resolution logic queries live tag state.)

**Expected outcome**: explicit versions deploy exactly as requested; unspecified resolves to whatever is truly latest at execution time.

## Scenario 5 — An AI agent resolves and deploys "latest" (User Story 5)

Cache present:
1. Ask an AI agent (e.g., Claude, in a session with `gh` access to this repo) to "deploy the latest backend version."
2. Confirm the agent's trace shows it checking `gh release list` for `backend-v*` before dispatching, then running `gh workflow run backend-deploy.yml -f version=""` (or an explicit version it resolved itself) — and that no new build occurred (the existing cached artifact was deployed as-is).

Cache absent (cold path):
3. Pick a component that has never been built (or simulate by ensuring no release exists for its would-be next version — e.g., a fresh merge just landed and the build hasn't run yet, or has been deliberately skipped).
4. Ask the agent to "deploy latest" for that component.
5. Confirm `ensure-artifact` in the deploy run detects the cache miss, invokes the shared build workflow, and the resulting freshly-built artifact is what gets deployed — all within the one deploy request, per FR-015/SC-004.

**Expected outcome**: cache hit deploys without rebuilding; cache miss on "latest" triggers exactly one build, then deploys it.

## Scenario 6 — Non-testable-only changes trigger nothing (Edge Cases / FR-019/FR-020)

1. Open a PR that only edits `specs/023-cicd-pipeline-optimization/spec.md` (or any `.md`/`specs/**`/`docs/**` content).
2. Confirm `test.yml` and all `*-build.yml` workflows show no run (or a run that immediately reports "skipped" via the `changes` job's `all-non-testable` output) for this push.
3. Add one code change (e.g., a one-line comment in `src/backend/`) to the same PR/branch and push again.
4. Confirm the full pipeline (test, and on merge, build/version/cache) now runs normally, including for the bundled docs changes from step 1.

**Expected outcome**: docs-only changes are pipeline-silent; the moment one testable file is present, nothing is skipped.

## Scenario 7 — Requesting a version that was never built fails clearly (Edge Cases / FR-016)

1. `gh workflow run frontend-deploy.yml -f version=99.99.99` (a version that has never existed).
2. Confirm the run fails with a clear, explicit error identifying that no such version's artifact could be found or built — not a silent fallback to another version, and not an attempt to build an unrequested one.

**Expected outcome**: a clear failure, no substitution.

---

Final acceptance (Constitution Principle IX): all seven scenarios above MUST be run against the real repository by the requesting user (or product owner) — not merely asserted by the automated `workflow-structure-test.yml`/`release-fixtures-test.yml` checks — before this feature is considered complete.
