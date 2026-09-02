# Phase 1 Data Model: CI/CD Pipeline Optimization

This feature has no application data model (no database, no user-facing entities) — its "entities" are pipeline concepts realized as GitHub Actions/Git/GitHub Releases constructs. This document maps each entity from `spec.md`'s Key Entities section to its concrete realization and states the invariants (validation rules) each one must uphold.

## Component

**Represents**: One of Frontend, Backend, or Infrastructure — an independently tested, built, versioned, and deployed unit of the system.

**Realized as**: A fixed set of three logical namespaces, each with its own:
- Path scope (which files "belong" to it): `src/frontend/**`; `src/backend/**` + `src/function_app.py` + `src/requirements.txt`; `infrastructure/**`.
- Tag/release prefix: `frontend-v*`; `backend-v*`; `infrastructure-v*`.
- `semantic-release` config: `src/frontend/.releaserc.json`; `src/backend/.releaserc.json`; `infrastructure/.releaserc.json`.
- CI workflow: `frontend-build.yml`; `backend-build.yml`; `infrastructure-build.yml`.
- CD workflow: `frontend-deploy.yml`; `backend-deploy.yml`; `infrastructure-deploy.yml`.

**Invariants**:
- A change to one component's path scope MUST NOT trigger another component's CI or CD workflow (FR-004, FR-005).
- The three components' CD workflows MUST share the same trigger/input shape (`workflow_dispatch` + `version`), differing only in whether the deploy job targets an approval-gated environment (FR-011/FR-011a/FR-011b).

## Version

**Represents**: A unique identifier assigned to a build artifact, scoped to its component, referencing exactly which tested change the artifact was built from.

**Realized as**: A SemVer string (e.g., `1.4.0`) computed by that component's `semantic-release` config from Conventional-Commit-typed, path-filtered changes since its last release; materialized as a git tag `<component>-v<version>` and a GitHub Release of the same name.

**Invariants**:
- Unique per (component, version) pair — `semantic-release`/git tags enforce this natively (a tag name can't be reused).
- Monotonically increasing per component, per standard SemVer precedence rules — used to resolve "latest" (highest version tag for that component's prefix, evaluated at deploy-execution time, not trigger time — FR-013).
- Every version that exists MUST correspond to a commit that was on `main` at the time it was tagged (a release is only ever created by the CI build workflow, which only ever runs post-merge) — this is what makes FR-016 well-defined (an explicit version with no matching tag has no corresponding tested state and MUST fail the deploy rather than build something ambiguous).

## Build Artifact

**Represents**: The immutable, versioned output of a successful build for one component; complete and usable as-is for deployment.

**Realized as**: A file (or small set of files) attached to a component's GitHub Release as release assets:
- Frontend: the built `dist/` directory, zipped, plus `dist/version.json`.
- Backend: a zip of the `src` deploy root with dependencies vendored into `.python_packages`, plus a `VERSION` file.
- Infrastructure: the saved Terraform plan (`tfplan` binary + a human-readable plan text rendering), plus a `VERSION` file — "usable as-is" here means "the exact plan that was validated is what gets applied," not a re-plan (Decision 3, research.md).

**Invariants**:
- Immutable once attached to a release — never overwritten in place (FR-007). A rebuild request for an already-cached version reuses the existing asset rather than re-uploading (FR-008).
- Self-sufficient for deploy: the deploy job downloads this asset and deploys it directly, with no install/build/re-plan step of its own (FR-009).
- Produced by exactly one code path (the shared `workflow_call` build workflow, Decision 5, research.md), invoked either by the post-merge CI workflow or by a CD workflow's cache-miss fallback — never duplicated logic.

## Cache

**Represents**: The store of build artifacts, keyed by component and version, consulted before any new build and used to serve deploys without rebuilding.

**Realized as**: The set of GitHub Releases for a given component's tag prefix — "checking the cache" means querying `gh release list`/`gh release view <tag>` (or `git tag --list`) for that component; "cache hit" means a release with that exact tag already exists and has the expected asset attached.

**Invariants**:
- No expiry — GitHub Releases have no retention limit, satisfying "indefinitely retrievable" (Assumptions, spec.md).
- Keyed uniquely by (component, version) — see Version's invariants above.

## Deploy Action

**Represents**: A manually triggered operation, one per component, that takes an optional version (defaulting to latest-at-execution-time) and results in that version's cached artifact being deployed.

**Realized as**: The `workflow_dispatch` event on each `<component>-deploy.yml`, with a single input:

| Input | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `version` | string | no | `""` (empty) | The exact `<component>-v<version>` to deploy. Empty means "resolve to latest at execution time" (FR-013). |

**Invariants**:
- MUST NOT be triggerable by `push` or `pull_request` — `workflow_dispatch` is its only trigger (FR-010).
- MUST resolve an empty/unspecified `version` to the most recently built version *at execution time*, not at trigger time (FR-013).
- MUST deploy the resolved version's cached artifact unchanged if a cache hit; MUST build-then-deploy on a cache miss only for the latest-not-yet-built case; MUST fail clearly (no fallback, no substitution) for an explicit version with no corresponding cached-or-buildable state (FR-014/FR-015/FR-016).
- For infrastructure only: the apply step MUST NOT execute until a human has approved the run via the target GitHub Environment's required-reviewer protection (FR-011a). For frontend/backend: no equivalent approval step exists — the deploy job runs straight through once triggered (FR-011b).
