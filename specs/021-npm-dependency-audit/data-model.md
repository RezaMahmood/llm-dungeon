# Phase 1 Data Model: Frontend Dependency Security & Freshness Audit

This feature has no application data model (no database, no API request/response
schemas). The "entities" below are CI/config artifacts, per spec.md's Key Entities.

## Dependency Finding

A single reported issue against one frontend npm package, as emitted by `npm audit
--json` under `vulnerabilities.<name>`.

| Field | Source | Notes |
|---|---|---|
| package name | `vulnerabilities.<name>.name` | e.g. `react-router` |
| installed version / range | `vulnerabilities.<name>.range` | affected range in the current lockfile |
| severity | `vulnerabilities.<name>.severity` | `low` \| `moderate` \| `high` \| `critical` |
| vulnerability identifier | `vulnerabilities.<name>.via[].url` / GHSA id | present for direct advisories; absent when `via` is only a package name (indirect effect) |
| fixed version (if any) | `vulnerabilities.<name>.fixAvailable.version` | `false` when no fix exists |
| direct vs transitive | `vulnerabilities.<name>.isDirect` | informs whether the project can fix it by bumping its own `package.json`, or must wait on an upstream dependency (edge case in spec.md) |

Blocking rule (FR-003): a Dependency Finding blocks merge when `severity` is `high` or
`critical`. This is enforced by running `npm audit --audit-level=high`, not by
custom parsing — its exit code already encodes this rule.

## Dependency Audit Report

The aggregated output of one `npm audit` run — the full `npm audit --json` document plus
the human-readable `npm audit` text output, both produced by the same CI step run. Used
identically for:
- User Story 1 (CI gate): the report from the PR's `frontend-test` job run.
- User Story 2 (initial remediation): the report from a local/on-demand run, before and
  after remediation, as captured in [research.md](./research.md)'s baseline section.

No persistence is required — each run's report exists only in that CI run's logs /
that terminal's output, per FR-010 ("re-runnable on demand," not "stored").

## Critical Finding Issue

A GitHub issue automatically opened by the CI audit step when a Dependency Finding's
`severity` is `critical`.

| Field | Source | Notes |
|---|---|---|
| title | `[dependency-audit] Critical: <package>` | stable/deterministic — doubles as the dedupe key (FR-011) |
| body | Dependency Finding fields (package, installed version, severity, fixed version) | satisfies FR-004's required fields, reused here per FR-011 |
| labels | `priority: high`, `bug` | FR-011's "marked with high priority"; see research.md |
| dedupe rule | `gh issue list --search "<title> in:title" --state open` before creating | no duplicate issue for a finding that already has an open tracking issue — FR-011, Acceptance Scenario 5 |

Lifecycle: created by CI when first detected; a maintainer closes it once the finding is
resolved (upgrade/replacement lands) — closing is a manual GitHub action, not automated
by this feature. If the same package regresses to a new Critical finding after its prior
issue was closed, the dedupe search (which is scoped to `state:open`) finds nothing, so a
new issue is correctly created — this is the intended behavior per spec.md's edge cases.

## Dependabot Configuration

A single entry in `.github/dependabot.yml`:

| Field | Value | Maps to |
|---|---|---|
| `package-ecosystem` | `npm` | FR-008 ("npm package manifest") |
| `directory` | `/src/frontend` | the manifest location (spec's Key Entity: "manifest location Dependabot monitors") |
| `schedule.interval` | `weekly` | FR-008 ("recurring schedule"); see research.md for cadence rationale |
| `open-pull-requests-limit` | a small bounded number (e.g. `10`, GitHub's typical default) | avoids unbounded PR spam while still surfacing findings, per FR-009 |

Repository-level "Dependabot alerts" (Settings > Code security) is a separate,
non-file-based GitHub setting that must also be enabled/confirmed for FR-009's
"security alerts" visibility channel — verified as part of the acceptance task, not
expressed in `dependabot.yml` itself.
