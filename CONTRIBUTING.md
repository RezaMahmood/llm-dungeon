# Contributing to LLM Dungeon Adventure

Thank you for contributing! This document outlines our development workflow, branch governance, and CI/CD policies.

---

## 1. Governance & Development Principles

This repository enforces our project constitution ([`.specify/memory/constitution.md`](.specify/memory/constitution.md)) and repository governance policies ([`specs/001-ci-cd-foundation`](specs/001-ci-cd-foundation/spec.md)):

1. **Pull-Request-Only Changes**: Direct commits and pushes to the `main` branch are disabled via GitHub branch rulesets. All changes must be submitted via pull requests.
2. **Automated CI Gating**: Every pull request triggers the automated test suite across backend (Python/pytest) and frontend (React/Node). PRs cannot merge while CI checks are failing.
3. **Review Requirements**: Pull requests require at least 1 approval before they can be merged.
4. **No Direct Admin Bypasses**: Branch rules apply uniformly across all contributors.

---

## 2. Standard PR Workflow

### Step 1: Create a Feature Branch
Create a branch with a descriptive name from latest `main`:
```bash
git checkout main
git pull origin main
git checkout -b feature/my-feature-name
```

### Step 2: Implement and Test Locally
Ensure all relevant tests pass locally before opening a pull request:
```bash
# Run backend tests
pytest -v

# Run frontend tests
cd src/frontend && npm test
```

### Step 3: Open a Pull Request
Push your branch to GitHub and create a pull request targeting `main`:
```bash
git push -u origin feature/my-feature-name
gh pr create --title "feat: describe changes" --body "Summary of changes..."
```

### Step 4: CI Verification & Review
1. Monitor the automated status checks under the PR **Checks** tab.
2. If any test fails, inspect the Actions logs, commit the fix, and push to your feature branch. GitHub Actions will automatically rerun tests on push.
3. Obtain required reviewer approval.

### Step 5: Merge
Once all required status checks have passed and approval is obtained, merge the PR (squash merge is recommended).

---

## 3. Reference Guides
- [CI/CD Validation Guide (`quickstart.md`)](specs/001-ci-cd-foundation/quickstart.md)
- [CI/CD Troubleshooting Guide](docs/CI_CD_TROUBLESHOOTING.md)
- [GitHub Actions Workflows Documentation](.github/workflows/README.md)
