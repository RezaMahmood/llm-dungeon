# Phase 0 Research: CI/CD Pipeline Optimization

All Technical Context fields were resolvable from the spec, its three clarification sessions, and the existing repository (which already implements a related-but-superseded design for the same three components). No `NEEDS CLARIFICATION` markers remain. Each decision below replaces or extends something the existing `.github/workflows/` implementation already does.

## Decision 1: Split each component's single workflow into a CI workflow and a CD workflow

**Decision**: For each of frontend, backend, and infrastructure, replace the current single push-triggered `test → release → build → deploy` workflow with two workflows: a CI workflow triggered by push-to-`main` (path-scoped to that component) that ends at `build → version → cache`, and a CD workflow triggered only by `workflow_dispatch` that starts from version resolution and ends at deploy.

**Rationale**: FR-010 requires deploy never be a side effect of push or merge, for all three components uniformly. The existing `frontend-deploy.yml`/`backend-deploy.yml`/`terraform-apply.yml` all currently deploy/apply directly off a `push: branches: [main]` trigger — exactly the behavior the current spec forbids. Splitting the job graph at the artifact boundary (build/version/cache stays automatic; deploy becomes manual) is the smallest change that satisfies FR-010/FR-011 while preserving everything CI already does correctly (test gating, caching, artifact-once-deploy-that-artifact).

**Alternatives considered**:
- *Keep one workflow per component, gate the `deploy` job behind `workflow_dispatch` inputs checked at runtime*: rejected — a single workflow triggered by `push` cannot also be "only explicitly triggered," since the workflow run itself still starts automatically on push; the deploy job would need an `if:` condition on the event name, which is fragile (a bad condition silently deploys on merge) compared to simply never listening for `push` in the deploy workflow at all.
- *Use GitHub Environments' required-reviewer gate as the "manual trigger" mechanism for all three components*: rejected — an environment approval gate pauses an already-started, push-triggered run; it does not stop that run from being *initiated* by a merge, so it can't satisfy "never initiated automatically" for frontend/backend (FR-010), and per the clarification session, frontend/backend must have **no** approval step at all (FR-011b), only infrastructure does (FR-011a).

**Amendment (post-merge follow-up, 2026-09-02)**: Infrastructure's CI side does not end at `build → version → cache` as originally decided here — see Decision 9's amendment. It has no dedicated CI build workflow at all; its existing `terraform-validate.yml` (PR-time) and `infrastructure-tests.yml` (scheduled) are unchanged by this feature. Infrastructure's CD workflow (`infrastructure-deploy.yml`) still starts from nothing but its own trigger and remains `workflow_dispatch`-only, but its job graph is `validate-and-test → plan → apply`, not "version resolution → deploy."

## Decision 2: Retire the `concurrency`-group cancel-in-progress guard from deploy

**Decision**: Remove the `concurrency: {group: deploy-<component>, cancel-in-progress: true}` block from what becomes each CD workflow. It may optionally be kept on the CI (build) workflow to avoid redundant concurrent builds for rapid successive merges, but is no longer load-bearing for deploy ordering.

**Rationale**: That guard existed to solve "a newer push's deploy should supersede an older push's in-flight deploy" — a problem specific to the old *auto-deploy-on-merge* design. Once deploy is only ever explicitly, individually triggered (Decision 1) and always resolves "latest" at execution time (FR-013, already required), there is no automatic chain of deploys to race against each other; the spec's own "latest changes if a newer version lands before you deploy" requirement is satisfied by version resolution happening at execution time, not by cancelling other runs.

**Alternatives considered**: *Keep the concurrency guard on the deploy workflow anyway, as a safety net against two people/agents triggering the same component's deploy at once*: reasonable defense-in-depth, but not required by any FR — left as an implementation-time judgment call for `tasks.md`, not a plan-level requirement, since two concurrent manual deploys of the same version are already required to converge on the same artifact (FR-007/idempotency), and two concurrent deploys of different versions is a human/agent coordination question outside this feature's stated scope.

## Decision 3: Use GitHub Releases (tag + release + attached asset) as the artifact cache, for frontend and backend

**Decision**: `semantic-release` (via `semantic-release-monorepo`) computes each component's next SemVer from path-scoped Conventional-Commit-typed changes, creates a git tag (`frontend-v*` / `backend-v*`) and GitHub Release, and the build job attaches the deployable artifact as a release asset. (This was originally also extended to infrastructure; that extension was reversed post-merge — see Decision 9's amendment. Infrastructure's plan is a same-run `actions/upload-artifact` only, never a GitHub Release.)

**Rationale**: FR-006/FR-007 require the cache to be indefinitely retrievable and immutable. GitHub Actions' own `actions/upload-artifact` mechanism defaults to ~90-day retention and is explicitly designed for same-run/short-lived artifact passing, not a durable versioned store — it cannot satisfy "usable as-is, indefinitely" (Assumptions: no expiry policy). GitHub Releases have no retention limit, are already the mechanism this repo uses for frontend/backend, and Constitution Principle IV (Simplicity/YAGNI) counsels against introducing a second storage system (e.g., Azure Blob Storage, a container registry) for infrastructure alone when the existing mechanism generalizes cleanly.

**Alternatives considered**:
- *Azure Blob Storage / Azure Container Registry as a dedicated artifact store*: rejected — adds a new Azure resource, new authentication surface, and new lifecycle-management concern for no capability GitHub Releases doesn't already provide for this scale (three components, infrequent releases).
- *GitHub Actions cache (`actions/cache`)*: rejected — designed for build-speedup caching (e.g., `node_modules`), evictable under storage pressure (LRU) and scoped by branch, which violates "immutable, indefinitely retrievable" (FR-006/FR-007).

**Amendment (confirmed in production during this repository's prior 023-cicd-pipeline-optimization rollout, PR #149/#155)**: Backend's build originally also vendored dependencies into `.python_packages/lib/site-packages` and its deploy job called `Azure/functions-action` with `remote-build: false`, on the assumption that this Function App's plan supported a pre-built Python package the way classic Consumption/Premium plans do. It doesn't: this app runs on **Flex Consumption**, and a real deploy showed `remote-build: false` reporting "successfully deployed" while the app then loaded **zero functions** (404 on every route — a live production outage, fixed within minutes by reverting to `remote-build: true`). Flex Consumption Python apps require Azure's own Oryx remote build; there is no supported pre-vendored-dependency deploy path for this plan type. `backend-deploy.yml`'s `deploy` job therefore still triggers a remote build inside `Azure/functions-action` — the one piece of FR-009's "no build step at deploy time" a genuine platform constraint prevents, for backend specifically. Frontend and infrastructure are unaffected. `_build-backend.yml` no longer vendors dependencies (pointless now — Oryx reinstalls them from `src/requirements.txt` regardless); `deploy` still deploys the exact tested-and-versioned source tree `_build-backend.yml` produced, with no separate checkout/rebuild step of its own — so FR-009/SC-002's actual guarantee (deploy ships what was tested, not a divergent copy) still holds; only "no remote build at all" does not, for backend.

## Decision 4: Deploy workflow version resolution and cache-or-build-then-deploy

**Decision**: Each CD workflow (`workflow_dispatch`) declares a `version` input (`required: false`, default empty string = "latest"). A `resolve-version` job:
1. If `version` was supplied, use it as-is.
2. If blank, resolve "latest" by querying that component's tags (`git tag --list '<component>-v*' | sort -V | tail -1` or equivalently `gh release list`), evaluated fresh at execution time (not at trigger time) so a newer version landing between trigger and execution is picked up, per FR-013.

A subsequent `ensure-artifact` job checks whether a GitHub Release/tag exists for the resolved version:
- **Cache hit**: download that release's asset and pass it to `deploy` unchanged (FR-014).
- **Cache miss**: invoke the same build logic the CI workflow uses (via a shared reusable workflow, Decision 5) against the commit that version's tag would correspond to — but only when that version is genuinely "latest and not yet built" (the common AI-agent "deploy latest, build if needed" case, FR-015/User Story 5). An explicit version that has no corresponding tag/commit anywhere in history fails with a clear error rather than building something unrequested (FR-016) — resolving *which* commit an arbitrary never-tagged version string would even correspond to is undefined, so "build on cache-miss" only applies to the one case the spec actually describes: latest-resolved-but-not-yet-built.

**Rationale**: Directly implements FR-012 through FR-016 and User Stories 4-5. Evaluating "latest" at execution time (not capturing it once at trigger time) is what makes FR-013's "a newer version landing before deploy executes still gets deployed" scenario correct.

**Alternatives considered**: *Resolve "latest" once, at trigger time, as a workflow_dispatch input default computed by a bot/action before the human/agent even sees the trigger form*: rejected — GitHub Actions `workflow_dispatch` input defaults are static YAML, not computed at dispatch time, so this isn't mechanically possible without an extra pre-step that itself would need to run at execution time anyway; simpler to resolve inside the run.

## Decision 5: Extract the build step into a reusable (`workflow_call`) workflow shared by CI and CD

**Decision**: Move each component's build logic (install/build/package/stamp-version/attach-to-release) into a `workflow_call`-triggered reusable workflow, called both by that component's CI workflow (the normal post-merge build) and by that component's CD workflow's cache-miss fallback (Decision 4).

**Rationale**: FR-008 requires building to be idempotent — the same version, built twice, must be the same artifact. Keeping one build implementation (rather than duplicating build steps in both the CI and CD workflow files) is what makes that guarantee structurally true rather than something that can drift between two copies of similar-but-not-identical YAML.

**Alternatives considered**: *Duplicate the build steps in both workflows*: rejected — directly risks the two copies drifting (e.g., a dependency-install flag added to one and not the other), which would make "idempotent, immutable" an assertion rather than an enforced property.

## Decision 6: Infrastructure's human-approval gate uses a GitHub Environment with required reviewers

**Decision**: `infrastructure-deploy.yml`'s apply job targets a GitHub Environment (e.g., `production-infra`, continuing the existing name) configured with a required-reviewer protection rule **with "Prevent self-review" enabled, and with the requesting user — the sole human in the loop for this repository — set as the required reviewer**. The workflow run pauses at that job until that human approves it in the GitHub UI; an AI agent can trigger the workflow (`workflow_dispatch`) and can complete the earlier validation steps, but cannot itself satisfy the required-reviewer check. This separation is not automatic: GitHub Environments only prevent the dispatching identity from approving its own run when "Prevent self-review" is explicitly turned on (it is off by default) — without it, the same identity that dispatched the run (human or an agent acting under that human's credentials) could also approve it, silently defeating FR-011a.

**Rationale**: Directly implements FR-011a. This repo's `terraform-apply.yml` already targets a `production-infra` environment today (existing evidence: `environment: production-infra` on its `apply` job) — this decision keeps that mechanism and repoints it at the new manually-triggered `infrastructure-deploy.yml`, rather than inventing a new approval mechanism.

**Alternatives considered**: *A custom "approval" step (e.g., an issue comment `/approve` bot)*: rejected — reinvents a capability GitHub Environments already provides natively, adding maintenance surface for no functional gain.

## Decision 7: Skip the pipeline entirely when a push/PR's changed files are all non-testable content

**Decision**: A `changes` job (test.yml already has one; extend it, and add an equivalent to each CI/build workflow) computes the full list of changed files for the push/PR and evaluates two things: (a) which component paths were touched (existing behavior, unchanged), and (b) whether *every* changed file matches a defined non-testable-artifact glob set (`**/*.md`, `specs/**`, `docs/**`, `LICENSE`, `CONTRIBUTING.md`, and similar documentation-only patterns). If (b) is true, all downstream test/build jobs are skipped via `if:` conditions reading that job's output, regardless of (a). If even one changed file falls outside that glob set, the normal per-component path-scoped pipeline runs exactly as it does today, non-testable files included in that same change notwithstanding.

**Rationale**: Directly implements FR-019/FR-020 as clarified — exclusion is by content-type across the *entire* change set, not by directory location, and the exclusion is void the moment one testable file is present.

**Alternatives considered**: *Use GitHub Actions' native `paths-ignore` on the trigger*: rejected — `paths-ignore` at the trigger level cannot express "skip only if **every** changed file matches," it can only express per-path include/exclude independently, which doesn't match the "any single testable file re-enables the full pipeline" semantics the clarification specifically called for.

## Decision 8: AI-agent-driven deploy uses the existing `gh` CLI against the same `workflow_dispatch` interface — no new API surface

**Decision**: An AI agent (e.g., Claude) triggers a deploy the same way a human would from a script: `gh release list --repo <owner>/<repo>` (or equivalent) to inspect whether a cached version exists, then `gh workflow run <component>-deploy.yml -f version=<version-or-blank>` to trigger it. No bespoke API, webhook, or MCP tool is introduced by this feature.

**Rationale**: Directly implements FR-018/User Story 5 with zero new surface area — Constitution Principle IV (YAGNI) counsels against building a custom deploy-orchestration API when the existing `gh` CLI, already available in this project's tooling, exposes exactly the operations needed (list releases, dispatch a workflow with inputs).

**Alternatives considered**: *A custom internal API/service the agent calls instead of `gh`*: rejected — pure added complexity for a capability `gh workflow run` and `gh release list` already provide.

## Decision 9 (SUPERSEDED): Infrastructure gets its own SemVer version history (independent of frontend/backend), starting at `0.1.0`

**Status**: Superseded by the post-merge amendment below — kept for history since `infrastructure/.releaserc.json` genuinely shipped and was later removed.

**Original decision**: `infrastructure/.releaserc.json` was a new `semantic-release` config, path-scoped to `infrastructure/**`, producing independently-numbered `infrastructure-v*` tags/releases — mirroring frontend's and backend's existing configs and their `0.1.0` starting baseline.

**Original rationale**: FR-005 required each component to have its own independent version history; the earlier (superseded) version of this spec had explicitly excluded infrastructure from versioning, but that version of the current spec's User Stories 3-5 and Assumptions explicitly included infrastructure in the same versioned/cached/deployable pattern as frontend and backend.

**Amendment (post-merge follow-up, 2026-09-02)**: After this feature's first version merged (PR #160) and the requesting user reviewed it against the real repository, they reversed this decision: infrastructure does not need versioning. `infrastructure/.releaserc.json`, `infrastructure-build.yml`, and `_build-infrastructure.yml` were removed. `infrastructure-deploy.yml` was restructured to `validate-and-test → plan → apply`, always operating against the current state of `main`, applying only the plan produced in that same run (uploaded via `actions/upload-artifact`, never a persistent GitHub Release) — no version input, no cache, no build-on-demand fallback. This keeps FR-011a's human-approval gate and the explicit-trigger-only guarantee (FR-010/FR-011) intact; it only removes the versioned-artifact machinery. See spec.md's Clarifications Amendment and the new FR-021/FR-022.

**Why this is simpler, not just different**: infrastructure changes are comparatively infrequent and already gated by a human approval step regardless of versioning; re-validating and re-planning fresh at deploy time removes an entire class of "is this cached plan still valid" staleness questions (a stale cached plan would have failed anyway per Terraform's own drift detection, per Decision 3 below, but never generating one avoids the question entirely) at the cost of needing to know an artifact's provenance was `main` on deploy attempt rather than a specific tagged commit.
