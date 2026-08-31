# Feature Specification: Frontend Dependency Security & Freshness Audit

**Feature Branch**: `021-npm-dependency-audit`

**Created**: 2026-08-30

**Status**: Draft

**Input**: User description: "front end react should use up to date components that are not subject to memory leaks or security vulnerabilities. a check needs to be done using npm to ensure that components meet this requirement. In the event a component does not have an up to date version that is secure and community approved then it should be replaced with an equivalent. To mitigate this going forward, github dependabot should be configured to report on packages that need updating"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Automated dependency vulnerability check on every change (Priority: P1)

As a maintainer, I want every pull request that touches the frontend to be automatically checked for npm packages with known security vulnerabilities, so that an unsafe package can never merge into the frontend unnoticed.

**Why this priority**: This is the enforcement mechanism that makes the rest of the feature durable. Without a check wired into the normal contribution flow, "keep dependencies secure" is a one-time cleanup that immediately starts decaying again.

**Independent Test**: Can be fully tested by opening a pull request that introduces or retains a frontend npm package with a known vulnerability and confirming the pull request is blocked from merging with a clear description of the finding; and by opening a pull request with no vulnerable packages and confirming the check passes.

**Acceptance Scenarios**:

1. **Given** a pull request that changes the frontend's npm dependencies, **When** the dependency check runs, **Then** it reports any package with a known security vulnerability, including the affected package name, installed version, and severity.
2. **Given** a pull request whose frontend npm dependencies contain a vulnerability at or above the blocking threshold, **When** the check completes, **Then** the pull request is prevented from merging until the vulnerability is resolved.
3. **Given** a pull request whose frontend npm dependencies contain no vulnerabilities at or above the blocking threshold, **When** the check completes, **Then** the pull request is allowed to proceed to merge (subject to the project's other merge gates).
4. **Given** the check identifies a vulnerability of Critical severity, **When** the check completes, **Then** a GitHub issue is automatically created documenting the finding (package, installed version, severity, fixed version if available) and is marked with a high-priority label.
5. **Given** a Critical-severity finding for a specific package already has an open, automatically-created issue, **When** a later check run detects that same finding again, **Then** no duplicate issue is created for it.

---

### User Story 2 - Initial remediation of the current frontend dependency set (Priority: P2)

As a maintainer, I want the frontend's current npm packages reviewed now, so that any package that is outdated, carries a known security vulnerability, or is no longer actively maintained by its community is replaced with a current, secure, actively-maintained equivalent before this feature is considered complete.

**Why this priority**: Turning on an automated check (User Story 1) only catches new risk going forward; it does nothing about risk that already exists in the frontend today. This story closes that starting gap.

**Independent Test**: Can be fully tested by running the dependency check against the frontend's dependency set before and after remediation and confirming the "before" run identifies findings that the "after" run no longer reports, with the frontend application continuing to build and pass its existing automated tests after each replacement.

**Acceptance Scenarios**:

1. **Given** the frontend's current npm dependency set, **When** the dependency check is run against it, **Then** a report is produced listing every package that fails the freshness/security/maintenance criteria.
2. **Given** a package flagged in that report that has a newer version resolving the finding, **When** the package is upgraded to that version, **Then** the frontend continues to build and its existing automated tests continue to pass.
3. **Given** a package flagged in that report that has no newer version resolving the finding, **When** a replacement package is selected, **Then** the replacement provides equivalent functionality, is itself current/secure/actively maintained, and the frontend continues to build and its existing automated tests continue to pass after substitution.
4. **Given** the remediation is complete, **When** the dependency check is re-run, **Then** it reports no remaining findings at or above the blocking threshold.

---

### User Story 3 - Ongoing automated reporting of packages needing updates (Priority: P3)

As a maintainer, I want GitHub Dependabot configured for the frontend's npm packages, so that newly-disclosed vulnerabilities and newly-available updates are surfaced automatically over time, without someone needing to remember to re-run a manual audit.

**Why this priority**: This is the forward-looking mitigation the user explicitly asked for ("to mitigate this going forward"). It is lower priority than Stories 1-2 because it monitors for *future* drift, whereas the CI check (Story 1) is what actually blocks unsafe code from merging today.

**Independent Test**: Can be fully tested by configuring Dependabot for the frontend's npm package manifest and confirming it produces update/vulnerability notifications (e.g., pull requests or alerts) on a recurring schedule, verifiable by inspecting the repository's Dependabot configuration and its resulting alerts/PRs.

**Acceptance Scenarios**:

1. **Given** the frontend's npm package manifest, **When** Dependabot is configured for this repository, **Then** it monitors that manifest on a recurring schedule for available updates and known vulnerabilities.
2. **Given** Dependabot detects a package with an available update or a disclosed vulnerability, **When** its scheduled check runs, **Then** it opens or updates a report (e.g., a pull request or security alert) describing the finding.

---

### Edge Cases

- What happens when a vulnerable package has no newer secure version and no reasonable community-approved replacement exists (e.g., it is the only package providing a niche capability the frontend depends on)?
- How does the check handle vulnerabilities reported in a transitive (indirect) dependency that the frontend does not declare directly and cannot upgrade in isolation?
- What happens when resolving a finding requires a breaking major-version upgrade of a package that is deeply integrated into the frontend?
- How are findings that have no fix currently available (only a future fix promised by the package's maintainers) tracked so they are not silently lost?
- What happens when Dependabot proposes an update whose accompanying pull request causes the frontend's automated tests to fail?
- What happens when the same Critical finding is detected again on a subsequent check run while its automatically-created issue is still open? (See FR-011: no duplicate issue is created; the existing open issue is treated as still tracking it.)
- What happens once a Critical finding's automatically-created issue has been closed (the vulnerability was resolved) and, later, an unrelated new Critical finding appears for the same package? (Treated as a new finding: a new issue is created, since no open issue currently tracks it.)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The project MUST run an automated check, using npm's dependency-scanning capability, that identifies frontend npm packages with known security vulnerabilities.
- **FR-002**: The check in FR-001 MUST run automatically as part of the pull request pipeline for changes affecting the frontend, consistent with this project's existing continuous-integration gate.
- **FR-003**: A pull request MUST be blocked from merging when the check identifies a vulnerability of High or Critical severity. Low and Moderate severity findings MUST still be reported (per FR-004) but MUST NOT block merge.
- **FR-004**: The check MUST report, for each finding, at minimum the affected package name, the installed version, the severity, and a fixed version if one is available.
- **FR-005**: As part of this feature, the frontend's current npm dependency set MUST be reviewed against the check in FR-001 and against package maintenance status, and every package that is outdated, vulnerable, or flagged as deprecated/unmaintained/abandoned (per the npm registry's deprecation flag and release recency) MUST be identified. This maintenance-status signal, together with the vulnerability check in FR-001 (which also catches any memory-leak-class defect published as a formal security advisory), is the sole proxy used to satisfy the "not subject to memory leaks" requirement, since npm's tooling does not measure runtime memory behavior directly.
- **FR-006**: Every package identified by FR-005 MUST either be upgraded to a version that resolves the finding, or replaced with a functionally equivalent package that is current, free of known vulnerabilities, and actively maintained by its community, before this feature is considered complete.
- **FR-007**: Any package upgrade or replacement performed under FR-006 MUST NOT change the frontend's observable behavior for end users, and the frontend MUST continue to pass its existing automated test suite after each change.
- **FR-008**: The project MUST configure GitHub Dependabot to monitor the frontend's npm package manifest on a recurring schedule and to report packages that have available updates or disclosed vulnerabilities.
- **FR-009**: Dependabot's reports MUST be visible to maintainers through the repository's normal GitHub workflow (e.g., pull requests and/or security alerts) so that no separate tool or process is required to see them.
- **FR-010**: The dependency check from FR-001 MUST be re-runnable on demand (not only automatically in CI) so a maintainer can verify the current state of the frontend's dependencies at any time.
- **FR-011**: When the check in FR-001 identifies a vulnerability of Critical severity, the project MUST automatically create a GitHub issue documenting that finding (at minimum the fields required by FR-004: package name, installed version, severity, fixed version if available) and MUST mark that issue as high priority (e.g., a dedicated priority label). If an open, automatically-created issue already exists for that same Critical finding (same package and vulnerability), a new duplicate issue MUST NOT be created for it.

### Key Entities

- **Dependency Finding**: A single reported issue against one frontend npm package — includes the package name, installed version, severity, vulnerability identifier (if security-related), and available fixed version (if any).
- **Dependency Audit Report**: The aggregated set of Dependency Findings produced by one run of the check, used both for the one-time initial remediation (User Story 2) and for each CI run (User Story 1).
- **Dependabot Configuration**: The repository setting that defines which package ecosystem (npm) and manifest location Dependabot monitors, and how often it checks.
- **Critical Finding Issue**: A GitHub issue automatically opened when a Dependency Finding's severity is Critical — carries the finding's details (per FR-004) and a high-priority label; deduplicated per open finding per FR-011.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of pull requests that modify the frontend's npm dependencies are automatically checked for known security vulnerabilities before merge.
- **SC-002**: Zero frontend npm packages remain with a known vulnerability at or above the blocking threshold immediately after this feature's initial remediation is complete.
- **SC-003**: A pull request that introduces a frontend npm package with a vulnerability at or above the blocking threshold is blocked from merging in 100% of cases.
- **SC-004**: Newly disclosed vulnerabilities or available updates in the frontend's npm packages are surfaced to maintainers automatically (without a manual audit) within Dependabot's configured check interval.
- **SC-005**: The frontend continues to build successfully and pass its existing automated test suite immediately after every dependency upgrade or replacement performed under this feature.
- **SC-006**: 100% of Critical-severity findings surfaced by the automated check result in a high-priority GitHub issue existing (either newly created, or an existing open one already tracking that finding) by the time the check run completes.

## Assumptions

- "Up to date" and "community approved" are interpreted as: no known published security vulnerability, not flagged as deprecated/abandoned by its publisher or package registry, and actively receiving maintenance (recent releases) — the standard, verifiable signals npm's own tooling and the npm registry expose. There is no separate, project-defined popularity or adoption threshold beyond this.
- The automated vulnerability check is implemented using npm's built-in audit capability (or the equivalent mechanism already used elsewhere in this project's CI, if one exists) rather than a new third-party scanning service, consistent with the user's instruction that the check be "done using npm."
- This feature covers the frontend's npm dependencies only; the Python backend's dependency hygiene is out of scope for this feature.
- Existing automated tests are assumed sufficient to catch a behavioral regression introduced by a dependency upgrade or replacement; this feature does not introduce new test coverage beyond what FR-007/SC-005 require passing.
- Dependabot's default recurring check interval (daily or weekly, configured per this project's preference) is acceptable; no specific real-time/instant-alert requirement was stated.
- "Marked with high priority" (FR-011) is satisfied by a dedicated GitHub label (e.g. `priority: high`) applied to the automatically-created issue, since this repository has no pre-existing priority-labeling scheme; the label is created as part of this feature if it does not already exist.
- Automatic issue creation (FR-011) is scoped to the CI check in FR-001/User Story 1 (i.e., a Critical finding surfaced by a PR's audit run), not to Dependabot's separate scheduled scan (User Story 3), which already has its own native alert/PR reporting channel (FR-008/FR-009).
