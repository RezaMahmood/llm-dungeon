# GitHub Actions Workflows

This directory contains the automated workflows and CI/CD pipelines for the **LLM Dungeon Adventure** repository.

---

## Workflows Overview

| Workflow File | Name | Trigger | Description |
| :--- | :--- | :--- | :--- |
| [`test.yml`](test.yml) | **Test Suite** | `pull_request` (opened, synchronize, reopened) | Primary CI test gate. Runs Python backend tests (pytest) and React frontend tests (npm test) on pull requests. Merge gate required status check: `test`. |
| [`backend-deploy.yml`](backend-deploy.yml) | **Backend Deploy** | `push` to `main` (paths: `src/backend/**`) | Packages and deploys Azure Functions backend. |
| [`frontend-deploy.yml`](frontend-deploy.yml) | **Frontend Deploy** | `push` to `main` (paths: `src/frontend/**`) | Builds and deploys React frontend to Azure Static Web Apps. |
| [`infrastructure-tests.yml`](infrastructure-tests.yml) | **Infrastructure Tests** | `pull_request` (paths: `infrastructure/**`) | Validates Terraform configuration and executes infrastructure unit tests. |
| [`terraform-validate.yml`](terraform-validate.yml) | **Terraform Validate** | `pull_request` (paths: `infrastructure/**`) | Runs `terraform validate` and format checks. |
| [`terraform-apply.yml`](terraform-apply.yml) | **Terraform Apply** | `push` to `main` (paths: `infrastructure/**`) | Applies Terraform changes to provision Azure resources. |

---

## Test Suite Workflow (`test.yml`)

### Job Details
1. **`test` (Backend Test Suite)**:
   - **Runner**: `ubuntu-latest`
   - **Timeout**: 30 minutes (per FR-004a)
   - **Environment**: Python 3.11
   - **Steps**:
     - Checkout code (`actions/checkout@v4`)
     - Setup Python runtime (`actions/setup-python@v4`)
     - Upgrade pip and install dependencies from `requirements*.txt` files
     - Execute `pytest -v` across all test suites
   - **Required Status Check**: This job registers the `test` check required by repository branch rulesets.

2. **`frontend-test` (Frontend Test Suite)**:
   - **Runner**: `ubuntu-latest`
   - **Timeout**: 30 minutes
   - **Environment**: Node.js 24
   - **Steps**:
     - Check if `src/frontend/package.json` exists
     - Install dependencies (`npm install`)
     - Execute frontend tests (`npm test`)

---

## Local Verification

Before pushing, you can execute the same checks locally:

```bash
# Backend pytest suite
pytest -v

# Frontend suite
cd src/frontend && npm test
```
