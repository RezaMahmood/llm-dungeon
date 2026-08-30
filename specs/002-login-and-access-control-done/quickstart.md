# Quickstart: Validate Login and Access Control

**Date**: 2026-08-28

**Feature**: Login and Access Control (002-login-and-access-control)

This guide provides step-by-step validation scenarios to confirm the login and access control feature works end-to-end. Each scenario is independent and can be run in any order.

---

## Prerequisites

Before running validation scenarios, ensure:

1. **Azure AD app registration is configured** (see [research.md](research.md) for MSAL setup details)
2. **Azure SQL Database or Table Storage has allow-list table** populated with test users
3. **Capability assignments are configured** for test users (Player, Administrator, or both)
4. **Backend Azure Functions are deployed** with `/api/auth/login`, `/api/auth/me`, and capability-gated endpoints
5. **Frontend MSAL is configured** with the correct tenant ID, app ID, and redirect URI
6. **Test Microsoft accounts are available** (at least 3: Player-only, Admin-only, Denied account)
7. **Application is running locally or deployed** and accessible via HTTPS

---

## Validation Scenario 1: Player Signs In Successfully

**Objective**: Verify that a user with Player capability can sign in and see the game menu item (User Story 1).

**Setup**:
- Test account: User with Player capability (e.g., player@outlook.com)
- Account must be on the allow-list
- Account must have "Player" capability assigned
- No Administrator capability

**Steps**:

1. Open the application login page
2. Click "Sign in with Microsoft"
3. You are redirected to Microsoft's sign-in page
4. Sign in with the test account (player@outlook.com)
5. Grant consent (if prompted)
6. You are redirected back to the application

**Expected Outcome**:
- Authentication succeeds (no 401 error)
- Menu is displayed showing "Start or Continue Game"
- Menu does NOT show "Administration"
- Capabilities returned from `/api/auth/me` include only "Player"

**Passing Criteria**:
- Sign-in completes without error
- Menu shows correct capability-based items
- No 403 Forbidden or access denied message

---

## Validation Scenario 2: Administrator Signs In Successfully

**Objective**: Verify that a user with Administrator capability can sign in and see the admin menu item (User Story 2).

**Setup**:
- Test account: User with Administrator capability (e.g., admin@outlook.com)
- Account must be on the allow-list
- Account must have "Administrator" capability assigned
- No Player capability

**Steps**:

1. Open the application login page
2. Click "Sign in with Microsoft"
3. Sign in with the test account (admin@outlook.com)
4. Grant consent (if prompted)
5. You are redirected back to the application

**Expected Outcome**:
- Authentication succeeds
- Menu is displayed showing "Administration"
- Menu does NOT show "Start or Continue Game"
- Capabilities returned from `/api/auth/me` include only "Administrator"

**Passing Criteria**:
- Sign-in completes without error
- Menu shows correct capability-based items
- No 403 Forbidden

---

## Validation Scenario 3: Dual-Capability User Signs In

**Objective**: Verify that a user with both Player and Administrator capabilities can see both menu items.

**Setup**:
- Test account: User with both Player and Administrator capabilities (e.g., dual@outlook.com)
- Account must be on the allow-list
- Account must have both "Player" and "Administrator" capabilities assigned

**Steps**:

1. Open the application login page
2. Click "Sign in with Microsoft"
3. Sign in with the dual-capability account
4. Grant consent (if prompted)
5. You are redirected back to the application
6. Verify both menu items are visible
7. Click "Start or Continue Game" → Verify navigation succeeds
8. Return to menu
9. Click "Administration" → Verify navigation succeeds

**Expected Outcome**:
- Authentication succeeds
- Menu shows both "Start or Continue Game" AND "Administration"
- Both menu items are clickable
- Navigation to both areas succeeds without 403 errors
- Capabilities include both "Player" and "Administrator"

**Passing Criteria**:
- Both menu items visible
- No re-login required when navigating between game and admin
- Both destinations are reachable

---

## Validation Scenario 4: Unauthorized Account Is Denied (User Story 3)

**Objective**: Verify that an account not on the allow-list cannot sign in (User Story 3).

**Setup**:
- Test account: A valid Microsoft account that is NOT on the allow-list (e.g., unauthorized@gmail.com)
- Ensure this account does not exist in the Allow-List Entry table

**Steps**:

1. Open the application login page
2. Click "Sign in with Microsoft"
3. Sign in with the unauthorized account
4. Grant consent (if prompted)
5. You are redirected back to the application

**Expected Outcome**:
- User completes Microsoft sign-in successfully
- Application receives a valid token
- Application checks allow-list and finds user is NOT allowed
- Application displays an error message: "Access not granted" (generic, no account-enumeration reveal)
- No menu or application content is shown
- User remains on login screen or error page

**Passing Criteria**:
- Sign-in to Microsoft succeeds (user is authentic)
- Application-level access is denied
- Error message is generic (does not reveal whether account exists in system)
- No menu or protected content is exposed

---

## Validation Scenario 5: Allowed User with No Capabilities

**Objective**: Verify that an allowed user with no assigned capabilities sees a clear message.

**Setup**:
- Test account: User on the allow-list but with no capabilities (e.g., future@outlook.com)
- Account is in Allow-List Entry table with `date_removed = NULL`
- Account has NO rows in Capability Assignment table

**Steps**:

1. Open the application login page
2. Click "Sign in with Microsoft"
3. Sign in with the test account
4. Grant consent (if prompted)
5. You are redirected back to the application

**Expected Outcome**:
- User completes Microsoft sign-in
- User is on the allow-list
- Application displays a message: "Access provisioned but no roles assigned. Contact your administrator."
- No menu items are shown (no game, no admin)
- User sees a clear next action (contact administrator)

**Passing Criteria**:
- Sign-in succeeds
- Message clearly explains the situation (not an error, but a configuration state)
- No menu items available
- User can sign out and try a different account

---

## Validation Scenario 6: Sign-In Cancelled by User

**Objective**: Verify that cancelling the Microsoft sign-in flow returns user to login screen safely.

**Setup**:
- Application is on login page
- MSAL is configured correctly

**Steps**:

1. Open the application login page
2. Click "Sign in with Microsoft"
3. You are redirected to Microsoft's sign-in page
4. Close the sign-in window or click "Back" instead of signing in
5. You are returned to the application

**Expected Outcome**:
- Application detects the cancelled sign-in
- User is returned to the login page (not an error page)
- A message is displayed: "Sign in was cancelled. Please try again." (or similar)
- User can click the button again to retry

**Passing Criteria**:
- User can retry sign-in after cancellation
- No error state persists
- Application is usable after cancellation

---

## Validation Scenario 7: Menu Reflects Capability Changes

**Objective**: Verify that capability changes (e.g., adding a role) are reflected in the menu on next refresh or navigation.

**Setup**:
- Test account: User with Player capability only (e.g., player@outlook.com)
- User is currently signed in and viewing the game menu

**Steps**:

1. User is signed in and can see "Start or Continue Game" menu
2. Administrator adds "Administrator" capability to this user (external action, e.g., database update)
3. User clicks "Refresh" button or navigates to another page
4. Application calls `/api/auth/me` to fetch updated capabilities
5. Menu is re-rendered

**Expected Outcome**:
- Before refresh: Menu shows only "Start or Continue Game"
- After refresh: Menu shows both "Start or Continue Game" AND "Administration"
- No re-login required
- Change is detected and reflected in next menu render

**Passing Criteria**:
- Capability changes are reflected on next refresh
- No manual re-login required
- Menu updates smoothly

---

## Validation Scenario 8: Endpoint-Level Capability Enforcement

**Objective**: Verify that capability checks are enforced at API endpoints, not just in the menu.

**Setup**:
- Test account: User with Player capability only
- Test account must be signed in with a valid token

**Steps**:

1. User is signed in as Player-only
2. Using a REST client (e.g., curl, Postman) or browser console, call:
   ```bash
   curl -H "Authorization: Bearer <access_token>" \
        https://yourapp.azurewebsites.net/api/manage/stories
   ```
3. Observe the response

**Expected Outcome**:
- Request includes valid token (user is authenticated)
- Backend checks user's capabilities
- User lacks Administrator capability
- Response is 403 Forbidden with message: "You do not have permission to access this resource"
- No admin data is returned

**Passing Criteria**:
- Menu-only gating is not sufficient; endpoint enforces capability
- User cannot bypass menu and access privileged endpoints
- Consistent error response across all capability-gated endpoints

---

## Validation Scenario 9: Session Persistence Across Navigation

**Objective**: Verify that user remains authenticated when navigating between pages without re-signing in.

**Setup**:
- Test account: User with both Player and Administrator capabilities (dual@outlook.com)
- User is signed in

**Steps**:

1. User is signed in and viewing the menu
2. Click "Start or Continue Game" → Navigate to game page
3. From game page, click menu or use navigation to return to menu
4. Click "Administration" → Navigate to admin page
5. From admin page, navigate back to game page
6. Verify no re-login is required at any step

**Expected Outcome**:
- Authentication token is maintained across all navigations
- User does not need to sign in again
- Bearer token is included in all API requests
- All endpoints accept the token without re-authentication

**Passing Criteria**:
- Session persists across navigation
- No 401 Unauthorized errors due to missing token
- No forced re-login

---

## Validation Scenario 10: Token Expiry and Refresh

**Objective**: Verify that expired tokens are handled gracefully (MSAL automatically refreshes).

**Setup**:
- Test account: User is signed in
- Application is open for an extended period (to trigger token expiry)

**Steps**:

1. User is signed in
2. Wait for access token to approach expiry (or manually expire it for testing)
3. User attempts to navigate or make an API call
4. Observe MSAL's automatic token refresh

**Expected Outcome**:
- Token is automatically refreshed by MSAL (user does not notice)
- No "session expired" error is shown to user
- API calls continue to work with new token
- User remains signed in

**Passing Criteria**:
- Token refresh is automatic and transparent
- No manual re-login required
- User experience is seamless

---

## Validation Scenario 11: Sign-Out and Session Cleanup

**Objective**: Verify that signing out clears the session and returns user to login page.

**Setup**:
- Test account: User is signed in

**Steps**:

1. User is signed in and viewing a menu or application page
2. User clicks "Sign Out" or equivalent button
3. Application calls MSAL's logout method
4. Browser storage is cleared (tokens removed)
5. User is redirected to login page

**Expected Outcome**:
- Token is removed from browser storage
- Session is cleared
- User is redirected to login page
- User cannot access protected pages without re-signing in

**Passing Criteria**:
- Sign-out removes all tokens
- User cannot navigate to protected pages after sign-out
- Fresh sign-in is required to re-access application

---

## Validation Scenario 12: Direct URL Access Without Capability

**Objective**: Verify that accessing a page directly (without menu navigation) still enforces capability checks.

**Setup**:
- Test account: User with Player capability only
- User is signed in

**Steps**:

1. User is signed in as Player-only
2. User manually navigates to the admin page URL (e.g., `https://yourapp.azurewebsites.net/admin`)
3. Observe the response

**Expected Outcome**:
- Frontend attempts to load the admin page
- API call for admin data returns 403 Forbidden
- Frontend displays an error or redirects user back to menu
- User cannot access admin area despite direct URL attempt

**Passing Criteria**:
- Backend enforces capability at endpoint level (not just menu)
- Direct URL access is prevented by API-level checks
- User is prevented from reaching privileged content

---

## Troubleshooting

### Sign-In Button Does Nothing

- **Check**: Is MSAL configured correctly in `public/env.js` or equivalent?
- **Check**: Is the Azure AD app registration ID and tenant ID correct?
- **Check**: Is the redirect URI registered in Azure AD app settings?
- **Action**: Verify MSAL configuration matches Azure AD app registration settings.

### "Access Not Granted" After Successful Microsoft Sign-In

- **Check**: Is the test user's object ID (oid) in the Allow-List Entry table?
- **Check**: Is the `date_removed` column NULL for the user?
- **Action**: Add user to allow-list via database or admin tool.

### Menu Shows No Items (But User Is Signed In)

- **Check**: Does the user have any capability assignments in the Capability Assignment table?
- **Check**: Are the capability rows `date_revoked IS NULL`?
- **Action**: Add Player or Administrator capability to user.

### Capability Changes Don't Take Effect

- **Check**: Did you call `/api/auth/me` or refresh the page?
- **Check**: Are the changes in the database?
- **Check**: Is `date_revoked` correctly set to NULL for active capabilities?
- **Action**: Refresh the page or call `/api/auth/me` to fetch latest capabilities.

### Token Validation Fails in Backend

- **Check**: Is the Azure AD public key URL reachable from the backend?
- **Check**: Is the app registration ID correct in the backend config?
- **Check**: Is the token issuer URL correct?
- **Action**: Verify backend is configured with correct tenant ID, app ID, and token validation library.

---

## Summary of Validation

All validation scenarios should pass before the feature is considered complete:

| Scenario | Pass Criteria | Status |
|----------|---------------|--------|
| 1. Player signs in | Menu shows game item only | **Must Pass** |
| 2. Administrator signs in | Menu shows admin item only | **Must Pass** |
| 3. Dual-capability user signs in | Menu shows both items | **Must Pass** |
| 4. Unauthorized account denied | "Access not granted" message shown | **Must Pass** |
| 5. Allowed user with no capabilities | "No capabilities" message shown | **Must Pass** |
| 6. Sign-in cancelled | User returned to login screen | **Must Pass** |
| 7. Capability changes detected | Menu updates on refresh | **Must Pass** |
| 8. Endpoint-level enforcement | 403 returned when accessing without capability | **Must Pass** |
| 9. Session persists across pages | No re-login when navigating | **Must Pass** |
| 10. Token refresh | Automatic, transparent to user | **Must Pass** |
| 11. Sign-out clears session | User cannot access after sign-out | **Must Pass** |
| 12. Direct URL access blocked | 403 returned for unauthorized URLs | **Must Pass** |

---

## Next Steps

Once all validation scenarios pass:

1. **Document Results**: Record test outcomes (pass/fail, date, tester) in a log
2. **Merge Test PRs**: Clean up any test PRs or branches
3. **Proceed to Implementation**: The feature spec and design are validated. Proceed to `/speckit-tasks` to generate the implementation task breakdown
4. **Begin Development**: Start building the login and access control feature per the implementation plan

---

## Notes for Testers

- Use consistent test accounts for repeatability
- Document any edge cases or unexpected behaviors found during testing
- If a scenario fails, investigate the root cause before marking "failed"
- Capability changes may require database updates; coordinate with backend team
- Token expiry testing may require waiting or manual token manipulation (for quick testing, coordinate with backend to reduce token lifetime in dev environment)
