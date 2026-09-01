# Phase 0 Research: CI/CD Pipeline Optimization

All Technical Context items were resolved during the pre-spec investigation and the `/speckit-clarify` session; no `NEEDS CLARIFICATION` markers remain. This document records the concrete tooling/pattern decisions and why each was chosen, so `/speckit-tasks` can generate implementation tasks against settled choices rather than open questions.

## 1. Job restructuring for build-once/deploy-that-artifact

**Decision**: Keep one workflow per component (`backend-deploy.yml`, `frontend-deploy.yml`), restructured into four sequential jobs: `test` → `release` → `build` → `deploy`, connected via `needs:` and `actions/upload-artifact`/`actions/download-artifact`.

**Rationale**: A single workflow with job-level artifact passing satisfies "CD deploys CI's pre-built package" without the complexity of cross-workflow `workflow_run` triggers or a separate CD workflow — which the spec explicitly puts out of scope (no rollback/redeploy-of-older-version requirement). Jobs in the same run share a natural ordering and a single triggering commit, which also simplifies the concurrency/staleness design (see #2).

**Alternatives considered**: Separate CI (build+tag) and CD (deploy) workflows connected via `workflow_run` — rejected because it only pays off if you need to redeploy/promote a previously built artifact independently of a new commit, which is explicitly out of scope; it would also reintroduce a real staleness race (CD's `workflow_run` trigger firing against a SHA that may no longer be `main`'s HEAD) that the concurrency-group approach avoids more simply within one workflow.

## 2. Concurrency-based stale-deploy cancellation

**Decision**: Add `concurrency: { group: deploy-<component>, cancel-in-progress: true }` at the workflow level for both `backend-deploy.yml` and `frontend-deploy.yml`, keyed per component (e.g. `deploy-backend`, `deploy-frontend`), not per-ref.

**Rationale**: GitHub Actions cancels an in-progress run sharing the same concurrency group when a new run in that group starts. Keying by component (not by branch/ref, since both workflows already only trigger on `push: branches: [main]`) means a second rapid push to `main` cancels the first run's `test`/`release`/`build`/`deploy` jobs before they complete, which is exactly FR-005/FR-006 and the spec's "abort on conflict/newer version" requirement — achieved natively by the platform rather than a custom SHA-comparison step.

**Alternatives considered**: A custom step in `deploy` that runs `git rev-parse origin/main` and compares it to the checked-out SHA, failing if they differ — rejected as strictly more code for an equivalent outcome that GitHub's built-in `concurrency` primitive already provides, and it would only catch the race at the last moment (after `build` already ran) rather than cancelling early.

## 3. Automated per-component Semantic Versioning

**Decision**: Use `semantic-release` for both frontend and backend, each with its own `.releaserc.json` scoped to that component's paths and a minimal tooling-only `package.json` (`name` + `version`, `"private": true`, never published to any registry). Plugin set: `@semantic-release/commit-analyzer`, `@semantic-release/release-notes-generator`, `@semantic-release/github` — deliberately **excluding** `@semantic-release/npm` (nothing to publish) and `@semantic-release/git` (would push a version-bump/changelog commit directly to `main`).

**Rationale**: `@semantic-release/github` creates the git tag and GitHub Release as part of its own run — it does not require a preceding commit-back step. Excluding `@semantic-release/git` means this feature's automation never pushes a commit to `main`, keeping it clear of the constitution's "no direct pushes to main" rule (see plan.md's Constitution Check) without needing a branch-protection bypass or exception. The component's `package.json` `version` field is never mutated by CI; the tag and release are the sole, authoritative version record — consistent with spec Key Entity "Release."

**Path scoping — superseded by path-diff filtering (see `/speckit-analyze` finding F1)**: The original version of this decision scoped each component's history solely via `tagFormat` plus each workflow's existing `on.push.paths` trigger filter, reasoning that a run's commit history would "naturally" only contain commits touching that component. This was incorrect: `on.push.paths` only gates whether a workflow *runs at all* for a given push — it does not filter which commits `semantic-release`'s commit-analyzer considers once the workflow does run. Because this project's specs are typically implemented as **vertical slices** (one PR/commit can legitimately touch frontend, backend, and infrastructure paths together), a single squash-merge commit touching both `src/frontend/**` and `src/backend/**` would trigger both workflows, and — without path-diff filtering — both components' `release` jobs would see that same commit in `main`'s shared history and could both treat it as releasable, regardless of which single scope word its PR title declared.

**Revised decision**: Each component's `release` job filters its commit-analysis input by **path-diff**, not by the PR title's scope word: for every commit since that component's last matching tag, check whether the commit's changed files fall under that component's path glob (`src/backend/**` / `src/frontend/**` etc., mirroring each workflow's existing trigger filter). A commit is only eligible for this component's version bump if its diff touched this component's paths — using the commit's declared Conventional Commit *type* (`feat`/`fix`/`BREAKING CHANGE`) as the bump signal. This is exactly what a monorepo-aware commit-analyzer plugin does (see `semantic-release-monorepo`'s `commitsPerPackage` filtering logic), so the concrete implementation is either that plugin or an equivalent custom filter step that greps `git log --name-only` per candidate commit against the component's path glob before handing surviving commits to `@semantic-release/commit-analyzer`.

**Consequence for the PR-title scope word**: the scope declared in a PR title (FR-011) is now descriptive only — it drives changelog/release-note content and satisfies the PR-title-format check (User Story 4) — but it no longer gates which component(s) release. A vertical-slice commit titled `fix(backend): ...` that also happens to touch frontend paths will still correctly bump frontend's version too, using the same `fix` type, because frontend's release job independently detects that its own paths were touched.

**Alternatives considered**: `python-semantic-release` for the backend — rejected in favor of a single tool (`semantic-release`) for both components, per the decision made with the user during pre-spec investigation, to avoid maintaining two different versioning tools/configs. Gating strictly on the PR title's scope word (requiring multi-scope titles like `feat(frontend,backend): ...` for vertical slices) was considered during `/speckit-analyze` remediation but rejected: it pushes correctness onto contributor discipline (remembering to list every affected scope) where a mechanical diff-based check is both more reliable and requires no change to how contributors write PR titles.

## 4. PR-title format enforcement (supersedes literal "commitlint" framing)

**Decision**: Use a PR-title-linting GitHub Action (validates the pull request's title against Conventional Commits with an enforced type/scope) as a required status check, rather than a commit-message linter (`commitlint`) run against individual commits.

**Rationale**: The `/speckit-clarify` session confirmed this repo merges exclusively by squash, so the PR title — not any individual commit message — becomes the sole commit on `main`, and is what `semantic-release`'s commit-analyzer reads. A tool that lints individual commits (`commitlint` via a commit-msg hook or a per-commit CI step) would validate content that squash-merge discards, giving contributors false negatives/positives relative to what actually lands on `main`. A PR-title checker directly validates the string that matters. This is a tool-selection correction from the original feature framing ("commitlint"), made to satisfy the same functional requirement (FR-011/FR-012) correctly given the repo's actual, confirmed merge strategy.

**Alternatives considered**: `commitlint` on a `pull_request` trigger, run against `git log` for the PR's commit range — rejected because it validates content that is discarded at merge time, and would require additional logic to decide which of N commits "counts," a problem the PR-title approach doesn't have.

## 5. Dependency caching and frontend lockfile

**Decision**: Enable `cache: npm` on `actions/setup-node` and `cache: pip` on `actions/setup-python` wherever those actions already run (`test.yml`, `backend-deploy.yml`, `frontend-deploy.yml`). Commit `src/frontend/package-lock.json` (removing it from `.gitignore`) and switch the frontend's install step from `npm install` to `npm ci`.

**Rationale**: Both cache mechanisms are built into the official setup actions and require no new infrastructure. `npm ci` requires a committed lockfile and is both faster and reproducible (installs exactly what's locked, fails on drift) versus `npm install`'s unlocked resolution — a prerequisite for the build-once guarantee in User Story 1, since a rebuild without a lockfile could silently install different transitive dependency versions than the build that was tested.

**Alternatives considered**: A third-party caching action (e.g. manually keyed `actions/cache`) — rejected as unnecessary; the setup actions' built-in `cache:` input covers this repo's needs without custom cache-key management.

## 6. Terraform apply-the-reviewed-plan fix

**Decision**: In `terraform-apply.yml`'s `validate` job, add `-out=tfplan` to the existing `terraform plan` step (it already exists) and upload `tfplan` via `actions/upload-artifact`. In the `apply` job, download that artifact and run `terraform apply -input=false tfplan` — passing the saved plan file as the apply target, with no `-var-file`/`-auto-approve` flags (both are only meaningful when generating a new plan; applying a saved plan needs neither).

**Rationale**: Terraform's own plan-file mechanism already guarantees "apply exactly what was planned" — applying a saved plan file that no longer matches current state fails outright with a stale-plan error, which directly satisfies FR-016 (fail clearly rather than silently re-planning) with no additional custom logic.

**Alternatives considered**: Adding a manual state-hash comparison step before apply — rejected as redundant; Terraform's native saved-plan staleness check already provides this guarantee.

## 7. Version stamping into the build artifact

**Decision**: The `build` job writes the version computed by the `release` job (passed via job `outputs`) into a small metadata file inside the artifact — a `VERSION` file at the artifact root for the backend zip, and a `version.json` (or equivalent) served alongside/within the frontend's `dist/` output — without modifying any file in the git-tracked source tree.

**Rationale**: Satisfies FR-010 ("version identifiable from the deployed artifact itself") without requiring any commit back to the repository, keeping the versioning mechanism entirely free of the "no direct pushes to main" constraint addressed in decision #3.

**Alternatives considered**: Stamping the version into an existing application file (e.g. injecting into `function_app.py` or `package.json` at build time) — viable but adds a build-time file-mutation step for marginal benefit over a dedicated metadata file; a separate `VERSION`/`version.json` file is simpler and keeps the built artifact's provenance file distinct from application source.

## 8. Automated validation for the pipeline changes themselves (added post-`/speckit-analyze`)

**Decision**: This feature's changes ARE testable in an automated, non-manual way, and the constitution's Principle I (NON-NEGOTIABLE — tests "MUST be fully automatable, no manual steps") applies to them like any other feature, story by story — not just the versioning logic. Add one automated check per user story, each running as part of the PR that introduces the corresponding change (not only as a post-merge manual quickstart pass):

1. **Workflow lint** (cross-cutting, all stories): run `actionlint` (or equivalent) against every changed file under `.github/workflows/` as a required PR check — catches YAML/schema/expression errors before merge. Syntax/schema only; does not assert job/step shape (see 2, 3, 5 below for that).
2. **Workflow-structure assertion (US1)**: a YAML-parsing script asserting `backend-deploy.yml`'s `deploy` job has no install step and `remote-build: false`, `frontend-deploy.yml`'s `deploy` job has no install/build step and `skip_app_build: true`, and each `build`→`deploy` artifact name pair matches. (Added in a second `/speckit-analyze` pass, finding G1 — the first pass only covered US3/US4, leaving US1/US2/US5 with no behavioral test of their own.)
3. **Workflow-structure assertion (US2)**: asserts each deploy workflow's `concurrency.group`/`cancel-in-progress: true` block is present and literal (not templated on `github.ref`).
4. **Version-computation fixture test (US3)**: a small script/job that runs `semantic-release --dry-run` (or directly exercises the configured commit-analyzer) against a fixed set of synthetic commit messages/diffs — including a same-component `fix`, a same-component `feat`, a non-releasable `chore`, and the vertical-slice case from decision #3's revision (one synthetic commit touching both components' paths) — and asserts each produces the expected bump (or no-bump) per component. This is what actually protects FR-013/FR-008 and the path-diff design in decision #3 going forward, rather than relying on a human noticing a misattributed release after the fact.
5. **PR-title format test (US4)**: a unit test (or the checker action's own test fixtures, if it ships them) asserting the configured PR-title pattern accepts known-good titles (`fix(backend): ...`, `feat(frontend): ...`) and rejects known-bad ones (no type, no scope, unknown type).
6. **Workflow-structure assertion (US5)**: asserts `terraform-apply.yml`'s `apply` job's `terraform apply` invocation references the downloaded `tfplan` file with neither `-auto-approve` nor `-var-file`.

**Rationale**: The original plan (pre-`/speckit-analyze`) treated this feature as validated solely by quickstart.md's manual, human-run scenarios, on the reasoning that CI/CD configuration isn't "application code." The constitution draws no such exception, and manual-only validation directly contradicts Principle I's explicit "no manual steps" language. A first remediation pass added checks 1, 4, and 5 but left US1/US2/US5 (checks 2, 3, 6) covered only by lint and manual quickstart — a second `/speckit-analyze` pass (finding G1) caught that this was the same violation, just narrower. All six checks above are ordinary automated tests — they run without a human driving them, they can fail a PR, and together they cover every user story's own behavior, not only YAML syntax.

**Relationship to quickstart.md**: quickstart.md's Scenarios 1–5 remain as the Principle IX human-acceptance layer — confirming the feature works against the *real* deployed environment — but they are no longer the *only* validation for this feature's logic. The automated checks above validate the logic itself, pre-merge; quickstart.md validates the real-world integration, at acceptance time.

**Alternatives considered**: Relying only on `quickstart.md`'s manual scenarios (the original plan) — rejected as a constitution conflict per `/speckit-analyze` finding C1. A full second CI pipeline dedicated to testing the first (e.g. spinning up a disposable GitHub repo to exercise real workflow runs end-to-end via `act` or the GitHub API) was considered but rejected as disproportionate — the fixture-based dry-run tests above exercise the actual decision logic (commit-analyzer behavior, PR-title regex) without needing a live sandboxed CI environment.
