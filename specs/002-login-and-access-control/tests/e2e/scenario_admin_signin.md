# E2E Scenario: Administrator Sign-In

**User Story**: US2 — Administrator Signs In and Reaches Administration Page

## Prerequisites

- A test Microsoft account on the allow-list with an active `CapabilityAssignment` of `Administrator` only

## Steps

1. Open the application login page (`/login`)
2. Click "Sign in with Microsoft"
3. Complete sign-in with the test account
4. Observe redirect to `/menu`

## Expected Outcome

- `GET /api/auth/me` returns `{"hasPlayer": false, "hasAdministrator": true}`
- Menu shows "Administration"
- Menu does NOT show "Start or Continue Game"

## Validation

- Navigate to `/admin` → expect 200 (not 403)
- Navigate to `/game` → expect inline "Access not granted" message (not a redirect)
