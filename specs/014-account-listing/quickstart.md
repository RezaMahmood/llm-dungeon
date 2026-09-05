# Quickstart: Account Listing

**Date**: 2026-09-05

Validates the account-listing behavior described in `spec.md`, on top of the existing `003-account-provisioning-done` setup. See `data-model.md` and `contracts/api.md` for the underlying entity/endpoint details.

## Prerequisites

- Local dev environment set up per repo `README.md` (backend Azure Functions host + Cosmos DB emulator running, frontend dev server running).
- At least one Administrator account signed in locally (the seed administrator, per `003-account-provisioning-done`).

## Backend validation

1. Start the Cosmos DB emulator and the Functions host locally (existing `003` setup — no new service to start).
2. Run the backend test suite, scoped to this feature's area:
   ```bash
   cd src/backend
   pytest tests/unit/test_account_provisioning_service.py tests/integration/test_admin_accounts_endpoint.py -v
   ```
   Expected: all tests pass, including the new/extended ones added for this feature:
   - `list_all` returns entries sorted ascending by email.
   - `GET /api/manage/accounts` reflects a role-merge as a single, updated entry (FR-002).
   - `GET /api/manage/accounts` returns 403 for a non-administrator caller (FR-003).
3. Manual/API-level check (optional, mirrors the automated coverage): as a signed-in administrator, call `GET /api/manage/accounts` and confirm the `accounts` array is alphabetically ordered by `email`.

## Frontend validation

1. Run the frontend test suite, scoped to `AccountList`:
   ```bash
   cd src/frontend
   npm test -- AccountList
   ```
   Expected: all tests pass, including the new assertion that an entry with `bound: false` renders the "Pending first sign-in" label (FR-005).
2. In a browser, sign in as the seed administrator, navigate to the accounts screen (`specs/designs/05-admin-users.html`'s implemented equivalent), and confirm:
   - Entries are listed alphabetically by email.
   - An entry that has never signed in shows "Pending first sign-in".
   - Adding a role to an already-listed email (via the existing add flow) results in one updated row, not two.

## Access-control validation

- Sign in as a non-administrator (Player-only) account and confirm the accounts screen/endpoint denies access, consistent with `002-login-and-access-control` (FR-003) — this should already be covered by the existing `test_list_accounts_returns_403_for_non_administrator` test; no new manual step beyond confirming it still passes.

## Out of scope for this quickstart

- No new deployment step, environment variable, or infrastructure change — nothing to validate in Azure beyond the existing `003-account-provisioning-done` deployment.
