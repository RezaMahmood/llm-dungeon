# Data Model: CI/CD Foundation & PR Governance

**Date**: 2026-08-28

**Feature**: CI/CD Foundation & PR Governance (001-ci-cd-foundation)

## Overview

This feature is configuration-driven. The "data model" consists of two primary entities:

1. **Branch Protection Rule** — repository-level configuration on the main branch
2. **CI Validation Workflow** — GitHub Actions workflow definition

These entities define how the repository enforces PR-only access and test-gated merge.

---

## Entity 1: Branch Protection Rule

**Definition**: Repository-level configuration applied to the main branch that enforces pull-request-only changes and requires passing status checks before merge.

**Scope**: Applies to the main branch of the repository; uniform enforcement for all users (no exemptions).

### Configuration Properties

| Property | Type | Required | Value | Rationale |
|----------|------|----------|-------|-----------|
| Branch | string | Yes | "main" | Feature specification requires main branch protection |
| Require pull request before merge | boolean | Yes | true | FR-001: No direct pushes allowed |
| Require status checks to pass | boolean | Yes | true | FR-004: Merge blocked if tests fail |
| Required status checks | array[string] | Yes | ["GitHub Actions"] | Specific workflow specified in CI Validation Workflow entity |
| Require code owner reviews | boolean | No | false | Single developer scenario; not specified in requirements |
| Dismiss stale pull request approvals | boolean | No | true | Best practice: require fresh review on new commits |
| Require commit signatures | boolean | No | false | Not specified; can be added via future amendment |
| Allow auto-merge | boolean | No | false | Ensure explicit PR-based merge only (Principle V) |
| Restrict who can push | boolean | No | false | Uniform enforcement; no exemptions for elevated roles (FR-002) |

### Validation Rules

- **Branch must be "main"**: The feature specifies main branch protection only; other branches are not affected.
- **Require pull request = true**: Non-negotiable per FR-001.
- **Status check required = true**: Non-negotiable per FR-004.
- **At least 1 status check must be configured**: Tests cannot be bypassed.

### State Transitions

The branch protection rule has no state transitions; it is a static configuration that remains in effect until explicitly modified (e.g., via a future amendment or configuration change).

**Lifecycle**:
1. **Configured** (initial): Rule is created via GitHub API or UI
2. **Active** (normal operation): Rule enforces PR-only access and test gating
3. **Modified** (when updated): Configuration values change (e.g., adding additional status checks)
4. **Disabled/Removed** (future, requires amendment): Rule is removed (would revert to no branch protection)

---

## Entity 2: CI Validation Workflow

**Definition**: GitHub Actions workflow that executes the project's full automated test suite on every pull request and reports pass/fail status to GitHub, enabling branch protection to gate merge.

**Scope**: Triggered on every pull request to any branch; status is reported to branch protection rule for main branch enforcement.

### Workflow Structure

```yaml
# File: .github/workflows/test.yml (or equivalent name)
name: Test Suite
on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  test:
    runs-on: ubuntu-latest  # Standard GitHub-hosted runner
    timeout-minutes: 30     # 30-minute timeout per spec
    steps:
      - uses: actions/checkout@v3
      - name: Set up [Language/Runtime]
        run: |
          # Project-specific runtime setup
      - name: Install dependencies
        run: |
          # Project-specific dependency installation
      - name: Run test suite
        run: |
          # Project-specific test command (e.g., pytest, npm test)
```

### Configuration Properties

| Property | Type | Value | Rationale |
|----------|------|-------|-----------|
| Trigger event | string | pull_request | Required by FR-003: "every pull request" triggers workflow |
| PR event types | array[string] | [opened, synchronize, reopened] | Re-run on new commits (synchronize), reopened after close |
| Runner | string | ubuntu-latest | Standard GitHub-hosted runner; no special environment needed |
| Timeout | integer (minutes) | 30 | FR-004a: CI must complete within 30 minutes |
| Job name | string | test | Descriptive; identifies the status check in branch protection |
| Steps | sequence | Checkout → Setup → Install → Test | Standard workflow pattern |

### Validation Rules

- **Timeout must be exactly 30 minutes**: Per clarified requirement in spec.
- **Test command must exit with status 0 on success, non-zero on failure**: GitHub Actions interprets exit code as workflow success/failure.
- **Workflow must complete (not time out)**: If timeout is exceeded, workflow fails and merge is blocked (per design).
- **Test suite must be idempotent**: Running the test suite multiple times must yield consistent results (no side effects between runs).

### State Transitions

The workflow has no persistent state. On each PR event:

1. **Triggered** → Workflow job starts on runner
2. **Running** → Steps execute sequentially
3. **Completed** (Success or Failure) → Status is reported to GitHub
   - Success → PR status check passes → merge eligible
   - Failure → PR status check fails → merge blocked
   - Timeout → Treated as failure → merge blocked

**Error Handling**:
- If any step fails (non-zero exit code), the job fails and reports failure to GitHub
- If timeout is exceeded, GitHub Actions marks the job as failed
- No retry logic; PR author must fix the issue and push a new commit (which re-triggers the workflow)

---

## Relationships

```
Branch Protection Rule
  └── requires →  CI Validation Workflow
                   (status check "GitHub Actions" / "test")

Pull Request
  └── triggers →  CI Validation Workflow
                   (on opened/synchronize/reopened)
  └── gated by →  Branch Protection Rule
                   (merge blocked if tests fail or review not approved)
```

---

## Configuration Artifacts

### In Version Control (.github/workflows/test.yml)

The GitHub Actions workflow YAML file is the primary configuration artifact. It is:
- Version-controlled (tracked in git)
- Reviewed via pull request (before merge to main)
- Executable (tests are run against every PR)
- Self-documenting (YAML structure describes the workflow)

### In GitHub Repository Settings

The branch protection rule is:
- Configured via GitHub UI or GitHub API (REST or GraphQL)
- NOT version-controlled (stored in GitHub repository metadata)
- Applied uniformly to all users
- Documented in this data-model.md

---

## Scale & Performance

**Scale**: Single repository, single main branch, one branch protection rule, one CI workflow.

**Performance**: 
- CI workflow must complete within 30 minutes (timeout enforcement)
- No per-step SLA specified (covered by overall 30-minute budget)
- Workflow execution time depends on project's test suite (this feature runs it, does not optimize it)

**Future Scaling Considerations** (not applicable now, per Principle IV):
- If test suite grows beyond 30 minutes, consider parallelizing CI jobs
- If multiple branches need protection, create additional branch protection rules
- If multiple workflows are needed (lint, type-check, security scan), create separate workflows or parallel jobs

---

## Summary

The data model defines two tightly coupled entities:

1. **Branch Protection Rule**: Repository configuration that enforces PR-only access and gates merge on passing tests
2. **CI Validation Workflow**: Executable automation that runs tests, reports status, and enables the branch protection rule to enforce merge gating

Together, they implement the project constitution's CI/CD principles (Principles I & V) as mechanical, enforceable guarantees.
