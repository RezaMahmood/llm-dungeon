# Implementation Plan: Frontend Dependency Security & Freshness Audit

**Branch**: `021-npm-dependency-audit` | **Date**: 2026-08-31 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/021-npm-dependency-audit/spec.md`

## Summary

Add a CI-enforced `npm audit` gate for `src/frontend` that blocks merge on High/Critical
findings and reports Low/Moderate findings without blocking; remediate the frontend's
current npm dependency set (upgrade or replace every flagged package) so the audit starts
clean; add a `.github/dependabot.yml` configuration monitoring `src/frontend/package.json`
on a recurring schedule so future drift is surfaced automatically via Dependabot
PRs/alerts; and, when the CI audit finds a Critical-severity vulnerability, automatically
open a `priority: high`-labeled GitHub issue for it (deduplicated against any already-open
issue for that same finding). No application code, UI, or user-facing behavior changes —
this is CI tooling plus dependency-version bumps.

## Technical Context

**Language/Version**: Node.js 24 (matches `.github/workflows/test.yml` frontend-test job), npm 11

**Primary Dependencies**: React 18, react-router-dom, @azure/msal-browser, @azure/msal-react, axios (frontend runtime); vite, vitest, eslint, @testing-library/* (frontend dev/test tooling)

**Storage**: N/A

**Testing**: vitest (`npm test` in `src/frontend`), existing GitHub Actions `frontend-test` job

**Target Platform**: GitHub Actions CI (ubuntu-latest); frontend runs in the browser

**Project Type**: Web application (existing `src/frontend` React app + `src/backend` Python Azure Functions); this feature touches only `src/frontend` and `.github/`

**Performance Goals**: N/A — no runtime performance change

**Constraints**: `npm audit` run MUST be re-runnable on demand (FR-010), not only in CI; upgrades/replacements MUST NOT change observable frontend behavior (FR-007) and MUST keep the existing vitest suite passing (SC-005); Critical findings MUST result in a high-priority GitHub issue without creating duplicates across repeated CI runs (FR-011), which requires the CI job to have `issues: write` permission and the `gh` CLI (pre-installed on `ubuntu-latest` runners)

**Scale/Scope**: Single npm project (`src/frontend/package.json`), 11 direct dependencies today; no new services or infrastructure

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle I (Meaningful, Automated Testing)**: No new application behavior is added,
  so no new unit tests are required. The existing vitest suite is the regression guard for
  User Story 2's package upgrades/replacements (FR-007, SC-005) and MUST continue to pass
  after every dependency change. PASS.
- **Principle V (Continuous Integration Gate)**: This feature's entire purpose is
  strengthening the CI gate — adding an `npm audit` step to the existing `frontend-test`
  job in `.github/workflows/test.yml` that fails the job (and therefore blocks merge, per
  the existing branch-protection requirement on that workflow) when a High/Critical
  vulnerability is found. PASS — this plan implements the principle rather than risking it.
- **Principle III (Defined Technology Stack)**: No stack change — frontend stays ReactJS;
  `npm audit` and Dependabot are npm/GitHub-native tooling, not a new framework. PASS.
- **Principle IV (Simplicity/YAGNI)**: `npm audit` (already bundled with npm, already
  installed in CI via `actions/setup-node`) is used directly rather than introducing a
  third-party SCA service or a custom scanning script. Dependabot is configured with the
  minimum needed (npm ecosystem, `src/frontend` directory, a recurring schedule) rather
  than a broader multi-ecosystem or custom-cadence setup not asked for by the spec.
  Critical-finding issue creation (FR-011) uses the `gh` CLI already available on
  `ubuntu-latest` runners with the job's own `GITHUB_TOKEN`, and a plain `gh issue list
  --search` dedupe check, rather than a bot account, a third-party issue-management
  action, or a persisted state file. PASS.
- **Principle VIII / XI (UI Design System & Pre-Agreement)**: No UI surface is added,
  changed, or restyled by this feature — it is CI configuration and dependency-version
  bumps only. N/A — no design/UI sign-off task is required in tasks.md for this feature.
- **Principle IX (User-Verified Acceptance)**: Applies as usual — tasks.md MUST end with
  an explicit acceptance task where the requesting user confirms (a) a deliberately
  vulnerable/outdated test dependency is caught and blocks a PR, (b) the real PR
  pipeline shows the audit step passing on the remediated `main`/`021` state, (c) the
  Dependabot configuration is visible under the repo's Insights > Dependency graph >
  Dependabot, per FR-009, and (d) a deliberately-introduced Critical finding results in a
  `priority: high`-labeled GitHub issue, and re-running the check does not create a
  duplicate, per FR-011.
- **Development Workflow**: This work happens in this feature's own worktree/devcontainer
  per the workflow rule already in effect (this session is already running there). PASS.

No violations requiring Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/021-npm-dependency-audit/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md         # Phase 1 output (/speckit-plan command)
├── contracts/            # Phase 1 output (/speckit-plan command)
└── tasks.md              # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
.github/
├── workflows/
│   └── test.yml          # MODIFIED: add `npm audit` step + Critical-finding issue-creation step
│                           #   to the frontend-test job; job gains `issues: write` permission
└── dependabot.yml         # NEW: npm ecosystem config for src/frontend, recurring schedule

src/frontend/
├── package.json           # MODIFIED: dependency version bumps / replacements from remediation
├── package-lock.json       # MODIFIED: lockfile updated to match
└── src/                    # unchanged application code (no behavior change expected)
```

**Structure Decision**: This is the existing single-frontend web application
(`src/frontend`, React + Vite) plus repository-level CI/GitHub configuration
(`.github/workflows/test.yml`, `.github/dependabot.yml`). No new project, service, or
directory is introduced; the feature is additive CI configuration and in-place dependency
maintenance within the existing frontend project.

## Complexity Tracking

*No Constitution Check violations — table not needed.*
