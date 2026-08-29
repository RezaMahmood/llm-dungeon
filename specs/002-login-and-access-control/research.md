# Research: Login and Access Control Technical Decisions

**Date**: 2026-08-28

**Feature**: Login and Access Control (002-login-and-access-control)

This document captures technical research and decisions made to satisfy the functional requirements of this feature within the constraints of the project's technology stack and constitution.

---

## Decision 1: Frontend Authentication Library (MSAL React)

**Decision**: Use Microsoft Authentication Library for React (MSAL React, `@azure/msal-react@2.x`) for handling Microsoft Entra ID sign-in flow on the frontend.

**Rationale**:
- MSAL React is the official, Microsoft-maintained library for React applications authenticating with Entra ID
- Provides automatic token refresh and cache management
- Handles the OAuth 2.0 Authorization Code flow with PKCE (Proof Key for Code Exchange) — the recommended flow for public clients (browser-based SPAs)
- Integrates seamlessly with Azure Functions backend via token bearer authentication
- Actively maintained and widely used in production Azure applications

**Alternatives Considered**:
- Direct `fetch` calls to Azure AD endpoints: Too low-level; would require manual token refresh, caching, and error handling
- Auth0 or alternate identity provider: Violates Constitution Principle II (Microsoft Entra ID is required)
- ADAL (deprecated): Replaced by MSAL; no longer receiving updates

**Implementation Detail**: 
- MSAL configuration will be stored in environment variables (e.g., Azure subscription tenant ID, app registration ID, redirect URI)
- Frontend will call `useMsal()` hook to get authentication state and request token
- Token will be sent to backend in `Authorization: Bearer <token>` header

---

## Decision 2: Backend Token Validation Strategy

**Decision**: Validate ID tokens on every incoming request (no caching of token validation state). Cache only the user identity and capability roles in the Azure Functions context during a single request.

**Rationale**:
- Validates that token has not been revoked (security requirement per Constitution Principle II)
- Ensures capability changes (allow-list removal, role assignment changes) take effect on the next request, not the next browser restart
- Azure Functions' stateless nature makes per-request validation a natural fit (no persistent in-memory cache to invalidate)
- Token validation cost is acceptable given expected load; performance can be optimized later if needed (per Principle IV)

**Alternatives Considered**:
- Cache validation result in Azure Functions memory across requests: Risky because function instance may be recycled; capability changes wouldn't take effect until instance restart
- Cache validation result in distributed store (Redis): Violates Principle IV (adds complexity without stated scale requirement) and Principle VII (introduces another Azure service and credential management)
- Validate only on first request per session: Doesn't catch revocation or allow-list removal mid-session

**Implementation Detail**:
- Backend will extract and validate JWT tokens using the public key from Azure AD's `/.well-known/openid-configuration` endpoint
- Token expiry and signature will be verified
- User's object ID (oid claim) will be extracted and used to look up capabilities

---

## Decision 3: Allow-List and Capability Storage

**Decision**: Store allow-list entries and capability assignments in Azure SQL Database or Azure Table Storage (exact choice deferred to infrastructure phase). Each entry maps a Microsoft user's object ID (oid) to:
- Whether they are on the allow-list (boolean flag)
- Assigned capabilities: Player (yes/no), Administrator (yes/no)

**Rationale**:
- Allows fine-grained, per-user capability assignment independent of Entra ID's app-role system
- Simplifies administration (add/remove rows vs managing Entra ID role assignments)
- Provides an audit trail (who changed what, when)
- Can be extended later to store other per-user data without schema changes to Entra ID

**Alternatives Considered**:
- Store capabilities as Entra ID app roles and check via role claims in token: More rigid; requires app registration changes to add/remove users or roles; less audit history
- Store in GitHub config file or app settings: Not suitable for user data (security, scalability, audit trail)
- Use Entra ID's Dynamic Groups: Over-engineered for this use case; adds complexity without benefit

**Implementation Detail**:
- Backend will query the allow-list table on every request (after token validation)
- If user's oid is not on the allow-list, return 403 Forbidden with a generic message (no account enumeration)
- If user is on allow-list, fetch their assigned capabilities (Player, Administrator, or both)
- If user is on allow-list but has no capabilities assigned, allow them to sign in but show a "no access provisioned yet" message

---

## Decision 4: Session Management and Token Refresh

**Decision**: Use browser-native session storage (managed by MSAL's token cache) to store access tokens. Tokens are requested with a 1-hour default lifetime (Entra ID default). Frontend will automatically refresh tokens via MSAL's silent token request flow before expiry. No explicit "logout" token blacklist; logout clears local browser storage.

**Rationale**:
- MSAL automatically handles token refresh without user interaction (silent flow)
- No need to build a custom token refresh endpoint or manage server-side session state
- 1-hour token lifetime is the Entra ID default and provides a reasonable balance between security and UX (if a token is compromised, damage is time-limited)
- User's capability changes will take effect on the next API request (which may require token refresh), per Decision 2
- Stateless backend design (per Principle IV, no in-memory session caching)

**Alternatives Considered**:
- Store access token in httpOnly cookie: More secure against XSS but less common in SPA patterns; MSAL doesn't natively support this
- Custom session table in backend: Adds backend state management; violates Principle IV
- Longer token lifetime (e.g., 8 hours): Increases risk window for revoked tokens; changes take effect slower

**Implementation Detail**:
- MSAL's token cache will persist to browser `localStorage` (unencrypted; tokens are short-lived and bearer tokens)
- Frontend will intercept API calls and attach `Authorization: Bearer <token>` header
- MSAL will automatically request a new token before current one expires
- On logout, MSAL clears local storage; subsequent API calls without a token return 401

---

## Decision 5: Capability Change Detection and Timing

**Decision**: Capability changes (e.g., adding/removing a user, changing Player to Administrator) take effect on the next API request, not immediately. No real-time push notification to the browser. User menu re-evaluates on every page navigation or explicit refresh.

**Rationale**:
- Simplifies implementation (no server push required; violates Principle IV)
- Still provides reasonable UX: changes within one request latency (typically <1 second)
- Matches typical SPA behavior for permission/role changes
- Aligns with Constitution Principle IV (no unnecessary complexity for immediate consistency, which isn't a stated requirement)
- If a user is in the middle of an action when their role is revoked, their current page won't break; next navigation or manual refresh shows the updated menu

**Alternatives Considered**:
- WebSocket or Server-Sent Events for real-time capability updates: Over-engineered; adds significant complexity and backend state
- Cache invalidation via a version number: Still requires polling or push; doesn't improve latency

**Implementation Detail**:
- Frontend fetches user capabilities once at login and on explicit refresh
- Backend returns updated capabilities on every auth check (menu fetch, page navigation)
- No in-browser caching of menu items; menu component is re-rendered from capabilities on every navigation

---

## Decision 6: Sign-In Failure and Error Handling

**Decision**: 
- Sign-in failures from Microsoft (e.g., user closes login window, network error): Return user to pre-login state with option to retry, display a user-friendly message
- Allow-list denial (user is not on allow-list): Display a clear, generic message ("Access not granted") without revealing whether the account exists
- No capabilities assigned: Display a message ("Access provisioned but no roles assigned; contact administrator") explaining the situation

**Rationale**:
- Prevents account enumeration attacks (spec FR-010, Principle II)
- Provides helpful UX without exposing security-sensitive details
- Aligns with spec requirement for "clear, human-readable messages"

**Implementation Detail**:
- Frontend catches MSAL authentication errors; displays a modal or banner with the message
- Backend returns generic 403 responses with identical message for allow-list denial and revoked tokens (indistinguishable to attacker)
- Backend returns 401 if no token provided, 403 if token is invalid or user is not on allow-list

---

## Decision 7: Frontend Menu Component Architecture

**Decision**: Create a server-side endpoint `/api/auth/me` that returns the current user's identity and capabilities. The frontend calls this after sign-in and on page navigation to determine which menu items to show.

**Rationale**:
- Single source of truth for capability-to-menu-item mapping (server-side)
- Supports easy capability changes without frontend redeploy
- Prevents client-side menu manipulation (frontend is not trusted per Principle II)
- Enables menu-item order/content customization per user or tenant without frontend changes

**Alternatives Considered**:
- Embed capabilities in the ID token (as Entra ID app roles): Doesn't support custom allow-list; requires app registration changes to add users
- Frontend calls separate endpoint for each menu permission: Inefficient; requires many API calls

**Implementation Detail**:
- Backend endpoint `/api/auth/me` requires valid token and return user oid, email, and assigned capabilities (Player: yes/no, Administrator: yes/no)
- Frontend calls this after MSAL completes login and stores result in React state
- Menu component uses state to conditionally render game and admin menu items
- Menu component calls `/api/auth/me` on every page load/navigation to refresh

---

## Decision 8: Bypass Prevention (Direct URL Access)

**Decision**: Backend enforces capability checks at the destination endpoint (e.g., `/api/game/start` requires Player capability, `/api/admin/*` requires Administrator capability), in addition to frontend menu gating.

**Rationale**:
- Specification requirement FR-009: "enforce capability-based access at the destination (administration page, game menu) as well as at the menu display"
- Prevents bypassing frontend menu restrictions (malicious user visits `/admin` directly without permission)
- Client-side gating alone is not sufficient per Principle II (server-side enforcement required)

**Implementation Detail**:
- Backend will check capabilities on every request to a capability-gated endpoint
- `/api/auth/me` is public (but requires valid token)
- `/api/game/*` endpoints require Player capability and return 403 if not present
- `/api/admin/*` endpoints require Administrator capability and return 403 if not present

---

## Summary of Technical Stack for This Feature

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Frontend Auth | MSAL React | Microsoft-maintained, official Entra ID library |
| Backend Auth | Azure AD JWT validation (via PyJWT or similar) | Validates tokens, extracts user identity |
| Allow-List Storage | Azure SQL Database or Table Storage | Persistent, queryable, auditable |
| Session Management | Browser localStorage + MSAL auto-refresh | Stateless backend; automatic token refresh |
| Menu API | GET `/api/auth/me` | Returns user identity and capabilities |
| Backend Validation | Per-request token + capability check | Catches revocations and capability changes immediately |

---

## Next Steps

These research findings inform the design phase:
- **data-model.md** will define the Allow-List and Capability entities in detail
- **contracts/** will define the `/api/auth/me` API contract and authentication headers
- **quickstart.md** will document validation scenarios for sign-in, capability checking, and access denial
