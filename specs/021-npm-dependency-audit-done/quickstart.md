# Quickstart: Frontend Dependency Security & Freshness Audit

## Prerequisites

- Node.js 24 and npm 11 (matches `.github/workflows/test.yml`'s `frontend-test` job)
- Repo checked out, working directory `src/frontend`

## 1. Run the audit on demand (FR-010)

```bash
cd src/frontend
npm install
npm run audit:frontend      # exits non-zero only on High/Critical (FR-003)
```

Expected after remediation (User Story 2 complete): exits `0`, no High/Critical findings.

For the full report (all severities, per FR-004):

```bash
npm audit
```

## 2. Validate User Story 1 — CI blocks a vulnerable PR

1. On a throwaway branch, in `src/frontend`, add or pin a devDependency known to carry a
   High/Critical advisory (e.g. temporarily `npm install --save-dev vitest@3.2.5`, per the
   pre-remediation baseline in [research.md](./research.md)).
2. Commit `package.json` + `package-lock.json`, open a PR.
3. Confirm the `frontend-test` job's audit step fails and the PR shows a blocked/failing
   required check.
4. Revert the change; confirm the audit step passes and the check goes green.

## 3. Validate User Story 2 — baseline remediation

1. Before: see [research.md](./research.md)'s captured baseline (7 vulnerabilities: 5
   moderate, 1 high, 1 critical, spanning `vite`/`vitest` toolchain and `react-router-dom`).
2. After remediation tasks are applied, run:
   ```bash
   cd src/frontend
   npm audit
   npm test
   npm run build
   ```
3. Expected: `npm audit` reports zero High/Critical findings (SC-002); `npm test` and
   `npm run build` both succeed (SC-005, FR-007).

## 4. Validate Critical-finding issue creation (FR-011)

1. On a throwaway branch, temporarily introduce a Critical-severity devDependency (e.g.
   `vitest@3.2.5`, per the pre-remediation baseline).
2. Open a PR; after the `frontend-test` job runs, confirm a new issue titled
   `[dependency-audit] Critical: vitest` exists, labeled `priority: high` and `bug`, with
   package/version/severity/fixed-version details in the body.
3. Re-run the same job (e.g. re-push an empty commit) without closing that issue; confirm
   no second, duplicate issue is created (FR-011 Acceptance Scenario 5).
4. Close the issue, then revert the throwaway change; confirm no new issue appears (no
   Critical finding remains).

## 5. Validate User Story 3 — Dependabot configured

1. Confirm `.github/dependabot.yml` exists with an npm entry for `/src/frontend` on a
   weekly schedule (see [contracts/ci-audit-step.md](./contracts/ci-audit-step.md)).
2. In the GitHub UI: Insights > Dependency graph > Dependabot — confirm the configuration
   is recognized (no parse errors) and, once GitHub has run its first scheduled check,
   that update PRs and/or Security > Dependabot alerts appear (FR-009, SC-004). This may
   take up to the configured interval to populate after merge — acceptable per SC-004's
   "within Dependabot's configured check interval."

## 6. Final acceptance (Constitution Principle IX)

A human (the requesting user/product owner) must confirm, against the real GitHub
repository (not just local runs):
- A deliberately vulnerable test PR is blocked by the new required check.
- The remediated `src/frontend` dependency set passes the real PR pipeline.
- `.github/dependabot.yml` is visible and active under the repo's Dependabot settings.
- A deliberately-introduced Critical finding creates a `priority: high`-labeled issue,
  and re-running the check does not duplicate it (FR-011).
