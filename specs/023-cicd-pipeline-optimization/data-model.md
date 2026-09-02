# Phase 1 Data Model: CI/CD Pipeline Optimization

This feature has no application data model (no database, no user-facing entities) — its "entities" are pipeline concepts realized as GitHub Actions/Git/GitHub Releases constructs. This document maps each entity from `spec.md`'s Key Entities section to its concrete realization and states the invariants (validation rules) each one must uphold.

**Post-merge amendment (2026-09-02)**: Infrastructure no longer participates in Version/Build Artifact/Cache below — only frontend and backend do. This document reflects that reversal; see spec.md's Clarifications Amendment and research.md's amendment to Decision 9.

## Component

**Represents**: One of Frontend, Backend, or Infrastructure — an independently tested and deployed unit of the system. Frontend and backend are also independently built, versioned, and cached; infrastructure is not.

**Realized as**: A fixed set of three logical namespaces:
- Path scope (which files "belong" to it): `src/frontend/**`; `src/backend/**` + `src/function_app.py` + `src/requirements.txt`; `infrastructure/**`.
- Tag/release prefix (frontend/backend only): `frontend-v*`; `backend-v*`. Infrastructure has none.
- `semantic-release` config (frontend/backend only): `src/frontend/.releaserc.json`; `src/backend/.releaserc.json`. Infrastructure has none.
- CI workflow (frontend/backend only): `frontend-build.yml`; `backend-build.yml`. Infrastructure has no CI build workflow — its existing `terraform-validate.yml`/`infrastructure-tests.yml` are unchanged by this feature.
- CD workflow: `frontend-deploy.yml`; `backend-deploy.yml`; `infrastructure-deploy.yml`.

**Invariants**:
- A change to one component's path scope MUST NOT trigger another component's CI or CD workflow (FR-004, FR-005).
- Frontend/backend's CD workflows share the same trigger/input shape (`workflow_dispatch` + `version`), no approval gate. Infrastructure's CD workflow is `workflow_dispatch` with no inputs, and does have an approval gate (FR-011/FR-011a/FR-011b/FR-021/FR-022).

## Version (frontend & backend only)

**Represents**: A unique identifier assigned to a build artifact, scoped to its component, referencing exactly which tested change the artifact was built from. Infrastructure has no version.

**Realized as**: A SemVer string (e.g., `1.4.0`) computed by that component's `semantic-release` config from Conventional-Commit-typed, path-filtered changes since its last release; materialized as a git tag `<component>-v<version>` and a GitHub Release of the same name.

**Invariants**:
- Unique per (component, version) pair — `semantic-release`/git tags enforce this natively (a tag name can't be reused).
- Monotonically increasing per component, per standard SemVer precedence rules — used to resolve "latest" (highest version tag for that component's prefix, evaluated at deploy-execution time, not trigger time — FR-013).
- Every version that exists MUST correspond to a commit that was on `main` at the time it was tagged (a release is only ever created by the CI build workflow, which only ever runs post-merge) — this is what makes FR-016 well-defined (an explicit version with no matching tag has no corresponding tested state and MUST fail the deploy rather than build something ambiguous).

## Build Artifact (frontend & backend only)

**Represents**: The immutable, versioned output of a successful build for frontend or backend; complete and usable as-is for deployment. Infrastructure has no equivalent persisted artifact.

**Realized as**: A file (or small set of files) attached to a component's GitHub Release as release assets:
- Frontend: the built `dist/` directory, zipped, plus `dist/version.json`.
- Backend: a zip of the `src` deploy root (dependencies are not vendored — Azure Flex Consumption requires its own Oryx remote build at deploy time, so `deploy` triggers that build; see research.md's amendment to Decision 3), plus a `VERSION` file.

**Invariants**:
- Immutable once attached to a release — never overwritten in place (FR-007). A rebuild request for an already-cached version reuses the existing asset rather than re-uploading (FR-008).
- Self-sufficient for deploy: the deploy job downloads this asset and deploys it directly, with no install/build step of its own (FR-009).
- Produced by exactly one code path (the shared `workflow_call` build workflow, Decision 5, research.md), invoked either by the post-merge CI workflow or by a CD workflow's cache-miss fallback — never duplicated logic.

Infrastructure's equivalent — a Terraform plan — exists only for the duration of a single `infrastructure-deploy.yml` run (see "Infrastructure Plan" below), not as a persisted Build Artifact.

## Cache (frontend & backend only)

**Represents**: The store of build artifacts, keyed by component and version, consulted before any new build and used to serve deploys without rebuilding. Infrastructure has no cache.

**Realized as**: The set of GitHub Releases for a given component's tag prefix — "checking the cache" means querying `gh release list`/`gh release view <tag>` (or `git tag --list`) for that component; "cache hit" means a release with that exact tag already exists and has the expected asset attached.

**Invariants**:
- No expiry — GitHub Releases have no retention limit, satisfying "indefinitely retrievable" (Assumptions, spec.md).
- Keyed uniquely by (component, version) — see Version's invariants above.

## Infrastructure Plan (infrastructure only)

**Represents**: The Terraform plan infrastructure's deploy validates, tests, and generates fresh on every trigger, then applies within that same run.

**Realized as**: A `terraform plan -out=tfplan` output, passed from `infrastructure-deploy.yml`'s `plan` job to its `apply` job via a same-run `actions/upload-artifact`/`actions/download-artifact` pair — never a GitHub Release, never persisted beyond the run's artifact retention window.

**Invariants**:
- Never regenerated between `plan` and `apply` — `apply` MUST NOT run `terraform plan` itself (FR-021).
- If the real infrastructure state has drifted since `plan` ran, `terraform apply <saved-plan>` fails outright with Terraform's own native stale-plan error rather than silently re-planning or applying something no longer accurate.
- Exists only within a single `infrastructure-deploy.yml` run — no version, no cache, no cross-run identity (FR-022).

## Deploy Action

**Represents**: A manually triggered operation, one per component. Frontend/backend's takes an optional version (defaulting to latest-at-execution-time) and results in that version's cached artifact being deployed. Infrastructure's takes no version and always validates/tests/plans fresh before applying.

**Realized as**: The `workflow_dispatch` event on each `<component>-deploy.yml`.

Frontend/backend input:

| Input | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `version` | string | no | `""` (empty) | The exact `<component>-v<version>` to deploy. Empty means "resolve to latest at execution time" (FR-013). |

Infrastructure: no inputs.

**Invariants**:
- MUST NOT be triggerable by `push` or `pull_request` — `workflow_dispatch` is its only trigger, for all three components (FR-010).
- Frontend/backend: MUST resolve an empty/unspecified `version` to the most recently built version *at execution time*, not at trigger time (FR-013). MUST deploy the resolved version's cached artifact unchanged if a cache hit; MUST build-then-deploy on a cache miss only for the latest-not-yet-built case; MUST fail clearly (no fallback, no substitution) for an explicit version with no corresponding cached-or-buildable state (FR-014/FR-015/FR-016).
- Infrastructure: MUST validate, test, and plan fresh on every trigger, then apply only that same-run plan (FR-021). MUST NOT accept a version input (FR-022).
- For infrastructure only: the apply step MUST NOT execute until a human has approved the run via the target GitHub Environment's required-reviewer protection (FR-011a). For frontend/backend: no equivalent approval step exists — the deploy job runs straight through once triggered (FR-011b).
