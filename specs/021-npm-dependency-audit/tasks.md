---

description: "Task list for Frontend Dependency Security & Freshness Audit (021)"
---

# Tasks: Frontend Dependency Security & Freshness Audit

**Input**: Design documents from `/specs/021-npm-dependency-audit/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ci-audit-step.md, quickstart.md

**Tests**: No new automated test cases are requested by this feature (it adds a CI gate and
performs dependency maintenance); the existing `src/frontend` vitest suite is the
regression check for every remediation task and is run, not extended.

**Organization**: Tasks are grouped by user story per spec.md's priorities (US1, US2, US3).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

## Path Conventions

Web app structure already in the repo: `src/frontend/` (React/Vite), `.github/workflows/`
at repo root. No new top-level directories are introduced.

---

## Phase 1: Setup

**Purpose**: Confirm the working baseline before any change is made.

- [X] T001 Run `npm install` in `src/frontend` and capture the current `npm audit --json`
  output as the pre-remediation baseline (already captured in
  `specs/021-npm-dependency-audit/research.md` — verify it still matches by re-running
  `npm audit` in `src/frontend`; update research.md's baseline section if it has drifted)

**Checkpoint**: Baseline confirmed — proceed to Foundational phase.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Nothing in this feature requires shared scaffolding beyond the baseline
captured in Phase 1 — there is no database, auth, or routing layer to stand up. This
phase is intentionally minimal.

**⚠️ CRITICAL**: No user story work can begin until Phase 1 is complete.

*(No foundational tasks beyond Phase 1 — User Story 1's CI-gate work and User Story 2's
remediation work touch disjoint files (`test.yml`+`package.json` scripts vs.
`package.json` dependency versions) and can proceed in either order, though CI (US1)
should land first so US2's remediation PR is itself checked by the new gate.)*

**Checkpoint**: Foundation ready — user story implementation can now begin.

---

## Phase 3: User Story 1 - Automated dependency vulnerability check on every change (Priority: P1) 🎯 MVP

**Goal**: Every PR touching `src/frontend`'s npm dependencies is automatically checked
for known vulnerabilities; High/Critical findings block merge; all findings are reported
with package, installed version, severity, and fixed version; Critical findings also
auto-create a deduplicated, high-priority GitHub issue.

**Independent Test**: Open a PR that adds/retains a vulnerable frontend package and
confirm the PR's `frontend-test` check fails with a readable finding; open a PR with no
qualifying vulnerabilities and confirm the check passes; confirm a Critical finding opens
exactly one `priority: high` issue even across repeated runs.

### Implementation for User Story 1

- [X] T002 [US1] Add an `"audit:frontend": "npm audit --audit-level=high"` script to
  `src/frontend/package.json` `scripts` block, per
  `specs/021-npm-dependency-audit/contracts/ci-audit-step.md`
- [X] T003 [US1] Add a "Run dependency vulnerability audit" step to the `frontend-test`
  job in `.github/workflows/test.yml`, immediately after the existing "Install
  dependencies" step and gated on the same `steps.check.outputs.exists == 'true'`
  condition, running `npm run audit:frontend` (working directory already defaults to
  `src/frontend` via the job's `defaults.run.working-directory`)
- [X] T004 [US1] Add a second sub-step (or a follow-on `run:` line) in that same CI step
  that also runs plain `npm audit` (no `--audit-level`, non-fatal) so the full
  human-readable report — including Low/Moderate findings with package name, installed
  version, severity, and fixed version per FR-004 — is always printed to the job log
  regardless of whether the blocking check above passes or fails; ensure this does not
  mask the blocking step's exit code (run it as its own step, not chained with `&&`/`;`
  after the blocking command)
- [X] T005 [US1] Add `permissions: { contents: read, issues: write }` to the
  `frontend-test` job in `.github/workflows/test.yml` (job currently has no explicit
  `permissions` block, so this narrows/declares it explicitly rather than relying on the
  repo default), required for the issue-creation step in T006
- [X] T006 [US1] Add an "Open high-priority issue for Critical findings" step to the
  `frontend-test` job, after the audit steps from T003/T004, implementing the exact
  script in `specs/021-npm-dependency-audit/contracts/ci-audit-step.md`'s
  "Critical-finding issue-creation step" section: parse `npm audit --json` for
  `severity == "critical"` entries, and for each, search open issues by the deterministic
  title `[dependency-audit] Critical: <package>` via `gh issue list --search`, creating a
  new issue labeled `priority: high` + `bug` (with package/version/severity/fixed-version
  in the body, per FR-004/FR-011) only if no matching open issue already exists (FR-011
  dedupe)
- [X] T007 [US1] Ensure the `priority: high` GitHub label exists on the repository (`gh
  label create "priority: high" --color <hex> --description "High-priority finding
  requiring prompt attention"` — skip if it already exists), since T006's `gh issue
  create --label "priority: high"` fails if the label is undefined
- [X] T008 [US1] Verify locally: from `src/frontend`, run `npm run audit:frontend` and
  confirm it exits non-zero against the current (pre-remediation) baseline (7
  vulnerabilities including 1 high + 1 critical, per research.md) — confirming the gate
  actually triggers on today's known-bad state before it's relied upon to catch future
  regressions

**Checkpoint**: User Story 1 is fully implemented — the CI gate exists and correctly
fails on the current baseline, and the Critical-finding issue-creation step is wired in
(its actual firing/dedupe behavior is verified against the real repo in Phase 6's
quickstart validation and T017 acceptance, since it needs a real CI run with a live
`GITHUB_TOKEN`). It does not yet need to pass, since remediation (US2) hasn't happened;
the gate failing on real, existing vulnerabilities is expected and correct at this
checkpoint.

---

## Phase 4: User Story 2 - Initial remediation of the current frontend dependency set (Priority: P2)

**Goal**: Every currently-flagged frontend npm package (per the research.md baseline) is
upgraded or replaced so the audit from User Story 1 reports zero High/Critical findings,
with no observable behavior change and the existing test suite still passing.

**Independent Test**: Run `npm audit` in `src/frontend` before and after remediation;
confirm the "after" run reports no High/Critical findings, and `npm test` / `npm run
build` succeed after each change.

### Implementation for User Story 2

- [X] T009 [US2] Upgrade `vitest` (and its `@vitest/mocker`/`vite-node` transitive chain)
  to `^4.1.11` in `src/frontend/package.json`, resolving the critical `vitest` and
  moderate `@vitest/mocker`/`vite-node` findings from research.md's baseline; run `npm
  install` to regenerate `package-lock.json`
- [X] T010 [US2] Upgrade `vite` (and `@vitejs/plugin-react` if its peer range requires it)
  to a version `>=8.2.2` in `src/frontend/package.json`, resolving the high-severity
  `esbuild`/`vite` finding from research.md's baseline; run `npm install` to regenerate
  `package-lock.json` (coordinate with T009 — both touch the vite/vitest toolchain, do
  sequentially not in parallel)
- [X] T011 [P] [US2] Upgrade `react-router-dom` to `^7.18.3` in
  `src/frontend/package.json`, resolving the moderate `react-router`/`react-router-dom`
  open-redirect and constructor-injection findings from research.md's baseline; run `npm
  install` to regenerate `package-lock.json`
- [X] T012 [US2] Fix any breaking-change fallout from T009-T011 in `src/frontend/src/`:
  update `vite.config.js`/`vitest` config for the new major versions if their config API
  changed, and update any `react-router-dom` v6-only API usage (e.g. route element
  patterns) found by `npm run build` / `npm test` failures to the v7 equivalent — scope
  is whatever the build/test run in T013 actually reports, not a speculative rewrite
- [X] T013 [US2] Run `npm test` and `npm run build` in `src/frontend`; fix any failures
  surfaced (see T012) until both succeed, confirming FR-007/SC-005 (no observable
  behavior change, existing suite passes)
- [X] T014 [US2] Run `npm audit` (and `npm run audit:frontend` from T002) in
  `src/frontend`; confirm zero High/Critical findings remain (SC-002); update
  `specs/021-npm-dependency-audit/research.md`'s baseline section with the new "after"
  result for the record
- [X] T015 [US2] Review `npm outdated` output in `src/frontend` for any remaining flagged
  package that FR-005 requires checking beyond vulnerabilities — deprecated/unmaintained
  packages per npm registry deprecation flags — and confirm no direct dependency in
  `package.json` is currently npm-deprecated; if one is found, replace it with an
  actively-maintained equivalent (only IF such a package is found — this task may be a
  no-op confirmation)

**Checkpoint**: User Stories 1 AND 2 both work together — the CI gate from US1 now passes
because US2's remediation cleared every High/Critical finding, so the T006 issue-creation
step no longer fires on ordinary PRs.

---

## Phase 5: User Story 3 - Ongoing automated reporting of packages needing updates (Priority: P3)

**Goal**: GitHub Dependabot is configured to monitor `src/frontend`'s npm manifest on a
recurring schedule, surfacing future vulnerabilities and available updates automatically.

**Independent Test**: Confirm `.github/dependabot.yml` is valid and recognized under the
repository's Insights > Dependency graph > Dependabot settings, and that it is scoped to
`src/frontend` on a recurring schedule.

### Implementation for User Story 3

- [X] T016 [US3] Create `.github/dependabot.yml` with an npm entry for
  `directory: "/src/frontend"`, `schedule.interval: "weekly"`, and
  `open-pull-requests-limit: 10`, per
  `specs/021-npm-dependency-audit/contracts/ci-audit-step.md`
- [X] T017 [US3] Confirm (documenting the result in the PR description, not a code
  change) that GitHub's repository-level Dependabot alerts feature (Settings > Code
  security and analysis > Dependabot alerts) is enabled for this repository, since FR-009
  requires that visibility channel alongside the version-update PRs `dependabot.yml`
  produces — enable it if it is currently off (this is a repository setting, not a
  file in the repo)

**Checkpoint**: All three user stories are independently functional — CI blocks new
High/Critical findings and opens high-priority issues for Critical ones (US1), the
current dependency set is clean (US2), and future drift is monitored automatically
(US3).

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and the constitution's mandatory human acceptance gate.

- [ ] T018 [P] Run `specs/021-npm-dependency-audit/quickstart.md` sections 1-5 end-to-end
  (on-demand audit, PR-blocking demonstration, remediation validation, Critical-finding
  issue creation + dedupe, Dependabot visibility) and note results
- [ ] T019 User-verified acceptance (Constitution Principle IX, NON-NEGOTIABLE): the
  requesting user/product owner confirms, against the real GitHub repository — not the
  implementing agent's own local/CI runs — that (a) a deliberately vulnerable test PR is
  blocked by the new required check, (b) the remediated `src/frontend` dependency set
  passes the real PR pipeline, (c) `.github/dependabot.yml` is visible and active under
  the repo's Dependabot settings with alerts enabled, and (d) a deliberately-introduced
  Critical finding creates a `priority: high`-labeled issue and re-running the check does
  not duplicate it (FR-011). This task is not complete until that confirmation is given.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: No additional tasks; Phase 1 alone is the prerequisite.
- **User Story 1 (Phase 3)**: Depends on Phase 1. Independent of US2/US3's files.
- **User Story 2 (Phase 4)**: Depends on Phase 1. Independent of US1's files, but should
  land after US1 (T002) so T008/T014's `npm run audit:frontend` command already exists;
  otherwise use plain `npm audit` in T014 as a fallback.
- **User Story 3 (Phase 5)**: Depends on Phase 1 only; fully independent of US1/US2 files
  (`.github/dependabot.yml` is a new file untouched by either).
- **Polish (Phase 6)**: Depends on US1 + US2 + US3 all being complete.

### User Story Dependencies

- **US1 (P1)**: No dependency on US2/US3 — the gate (and issue-creation step) is correct
  to add even while it's failing against the pre-remediation baseline.
- **US2 (P2)**: No file dependency on US1, but its "done" definition (audit passes) is
  only meaningfully checkable once US1's `npm run audit:frontend` script exists (T002).
- **US3 (P3)**: Fully independent — can be done in parallel with US1/US2.

### Within Each User Story

- US1: T002 before T003/T004 (CI step calls the script T002 adds); T005 before T006
  (permissions must exist before the step that needs them); T007 before T006 fires in a
  real run (label must exist before `gh issue create --label` is called), though T007 can
  be authored/committed in any order relative to T006 since it's a one-time repo-level
  `gh` command, not a workflow YAML dependency; T008 last (verifies the audit gate).
- US2: T009 and T010 touch the same vite/vitest toolchain — do sequentially; T011 is
  independent (`react-router-dom`) and can run in parallel with T009/T010; T012 depends
  on T009-T011 being applied; T013 depends on T012; T014 depends on T013; T015 is
  independent and can run any time after T001.
- US3: T016 before T017 (config file before confirming the paired repo setting).

### Parallel Opportunities

- T011 (`react-router-dom` upgrade) can run in parallel with T009+T010 (vite/vitest
  upgrade) — different dependency, same file (`package.json`) but non-overlapping
  version fields; still run `npm install` once after both edits land to avoid lockfile
  churn, so treat as parallel-authorable, sequential-installed.
- T016 (Dependabot config) can run in parallel with all of Phase 3 and Phase 4 — entirely
  new, unrelated file.
- T007 (create the `priority: high` label) can run in parallel with everything else in
  Phase 3/4/5 — a one-time repo-level `gh label create` call, unrelated to any file edit.
- T018 (quickstart validation) can run in parallel with drafting T019's write-up, though
  T019 itself requires a human, not the agent.

---

## Parallel Example: Kicking off Phase 3 + Phase 5 together

```bash
# US1 CI-gate work and US3 Dependabot config touch disjoint files and have no
# dependency on each other — both can be worked simultaneously:
Task: "Add audit:frontend script + CI step + issue-creation step (T002-T008) in src/frontend/package.json and .github/workflows/test.yml"
Task: "Create .github/dependabot.yml (T016) for the npm ecosystem, src/frontend directory"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (confirm baseline).
2. Complete Phase 3: User Story 1 (CI gate + Critical-finding issue creation — correctly
   fires against today's known vulnerabilities).
3. **STOP and VALIDATE**: Open a throwaway PR, confirm the gate fires as expected and a
   high-priority issue is opened for the existing critical `vitest` finding.
4. This alone delivers FR-001–FR-004 and FR-011: automated detection, reporting, and
   high-priority escalation wired into CI, even before remediation.

### Incremental Delivery

1. Phase 1 → Phase 3 (US1) → gate exists, currently red against real findings; a
   high-priority issue exists for the pre-existing critical finding.
2. Phase 4 (US2) → gate turns green; dependency set is clean; the FR-011 issue can be
   closed since its finding is resolved.
3. Phase 5 (US3) → future drift now monitored automatically.
4. Phase 6 → quickstart validation + mandatory human acceptance (T019) closes the
   feature.

### Notes

- No test-writing tasks are included — this feature adds CI configuration and performs
  dependency maintenance; the existing vitest suite is the regression guard (per
  Constitution Principle I, "no new application behavior" needs no new tests).
- T019 (user-verified acceptance) is NON-NEGOTIABLE per Constitution Principle IX and
  MUST NOT be marked complete by the implementing agent on the strength of its own
  testing.
