# E2E Scenario: No Capabilities Assigned

**User Story**: US3 — Unauthorized Access Denied (edge case: allowed but unprovisioned)

## Prerequisites

- A test Microsoft account on the allow-list with NO active `CapabilityAssignment` rows

## Steps

1. Open the application login page (`/login`)
2. Click "Sign in with Microsoft"
3. Complete sign-in with the test account

## Expected Outcome

- `GET /api/auth/me` returns `200 OK` with `{"hasPlayer": false, "hasAdministrator": false}` (this is NOT a 403 — the user is allowed, just unprovisioned)
- Menu displays: "Access Provisioned — Your account is registered but no roles have been assigned yet. Contact your administrator to grant access."

## Validation

- Neither "Start or Continue Game" nor "Administration" menu items are shown
- A "Refresh" action re-calls `/api/auth/me` to pick up capability changes without requiring re-login
