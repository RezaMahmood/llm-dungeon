# Contracts: Workflow Interfaces

This feature has no application API. Its "interfaces" are the conventions other tooling, branch protection rules, and maintainers rely on: required check names, artifact/version naming, and job graph shape. These are the contracts implementation must honor exactly, since GitHub branch protection and any future automation will reference these names literally.

## Required status checks (branch protection surface)

| Check name (job) | Workflow | Trigger | Contract |
|---|---|---|---|
| PR title format | `pr-title-check.yml` | `pull_request` (opened, edited, synchronize) | MUST fail if the PR title does not parse as `type(scope): description` with `scope` ∈ {`frontend`, `backend`, ...} and `type` ∈ the Conventional Commits set. MUST re-run on title edits, not just first open. The declared `scope` is descriptive only (research.md decision #3) — it is validated for format here, but does not gate versioning eligibility. |
| `test` (backend) | `test.yml` | `pull_request` | Unchanged trigger/scope (FR-017); only caching added. |
| `frontend-test` | `test.yml` | `pull_request` | Unchanged trigger/scope (FR-017); only caching added. |
| Workflow lint (`actionlint`) | new, on changed `.github/workflows/**` | `pull_request` | Required per research.md decision #8 (Principle I compliance) — fails on YAML/schema/expression errors in changed workflow files. Syntax/schema only — does not assert job/step shape; see the structure-assertion checks below for that (`/speckit-analyze` finding G1). |
| Workflow structure assertion (deploy) | new (tasks.md T006/T009) | `pull_request` touching either deploy workflow | Required — asserts `deploy` has no install/build step and the correct `remote-build`/`skip_app_build` value, and that `build`→`deploy` artifact names match. |
| Workflow structure assertion (concurrency) | new (tasks.md T010/T013) | `pull_request` touching either deploy workflow | Required — asserts the literal `concurrency.group`/`cancel-in-progress: true` block is present in both workflows. |
| Version-computation fixture test | new, alongside the versioning tooling | `pull_request` touching `src/backend/.releaserc.json`, `src/frontend/.releaserc.json`, or either deploy workflow's `release` job | Required per research.md decision #8 — asserts correct per-component bump behavior against fixture commits, including the vertical-slice case. |
| Workflow structure assertion (terraform apply) | new (tasks.md T026/T029) | `pull_request` touching `terraform-apply.yml` | Required — asserts `apply` references the downloaded `tfplan` with no `-auto-approve`/`-var-file`. |

**Contract**: these check names MUST be added to the repository's branch protection required-checks list for `main` as part of this feature's rollout task — a check that exists but isn't required doesn't block merge.

## Per-component workflow job graph

Both `backend-deploy.yml` and `frontend-deploy.yml` expose this job sequence as their contract with each other and with anyone reading run history:

```
test → release → build → deploy
```

- `test`: MUST run on every push to `main` touching this component's paths (existing `on.push.paths` filter, unchanged). Failure MUST stop the chain — `release`/`build`/`deploy` MUST NOT run.
- `release`: MUST run only after `test` succeeds. MUST filter candidate commits since this component's last matching tag by **path-diff** (did the commit's changed files fall under this component's paths?), not by the PR title's scope word, before handing surviving commits to the commit-analyzer — see research.md decision #3. Outputs (job `outputs`) MUST expose at least `version` (the version this run's artifact should carry — either a newly cut Release version, or the current latest tag if no qualifying commit triggered a new Release) for `build` to consume.
- `build`: MUST run only after `release` succeeds (or is a no-op success with no new version). MUST produce exactly one `actions/upload-artifact` named `{component}-build-{run_id}` containing the deployable output plus its version metadata file (`VERSION` or `version.json`).
- `deploy`: MUST run only after `build` succeeds. MUST consume the artifact `build` produced via `actions/download-artifact` — MUST NOT invoke any install/build/remote-build step of its own.

**Contract**: the artifact name pattern `{component}-build-{run_id}` is how `deploy` locates the correct artifact; it MUST be unique per run (GitHub Actions run artifacts are already run-scoped, so `{run_id}` is primarily for human-readability in the Actions UI, not uniqueness enforcement).

## Concurrency contract

Both workflows MUST declare:

```yaml
concurrency:
  group: deploy-<component>   # deploy-backend / deploy-frontend, literal, not templated on ref
  cancel-in-progress: true
```

**Contract**: the group name MUST be a literal per-component string, not interpolated with `github.ref` or similar — the whole point is that all runs of a given component's workflow share one group, so a newer run cancels an older one regardless of ref. (Both workflows only trigger on `push: branches: [main]` today, so there is currently only one relevant ref per component; the literal group name is still the correct contract in case that ever changes.)

## Version/tag/release naming contract

| Component | Tag format | Example |
|---|---|---|
| backend | `backend-v{X.Y.Z}` | `backend-v0.2.0` |
| frontend | `frontend-v{X.Y.Z}` | `frontend-v0.3.1` |

**Contract**: this exact prefix format is what `semantic-release`'s `tagFormat` config in each component's `.releaserc.json` MUST use — it is also what any future tooling (dashboards, rollback scripts, incident runbooks) should match against to find a component's release history. Infrastructure MUST NOT receive tags in this format (FR-014) — no `infra-v*` tag is created by this feature.

## Version-in-artifact contract

| Component | File | Location | Format |
|---|---|---|---|
| backend | `VERSION` | artifact root (alongside `function_app.py`) | plain text, single line, e.g. `0.2.0` |
| frontend | `version.json` | artifact root (alongside `dist/index.html` or within `dist/`) | `{"version": "0.3.1"}` |

**Contract**: FR-010 requires the version be discoverable from the deployed artifact itself. Whatever mechanism `/speckit-tasks` implements MUST result in one of these two files existing, unmodified in the git-tracked source tree (see research.md decision #7 — no source-file mutation, no commit back to `main`).

## Terraform plan-artifact contract

| Artifact name | Producer job | Consumer job | Contract |
|---|---|---|---|
| `tfplan` | `validate` (in `terraform-apply.yml`) | `apply` (in `terraform-apply.yml`) | `apply` MUST run `terraform apply -input=false tfplan` (the downloaded file), with no `-var-file`/`-auto-approve` flags. If Terraform reports the plan is stale, the job MUST fail (native Terraform behavior — no custom handling required). |
