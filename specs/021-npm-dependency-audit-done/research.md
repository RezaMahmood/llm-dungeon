# Phase 0 Research: Frontend Dependency Security & Freshness Audit

## Decision: Use `npm audit` (built-in) as the vulnerability check, not a third-party SCA tool

**Rationale**: `npm` is already the frontend's package manager and `npm audit` is bundled
with it — no new tool, license, or account is needed, satisfying Constitution Principle IV
(YAGNI). FR-001 explicitly asks for a check "using npm's dependency-scanning capability."
`npm audit --json` produces machine-parseable severity data (`info` | `low` | `moderate` |
`high` | `critical`) that maps directly onto FR-003's High/Critical blocking threshold.

**Alternatives considered**: Snyk, GitHub CodeQL/Advanced Security dependency scanning,
`osv-scanner`. Rejected — all add an external account/service or a new binary to CI for
a capability `npm audit` already provides for this project's scale (11 direct deps).

## Decision: Add an `npm audit` step to the existing `frontend-test` job in `test.yml`

**Rationale**: `.github/workflows/test.yml` already has a `frontend-test` job that runs
`npm install` and `npm test` in `src/frontend`, gated by `needs.changes.outputs.code`.
Adding an audit step there (after `npm install`) reuses the existing PR-triggered,
frontend-path-aware job rather than creating a parallel workflow, satisfying FR-002
("consistent with this project's existing continuous-integration gate") and Constitution
Principle V. `npm audit --audit-level=high` exits non-zero when any High or Critical
finding exists, which fails the job/blocks merge per FR-003, while `npm audit --json`
(run unconditionally, not gated on exit code) produces the full report — including Low/
Moderate — for FR-004's required fields (package, installed version, severity, fixed
version).

**Alternatives considered**: A separate `dependency-audit.yml` workflow. Rejected — would
duplicate the existing path-filtering/Node-setup logic already in `test.yml` for no
functional benefit, and would need its own required-status-check wiring in branch
protection.

## Decision: Blocking threshold is `--audit-level=high` (High and Critical block; Low/Moderate report only)

**Rationale**: Directly specified by FR-003. `npm audit`'s `--audit-level` flag natively
supports this threshold (`low`, `moderate`, `high`, `critical`), so no custom severity
parsing is needed for the blocking decision.

**Alternatives considered**: Blocking on any severity (rejected — spec explicitly scopes
blocking to High/Critical only, Low/Moderate are report-only per FR-003/FR-004);
blocking on `moderate` (rejected — spec's edge cases anticipate that not every finding
has an available fix, and today's baseline audit is entirely Moderate/High/Critical with
some fixes requiring major-version bumps — an over-eager threshold would make the gate
un-mergeable without an escape hatch the spec doesn't define).

## Decision: Command is re-runnable on demand via the existing `npm` scripts, no new script wrapper needed

**Rationale**: FR-010 requires the check to be runnable outside CI. `npm audit` (and
`npm audit --json` for detail) already runs standalone from `src/frontend` with no
additional wiring — satisfying FR-010 without adding a project-specific script, per
Constitution Principle IV.

**Alternatives considered**: Adding an `"audit"` entry to `package.json` `scripts`
(e.g. `"audit": "npm audit --audit-level=high"`) to mirror the CI invocation exactly and
give maintainers a single documented command. Adopted as a convenience — see data-model.md
CI step design — since it costs nothing and keeps the CI command and the on-demand command
identical (avoids drift between what CI runs and what a maintainer runs locally).

## Decision: Baseline remediation target — current `npm audit` findings on `src/frontend` (captured 2026-08-31)

```
7 vulnerabilities (5 moderate, 1 high, 1 critical)

- esbuild <=0.24.2 (moderate) — via vite; fix: vite@8.2.2 (major, breaking)
- vite <=6.4.2 (high) — depends on vulnerable esbuild; fix: vite@8.2.2 (major, breaking)
- @vitest/mocker <=3.0.0-beta.4 (moderate) — via vite; fix: vitest@4.1.11 (major, breaking)
- vite-node <=2.2.0-beta.2 (moderate) — via vite; fix: vitest@4.1.11 (major, breaking)
- vitest <=3.2.5 (critical) — via @vitest/mocker/vite-node; fix: vitest@4.1.11 (major, breaking)
- react-router 6.0.0-7.17.0 (moderate) — GHSA-wrjc-x8rr-h8h6, GHSA-337j-9hxr-rhxg;
  fix: react-router-dom@7.18.3 (major, breaking)
- react-router-dom 6.0.0-alpha.0-7.17.0 (moderate) — via react-router; same fix
```

All seven findings are in **devDependencies (vite/vitest toolchain)** or in
**react-router-dom** (direct runtime dependency). All fixes require a semver-major bump.
None is a transitive dependency the project cannot address directly — every finding
resolves through `npm audit fix --force` or an equivalent manual major-version upgrade of
a directly-declared dependency (`vite`, `vitest`/`@vitejs/plugin-react` as needed,
`react-router-dom`). No edge case requiring "no fix available" or "replace with a
different package" applies to the current baseline — remediation is upgrade-only.

**After remediation (captured 2026-08-31, same session)**: `vite` → `^8.2.2`,
`@vitejs/plugin-react` → `^6.1.1` (required by vite 8's peer range), `vitest` →
`^4.1.11`, `react-router-dom` → `^7.18.3`. `npm audit` now reports **0 vulnerabilities**.
`npm run audit:frontend` (the CI-blocking script) exits `0`. Breaking-change fallout: Vite
8's rolldown bundler requires `build.rollupOptions.output.manualChunks` to be a function
rather than an object map — `src/frontend/vite.config.js` was updated accordingly,
preserving the same msal/react chunk-splitting behavior. `npm test` (88 tests, 20 files)
and `npm run build` both pass with no other code changes required — no
`react-router-dom` v6→v7 API usage in `src/frontend/src` needed updating. Two pre-existing
`npm run lint` errors (`react-hooks/exhaustive-deps` rule not found;  unused `axios`
import in `tokenInterceptor.js`) were confirmed present before this feature's changes
(via a stash-and-check) and are out of this feature's scope — FR-007/SC-005 gate on
build+test, not lint. `npm outdated` review (FR-005) found no npm-deprecated direct
dependency in the remediated set.

**Rationale**: FR-005 requires reviewing the current dependency set now. Capturing the
exact baseline in research.md (rather than re-discovering it during /speckit-implement)
lets tasks.md enumerate concrete upgrade tasks instead of a vague "run audit and fix
whatever it says" step.

**Alternatives considered**: Deferring discovery to implementation time. Rejected —
spec.md's User Story 2 independent test explicitly compares a "before" and "after" audit
run, so the "before" state should be recorded now as the acceptance baseline.

## Decision: Dependabot configuration — npm ecosystem, `src/frontend` directory, weekly schedule

**Rationale**: FR-008 requires monitoring "the frontend's npm package manifest... on a
recurring schedule." Dependabot's native `package-ecosystem: "npm"` with
`directory: "/src/frontend"` points it at `src/frontend/package.json` /
`package-lock.json`. A weekly interval is chosen as a sensible default recurring cadence
for a project of this size — frequent enough to catch new advisories promptly (supporting
SC-004) without generating excessive PR noise; the spec does not mandate a specific
interval, only that one exists.

**Alternatives considered**: `daily` (rejected as noisier than needed for an 11-dependency
project with no stated urgency requirement); `monthly` (rejected — too slow relative to
SC-004's "surfaced... automatically... within Dependabot's configured check interval"
expectation of timely disclosure).

## Decision: Critical findings auto-create a `priority: high`-labeled GitHub issue, via `gh` CLI in the same CI step, deduped by title search

**Rationale**: FR-011 requires that a Critical-severity finding automatically opens a
high-priority issue, without creating duplicates across repeated runs. `gh` (the GitHub
CLI) is preinstalled on GitHub-hosted `ubuntu-latest` runners and authenticates with the
job's own `GITHUB_TOKEN` — no PAT, bot account, or third-party Action is needed
(Constitution Principle IV). The step:
1. Parses `npm audit --json` for entries with `severity == "critical"`.
2. For each one, searches open issues for a stable, deterministic title
   (`[dependency-audit] Critical: <package>`) via `gh issue list --search
   "<title> in:title" --state open`.
3. If none is found, creates one via `gh issue create --title "..." --body "..." --label
   "priority: high" --label "bug"`, with the body containing the fields FR-004 requires
   (package, installed version, severity, fixed version if available).
This satisfies FR-011's dedupe clause (Acceptance Scenario 5) without needing any
persisted state beyond GitHub's own issue list — the search *is* the dedupe check.

**Alternatives considered**: A GitHub Action from the Marketplace (e.g. an
"issue-from-json" style action). Rejected — adds a third-party dependency and a pinned
external action version to maintain for a handful of `gh` CLI calls achievable inline
(Principle IV). A persisted-state file (e.g. committing a "known findings" JSON) to track
what's already been reported. Rejected — GitHub's own open-issue list is already the
durable, visible record; a parallel state file would be redundant and could drift from
reality (e.g. an issue closed by a human without updating the file).

## Decision: The high-priority label is a new `priority: high` label, applied alongside `bug`

**Rationale**: The repository's current label set (`bug`, `enhancement`, `documentation`,
`duplicate`, `good first issue`, `help wanted`, `invalid`, `question`, `wontfix`,
`AI Generated`, `Claude`) has no priority dimension. FR-011's "marked as high priority"
is most directly satisfied by a dedicated label a maintainer can filter/sort on, created
once (`gh label create "priority: high" --color ...` or via the repo settings) as part of
this feature rather than overloading an unrelated existing label. The issue is also
labeled `bug`, consistent with existing repo convention for defects, since a Critical
vulnerability is a defect.

**Alternatives considered**: Reusing `help wanted` or embedding "HIGH PRIORITY" only in
the issue title/body with no label. Rejected — a label is filterable/sortable in GitHub's
UI and API in a way title text is not, and no existing label carries a priority meaning.

## Decision: Dependabot security-update behavior — rely on GitHub's default Dependabot security alerts + version-update PRs, no custom auto-merge

**Rationale**: FR-009 requires findings visible "through the repository's normal GitHub
workflow (e.g., pull requests and/or security alerts)." A standard `dependabot.yml` with
`open-pull-requests-limit` produces version-update PRs; GitHub's repository-level
Dependabot alerts (separate toggle, not part of `dependabot.yml`) surface vulnerabilities
directly. Both are native, zero-additional-code GitHub features. Auto-merge is out of
scope — the spec's edge case explicitly notes a Dependabot PR could fail tests, meaning a
human must review, not auto-merge, so no auto-merge action is added.

**Alternatives considered**: A custom GitHub Action to auto-merge passing Dependabot PRs.
Rejected — out of scope for this spec (not requested by any FR) and conflicts with the
spec's own edge case about failing tests needing human attention.
