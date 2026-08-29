# E2E Scenario: Unauthorized User Denied

**User Story**: US3 — Unauthorized Access Denied

## Prerequisites

- A valid Microsoft account that has NO entry in `allowListEntries`

## Steps

1. Open the application login page (`/login`)
2. Click "Sign in with Microsoft"
3. Complete sign-in with the test account (Microsoft auth succeeds)

## Expected Outcome

- `POST /api/auth/login` returns `403 Forbidden` with `{"error": "access_denied", "message": "Access not granted"}`
- No menu or application content is shown
- The response does not reveal whether the account exists in the allow-list

## Validation

- Direct navigation to `/menu` is denied (redirected to `/login` if unauthenticated, or shown "Access not granted" if authenticated-but-denied)
- Direct `fetch('/api/auth/me')` with the account's token returns 403, not 200
