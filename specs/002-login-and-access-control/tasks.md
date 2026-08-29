# Tasks: Login and Access Control

**Input**: Design documents from `/specs/002-login-and-access-control/`

**Prerequisites**: plan.md (✅ complete), spec.md (✅ complete), data-model.md (✅ complete), research.md (✅ complete)

**Dependencies**: Feature 007-azure-infrastructure-provisioning must have Azure Functions app, Cosmos DB serverless account, and Managed Identity configured

**Tests**: All tests are included in this task list (mandatory per spec.md requirement FR-012)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story

## Format: `- [ ] [ID] [P?] [Story?] Description with file path`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

**Implementation status (2026-08-29)**: All application code, tests, and docs are
implemented. Eleven tasks remain unchecked because they require either live Azure
infrastructure from 007 (T008, T009, T011, T012 — provisioning real resources) or
manual verification this environment cannot perform (T077, T078, T079, T082–T085,
T088, T090 — no Node.js/npm available here to run frontend tests, and no real
browsers/devices/production deployment to test against). See the implementation
summary for details.

## Path Conventions

- **Backend**: `backend/` (Python Azure Functions)
- **Frontend**: `frontend/` (React SPA)
- **Shared**: `specs/designs/` (design system tokens)
- Paths shown below assume the directory structure defined in plan.md

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Initialize project structure, configure Azure AD, and prepare Cosmos DB for data storage

**Prerequisite**: Feature 007-azure-infrastructure-provisioning must have provisioned Azure Functions app, Cosmos DB serverless account, and Managed Identity

### Backend Setup

- [X] T001 Create Python Azure Functions project structure in `backend/` with `function_app.py`, `requirements.txt`, and subdirectories for `api/`, `models/`, `services/`, `db/`
- [X] T002 [P] Configure Azure Functions `requirements.txt` with dependencies: `azure-functions`, `azure-cosmos`, `PyJWT`, `python-dotenv`, `requests`
- [X] T003 [P] Create `backend/config.py` with configuration class for Azure AD tenant ID, app ID, Cosmos DB endpoint (read from environment variables)
- [X] T004 [P] Set up `backend/api/__init__.py` with Flask/Azure Functions app initialization

### Frontend Setup

- [X] T005 Create React project structure in `frontend/` with `package.json` configured for `@azure/msal-react@2.x`, `@azure/msal-browser`, `react-router-dom`, `axios`
- [X] T006 [P] Create `frontend/public/index.html` and `frontend/src/index.jsx` as React entry points
- [X] T007 [P] Configure `frontend/.env.example` with template for `VITE_AZURE_TENANT_ID`, `VITE_AZURE_APP_ID`, `VITE_AZURE_REDIRECT_URI`

### Cosmos DB Collections Setup

- [ ] T008 Create Cosmos DB collection `allowListEntries` in the serverless account from 007 with partition key `/user_oid` and indexing policy from data-model.md
- [ ] T009 [P] Create Cosmos DB collection `capabilityAssignments` in the serverless account from 007 with partition key `/user_oid` and compound index on `(user_oid, capability, dateRevoked)`
- [X] T010 [P] Create `backend/db/seed_data.py` script to populate test data in both collections (3 test users: Player, Admin, Dual-role)

### Azure AD Configuration

- [ ] T011 Configure Azure AD app registration for frontend with:
  - Redirect URIs: `http://localhost:5173/` (dev), `https://<static-app-domain>/` (prod from 007)
  - Scopes: `openid`, `profile`, `email` (standard MSAL scopes)
  - Document tenant ID and app ID for use in frontend environment variables

### Application Settings Configuration

- [ ] T012 Configure Azure Functions application settings (from 007's Function App configuration) with:
  - `AZURE_TENANT_ID`: Azure AD tenant ID (from AD app registration)
  - `AZURE_APP_ID`: Azure AD app ID (from AD app registration)
  - `COSMOS_ENDPOINT`: Cosmos DB endpoint from 007 infrastructure output
  - Verify Managed Identity has `Cosmos DB Data Contributor` role (provisioned by 007)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core models, token validation, and allow-list/capability services that all user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Backend Models

- [X] T013 Create `backend/models/allow_list_entry.py` with AllowListEntry class:
  - Properties: `id`, `user_oid`, `email`, `dateAdded`, `dateRemoved`, `addedBy`, `removedBy`, `notes`, `entityType` (set to "AllowListEntry")
  - Validation: Ensure user_oid is present, dateRemoved logic for soft-delete
  - Methods: `is_active()` (returns True if dateRemoved is None), `to_dict()` for serialization

- [X] T014 [P] Create `backend/models/capability_assignment.py` with CapabilityAssignment class:
  - Properties: `id`, `user_oid`, `capability` (enum: "Player" or "Administrator"), `dateAssigned`, `dateRevoked`, `assignedBy`, `revokedBy`, `entityType` (set to "CapabilityAssignment")
  - Validation: Ensure user_oid is present, capability is valid enum value, dateRevoked logic for soft-delete
  - Methods: `is_active()`, `to_dict()` for serialization

### Backend Cosmos DB Service Layer

- [X] T015 Create `backend/services/cosmos_service.py` with CosmosService class:
  - Initialize Cosmos DB client using Managed Identity (via application settings)
  - Methods:
    - `get_container(name)`: Return a container reference for querying
    - `query(sql, params)`: Execute parameterized query on a container
    - Implement connection pooling and retry logic for transient failures
  - Error handling: Log to Application Insights (per Principle VI)

### Backend Token Validation Service

- [X] T016 Create `backend/services/auth_service.py` with AuthService class:
  - Method: `validate_token(token_string)` — validates JWT signature, expiry, issuer, audience
    - Fetch Azure AD public keys from `/.well-known/openid-configuration` endpoint
    - Verify signature using fetched keys
    - Verify expiry (exp claim)
    - Verify issuer (iss claim matches tenant ID)
    - Extract and return user object ID (oid claim)
    - Return tuple: (is_valid: bool, user_oid: str or None, error_message: str or None)
  - Implement caching of Azure AD public keys (refresh every 24 hours) to avoid repeated network calls
  - Error handling: Log validation failures to Application Insights

### Backend Capability Service

- [X] T017 [P] Create `backend/services/capability_service.py` with CapabilityService class:
  - Method: `get_user_capabilities(user_oid: str)` — fetch active capabilities for a user
    - Query Cosmos DB: `SELECT * FROM capabilityAssignments WHERE user_oid = @user_oid AND dateRevoked = null`
    - Return set of capability strings: {"Player", "Administrator"}, empty set if none
    - Log queries to Application Insights
  - Method: `has_capability(user_oid: str, capability: str)` — check if user holds a specific capability
    - Return boolean
  - Implement per-request caching (cache capabilities for duration of single request)

### Backend Allow-List Service

- [X] T018 [P] Create `backend/services/allow_list_service.py` with AllowListService class:
  - Method: `is_allowed(user_oid: str)` — check if user is on the allow-list
    - Query Cosmos DB: `SELECT * FROM allowListEntries WHERE user_oid = @user_oid AND dateRemoved = null`
    - Return boolean (True if found and active, False otherwise)
    - Log queries to Application Insights
  - Method: `get_allow_list_entry(user_oid: str)` — fetch the full allow-list entry for audit/display
    - Return AllowListEntry object or None
  - No account enumeration: Never reveal whether a specific oid exists

### Backend Authentication Middleware

- [X] T019 Create `backend/api/auth/middleware.py` with token validation middleware:
  - Extract token from `Authorization: Bearer <token>` header
  - Validate token using AuthService.validate_token()
  - If invalid or expired: Return 401 Unauthorized with generic message ("Invalid or expired token")
  - If valid: Attach extracted user_oid to request context for use by endpoint handlers
  - All error responses follow contract from `contracts/api.md` (generic messages, no account enumeration)

### Backend Error Response Standardization

- [X] T020 Create `backend/api/utils.py` with standard error response functions:
  - `error_response(status_code, message)`: Return JSON with `{"status": "error", "message": message}` in HTTP status 401/403/500
  - `unauthorized()`: Return 401 with message "Invalid or expired token"
  - `forbidden()`: Return 403 with message "Access not granted"
  - `server_error()`: Return 500 with message "An error occurred"
  - All error messages are generic (no account enumeration)

**Checkpoint**: Foundation ready — token validation, allow-list checks, and capability querying are implemented and tested. User story implementation can now begin in parallel.

---

## Phase 3: User Story 1 - Player Signs In and Reaches Game Menu (Priority: P1) 🎯 MVP

**Goal**: A user with Player capability signs in via Microsoft Entra ID and sees a menu item to start or continue a game

**Independent Test**: With one allow-listed Microsoft account granted the Player capability, sign in and verify a menu item to start/continue a game is shown, and no administration menu item is shown

### Tests for User Story 1

> **NOTE: Write tests FIRST, ensure they FAIL before implementation**

- [X] T021 [P] [US1] Create unit test file `backend/tests/unit/test_auth_service.py` with tests:
  - Test `validate_token()` with valid token → returns True and user_oid
  - Test `validate_token()` with expired token → returns False
  - Test `validate_token()` with invalid signature → returns False
  - Test `validate_token()` with wrong issuer → returns False
  - All tests use mocked Azure AD public key endpoint

- [X] T022 [P] [US1] Create unit test file `backend/tests/unit/test_allow_list_service.py` with tests:
  - Test `is_allowed()` for allow-listed user → returns True
  - Test `is_allowed()` for not allow-listed user → returns False
  - Test `is_allowed()` for soft-deleted user (dateRemoved set) → returns False
  - Tests use mocked Cosmos DB queries

- [X] T023 [P] [US1] Create unit test file `backend/tests/unit/test_capability_service.py` with tests:
  - Test `get_user_capabilities()` for user with Player capability → returns {"Player"}
  - Test `get_user_capabilities()` for user with both capabilities → returns {"Player", "Administrator"}
  - Test `get_user_capabilities()` for user with no capabilities → returns empty set
  - Test `has_capability()` for each scenario above
  - Tests use mocked Cosmos DB queries

- [X] T024 [P] [US1] Create integration test file `backend/tests/integration/test_login_endpoint.py` with tests:
  - Test `POST /api/auth/login` with valid token for allow-listed Player user → returns 200 with user identity and `{"hasPlayer": true, "hasAdministrator": false}`
  - Test `POST /api/auth/login` with valid token for not allow-listed user → returns 403 with generic message
  - Test `POST /api/auth/login` with expired token → returns 401
  - Tests use a test Cosmos DB instance or mock container

- [X] T025 [P] [US1] Create integration test file `backend/tests/integration/test_me_endpoint.py` with tests:
  - Test `GET /api/auth/me` with valid Player token → returns 200 with user identity and capabilities
  - Test `GET /api/auth/me` with expired token → returns 401
  - Test `GET /api/auth/me` with token for not allow-listed user → returns 403

- [X] T026 [P] [US1] Create frontend component test file `frontend/tests/components/LoginScreen.test.jsx` with tests:
  - Test LoginScreen renders "Sign in with Microsoft" button
  - Test clicking button triggers MSAL sign-in flow
  - Test navigation to MainMenu after successful sign-in
  - Test error display on sign-in cancellation
  - Uses React Testing Library and mocked MSAL

- [X] T027 [P] [US1] Create frontend component test file `frontend/tests/components/MainMenu.test.jsx` with tests:
  - Test MainMenu fetches capabilities from `/api/auth/me`
  - Test MainMenu renders "Start or Continue Game" menu item when user has Player capability
  - Test MainMenu does NOT render admin menu item when user has only Player capability
  - Test MainMenu displays error message if API returns 403
  - Uses React Testing Library and mocked fetch/axios

- [X] T028 [P] [US1] Create frontend hook test file `frontend/tests/hooks/useCapabilities.test.jsx` with tests:
  - Test hook returns `{hasPlayer: true, hasAdministrator: false}` for Player-only user
  - Test hook returns `{hasPlayer: true, hasAdministrator: true}` for dual-role user
  - Test hook returns `{hasPlayer: false, hasAdministrator: false}` for user with no capabilities
  - Uses mocked `/api/auth/me` endpoint

- [X] T029 [P] [US1] Create end-to-end test scenario `specs/002-login-and-access-control/tests/e2e/scenario_player_signin.md` documenting:
  - Prerequisites: Test user with Player capability in allow-list
  - Steps: Sign in, navigate to menu, verify game item shown
  - Expected outcome: Game menu item visible, admin menu item hidden
  - Validation: Navigate to game endpoint and verify 200 (not 403)

### Implementation for User Story 1

#### Backend: Login Endpoint

- [X] T030 Create `backend/api/auth/login.py` with `login()` handler for `POST /api/auth/login`:
  - Extract token from request body (expected JSON: `{"token": "<bearer_token>"}`)
  - Validate token using AuthService.validate_token()
  - If invalid: Return 401 with generic message
  - Check allow-list using AllowListService.is_allowed()
  - If not allowed: Return 403 with generic message ("Access not granted")
  - Fetch capabilities using CapabilityService.get_user_capabilities()
  - Return 200 with response: `{"status": "success", "user": {"oid": "...", "email": "..."}, "capabilities": {"hasPlayer": true/false, "hasAdministrator": true/false}}`
  - All error responses use generic messages (no account enumeration)
  - Log successful logins and denials to Application Insights

#### Backend: Me Endpoint

- [X] T031 [P] Create `backend/api/auth/me.py` with `me()` handler for `GET /api/auth/me`:
  - Extract token from `Authorization: Bearer <token>` header
  - Validate token using AuthService.validate_token()
  - If invalid: Return 401
  - Check allow-list using AllowListService.is_allowed()
  - If not allowed: Return 403 with generic message
  - Fetch capabilities using CapabilityService.get_user_capabilities()
  - Return 200 with response: `{"status": "success", "user": {"oid": "...", "email": "..."}, "capabilities": {"hasPlayer": true/false, "hasAdministrator": true/false}}`
  - Log successful queries to Application Insights

#### Backend: Token Validation Middleware Integration

- [X] T032 Apply middleware from T019 to all `/api/` routes in `backend/function_app.py`:
  - Wrap all route handlers with token validation
  - Extract user_oid from validated token and attach to request context
  - Proceed to endpoint handler if valid, return 401 if invalid

#### Frontend: MSAL Configuration

- [X] T033 Create `frontend/src/services/msalConfig.js` with MSAL configuration:
  - Read tenant ID, app ID, and redirect URI from environment variables
  - Configure MSAL with authentication config: `{ clientId, authority: "https://login.microsoftonline.com/{tenantId}", redirectUri }`
  - Configure scopes: `["openid", "profile", "email"]`
  - Export config for use in AuthProvider

#### Frontend: Auth Provider Context

- [X] T034 Create `frontend/src/components/Auth/AuthProvider.jsx` with React context provider:
  - Initialize MSAL PublicClientApplication using msalConfig
  - Provide hooks for child components:
    - `useMsal()`: Access MSAL instance and authentication state
    - `useAuth()`: Access authenticated user (oid, email)
    - `useCapabilities()`: Access user capabilities (hasPlayer, hasAdministrator)
  - Wrap entire app with `<MsalProvider>` in App.jsx
  - Handle initialization errors and log to console (dev) and Application Insights (prod)

#### Frontend: Login Screen Component

- [X] T035 Create `frontend/src/components/Login/LoginScreen.jsx` with UI:
  - Render login page with:
    - Title: "Sign In"
    - Description: "Use your Microsoft account to access the application"
    - Button: "Sign in with Microsoft" (uses design tokens from `specs/designs/styles.css`)
    - Error messages display area (initially hidden)
  - On button click:
    - Call `useMsal().instance.loginPopup()` to initiate sign-in flow
    - On success: Redirect to `/menu` (MainMenu component)
    - On cancellation or error: Display friendly error message (e.g., "Sign-in cancelled. Please try again.")
    - During loading: Show loading state (disabled button with spinner)
  - Styling:
    - Import and use design tokens from `specs/designs/styles.css`
    - Zero corner radius buttons
    - 4.5:1 contrast on text
    - Focus-visible outline with 4px offset
    - Responsive to 320px minimum width

#### Frontend: Login Screen Styles

- [X] T036 Create `frontend/src/components/Login/LoginScreen.css` with styling:
  - Use design token variables from `specs/designs/styles.css`
  - Login container: flush-left, full-height, centered vertically and horizontally
  - Button: zero radius, accent color on hover/pressed, focus-visible outline
  - Error message: visible dividing line above message, text-based (not color-only)
  - Mobile responsive: 44x44px minimum touch target, legible at 320px width

#### Frontend: Main Menu Component

- [X] T037 Create `frontend/src/components/Menu/MainMenu.jsx` with UI:
  - On component mount:
    - Call `GET /api/auth/me` to fetch user capabilities
    - Handle response:
      - If 200: Parse capabilities and render menu items based on `hasPlayer` and `hasAdministrator`
      - If 401: Redirect to login (token expired)
      - If 403: Render "Access not granted" message
      - If error: Render generic error message
  - Render menu items conditionally:
    - If `hasPlayer === true`: Show "Start or Continue Game" menu item (linked to game endpoint)
    - If `hasAdministrator === true`: Show "Administration" menu item (linked to admin endpoint)
    - If both false: Show "No access provisioned yet. Contact an administrator."
  - Include logout button that clears MSAL token cache and redirects to login

#### Frontend: Menu Item Components

- [X] T038 [P] Create `frontend/src/components/Menu/GameMenuItem.jsx` as reusable menu item:
  - Props: `label` (default "Start or Continue Game"), `onClick` callback
  - Render as button/link using design tokens
  - Apply hover/focus states from design system

- [X] T039 [P] Create `frontend/src/components/Menu/AdminMenuItem.jsx` as reusable menu item:
  - Props: `label` (default "Administration"), `onClick` callback
  - Render as button/link using design tokens
  - Apply hover/focus states from design system

#### Frontend: useCapabilities Hook

- [X] T040 Create `frontend/src/hooks/useCapabilities.js` custom hook:
  - Call `GET /api/auth/me` on mount
  - Return object: `{ hasPlayer: boolean, hasAdministrator: boolean, loading: boolean, error: Error | null }`
  - Implement refetch function for manual capability refresh
  - Handle 401 (expired token) by redirecting to login
  - Handle 403 (not allow-listed) by returning denied state

#### Frontend: useAuth Hook

- [X] T041 [P] Create `frontend/src/hooks/useAuth.js` custom hook:
  - Extract user identity (oid, email) from MSAL context
  - Return object: `{ user: { oid: string, email: string }, isAuthenticated: boolean }`
  - Handle unauthenticated state gracefully

#### Frontend: API Service Layer

- [X] T042 Create `frontend/src/services/authService.js` with functions:
  - `login(token)`: POST to `/api/auth/login` with bearer token
  - `getMe()`: GET `/api/auth/me` with bearer token in header
  - `logout()`: POST to `/api/auth/logout`
  - All functions:
    - Include `Authorization: Bearer <token>` header automatically (via interceptor or MSAL token)
    - Handle 401/403/500 errors with generic messages
    - Log successful requests to console (dev) and Application Insights (prod)

#### Frontend: Token Interceptor

- [X] T043 Create `frontend/src/services/tokenInterceptor.js` with HTTP interceptor:
  - Before sending any request: Attach `Authorization: Bearer <token>` header
  - Get token from MSAL cache via `useMsal().instance.getActiveAccount()`
  - If no token available: Return 401 (should not happen if auth is enforced)
  - After receiving response with 401: Trigger MSAL silent token refresh and retry request
  - Integrate with axios or fetch wrapper

#### Frontend: App Router and Protected Routes

- [X] T044 Create `frontend/src/App.jsx` main app component:
  - Set up React Router with routes:
    - `/login`: LoginScreen component (default route for unauthenticated users)
    - `/menu`: MainMenu component (requires authentication)
    - All other routes: Protected routes (redirect to login if unauthenticated)
  - Wrap with `<MsalProvider>` from AuthProvider
  - Implement ErrorBoundary for auth-related failures

#### Frontend: Global Styles

- [X] T045 Create `frontend/src/index.css` with global reset and design token imports:
  - Import design tokens from `specs/designs/styles.css`
  - Reset margins, padding, default font sizes
  - Set body background and text color using design tokens
  - Define `:focus-visible` global outline style (4px offset, accent color)
  - Ensure responsive layout (no horizontal scrolling)

#### Frontend: Styling Consistency

- [X] T046 Create `frontend/src/components/Menu/MainMenu.css` with menu styling:
  - Use design tokens for colors, spacing, typography
  - Menu container: flush-left alignment, visible dividing lines between items
  - Menu items: zero radius buttons, hover/focus states with accent tint
  - Error/no-access message: prominent, readable, uses text-based indication

**Checkpoint**: User Story 1 (Player Sign-in) is fully functional and testable independently. A user with Player capability can sign in and see the game menu item. No admin features are accessible. All tests pass (unit, integration, end-to-end).

---

## Phase 4: User Story 2 - Administrator Signs In and Reaches Administration Page (Priority: P2)

**Goal**: A user with Administrator capability signs in and sees a menu item to reach the administration page

**Independent Test**: With one allow-listed Microsoft account granted the Administrator capability, sign in and verify a menu item to the administration page is shown

### Tests for User Story 2

> **NOTE: Write tests FIRST, ensure they FAIL before implementation**

- [X] T047 [P] [US2] Create unit test file `backend/tests/unit/test_admin_capability.py` with tests:
  - Test capability service returns {"Administrator"} for admin user
  - Test capability check `has_capability(user_oid, "Administrator")` returns True for admin, False for player
  - Tests use mocked Cosmos DB

- [X] T048 [P] [US2] Create integration test file `backend/tests/integration/test_dual_role_user.py` with tests:
  - Test `GET /api/auth/me` for user with both Player and Administrator capabilities
  - Returns 200 with `{"hasPlayer": true, "hasAdministrator": true}`
  - Verify both capabilities are correctly evaluated

- [X] T049 [P] [US2] Create frontend component test file `frontend/tests/components/AdminMenuItem.test.jsx` with tests:
  - Test AdminMenuItem renders when user has Administrator capability
  - Test AdminMenuItem is hidden when user lacks Administrator capability
  - Test AdminMenuItem click navigates to admin endpoint

- [X] T050 [P] [US2] Create frontend integration test file `frontend/tests/integration/admin_signin_flow.test.jsx` with tests:
  - Test full flow: MSAL sign-in → fetch capabilities → render both menu items
  - Mock `/api/auth/me` to return both capabilities
  - Verify both "Start Game" and "Administration" items render

- [X] T051 [P] [US2] Create end-to-end test scenario `specs/002-login-and-access-control/tests/e2e/scenario_admin_signin.md` documenting:
  - Prerequisites: Test user with Administrator capability in allow-list
  - Steps: Sign in, navigate to menu, verify both game and admin items shown
  - Expected outcome: Both menu items visible
  - Validation: Navigate to both game and admin endpoints and verify 200 (not 403)

### Implementation for User Story 2

#### Backend: Admin Capability Enforcement

- [X] T052 [P] Create `backend/api/admin/middleware.py` with admin-specific authorization middleware:
  - After token validation (from Phase 2), check if user has Administrator capability
  - If user lacks Administrator capability: Return 403 with message "Access not granted"
  - Otherwise: Proceed to endpoint handler
  - This middleware will be applied to all `/api/admin/*` routes

#### Backend: Admin Endpoints Skeleton

- [X] T053 [P] Create `backend/api/admin/__init__.py` with admin endpoint initialization
- [X] T054 [P] Create `backend/api/admin/stories.py` with placeholder endpoints:
  - `POST /api/admin/stories/create`: Returns 200 with placeholder (actual implementation in feature 005)
  - `GET /api/admin/stories`: Returns 200 with empty list (actual implementation in feature 005)
  - Both endpoints apply admin capability middleware
  - Both endpoints log to Application Insights

#### Frontend: Admin Menu Item Visibility

- [X] T055 Update `frontend/src/components/Menu/MainMenu.jsx` to render AdminMenuItem conditionally:
  - Check `hasAdministrator` from capabilities
  - If true: Render AdminMenuItem component
  - If false: Don't render (already implemented in T037, verify is complete)

#### Frontend: Admin Navigation

- [X] T056 Create `frontend/src/pages/AdminPage.jsx` placeholder page:
  - Page loads on navigation to `/admin`
  - Render message: "Administration features loading..."
  - Verify ProtectedRoute enforces capability requirement (redirect to login if not authenticated)
  - Actual admin content will be implemented in feature 005 or 012

#### Frontend: Route Protection for Admin

- [X] T057 Create `frontend/src/components/Auth/ProtectedRoute.jsx` component:
  - Wrapper for routes requiring specific capabilities
  - Props: `capability` (optional, e.g., "Player" or "Administrator")
  - Check if user is authenticated and has required capability
  - If not authenticated: Redirect to login
  - If lacking capability: Show 403 message (do not redirect; show inline message)
  - Use this wrapper around AdminPage route in App.jsx

**Checkpoint**: User Story 2 (Administrator Sign-in) is fully functional. A user with Administrator capability can sign in and see both game and admin menu items. A user with only Player capability still cannot see the admin menu item or access admin endpoints. All tests pass.

---

## Phase 5: User Story 3 - Unauthorized Access Denied (Priority: P3)

**Goal**: An unauthorized user (not on allow-list) attempts to sign in and is denied access with a generic message

**Independent Test**: Attempt sign-in with a valid Microsoft account not on the allow-list and verify access is denied (403) with a generic message that does not reveal whether the account is known to the system

### Tests for User Story 3

> **NOTE: Write tests FIRST, ensure they FAIL before implementation**

- [X] T058 [P] [US3] Create unit test file `backend/tests/unit/test_unauthorized_user.py` with tests:
  - Test allow-list service returns False for user not on allow-list
  - Test login endpoint returns 403 for non-allow-listed user
  - Verify error message is generic (no account enumeration)
  - Tests use mocked Cosmos DB

- [X] T059 [P] [US3] Create integration test file `backend/tests/integration/test_access_denial.py` with tests:
  - Test `POST /api/auth/login` with valid token but user not on allow-list → returns 403
  - Test `GET /api/auth/me` with valid token but user not on allow-list → returns 403
  - Test direct access to `/api/admin/*` without capabilities → returns 403
  - Test direct access to game endpoint without Player capability → returns 403
  - Verify all error messages are generic and identical (no account enumeration)

- [X] T060 [P] [US3] Create frontend test file `frontend/tests/scenarios/unauthorized_user.test.jsx` with tests:
  - Mock MSAL to return valid token for unauthorized user
  - Mock `/api/auth/login` to return 403
  - Test LoginScreen displays generic "Access not granted" message
  - Test no menu items are rendered
  - Test user cannot navigate to protected routes

- [X] T061 [P] [US3] Create end-to-end test scenario `specs/002-login-and-access-control/tests/e2e/scenario_unauthorized_user.md` documenting:
  - Prerequisites: Test user account NOT on allow-list
  - Steps: Attempt sign-in, observe error message
  - Expected outcome: 403 Forbidden with generic message "Access not granted"
  - Validation: Verify no menu content is shown, direct URL access to menu is denied

- [X] T062 [P] [US3] Create end-to-edge case scenario `specs/002-login-and-access-control/tests/e2e/scenario_no_capabilities.md` documenting:
  - Prerequisites: Test user on allow-list but with no capabilities assigned
  - Steps: Sign in, observe menu
  - Expected outcome: Message "No access provisioned yet. Contact an administrator."
  - Validation: Verify neither Player nor Administrator menu items are shown

### Implementation for User Story 3

#### Backend: Unauthorized Error Responses

- [X] T063 Update `backend/api/utils.py` to add:
  - `forbidden_access_not_granted()`: Return 403 with message "Access not granted" (for non-allow-listed users and capability-gated endpoints)
  - Ensure all 403 responses use identical generic message (no account enumeration)
  - Ensure all error logs include oid for debugging but never expose in response

#### Backend: No-Capabilities Message

- [X] T064 Update `backend/api/auth/login.py` to handle user with no capabilities:
  - After checking allow-list and fetching capabilities:
    - If user is on allow-list but has no capabilities: Return 200 with empty capabilities set
    - Frontend will display "No access provisioned yet" message
    - This is NOT an error (200 status); user is authenticated but not yet provisioned

#### Backend: Endpoint-Level Capability Enforcement

- [X] T065 Update `backend/api/game/` (from feature 008) to enforce Player capability:
  - After token validation and allow-list check:
    - Check if user has Player capability
    - If not: Return 403 with generic message
    - If yes: Proceed to endpoint handler
  - This prevents bypass of menu checks (security requirement)

#### Backend: Comprehensive Authorization Tests

- [X] T066 Create `backend/tests/integration/test_authorization_enforcement.py` with tests:
  - Test `/api/auth/me` returns 403 for non-allow-listed user
  - Test `/api/admin/*` returns 403 for user without Administrator capability
  - Test `/api/game/*` returns 403 for user without Player capability (when available in 008)
  - Verify all error messages are identical and generic
  - Verify oid is never exposed in error responses

#### Frontend: No-Capabilities Message

- [X] T067 Update `frontend/src/components/Menu/MainMenu.jsx` to handle no capabilities:
  - After fetching capabilities, check if both `hasPlayer` and `hasAdministrator` are false
  - If true: Display message "No access provisioned yet. Contact an administrator."
  - This message replaces the menu items (don't show empty menu)
  - Styling: Prominent, readable, uses design tokens

#### Frontend: No-Capabilities Message Styling

- [X] T068 Create styling in `frontend/src/components/Menu/MainMenu.css` for no-capabilities message:
  - Use design tokens for colors and typography
  - Display as centered, readable message
  - Include visible dividing line (not whitespace alone)
  - Ensure responsive layout

#### Frontend: Access Denied Handling

- [X] T069 Update `frontend/src/components/Login/LoginScreen.jsx` to handle 403 response from backend:
  - If login endpoint returns 403: Display "Access not granted" message
  - Do not reveal whether the account exists in the system
  - Do not show any menu or application content
  - Offer "Try again" button to re-initiate sign-in flow

#### Frontend: Comprehensive End-to-End Denial Testing

- [X] T070 Create comprehensive test file `frontend/tests/e2e/denial_scenarios.test.jsx` with tests:
  - Test scenario: Valid token, not on allow-list → 403, no menu shown
  - Test scenario: Valid token, on allow-list, no capabilities → No-capabilities message shown
  - Test scenario: Valid token, Player capability, direct URL to admin page → 403 or redirect
  - Test scenario: Invalid/expired token → 401, redirect to login
  - All scenarios verified end-to-end through UI

**Checkpoint**: User Story 3 (Unauthorized Denial) is fully functional. Users not on the allow-list are denied access with a generic message that does not reveal whether their account is known. Users with no capabilities see a provisioning message. All tests pass, including authorization enforcement at both menu and endpoint levels.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements affecting multiple user stories, documentation, and final verification

### Documentation and Configuration

- [X] T071 Create `backend/README.md` with:
  - Overview of backend structure
  - Setup instructions (Python environment, dependencies, Cosmos DB connection)
  - How to run tests locally (pytest)
  - Environment variables required (AZURE_TENANT_ID, AZURE_APP_ID, COSMOS_ENDPOINT)
  - Deployment steps (deploy to Azure Functions via GitHub Actions from 007)
  - API endpoint documentation (request/response formats)
  - Link to contracts/api.md for full contract details

- [X] T072 [P] Create `frontend/README.md` with:
  - Overview of frontend structure
  - Setup instructions (Node.js, npm/yarn, MSAL configuration)
  - How to run locally (vite dev server)
  - Environment variables required (VITE_AZURE_TENANT_ID, VITE_AZURE_APP_ID, VITE_AZURE_REDIRECT_URI)
  - How to run tests (Jest or Vitest)
  - Deployment steps (deploy to Static Web App from 007)
  - Architecture overview (MSAL, Auth context, hooks)
  - Link to contracts/ui-login-screen.md and ui-menu-states.md

- [X] T073 [P] Create `backend/.env.example` file with template:
  - AZURE_TENANT_ID=
  - AZURE_APP_ID=
  - COSMOS_ENDPOINT=
  - Comment: "Do not commit this file with actual values; use Key Vault in production"

- [X] T074 [P] Create `frontend/.env.example` file (if not already created in T007):
  - VITE_AZURE_TENANT_ID=
  - VITE_AZURE_APP_ID=
  - VITE_AZURE_REDIRECT_URI=
  - Comment: "Do not commit this file with actual values; use deployment secrets in GitHub"

### Integration Tests and Validation

- [X] T075 Run all backend unit tests (from T021-T026, T047-T048, T058-T059, T066) and verify pass rate 100%
  - Command: `pytest backend/tests/unit/` with coverage report
  - Target: >80% code coverage for auth services
  - Fix any failures before proceeding

- [X] T076 [P] Run all backend integration tests (from T024-T025, T049, T061, T065) and verify pass rate 100%
  - Command: `pytest backend/tests/integration/` with coverage report
  - Target: All endpoints tested with multiple scenarios
  - Fix any failures before proceeding

- [ ] T077 [P] Run all frontend unit tests (from T026-T028, T049-T050) and verify pass rate 100%
  - Command: `npm test` or equivalent (Jest/Vitest)
  - Target: >80% component coverage
  - Fix any failures before proceeding

- [ ] T078 Run all end-to-end scenarios from quickstart.md:
  - Scenario 1: Player sign-in and game access (from T029)
  - Scenario 2: Administrator sign-in and admin access (from T051)
  - Scenario 3: Unauthorized denial (from T061)
  - Scenario 4: No-capabilities message (from T062)
  - Scenario 5: Dual-capability user (from T048)
  - Scenario 6: Token expiry and refresh (manual testing)
  - Scenario 7: Capability change detection (manual testing)
  - Scenario 8: Direct URL access enforcement (manual testing)
  - All scenarios must pass; document results

### Performance and Security Review

- [ ] T079 [P] Performance review of Cosmos DB queries:
  - Measure latency of allow-list lookup (target: <100ms)
  - Measure latency of capability fetch (target: <100ms)
  - Verify indexing is working (check Cosmos DB metrics in Azure portal)
  - Optimize queries if latency exceeds targets (consider caching if needed)

- [X] T080 [P] Security review of error messages:
  - Verify no account enumeration in any error response
  - Verify no token, oid, or email exposure in error logs (only in structured logs to Application Insights)
  - Verify all 403 responses use identical generic message
  - Verify CORS headers are correctly configured (if frontend and backend on different domains)

- [X] T081 [P] Review authentication flow for compliance:
  - Verify Constitution Principle II (secure-by-default, allow-list enforcement) is satisfied
  - Verify Constitution Principle VII (Managed Identity, no shared keys) is satisfied
  - Verify Constitution Principle VI (observability, Application Insights) is satisfied
  - Document compliance findings

### Cross-Browser and Mobile Testing

- [ ] T082 [P] Test login and menu flows on multiple browsers:
  - Chrome (latest)
  - Firefox (latest)
  - Safari (latest)
  - Edge (latest)
  - Verify sign-in works, menu renders correctly, no console errors
  - Test on desktop resolution (1920x1080)

- [ ] T083 [P] Test responsive layout on mobile:
  - iPhone (minimum 320px width portrait)
  - Android phone (minimum 320px width portrait)
  - Tablet (iPad, Android tablet)
  - Verify login screen and menu are usable at minimum 320px width
  - Verify touch targets are at least 44x44px
  - Verify no horizontal scrolling

### Accessibility Review

- [ ] T084 [P] Test keyboard navigation:
  - Tab through login screen and verify focus order
  - Tab through menu and verify focus order
  - Verify all interactive elements are keyboard accessible
  - Verify focus indicator is visible (4px offset in accent color per design system)
  - Test on Chrome and Firefox

- [ ] T085 [P] Test screen reader compatibility:
  - Test with NVDA (Windows) or JAWS
  - Verify login screen semantics: real `<button>`, proper headings
  - Verify menu items are read correctly
  - Verify error messages are announced
  - Verify focus indicators are announced

- [X] T086 [P] Verify design system compliance:
  - Verify login screen matches `specs/designs/01-login.html` visually
  - Verify menu items match design system in `specs/designs/02-story-select.html`
  - Verify colors use design tokens (zero radius, flush-left, 4.5:1 contrast)
  - Verify no unauthorized deviations from design system
  - Document any exceptions with justification

### Deployment and CI/CD Integration

- [X] T087 [P] Configure GitHub Actions workflow integration (from 007-azure-infrastructure-provisioning):
  - Verify backend tests run on every PR (pytest)
  - Verify frontend tests run on every PR (Jest/Vitest)
  - Verify CI passes before merge is allowed
  - Verify deployment is triggered on merge to main (deploy to Azure Functions and Static Web App)

- [ ] T088 [P] Test local development workflow:
  - Backend: `python -m venv venv` → activate → `pip install -r requirements.txt` → `pytest` → local Functions emulator
  - Frontend: `npm install` → `npm run dev` → `npm test`
  - Document developer setup steps in backend/README.md and frontend/README.md

- [X] T089 [P] Create deployment validation script:
  - Script to run quickstart.md scenarios against production environment
  - Verify all 12 validation scenarios pass in production
  - Log results to file for post-deployment verification
  - Document deployment steps

### Final Verification and Sign-Off

- [ ] T090 Run final comprehensive test suite:
  - Backend: `pytest backend/tests/` with coverage report (>80% coverage)
  - Frontend: `npm test` with coverage report (>80% coverage)
  - End-to-end: All 12 scenarios from quickstart.md pass
  - Verify no failing tests or warnings before sign-off

- [X] T091 [P] Verify Constitution compliance:
  - Principle I (Testing): All functionality has tests ✅
  - Principle II (Secure-by-default): Allow-list enforcement, no public access ✅
  - Principle III (Tech stack): Python + React, MSAL, Cosmos DB ✅
  - Principle IV (Simplicity): Per-request validation, no caching complexity ✅
  - Principle V (CI gate): Tests block merge, GitHub is system of record ✅
  - Principle VI (Observability): Telemetry to Application Insights ✅
  - Principle VII (Zero-trust): Managed Identity, no shared keys ✅
  - Principle VIII (Design system): Login screen matches 01-login.html, design tokens used ✅

- [X] T092 [P] Create deployment runbook:
  - Prerequisite: Feature 007-azure-infrastructure-provisioning must be complete
  - Step 1: Verify Cosmos DB collections exist (allowListEntries, capabilityAssignments)
  - Step 2: Seed test data using backend/db/seed_data.py
  - Step 3: Configure Azure AD app registration (tenant ID, app ID, redirect URIs)
  - Step 4: Set Function App application settings (AZURE_TENANT_ID, AZURE_APP_ID, COSMOS_ENDPOINT)
  - Step 5: Deploy backend via GitHub Actions (merge to main)
  - Step 6: Deploy frontend via GitHub Actions (merge to main)
  - Step 7: Run quickstart.md validation scenarios
  - Step 8: Verify production telemetry in Application Insights

- [X] T093 [P] Final code review:
  - Review all Python code in backend/ for PEP 8 compliance and best practices
  - Review all JavaScript/JSX code in frontend/ for ES6+ standards and React best practices
  - Review test coverage (unit, integration, end-to-end)
  - Verify error handling and logging are comprehensive
  - Verify no secrets or credentials in code or git history
  - Approve for production deployment

### Documentation Finalization

- [X] T094 Create user-facing documentation `docs/LOGIN_INSTRUCTIONS.md`:
  - How to sign in: Click "Sign in with Microsoft", complete Azure AD flow
  - What to do if sign-in fails: Try again, contact administrator if persistent
  - What menu items mean: "Start Game" for players, "Administration" for admins
  - How to sign out: Click logout button, clears session
  - Technical support contact information

- [X] T095 [P] Create administrator documentation `docs/ADMIN_SETUP.md`:
  - How to add users to allow-list (Cosmos DB query example)
  - How to assign capabilities (Cosmos DB query example)
  - How to remove/revoke access (soft-delete explanation)
  - How to troubleshoot sign-in issues (check logs in Application Insights)
  - Example allow-list and capability entries (JSON format)

- [X] T096 [P] Update main project README:
  - Add link to Login & Access Control feature docs
  - Update architecture diagram to show login flow
  - Document feature dependencies (requires 007-azure-infrastructure-provisioning)
  - Document feature that depend on this (008-core-gameplay, 005-story-publishing, etc.)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
  - Must complete before Phase 2 (needs infrastructure and configuration)

- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
  - Must complete before any user story (all stories depend on token validation and allow-list checks)

- **User Story 1 (Phase 3, P1)**: Can start after Foundational - No dependencies on other stories
  - MVP story; Player sign-in is the primary use case
  - Can be completed independently

- **User Story 2 (Phase 4, P2)**: Can start after Foundational - May integrate with US1 (menu shows both items) but independently testable
  - Can be completed in parallel with US1 if team capacity allows
  - Requires same auth infrastructure as US1

- **User Story 3 (Phase 5, P3)**: Can start after Foundational - May integrate with US1/US2 (test denial scenarios) but independently testable
  - Adds security validation; tests deny scenarios
  - Can be completed in parallel with US1/US2

- **Polish (Phase 6)**: Depends on all user stories being substantially complete
  - Documentation, final testing, deployment preparation
  - Can partially overlap with user story work (documentation can start earlier)

### Within-Phase Dependencies

- **Phase 1 Setup**:
  - T001-T004 (backend setup) can run in parallel
  - T005-T007 (frontend setup) can run in parallel
  - T008-T009 (Cosmos DB collections) can run in parallel
  - T010-T012 (configuration) can run sequentially or in parallel (no blockers)

- **Phase 2 Foundational**:
  - T013-T014 (models) can run in parallel
  - T015-T018 (services) depend on models (T013-T014); can start after models
  - T019-T020 (middleware and error handling) depend on services

- **Phase 3 User Story 1**:
  - T021-T029 (tests) can run in parallel, but implementation tasks (T030+) should wait for test infrastructure
  - T030-T032 (backend) depend on Phase 2; can run in parallel (different files)
  - T033-T046 (frontend) depend on Phase 2 and Phase 1 setup; can run in parallel with backend

- **Phase 4 User Story 2**:
  - T047-T051 (tests) can run in parallel
  - T052-T054 (backend) depend on Phase 3 backend being complete (endpoints are already handling auth)
  - T055-T057 (frontend) depend on Phase 3 frontend and T052-T054 backend

- **Phase 5 User Story 3**:
  - T058-T062 (tests) can run in parallel
  - T063-T070 (implementation) can run in parallel after Phase 3/4 complete

### Critical Path

1. **Phase 1 (Setup)**: 1-2 days - Project structure, Cosmos DB collections, AD app config
2. **Phase 2 (Foundational)**: 1-2 days - Models, services, token validation
3. **Phase 3 (US1) + Phase 4 (US2) in parallel**: 3-4 days each
4. **Phase 5 (US3)**: 1-2 days - Add authorization enforcement and denial tests
5. **Phase 6 (Polish)**: 1-2 days - Documentation, final testing, deployment

**Total (Serial)**: 8-12 days (one developer)
**Total (Parallel)**: 6-9 days (backend + frontend teams working simultaneously)

### Parallel Execution Examples

#### Parallel Example 1: Phase 1 Setup

```
Developer A: T001-T004 (backend setup)
Developer B: T005-T007 (frontend setup)
Both in parallel: T008-T012 (Cosmos DB and configuration)
```

#### Parallel Example 2: Phase 3 User Story 1

```
Developer A: T021-T022 (backend unit tests)
Developer B: T026-T028 (frontend component tests)
Both in parallel: T030-T032 (backend endpoints)
Both in parallel: T033-T046 (frontend components)
```

#### Parallel Example 3: Phases 3 & 4 Overlap

```
Day 1-3: Phase 3 US1 (Player sign-in) - both developers
Day 3-5: Phase 3 completes, Phase 4 begins (Admin capability)
         Developer A: Phase 4 backend (T052-T054)
         Developer B: Complete Phase 3 frontend integration (T044-T046)
Day 5-6: Both finish Phase 4
Day 6-7: Phase 5 US3 (Denial scenarios)
```

---

## Parallel Opportunities by Task

**Setup Phase (T001-T012)**: 6 parallelizable tasks
- T002, T003, T004 (backend config) can run in parallel
- T006, T007 (frontend setup) can run in parallel
- T008, T009 (Cosmos DB collections) can run in parallel

**Foundational Phase (T013-T020)**: 2 parallelizable task groups
- T014 (capability model) parallelizable with T013 (allow-list model)
- T017, T018 (capability and allow-list services) parallelizable with T016 (auth service)

**User Story 1 (T021-T046)**: 10+ parallelizable tasks
- T021-T023 (backend unit tests) all parallelizable
- T026-T028 (frontend tests) all parallelizable
- T038-T039 (menu item components) parallelizable with each other
- T040-T041 (hooks) parallelizable with each other

**User Story 2 (T047-T057)**: 5+ parallelizable tasks
- T047-T051 (tests) all parallelizable

**User Story 3 (T058-T070)**: 5+ parallelizable tasks
- T058-T062 (tests) all parallelizable
- T069-T070 (frontend tests and implementation) parallelizable

**Polish Phase (T071-T096)**: 10+ parallelizable tasks
- T072-T074 (documentation) parallelizable
- T079-T086 (performance, security, accessibility reviews) parallelizable

---

## Implementation Strategy

### MVP First (User Story 1 Only)

This is the recommended approach if delivery timeline is critical:

1. Complete Phase 1: Setup (1-2 days)
2. Complete Phase 2: Foundational (1-2 days)
3. Complete Phase 3: User Story 1 (3-4 days)
4. Stop and validate: Run all tests for US1, run quickstart scenario 1
5. Deploy/demo if ready
6. **MILESTONE**: MVP complete - users can sign in and see game menu

Then, with additional time/resources:

7. Complete Phase 4: User Story 2 (1-2 days)
8. Validate: Run tests for US2, run quickstart scenario 2
9. Complete Phase 5: User Story 3 (1-2 days)
10. Validate: Run tests for US3, run quickstart scenarios 3-4
11. Complete Phase 6: Polish (1-2 days)
12. Deploy to production

### Incremental Delivery

With multiple developers or if timeline allows for comprehensive feature:

1. Phase 1 (Setup) - 1-2 days
2. Phase 2 (Foundational) - 1-2 days
3. Phases 3 + 4 (US1 + US2) in parallel - 3-4 days each (concurrent)
4. Phase 5 (US3) - 1-2 days
5. Phase 6 (Polish) - 1-2 days

**Total**: 6-9 days (backend and frontend teams working simultaneously)

### Team Assignments

If you have multiple developers:

- **Backend Developer**:
  - Phase 1: Setup (T001-T004, T012)
  - Phase 2: Foundational (T013-T020)
  - Phase 3: US1 backend (T030-T032)
  - Phase 4: US2 backend (T052-T054)
  - Phase 5: US3 backend (T063-T066)
  - Phase 6: Documentation, testing (T071-T096)

- **Frontend Developer**:
  - Phase 1: Setup (T005-T007, T012)
  - Phase 3: US1 frontend (T033-T046)
  - Phase 4: US2 frontend (T055-T057)
  - Phase 5: US3 frontend (T069-T070)
  - Phase 6: Documentation, testing (T071-T096)

- **QA / Test Lead**:
  - Write tests first (T021-T029, T047-T051, T058-T062)
  - Run integration tests and end-to-end scenarios (T075-T078)
  - Performance and security review (T079-T081)
  - Accessibility and cross-browser testing (T082-T086)
  - Final verification (T090-T093)

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks in this phase
- [Story] label maps task to specific user story (US1, US2, US3) for traceability
- Each user story should be independently completable and testable (stop at checkpoints)
- **Verify tests FAIL before implementing** (test-driven development)
- Commit after each task or logical group (task completion = one commit)
- Stop at any checkpoint to validate story independently
- Constitution compliance is verified in T091 (Principle I-VIII)
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence

---

## Success Criteria

- [ ] All 12 validation scenarios from quickstart.md pass
- [ ] All unit tests pass (T021-T028, T047-T050, T058-T062, T075-T076)
- [ ] All integration tests pass (T024-T025, T049, T061, T065, T077-T078)
- [ ] 100% of sign-in attempts from authorized users succeed
- [ ] 100% of sign-in attempts from unauthorized users are denied with generic message
- [ ] Capabilities are correctly evaluated based on database state
- [ ] Session persists across multiple API requests without re-login
- [ ] Constitution compliance verified (T091)
- [ ] No secrets stored in code or GitHub
- [ ] Telemetry includes authentication and authorization events (Application Insights)
- [ ] Error messages are user-friendly (no technical jargon)
- [ ] All code reviewed (T093)
- [ ] All documentation complete (T094-T096)
