# CI/CD & Branch Governance Troubleshooting Guide

This guide helps diagnose and resolve common issues encountered with GitHub Actions workflows, branch protection rules, and pull request gating.

---

## 1. Workflow Does Not Trigger on PR

### Symptoms
Opening or updating a PR does not show any status checks or workflow runs.

### Causes & Remedies
- **Trigger Event Configuration**: Ensure `.github/workflows/test.yml` includes the proper triggers:
  ```yaml
  on:
    pull_request:
      types: [opened, synchronize, reopened]
  ```
- **Actions Disabled**: Check repository settings (`Settings` → `Actions` → `General`) to ensure GitHub Actions is enabled.
- **Workflow on Main Branch**: Workflows defined in PRs must also be committed and merged to `main` to be recognized as default repository checks.

---

## 2. PR Merge Button is Blocked ("Required Status Checks Must Pass")

### Symptoms
The merge button is disabled with a message indicating required status checks are pending or failed.

### Causes & Remedies
- **Failed Unit Tests**: Inspect the failed job logs under the **Checks** tab to identify the failing test assertion.
- **Fix and Rerun**: Fix the code or test locally, commit, and push to your feature branch. GitHub Actions automatically re-evaluates the PR on push (`synchronize` event).
- **Required Check Name Mismatch**: The branch ruleset requires the job named `test`. Ensure `.github/workflows/test.yml` job ID matches `test`.

---

## 3. PR Merge Blocked on Approval ("Review Required")

### Symptoms
All CI tests passed (green checkmarks), but the PR merge button is still grayed out.

### Causes & Remedies
- **Approval Count**: Repository governance requires at least 1 approving review.
- **Self-Approval**: Under single-developer policy, the author may approve their own PR via GitHub UI (`Review changes` → `Approve`) if enabled, or request a review from a collaborator.

---

## 4. Direct Push to `main` is Rejected

### Symptoms
Running `git push origin main` or pushing directly fails with error `GH006: Protected branch update failed`.

### Causes & Remedies
- **Expected Behavior**: Repository governance strictly prohibits direct pushes to `main`.
- **Solution**: Create a feature branch (`git checkout -b feature/my-change`), push to the feature branch, and open a PR.

---

## 5. CI Workflow Timeout

### Symptoms
Workflow run gets cancelled after 30 minutes with a timeout error.

### Causes & Remedies
- **Job Timeout Setting**: Workflows are configured with `timeout-minutes: 30` per spec requirement (FR-004a).
- **Hanging Processes or Network Calls**: Ensure unit/integration tests do not perform unbounded waits, infinite loops, or hang on unmocked external network resources.

---

## 6. Further References
- [CI/CD Validation Guide (`quickstart.md`)](../specs/001-ci-cd-foundation/quickstart.md)
- [Feature Specification](../specs/001-ci-cd-foundation/spec.md)
- [Implementation Plan](../specs/001-ci-cd-foundation/plan.md)
