# Implementation Plan: Login and Access Control

**Date**: 2026-08-28

**Feature**: Login and Access Control (002-login-and-access-control)

**Status**: Planning Complete (Ready for Implementation)

---

## Overview

This document outlines the technical implementation plan for the login and access control feature. It provides the architecture, technology stack, file structure, and a constitution compliance check to ensure the implementation will satisfy both functional requirements and project governance.

**Dependency Note**: This feature depends on infrastructure provisioned by [007-azure-infrastructure-provisioning](../007-azure-infrastructure-provisioning/spec.md). The infrastructure feature provides:
- Azure Cosmos DB serverless account (with collections provisioned by 002)
- Azure Functions app (runtime for authentication backend)
- Azure Static Web App (frontend hosting)
- Managed Identity authentication and Private Endpoints
- GitHub Actions workflows for automated deployment

Phase 0 (Infrastructure Setup) assumes infrastructure from 007 already exists or is being provisioned in parallel. See [Relationship with Feature 007](#relationship-with-feature-007) below.

---

## Technical Context

### Technology Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Frontend Auth | MSAL React (`@azure/msal-react@2.x`) | Official Microsoft library for Azure AD sign-in in React SPAs |
| Backend Auth | Python with PyJWT or equivalent | Validates tokens, extracts user identity |
| Allow-List Storage | Azure Cosmos DB (serverless) | Serverless JSON document store; optimal for small private app with occasional queries; partition key on user_oid for efficient lookups |
| Session Management | Browser localStorage + MSAL auto-refresh | Stateless backend per Principle IV; automatic token refresh |
| Menu API | GET `/api/auth/me` returning JSON | Returns user identity and capabilities |
| Backend Validation | Per-request token + capability check | Catches revocations and capability changes immediately |

### Architecture

**Authentication Flow**:
1. User clicks "Sign in with Microsoft" on login screen
2. MSAL opens Microsoft Entra ID sign-in flow (OAuth 2.0 with PKCE)
3. User completes sign-in and is redirected back with access token
4. Frontend calls `/api/auth/login` with token
5. Backend validates token, checks allow-list, fetches capabilities
6. Backend returns user identity and capabilities JSON
7. Frontend stores token in MSAL's cache and renders menu based on capabilities
8. All subsequent API calls include `Authorization: Bearer <token>` header
9. Backend validates token and capabilities on every request

**Authorization Flow**:
1. Backend validates bearer token on every API request
2. Backend checks allow-list (is user on the allow-list?)
3. Backend fetches user's capabilities (Player, Administrator, or both)
4. Endpoint-level checks enforce capability requirements (e.g., `/api/game/*` requires Player)
5. Return 403 Forbidden if user lacks required capability

**Session Management**:
- No server-side session table; all session state is in the JWT token
- MSAL automatically refreshes token before expiry (transparent to user)
- Browser localStorage holds cached token; cleared on logout
- Token expiry is 1 hour (Azure AD default); change in Azure AD app settings if needed

### Key Design Decisions

1. **Token validation on every request**: Catches revocations and capability changes immediately (instead of caching)
2. **Separate allow-list and capability tables**: Allows users to exist on allow-list without capabilities (shows "no access provisioned" message)
3. **Server-side capability enforcement**: API endpoints verify capabilities; menu gating alone is not sufficient
4. **No server-side session state**: Stateless backend per Principle IV (YAGNI)
5. **Generic error messages**: No account enumeration; "Access not granted" for both missing and denied users
6. **Capability changes take effect on next request**: No real-time push required

See [research.md](research.md) for detailed rationale on all technical decisions.

---

## File Structure

### Backend Components (Python Azure Functions)

```
src/backend/
├── api/
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── login.py                 # POST /api/auth/login (token validation, allow-list check, fetch capabilities)
│   │   ├── me.py                    # GET /api/auth/me (current user identity and capabilities)
│   │   ├── logout.py                # POST /api/auth/logout (session cleanup signal)
│   │   └── middleware.py            # Token validation middleware (applied to all endpoints)
│   ├── game/
│   │   ├── __init__.py
│   │   └── start.py                 # POST /api/game/start (requires Player capability)
│   └── admin/
│       ├── __init__.py
│       └── stories.py               # POST/GET /api/admin/stories (requires Administrator capability)
├── models/
│   ├── __init__.py
│   ├── allow_list_entry.py          # AllowListEntry entity (schema, validation)
│   └── capability_assignment.py     # CapabilityAssignment entity (schema, validation)
├── services/
│   ├── __init__.py
│   ├── auth_service.py              # Token validation, allow-list check, user authentication
│   ├── capability_service.py        # Fetch user capabilities from Cosmos DB
│   └── cosmos_service.py            # Cosmos DB connection and query helpers
├── db/
│   ├── __init__.py
│   └── seed_data.py                 # Script to populate test data in Cosmos DB collections
├── config.py                         # Configuration (tenant ID, app ID, Cosmos DB connection string)
├── requirements.txt                  # Python dependencies (PyJWT, azure-functions, azure-cosmos, etc.)
└── function_app.py                   # Azure Functions app entry point
```

**Backend Responsibilities**:
- Token validation (PyJWT, verify signature and expiry)
- Allow-list enforcement (query Cosmos DB)
- Capability evaluation (query Cosmos DB for user's roles)
- API endpoints for login, auth check, and capability-gated operations
- Error responses (generic messages, no account enumeration)

**Cosmos DB Client**: Use `azure-cosmos` Python SDK for querying collections

---

### Frontend Components (React)

```
src/frontend/
├── src/
│   ├── components/
│   │   ├── Login/
│   │   │   ├── LoginScreen.jsx       # Login page UI (sign-in button, error states, loading)
│   │   │   └── LoginScreen.css       # Login styling (uses design tokens from specs/designs/styles.css)
│   │   ├── Menu/
│   │   │   ├── MainMenu.jsx          # Menu container (fetches capabilities, renders items)
│   │   │   ├── MainMenu.css          # Menu styling
│   │   │   ├── GameMenuItem.jsx      # Game/Story menu item (shown if has Player capability)
│   │   │   ├── AdminMenuItem.jsx     # Administration menu item (shown if has Administrator capability)
│   │   │   └── NoAccessMessage.jsx   # Message shown if no capabilities provisioned
│   │   ├── Auth/
│   │   │   ├── AuthProvider.jsx      # MSAL context provider (wraps app, manages tokens and login state)
│   │   │   └── ProtectedRoute.jsx    # Route wrapper (checks token and capability before rendering)
│   │   └── Common/
│   │       └── ErrorBoundary.jsx     # Error boundary for auth failures
│   ├── services/
│   │   ├── authService.js           # API calls to /api/auth/* endpoints (login, me, logout)
│   │   ├── msalConfig.js            # MSAL configuration (tenant ID, app ID, redirect URI, scopes)
│   │   └── tokenInterceptor.js      # HTTP interceptor to add Authorization header to all requests
│   ├── hooks/
│   │   ├── useAuth.js               # Hook for accessing user identity (oid, email)
│   │   ├── useCapabilities.js       # Hook for accessing user capabilities (hasPlayer, hasAdmin)
│   │   └── useFetchAuth.js          # Hook for calling /api/auth/me and handling responses
│   ├── styles/
│   │   └── designTokens.css         # Imported design tokens (specs/designs/styles.css)
│   ├── App.jsx                      # Main app entry point (login page or main menu based on auth state)
│   ├── index.jsx                    # React root
│   ├── index.css                    # Global reset styles
│   └── App.css                      # App-level styles
├── public/
│   ├── index.html
│   └── env.example.js               # Template for MSAL configuration (tenant, app ID, redirect URI)
├── package.json                     # Dependencies (@azure/msal-react, @azure/msal-browser, etc.)
├── .env.example                     # Template for environment variables
└── .eslintrc.json                   # ESLint config (code quality)
```

**Frontend Responsibilities**:
- Render login screen with "Sign in with Microsoft" button
- Coordinate MSAL sign-in flow (obtain token)
- Call backend `/api/auth/login` or `/api/auth/me` to fetch capabilities
- Render menu with capability-based items
- Automatically refresh token via MSAL before expiry
- Display error messages for all sign-in states
- Include Authorization header on all API requests

**MSAL Integration**: Use `@azure/msal-react` v2.x for token management and sign-in

---

### Shared Design System

```
specs/designs/
├── 01-login.html                   # Login screen prototype (reference implementation)
├── 02-story-select.html            # Story selection screen with menu (menu items based on capabilities)
├── 03-play.html                    # Play surface with menu
├── 04-admin-wizard.html            # Admin wizard with menu
├── styles.css                      # Vendored design tokens (colors, typography, spacing, states)
└── README.md                       # Implementer notes (token usage, component classes)
```

**Design System Usage**:
- Frontend imports `styles.css` as the single source of truth for design tokens
- Login and Menu components use design-system classes and token variables
- Zero corner radius, flush-left alignment, focus-visible states all from design system

---

## Database Schema (Cosmos DB Serverless)

**Storage Provider**: Azure Cosmos DB (serverless variant)
**Partition Key**: Both collections use `/user_oid` to optimize single-user lookups

### Allow-List Entry Collection

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "user_oid": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@outlook.com",
  "dateAdded": "2026-08-28T20:00:00Z",
  "dateRemoved": null,
  "addedBy": "admin@outlook.com",
  "removedBy": null,
  "notes": "Test account for player functionality",
  "entityType": "AllowListEntry",
  "_ttl": -1
}
```

**Indexes**:
- Automatic indexing on all properties
- Custom index on `dateRemoved` (filter active entries)
- Custom index on `email` (admin lookup)

### Capability Assignment Collection

```json
{
  "id": "capability-550e8400-e29b-41d4-a716-446655440000-Player",
  "user_oid": "550e8400-e29b-41d4-a716-446655440000",
  "capability": "Player",
  "dateAssigned": "2026-08-28T20:00:00Z",
  "dateRevoked": null,
  "assignedBy": "admin@outlook.com",
  "revokedBy": null,
  "entityType": "CapabilityAssignment",
  "_ttl": -1
}
```

**Indexes**:
- Automatic indexing on all properties
- Custom index on `dateRevoked` (filter active capabilities)
- Custom compound index on `(user_oid, capability, dateRevoked)` (efficient capability queries)

**See [data-model.md](data-model.md) for detailed schema, partition key strategy, and query patterns.**

---

## API Endpoints

### Authentication Endpoints (This Feature)

**`POST /api/auth/login`**
- Input: Bearer token from MSAL
- Output: User identity and capabilities, or 403/401 error
- See [contracts/api.md](contracts/api.md) for full contract
- Backend: Validates token, queries Cosmos DB for allow-list and capabilities

**`GET /api/auth/me`**
- Input: Bearer token
- Output: Current user's identity and capabilities
- Used for menu rendering and capability checks
- Backend: Extracts user identity from token, queries Cosmos DB for active capabilities

**`POST /api/auth/logout`**
- Input: Bearer token
- Output: Success message
- Backend: Signals session cleanup (backend is stateless; primarily a browser signal to clear tokens)

### Capability-Gated Endpoints (Other Features)

These endpoints are defined in their respective features but are protected by the token validation middleware from this feature:

**Game-Related** (require Player capability; feature 008-core-gameplay):
- `POST /api/game/start`
- `GET /api/game/stories`
- `POST /api/game/save`

**Admin-Related** (require Administrator capability; features 005-story-publishing, 012-story-editing-and-review):
- `POST /api/admin/stories/create`
- `GET /api/admin/stories`
- `PUT /api/admin/stories/{id}`

All endpoints share the same token validation middleware and error response format (defined in [contracts/api.md](contracts/api.md))

---

## Frontend Components

### LoginScreen Component

- Renders login page with "Sign in with Microsoft" button
- Handles MSAL authentication flow
- Displays error states (cancelled, network error, access denied, no capabilities)
- Navigates to main menu on successful login

### MainMenu Component

- Fetches user capabilities from `/api/auth/me`
- Conditionally renders menu items based on capabilities
- Shows "Start or Continue Game" if user has Player capability
- Shows "Administration" if user has Administrator capability
- Shows "No access provisioned" if user has no capabilities

### AuthProvider Component

- Wraps application with MSAL context
- Manages global authentication state
- Exposes hooks for accessing user identity and capabilities

### ProtectedRoute Component

- Wraps routes that require authentication
- Checks for valid token and capabilities
- Redirects to login if unauthenticated
- Returns 403 Forbidden if lacking required capability

---

## Implementation Phases

### Phase 0: Shared Infrastructure Setup (1-2 days)

**Must complete before parallel src/backend/frontend work**. Part of this is handled by 007-azure-infrastructure-provisioning; see note below.

**Infrastructure Provisioned by Feature 007** (must be complete):
- ✓ Azure Cosmos DB serverless account exists
- ✓ Azure Functions app provisioned and deployed
- ✓ Azure Static Web App provisioned
- ✓ Managed Identity configured on Functions app
- ✓ Private Endpoints configured (Cosmos DB, Blob Storage, Azure AI Foundry)
- ✓ GitHub Actions deployment workflow configured with OIDC
- ✓ Application settings framework in place (Function App configuration)

**Phase 0 Tasks for This Feature**:
- [ ] Create Cosmos DB collections (within existing serverless account from 007)
  - Collection: `allowListEntries` (partition key: `/user_oid`)
  - Collection: `capabilityAssignments` (partition key: `/user_oid`)
  - Set up indexing policies per [data-model.md](data-model.md)
- [ ] Configure Azure AD app registration (get tenant ID, app ID, configure redirect URIs for frontend)
- [ ] Set up Azure Functions project structure (Python runtime, project layout; deploy to Function App from 007)
- [ ] Set up React project (create-react-app or equivalent with Vite)
- [ ] Configure application settings in Function App (tenant ID, Cosmos DB connection via Managed Identity, app ID)
- [ ] Populate seed data in Cosmos DB collections (test users and capabilities)

**Outcome**: Both backend and frontend teams can start work independently with infrastructure ready

---

### Phase 1: Backend Implementation (Parallel Track, 3-4 days)

**Note**: Can start once Phase 0 is complete; independent of frontend

**Database & Models**:
- [ ] Create Cosmos DB document models (AllowListEntry, CapabilityAssignment)
- [ ] Implement data validation logic
- [ ] Set up Cosmos DB client and connection pooling
- [ ] Implement query helpers (find active entries, fetch user capabilities, soft-delete)

**Token Validation & Auth Service**:
- [ ] Implement token validation (PyJWT)
- [ ] Fetch Azure AD public keys from `.well-known/openid-configuration`
- [ ] Validate token signature, expiry, issuer, audience
- [ ] Implement allow-list check (query Cosmos DB)
- [ ] Implement capability fetch (query Cosmos DB for active capabilities)
- [ ] Handle error cases (expired token, invalid signature, not on allow-list, no capabilities)

**API Endpoints**:
- [ ] Implement `POST /api/auth/login` (validate token, check allow-list, fetch capabilities)
- [ ] Implement `GET /api/auth/me` (return current user identity and capabilities)
- [ ] Implement `POST /api/auth/logout` (signal session cleanup)
- [ ] Implement token validation middleware (apply to all endpoints)
- [ ] Add error handling and standard error responses (generic messages, no account enumeration)

**Testing (Backend)**:
- [ ] Unit tests: Token validation (valid, expired, invalid signature, wrong issuer)
- [ ] Unit tests: Allow-list check (allow-listed, not allow-listed, soft-deleted)
- [ ] Unit tests: Capability fetch (Player, Admin, both, neither)
- [ ] Integration tests: `/api/auth/login` with various token states
- [ ] Integration tests: `/api/auth/me` returns correct capabilities
- [ ] Integration tests: Capability-gated endpoints enforce restrictions

**Deliverables**: Fully functional backend with all endpoints tested and ready for frontend integration

---

### Phase 2: Frontend Implementation (Parallel Track, 3-4 days)

**Note**: Can start once Phase 0 is complete; can use mock backend while Phase 1 is in progress

**MSAL Setup & Auth Context**:
- [ ] Configure MSAL React with tenant ID, app ID, redirect URI, scopes
- [ ] Create AuthProvider context component (wraps app, manages login state)
- [ ] Implement token acquisition flow (MSAL login popup or redirect)
- [ ] Implement automatic token refresh (MSAL silent token request before expiry)
- [ ] Implement useAuth hook (expose user identity)
- [ ] Implement useCapabilities hook (expose user capabilities)

**UI Components**:
- [ ] Implement LoginScreen component
  - Render login page with "Sign in with Microsoft" button
  - Handle sign-in flow (loading state, cancellation, errors)
  - Display error states (cancelled, network error, access denied, no capabilities)
  - Navigate to menu on successful login
- [ ] Implement MainMenu component
  - Fetch capabilities from `/api/auth/me` on component mount
  - Conditionally render menu items based on capabilities
  - Show error message if no capabilities provisioned
- [ ] Implement GameMenuItem component (shown if has Player capability)
- [ ] Implement AdminMenuItem component (shown if has Administrator capability)
- [ ] Implement ProtectedRoute component (protect routes that require capabilities)
- [ ] Implement ErrorBoundary for auth failures

**HTTP Integration**:
- [ ] Create authService (API calls to `/api/auth/*` endpoints)
- [ ] Create token interceptor (add Authorization header to all requests)
- [ ] Handle error responses (401 Unauthorized, 403 Forbidden)
- [ ] Implement retry logic for transient errors

**Styling**:
- [ ] Import design-system tokens from `specs/designs/styles.css`
- [ ] Implement LoginScreen CSS (flush-left, zero radius, 4.5:1 contrast)
- [ ] Implement MainMenu CSS (design tokens, interaction states)
- [ ] Implement focus-visible outlines on all interactive elements
- [ ] Ensure responsive layout (minimum 320px width)

**Testing (Frontend)**:
- [ ] Unit tests: LoginScreen component (render, handle click, show error)
- [ ] Unit tests: MainMenu component (render items based on capabilities)
- [ ] Unit tests: useAuth hook (return user identity)
- [ ] Unit tests: useCapabilities hook (return capabilities)
- [ ] Integration tests: Full login flow with mock backend
- [ ] Integration tests: Menu rendering for all capability combinations

**Deliverables**: Fully functional frontend UI with MSAL integration and component tests

---

### Phase 3: Integration Testing (2-3 days)

**Note**: Can start once both Phase 1 and Phase 2 are substantially complete

**End-to-End Testing**:
- [ ] Run all 12 validation scenarios from [quickstart.md](quickstart.md)
  - Player sign-in → shows game menu
  - Administrator sign-in → shows admin menu
  - Dual-capability user → shows both menus
  - Unauthorized user → denied with generic message
  - Allowed user with no roles → "no access provisioned" message
  - Capability changes detected on refresh
  - Endpoint-level enforcement prevents bypass
  - Session persistence across navigation
  - Token refresh (automatic and transparent)
  - Sign-out clears session
  - Direct URL access to restricted page is denied
- [ ] Cross-browser testing (Chrome, Firefox, Safari, Edge)
- [ ] Mobile testing (iOS Safari, Android Chrome; minimum 320px width)
- [ ] Accessibility testing (keyboard navigation, screen reader, focus indicators)
- [ ] Performance testing (token validation latency, Cosmos DB query latency)
- [ ] Load testing (simulate multiple concurrent sign-ins)

**Bug Fixes & Refinements**:
- [ ] Fix any issues discovered during end-to-end testing
- [ ] Optimize Cosmos DB queries if latency issues found
- [ ] Improve error messages based on user feedback

**Deliverables**: Fully functional, tested, production-ready login system

---

### Phase 4: Documentation & Deployment (1-2 days)

- [ ] Document API endpoints (Swagger/OpenAPI spec)
- [ ] Document MSAL configuration steps (tenant ID, app ID, redirect URI, scopes)
- [ ] Document Cosmos DB setup (collections, indexing, partition keys)
- [ ] Document environment variables (template .env file)
- [ ] Document deployment steps (Azure Functions, React app, database seeding)
- [ ] Update project README with login instructions
- [ ] Create troubleshooting guide (common sign-in errors, solutions)
- [ ] Deploy to Azure Functions (production)
- [ ] Deploy frontend to App Service or Static Web App (production)
- [ ] Verify production deployment (run validation scenarios against production)

**Deliverables**: Fully documented, deployed, production-ready feature

---

## Parallelization Strategy

**Phase 0** must complete before other phases. Then:

- **Phase 1 (Backend)** and **Phase 2 (Frontend)** can run in parallel
  - Backend team implements API endpoints and database queries
  - Frontend team implements UI components and MSAL integration
  - Frontend can use mock/stub backend for initial component testing
  - They coordinate on API contract (request/response formats from [contracts/api.md](contracts/api.md))
  
- **Phase 3 (Integration)** begins once both Phase 1 and Phase 2 are ready
  - Combines backend and frontend into single end-to-end system
  - Runs full validation suite
  
- **Phase 4 (Documentation)** can start during Phase 3 (in parallel) and completes after Phase 3

**Team Assignments**:
- **Backend Team** (1 developer): Phase 0 (infrastructure), Phase 1 (backend implementation and backend tests)
- **Frontend Team** (1 developer): Phase 0 (infrastructure), Phase 2 (frontend implementation and frontend tests)
- **QA/Integration Team** (1 developer): Phase 3 (integration testing and validation scenarios)
- **All Teams**: Phase 4 (documentation, deployment, verification)

---

## Constitution Compliance Check

This section verifies that the implementation plan satisfies all project governance principles (from `.specify/memory/constitution.md`).

### Principle I: Meaningful, Automated Testing

**Requirement**: Every functionality must have a corresponding automated test before work is considered complete.

**Compliance**:
- ✅ Test: Player sign-in and menu visibility (User Story 1)
- ✅ Test: Administrator sign-in and menu visibility (User Story 2)
- ✅ Test: Unauthorized access denial (User Story 3)
- ✅ Test: Capability changes and re-evaluation
- ✅ Test: Endpoint-level capability enforcement
- ✅ Test: Session persistence across requests
- ✅ Test: Token validation (valid, expired, invalid signature, wrong issuer)
- ✅ Test: Allow-list check (allow-listed and not allow-listed)

**Implementation Detail**: All tests will be automated via pytest (Python) and Jest/React Testing Library (JavaScript). Tests will run as part of CI (GitHub Actions workflow from feature 001-ci-cd-foundation).

---

### Principle II: Secure-by-Default Access

**Requirements**:
- Authentication via Microsoft Entra ID (no public/anonymous access)
- Allow-list based authorization (explicit whitelist only)
- Server-side enforcement (client-side checks not sufficient)

**Compliance**:
- ✅ All endpoints require valid JWT token from Azure AD
- ✅ All endpoints check allow-list before granting access
- ✅ Server-side token validation (PyJWT in backend)
- ✅ Server-side capability checks (every endpoint verifies required capability)
- ✅ No credentials stored in GitHub (use Key Vault and app settings)
- ✅ No public endpoints (all require authentication)

**Implementation Detail**: 
- Token validation middleware is applied to all endpoints
- Allow-list check happens immediately after token validation
- Capability checks happen at both menu render (frontend) and endpoint access (backend)

---

### Principle III: Defined Technology Stack

**Requirements**:
- Backend: Python with Azure Functions
- Frontend: ReactJS
- Any deviation requires documented justification and amendment

**Compliance**:
- ✅ Backend uses Python with PyJWT for token validation
- ✅ Backend is Azure Functions (serverless)
- ✅ Frontend uses ReactJS with MSAL React
- ✅ No alternate technologies (no Node.js backend, no Vue frontend, etc.)
- ✅ Authentication: Microsoft Entra ID (no alternate identity provider)

---

### Principle IV: Simplicity Over Premature Scale

**Requirements**: Build for current requirements only; no speculative scaling infrastructure.

**Compliance**:
- ✅ No Redis/cache layer (per-request token validation is simple)
- ✅ No WebSocket or real-time push (capability changes take effect on next request)
- ✅ No load balancer or CDN (simple Azure Functions + App Service setup)
- ✅ Stateless backend (no in-memory session state to scale horizontally)
- ✅ Database queries are simple and indexed (no complex joins or aggregations)

---

### Principle V: Continuous Integration Gate

**Requirements**:
- GitHub is the system of record
- CI must run automated tests on every PR
- PR must be blocked while tests fail

**Compliance**:
- ✅ All changes via pull request (feature branch workflow)
- ✅ CI (GitHub Actions from feature 001-ci-cd-foundation) runs tests on every PR
- ✅ Merge is blocked if CI fails (branch protection rule)
- ✅ Tests include login and access control scenarios (token validation, allow-list, capabilities)
- ✅ Deployment (via GitHub Actions from 007-azure-infrastructure-provisioning) is triggered only after CI passes
- ✅ Automated deployment prevents manual/untracked changes

---

### Principle VI: Observability & AI Cost Transparency

**Requirements**: OpenTelemetry + Azure Application Insights; no alternate collector or sink.

**Compliance**:
- ✅ Telemetry will include authentication events (login, logout, access denial)
- ✅ Telemetry includes capability checks and authorization decisions
- ✅ Telemetry is structured (JSON, not free-text logs)
- ✅ Application Insights is configured as sink
- ✅ No LLM interactions in this feature, but framework is in place for future features

**Future-Proofing**: Login feature does not make LLM calls (no token tracking needed), but telemetry structure supports LLM features (005, 008, etc.) that will follow.

---

### Principle VII: Zero-Trust Azure Resource Communication

**Requirements**: Managed Identities, Private Endpoints; no shared keys or connection strings.

**Compliance**:
- ✅ Azure Functions uses Managed Identity (provisioned by 007-azure-infrastructure-provisioning) to access Cosmos DB
- ✅ Cosmos DB connection uses Managed Identity authentication (via `AuthType=AAD` in connection string, not shared key)
- ✅ Private Endpoint for Cosmos DB (provisioned by 007; no public network access)
- ✅ App registration secrets managed via Azure AD; not hardcoded
- ✅ No shared keys or connection strings in code (Managed Identity handles authentication; resource names/IDs in application settings)

**Implementation Detail**: 
- Managed Identity is auto-created by 007 on Azure Functions app deployment
- 007 assigns Cosmos DB `Cosmos DB Data Contributor` role to the function identity
- 007 configures Cosmos DB to reject public network access; accepts only Private Endpoint traffic
- This feature uses connection string format: `AccountEndpoint=https://<account>.documents.azure.com/;AuthType=AAD;` (Managed Identity authentication)
- Application settings (from 007's Function App configuration) provide the Cosmos DB endpoint; no credentials needed in code

---

### Principle VIII: UI Design System & Accessibility Compliance

**Requirements**:
- Exclusive use of design-token layer and shared components
- Visual, interaction, readability, layout, and accessibility requirements
- Every implementation plan includes Constitution Check

**Compliance**:

#### Visual Rules

- ✅ Zero corner radius (all buttons and containers are flush-cornered)
- ✅ Flush-left alignment (text and form elements start at left edge)
- ✅ Section separation via visible dividing rules (not whitespace alone)
- ✅ Accent color used sparingly (only on primary action button)
- ✅ Layout structure visible (no hidden behind whitespace)
- ✅ No oversized playful typography (reserved for chapter numbers in game, not login screen)
- ✅ No photography or tinted imagery
- ✅ Icons from single consistent set (if any used)

#### Interaction States

- ✅ Hover: Accent tint on "Sign in with Microsoft" button
- ✅ Pressed: One step past base accent shade
- ✅ Focus: Visible `:focus-visible` outline with 4px offset in accent color
- ✅ Disabled: Reduced opacity + `cursor: not-allowed` during loading

#### Readability Requirements

- ✅ Body copy at minimum comfortable reading size
- ✅ Interface labels never below legible size
- ✅ Touch targets at least 44x44px (button height for mobile)
- ✅ No required exact spelling or phrasing (not applicable for this feature)
- ✅ Player input forgiving (not applicable for login; Microsoft handles input)
- ✅ Suggested actions always available (Microsoft sign-in is the only action)
- ✅ Copy is plain, warm, and concrete (no technical jargon; clear error messages)
- ✅ No shaming language or artificial pressure

#### Layout and Scroll Contract

- ✅ Application shell fixed to viewport (no page-level scroll)
- ✅ Login screen is single screen; no scrolling needed
- ✅ Usable at minimum viewport width 320px (mobile portrait)
- ✅ Secondary panels collapse above primary content (not applicable for login)

#### Accessibility

- ✅ Body copy meets 4.5:1 contrast (dark text on light background per design system)
- ✅ Fully operable by keyboard alone (Tab to button, Enter to sign in)
- ✅ Visible focus indicator at all times (::focus-visible outline)
- ✅ Semantic HTML (real `<button>`, not `<div>` with click handler)
- ✅ Meaning not carried by color alone (error messages include text, not just red color)

#### Design File Reference

- ✅ Login screen prototype at `specs/designs/01-login.html` is the acceptance reference
- ✅ Shared stylesheet `specs/designs/styles.css` is the token source
- ✅ Menu items on other screens (02-story-select.html, 03-play.html, 04-admin-wizard.html) also follow design system
- ✅ No screen-local reimplementation of menu; reuse same component

#### Exception Requests

**None requested**. This implementation adheres to all UI Design System requirements without exception.

---

## Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Token validation fails (malformed public key URL) | Medium | Implement retry logic; test with known-good Azure AD configuration |
| Database connection fails during auth | High | Use connection pooling; implement exponential backoff retry; log to Application Insights |
| MSAL configuration incorrect (app ID, redirect URI) | High | Validate MSAL config in test environment before deployment; document setup steps |
| Capability data stale between requests | Low | Per-request validation is intentional design (catches changes immediately) |
| Token refresh fails (network error) | Low | MSAL handles fallback; user can manually refresh or re-sign in |
| Unauthorized user guesses URL to admin page | Low | Server-side capability enforcement prevents access regardless of menu state |

---

## Testing Strategy

### Unit Tests

- Token validation logic (valid token, expired, invalid signature, wrong issuer)
- Allow-list lookup (found, not found, soft-deleted)
- Capability fetch (Player, Admin, both, neither)
- Error response formatting

### Integration Tests

- `/api/auth/login` with various token states
- `/api/auth/me` returns correct capabilities
- Capability-gated endpoints (`/api/game/start`, `/api/admin/stories`) enforce restrictions
- MSAL login flow end-to-end (in controlled environment)

### End-to-End Tests

- All 12 validation scenarios from quickstart.md
- Player sign-in, menu visibility, game access
- Administrator sign-in, menu visibility, admin access
- Unauthorized user denied
- Session persistence across pages
- Token refresh and expiry
- Capability change detection

---

## Deployment

### Prerequisites

- Azure subscription with access to resources provisioned by 007-azure-infrastructure-provisioning
- GitHub repository with CI/CD workflow (feature 001-ci-cd-foundation)
- Azure AD tenant and app registration (for MSAL frontend config)
- Infrastructure from 007-azure-infrastructure-provisioning complete:
  - Cosmos DB serverless account created
  - Azure Functions app provisioned
  - Azure Static Web App provisioned
  - Managed Identity and Private Endpoints configured
  - GitHub Actions deployment workflow with OIDC federation configured

### Deployment Steps

1. **Infrastructure Setup** (handled by feature 007; verify before proceeding):
   - ✓ Cosmos DB serverless account exists (provisioned by 007)
   - ✓ Azure Functions app exists (provisioned by 007)
   - ✓ Managed Identity configured on Functions app (provisioned by 007)
   - ✓ Private Endpoints configured (provisioned by 007)
   - ✓ GitHub Actions OIDC federation configured (provisioned by 007)

2. **Database Schema** (this feature):
   - Create `allowListEntries` collection in Cosmos DB (via code or SDK)
   - Create `capabilityAssignments` collection in Cosmos DB (via code or SDK)
   - Seed test data (allow-list entries, capability assignments)

3. **Backend**:
   - Deploy Azure Functions code (via GitHub Actions from 007's deployment workflow)
   - Configure Function App application settings:
     - `AZURE_TENANT_ID` (from Azure AD app registration)
     - `AZURE_APP_ID` (from Azure AD app registration)
     - `COSMOS_ENDPOINT` (from 007's infrastructure output)
   - Function App identity already has Cosmos DB access via Managed Identity (from 007)

4. **Frontend**:
   - Configure MSAL with Azure AD app ID, tenant ID, and redirect URI
   - Deploy React app to Static Web App (via GitHub Actions from 007's deployment workflow)

5. **Validation**:
   - Run quickstart validation scenarios from [quickstart.md](quickstart.md)
   - Verify all 12 end-to-end tests pass
   - Verify CI tests pass (from feature 001-ci-cd-foundation)

---

## Success Criteria

- [ ] All 12 validation scenarios from quickstart.md pass
- [ ] All unit and integration tests pass in CI
- [ ] 100% of sign-in attempts from authorized users succeed
- [ ] 100% of sign-in attempts from unauthorized users are denied with generic message
- [ ] Capabilities are correctly evaluated based on database state
- [ ] Session persists across multiple API requests without re-login
- [ ] Constitution compliance verified (all principles satisfied)
- [ ] No secrets stored in code or GitHub
- [ ] Telemetry includes authentication and authorization events
- [ ] Error messages are user-friendly (no technical jargon)

---

## Timeline Estimate

With parallel backend and frontend work, and accounting for 007-azure-infrastructure-provisioning:

| Phase | Serial Duration | Notes |
|-------|-----------------|-------|
| Phase 0: Infrastructure Setup | 0.5-1 day | Minimal effort (007 handles Azure resources); mostly: Cosmos DB collections, AD app config, seed data |
| Phase 1: Backend | 3-4 days | Runs parallel with Phase 2; assumes 007 infrastructure is ready |
| Phase 2: Frontend | 3-4 days | Runs parallel with Phase 1; can use mock backend initially |
| Phase 3: Integration & Testing | 2-3 days | Starts after Phase 1 & 2 substantially complete; requires 007 fully operational |
| Phase 4: Documentation & Deployment | 1-2 days | Can partially overlap with Phase 3; deployment via 007's GitHub Actions workflow |

**Total (Serial)**: 7-12 days (if one developer; assumes 007 infrastructure ready)  
**Total (Parallel)**: 6-9 days (with backend + frontend teams working simultaneously; assumes 007 infrastructure ready)

**Critical Path**: 007 infrastructure ready → Phase 0 → (Phase 1 + Phase 2 in parallel) → Phase 3 → Phase 4

**Dependency on 007**:
- If 007 infrastructure not yet ready: Phase 0 and initial Phase 1 backend can proceed in parallel with 007's provisioning
- Full integration testing (Phase 3) requires 007 to be fully operational
- Deployment (Phase 4) uses 007's GitHub Actions workflow and Azure resources

**Recommended Team Setup** (parallel execution):
- **Backend Developer**: 1.5-2 weeks (Phase 0, Phase 1 + Phase 3, Phase 4 documentation)
- **Frontend Developer**: 1.5-2 weeks (Phase 0, Phase 2 + Phase 3, Phase 4 documentation)
- **QA/Tester**: 1 week (Phase 3 validation, Phase 4 final verification)
- **Infrastructure Team** (Feature 007): ~2 weeks (runs in parallel; ready before Phase 3 of this feature)

---

## Relationship with Feature 007: Azure Infrastructure Provisioning

This feature has an explicit dependency on [007-azure-infrastructure-provisioning](../007-azure-infrastructure-provisioning/spec.md). The two features are designed to work together:

### What 007 Provides

Feature 007 handles all Azure infrastructure provisioning via Terraform:
- **Compute**: Azure Functions app with Python runtime
- **Frontend Hosting**: Azure Static Web App
- **Storage**: Cosmos DB serverless account (account-level; 002 creates collections)
- **Networking**: Private Endpoints for Cosmos DB, Blob Storage, Azure AI Foundry
- **Identity**: Managed Identity on Functions app for keyless authentication
- **CI/CD**: GitHub Actions deployment workflows with OIDC federation
- **Application Configuration**: Function App application settings framework

### What 002 Provides

This feature focuses on application-level authentication and authorization:
- **Auth Logic**: Token validation, allow-list checks, capability evaluation
- **Database Schema**: Cosmos DB collections (`allowListEntries`, `capabilityAssignments`)
- **API Endpoints**: `/api/auth/login`, `/api/auth/me`, `/api/auth/logout`
- **Frontend UI**: Login screen, menu components, MSAL integration
- **Test Scenarios**: 12 end-to-end validation scenarios

### Execution Order

1. **007 must be substantially complete** before 002 can fully deploy
   - Phase 0 of 002 assumes infrastructure from 007 exists
   - Early phases of 002 can proceed in parallel with 007's infrastructure provisioning
   - Phase 3+ of 002 (integration testing) requires 007's infrastructure to be fully operational

2. **Recommended flow**:
   - Start: 001-ci-cd-foundation (sets up GitHub Actions framework)
   - In parallel: 007-azure-infrastructure-provisioning (provisions Azure resources)
   - Once 007 Phase 0 complete: 002-login-and-access-control Phases 0-2 can proceed
   - Once 007 fully complete: 002 Phase 3+ (integration testing, deployment) proceeds

### Coordination Points

| Dependency | Provided By | Consumed By | Purpose |
|------------|-------------|------------|---------|
| Cosmos DB serverless account | 007 | 002 | Stores allow-list and capabilities |
| Azure Functions app | 007 | 002 | Backend runtime for auth endpoints |
| Managed Identity | 007 | 002 | Keyless Cosmos DB authentication |
| Private Endpoint (Cosmos DB) | 007 | 002 | Private network access to database |
| Function App application settings | 007 | 002 | Provides tenant ID, app ID, resource names |
| GitHub Actions deployment workflow | 007 | 002 | Automated backend and frontend deployment |
| Static Web App | 007 | 002 | Frontend hosting |

### Independence

The two features remain independent in their scopes:
- 007 does **not** know about authentication/authorization logic
- 002 does **not** define infrastructure provisioning details
- Changes to 002's auth logic do not require 007 changes
- Changes to 007's Terraform do not affect 002's code (except credentials/resource names, which flow via application settings)

---

## Next Steps

1. Review and approve this plan
2. Run `/speckit-tasks` to generate detailed implementation task breakdown
3. Begin Phase 1 (Infrastructure Setup)
4. Track progress in GitHub issues or project board
5. Run CI tests on every PR (automatic via feature 001-ci-cd-foundation)

---

## References

- [Specification](spec.md) — User stories and functional requirements
- [Research Document](research.md) — Technical decisions and rationale
- [Data Model](data-model.md) — Entities and database schema
- [API Contracts](contracts/api.md) — Request/response formats
- [UI Contracts](contracts/ui-login-screen.md) and [Menu States](contracts/ui-menu-states.md) — Screen designs and interactions
- [Quickstart Validation](quickstart.md) — End-to-end testing scenarios
- [Constitution](../../.specify/memory/constitution.md) — Project governance and principles
