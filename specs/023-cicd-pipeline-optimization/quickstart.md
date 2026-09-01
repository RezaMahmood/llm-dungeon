# Quickstart: Validating CI/CD Pipeline Optimization

Manual/operational validation scenarios for this feature — there is no application UI or API to exercise, so "running" this feature means observing real GitHub Actions runs and Azure deploys. Each scenario maps to a User Story in spec.md.

## Prerequisites

- Repo admin access to add/require the new PR-title status check in branch protection.
- A test change ready for each component (a trivial backend change under `src/backend/**`, a trivial frontend change under `src/frontend/**`).
- Access to the GitHub Actions run view and the repo's Releases page.

## Scenario 1 — Build-once/deploy-that-artifact (User Story 1)

1. Open a PR with a small backend-only change, titled e.g. `fix(backend): correct typo in error message`. Merge it (squash) once checks pass.
2. Open the resulting `backend-deploy.yml` run. Confirm the job graph shows `test → release → build → deploy` and that `deploy`'s logs show it downloading an artifact (`actions/download-artifact`) rather than running `pip install`/any build/remote-build step.
3. Repeat with a frontend-only change titled `fix(frontend): correct typo in button label`, confirming `frontend-deploy.yml`'s `deploy` job similarly only downloads and deploys, with no `npm install`/`npm run build` in that job's steps.
4. **Expected**: both deploys succeed, and inspecting each run confirms zero install/build activity inside the `deploy` job itself (SC-002).

## Scenario 2 — Stale deploy cancellation (User Story 2)

1. Push two backend-only commits to `main` in quick succession (e.g. two quick squash-merges), commit A then commit B.
2. Open the Actions tab and watch both `backend-deploy.yml` runs.
3. **Expected**: the run for commit A is shown as cancelled (not failed) before its `deploy` job starts, once commit B's run begins; commit B's run proceeds through to a successful deploy (SC-003). Repeat for frontend to confirm each component's concurrency group is independent (a backend race does not cancel a concurrent frontend run).

## Scenario 3 — Automated per-component SemVer (User Story 3)

1. Merge a PR titled `fix(backend): ...`. After the run completes, check the repo's Releases page and tags: confirm a new `backend-v{X.Y.(Z+1)}` tag/release exists, and no new `frontend-v*` tag was created.
2. Merge a PR titled `feat(frontend): ...`. Confirm a new `frontend-v{X.(Y+1).0}` tag/release exists, and no new `backend-v*` tag was created.
3. Download the artifact (or check the deployed app) from either run and confirm the version file (`VERSION` / `version.json` per contracts/workflow-interfaces.md) matches the tag just created (SC-005).
4. Merge a PR titled `chore(backend): update dev-only comment` (a non-releasable type). Confirm no new `backend-v*` tag/release is created.
5. Merge a PR titled `fix(backend): ...` whose diff touches files under **both** `src/backend/**` and `src/frontend/**` (a vertical-slice change). Confirm **both** `backend-v*` and `frontend-v*` receive a new patch version — path-diff filtering (research.md decision #3), not the title's single declared scope, determines eligibility. This is the case the automated version-computation fixture test (research.md decision #8) also covers pre-merge; this step confirms it holds in a real run too.

## Scenario 4 — PR title format gate (User Story 4)

1. Open a PR titled `updated the login typo` (no type/scope). Confirm the PR-title required check fails with a message explaining the expected `type(scope): description` format, and that merge is blocked (SC-006).
2. Edit the PR title to `fix(frontend): correct login typo`. Confirm the check re-runs and passes, unblocking merge.

## Scenario 5 — Terraform apply-the-reviewed-plan (User Story 5)

1. Make a small, reviewable infrastructure change under `infrastructure/terraform/**` and let `terraform-apply.yml` run through `validate` → `test` → the `production-infra` approval gate.
2. Approve the gate and confirm `apply`'s logs show `terraform apply -input=false tfplan` (or equivalent), referencing the downloaded plan artifact, not a freshly invoked `terraform plan` immediately before applying (SC-007).
3. (Optional, harder to stage) If infrastructure state drifts between `validate` and `apply` (e.g. a manual out-of-band change), confirm `apply` fails with Terraform's stale-plan error rather than silently applying a different set of changes (FR-016).

## Final acceptance (Constitution Principle IX)

Per the constitution's non-negotiable user-verified acceptance gate, `tasks.md`'s final task MUST have the requesting user or product owner confirm Scenarios 1–5 above against real merged PRs and real Azure/GitHub state — not merely that the workflow YAML is syntactically valid or that a dry run succeeded.
