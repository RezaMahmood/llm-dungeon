# Quickstart: Validate CI/CD Foundation & PR Governance

**Date**: 2026-08-28

**Feature**: CI/CD Foundation & PR Governance (001-ci-cd-foundation)

This guide provides step-by-step validation scenarios to confirm the CI/CD foundation feature works end-to-end. Each scenario is independent and can be run in any order.

---

## Prerequisites

Before running validation scenarios, ensure:

1. **GitHub branch protection rule is configured** on the main branch (see [data-model.md](data-model.md) for configuration details)
2. **GitHub Actions workflow is deployed** at `.github/workflows/test.yml` (or equivalent) and is active
3. **Project test suite is present and runnable** (e.g., pytest, npm test, cargo test — whatever the project uses)
4. **You have push access** to the repository and can create pull requests
5. **You have a local clone** of the repository with git configured

---

## Validation Scenario 1: Direct Push is Rejected

**Objective**: Verify that direct pushes to the main branch are rejected (User Story 1, FR-001).

**Steps**:

1. From your local machine, create a test branch and make a trivial change:
   ```bash
   git checkout main
   git pull origin main  # Ensure local main is up-to-date
   git checkout -b test-direct-push
   echo "test" > test.txt
   git add test.txt
   git commit -m "test: attempt direct push"
   ```

2. Attempt a direct push to main:
   ```bash
   git push origin test-direct-push:main
   ```

3. **Expected Outcome**: Push is rejected with an error message similar to:
   ```
   remote: error: GH006: Protected branch update failed for refs/heads/main.
   remote: error: Required status checks are expected. Please try again later.
   ```
   or
   ```
   remote: error: GH006: Protected branch update failed for refs/heads/main.
   remote: error: At least 1 approving review is required
   ```

4. **Passing Criteria**: Push is rejected; cannot bypass branch protection.

---

## Validation Scenario 2: GitHub Actions Workflow Runs on Pull Request

**Objective**: Verify that opening a pull request automatically triggers the CI workflow (User Story 2, FR-003).

**Steps**:

1. From your test branch, push to a feature branch and open a PR:
   ```bash
   git push origin test-direct-push
   ```

2. In GitHub, open a pull request from your feature branch to main.

3. Navigate to the **Checks** tab on the PR (or view the **Status checks** section in the PR description area).

4. **Expected Outcome**: 
   - GitHub Actions workflow is triggered automatically
   - A "Test Suite" job (or equivalent) appears in the checks list
   - Job status changes from "pending" → "in progress" → "completed"
   - Workflow completes within 30 minutes (timeout per spec)

5. **Passing Criteria**: Workflow runs automatically on PR creation; no manual trigger needed.

---

## Validation Scenario 3: PR Merge is Blocked When Tests Fail

**Objective**: Verify that PRs with failing tests cannot merge (User Story 2, FR-004).

**Steps**:

1. Create a feature branch with a deliberate test failure:
   ```bash
   git checkout -b test-failing-test
   # Modify a file to cause a test to fail (e.g., break a unit test assertion)
   git add .
   git commit -m "test: introduce failing test"
   git push origin test-failing-test
   ```

2. Open a pull request from this branch to main.

3. Wait for the GitHub Actions workflow to complete (check the **Checks** tab).

4. **Expected Outcome**:
   - Workflow runs and test suite execution fails
   - Status check shows ✗ (red, failed)
   - Merge button is disabled with message: "Required status checks must pass before merging"

5. **Passing Criteria**: Merge is blocked; failing tests prevent merge.

6. **Cleanup**: Close the PR without merging.

---

## Validation Scenario 4: PR Merge is Allowed When Tests Pass

**Objective**: Verify that PRs with passing tests can proceed toward merge (given reviews are satisfied).

**Steps**:

1. Create a feature branch with a valid change (no test failures):
   ```bash
   git checkout -b test-passing-feature
   echo "# New feature" > new-feature.md
   git add new-feature.md
   git commit -m "docs: add new feature documentation"
   git push origin test-passing-feature
   ```

2. Open a pull request from this branch to main.

3. Wait for the GitHub Actions workflow to complete (check the **Checks** tab).

4. **Expected Outcome**:
   - Workflow runs and test suite execution passes
   - Status check shows ✓ (green, passed)
   - Merge button becomes enabled (if reviewer requirement is met; see Scenario 5)
   - Message shows: "All checks have passed"

5. **Passing Criteria**: 
   - Tests pass → status check passes
   - Merge button is available (given review requirement met)

---

## Validation Scenario 5: Merge is Blocked Without Reviewer Approval

**Objective**: Verify that at least 1 reviewer approval is required before merge (from data-model.md: Branch Protection Rule configuration).

**Steps**:

1. Open a pull request with passing tests (from Scenario 4).

2. With tests passing, check the merge button status.

3. **Expected Outcome**:
   - Even with passing tests, merge button is disabled
   - Message shows: "1 approval is required" or similar

4. Approve the PR (author may self-approve per clarified requirement):
   ```
   In GitHub UI: Click "Review changes" → select "Approve" → submit
   ```

5. **Expected Outcome**:
   - After approval, merge button becomes enabled
   - Message updates: "All checks have passed and approvals are satisfied"

6. **Passing Criteria**: 
   - Merge is blocked without approval
   - Merge is allowed after 1 approval (including author self-approval)

---

## Validation Scenario 6: Rerunning Tests on New Commits

**Objective**: Verify that the CI workflow re-runs when new commits are pushed to the PR (synchronize event).

**Steps**:

1. Open a PR with a passing test (from Scenario 4).

2. Make a new commit and push it:
   ```bash
   git add .
   git commit -m "test: add another change"
   git push origin test-passing-feature
   ```

3. Check the **Checks** tab on the PR.

4. **Expected Outcome**:
   - GitHub Actions workflow is triggered again (new job run appears)
   - Previous test result is replaced with new run
   - New test result completes and updates the status check
   - PR remains mergeable if tests pass

5. **Passing Criteria**: Workflow re-runs automatically on new commits (synchronize event).

---

## Validation Scenario 7: Manual Verification of Branch Protection Rule

**Objective**: Verify the branch protection rule is configured correctly in GitHub (non-executable verification).

**Steps**:

1. Navigate to the repository settings on GitHub.

2. Go to **Settings** → **Branches** → **Branch protection rules**.

3. Click on the rule for the main branch.

4. **Expected Configuration** (see [data-model.md](data-model.md) for details):
   - ✓ Require a pull request before merging
   - ✓ Require status checks to pass
   - ✓ GitHub Actions (or equivalent test job) is listed as required status check
   - ✓ Dismiss stale pull request approvals (recommended)
   - ✓ Allow auto-merge: false (or unchecked)
   - ✓ Restrict who can push to matching branches: false (or unchecked, for uniform enforcement)

5. **Passing Criteria**: All expected settings are configured as shown above.

---

## Troubleshooting

### Workflow Does Not Run
- **Check**: Is `.github/workflows/test.yml` present and committed to main?
- **Check**: Does the workflow have `on: pull_request` trigger?
- **Action**: Verify workflow is pushed to main branch and GitHub Actions is enabled for the repository (Settings → Actions → General).

### Merge Button is Grayed Out But Tests Passed
- **Check**: Is the required reviewer approval satisfied? (See Scenario 5)
- **Check**: Are there other status checks required that are not yet passing?
- **Action**: Review the PR's status checks section for all required checks and their current state.

### Workflow Timeout
- **Check**: Did the workflow exceed 30 minutes?
- **Action**: Check workflow logs (Actions tab) to identify slow test steps. The workflow is working correctly (timeout enforcement is expected); the test suite may need optimization.

### Direct Push Attempt Still Succeeds
- **Check**: Is the branch protection rule applied to main?
- **Check**: Does your GitHub account have admin bypass permissions? (Branch protection should apply uniformly, including to admins.)
- **Action**: Verify rule is configured on the main branch and that "Restrict who can push" is not exempting your account.

---

## Summary of Validation

All validation scenarios should pass before the feature is considered complete:

| Scenario | Outcome | Status |
|----------|---------|--------|
| 1. Direct push rejected | ✓ Push to main is blocked | **Must Pass** |
| 2. Workflow runs on PR | ✓ GitHub Actions executes automatically | **Must Pass** |
| 3. Failing tests block merge | ✓ Merge disabled if tests fail | **Must Pass** |
| 4. Passing tests allow merge | ✓ Merge enabled if tests pass | **Must Pass** |
| 5. Review requirement enforced | ✓ At least 1 approval needed | **Must Pass** |
| 6. Rerun on new commits | ✓ Workflow re-runs on push | **Must Pass** |
| 7. Branch rule configured | ✓ GitHub settings match spec | **Must Pass** |

---

## Next Steps

Once all validation scenarios pass:

1. **Document Results**: Record test outcomes (pass/fail, date, tester) in a validation log (optional but recommended).

2. **Merge Test PRs**: Clean up test pull requests created during validation.

3. **Proceed to Implementation**: The feature specification and design are validated. Proceed to `/speckit-tasks` to generate the detailed implementation task breakdown.

4. **Iterate on Real Development**: Begin using the PR workflow for real feature work (e.g., 002-azure-infrastructure, 003-login, etc.). The CI/CD foundation is now in place.
