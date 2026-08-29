# E2E Scenario: Player Sign-In

**User Story**: US1 — Player Signs In and Reaches Game Menu

## Prerequisites

- A test Microsoft account on the allow-list (`allowListEntries`) with an active entry
- The same account has an active `CapabilityAssignment` of `Player` only (see `src/backend/db/seed_data.py`)

## Steps

1. Open the application login page (`/login`)
2. Click "Sign in with Microsoft"
3. Complete sign-in with the test account
4. Observe redirect to `/menu`

## Expected Outcome

- `GET /api/auth/me` returns `{"hasPlayer": true, "hasAdministrator": false}`
- Menu shows "Start or Continue Game"
- Menu does NOT show "Administration"

## Validation

- Navigate to `/game` → expect 200 (not 403)
- Navigate to `/admin` → expect inline "Access not granted" message (not a redirect)
