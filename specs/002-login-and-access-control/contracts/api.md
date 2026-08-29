# API Contracts: Login and Access Control

**Date**: 2026-08-28

**Feature**: Login and Access Control (002-login-and-access-control)

This document defines the API contracts (request/response schemas) that implement authentication and authorization for this feature.

---

## Overview

The login and access control feature exposes three primary API endpoints:

1. **`POST /api/auth/login`** — Validates a token obtained from Microsoft Entra ID and returns user identity and capabilities
2. **`GET /api/auth/me`** — Returns the currently authenticated user's identity and capabilities
3. **`POST /api/auth/logout`** — Clears the user's session (frontend-initiated; backend clears any server-side state)

Additional API endpoints (for game, admin, etc.) are capability-gated but defined in their respective feature specs.

---

## Authentication Header

**All requests (except initial login)** MUST include:

```http
Authorization: Bearer <access_token>
```

where `<access_token>` is a valid JWT token obtained from Microsoft Entra ID via MSAL.

**Token Format**:
- Issued by: Azure AD (`https://login.microsoftonline.com/{tenant-id}/v2.0`)
- Signed with: Azure AD's public key (available at `https://login.microsoftonline.com/{tenant-id}/discovery/v2.0/keys`)
- Contains claims: `oid` (user object ID), `email` (optional), `exp` (expiry), `iss` (issuer), `aud` (audience/app ID)

---

## Contract 1: POST /api/auth/login

**Purpose**: Validate a newly obtained token and return the user's identity and capabilities.

**Request**:

```http
POST /api/auth/login HTTP/1.1
Content-Type: application/json
Authorization: Bearer <id_token_from_msal>

{
  "token": "<id_token_string>"
}
```

**OR** (simpler): Extract token from `Authorization` header; no JSON body required.

```http
POST /api/auth/login HTTP/1.1
Authorization: Bearer <id_token_from_msal>
```

**Response (200 OK)** — User is authenticated and allowed:

```json
{
  "user_oid": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@outlook.com",
  "is_allowed": true,
  "capabilities": ["Player"],
  "has_player": true,
  "has_administrator": false,
  "expires_at": "2026-08-28T22:00:00Z"
}
```

**Response (401 Unauthorized)** — No valid token provided:

```http
HTTP/1.1 401 Unauthorized
Content-Type: application/json

{
  "error": "unauthenticated",
  "message": "No valid authentication token provided"
}
```

**Response (403 Forbidden)** — Token is valid but user is not on the allow-list:

```http
HTTP/1.1 403 Forbidden
Content-Type: application/json

{
  "error": "access_denied",
  "message": "Access not granted"
}
```

**Response (403 Forbidden)** — User is on allow-list but has no capabilities:

```http
HTTP/1.1 403 Forbidden
Content-Type: application/json

{
  "error": "no_capabilities",
  "message": "Access provisioned but no roles assigned. Contact your administrator."
}
```

### Validation Rules

- **Token must be a valid JWT**: Signature verified against Azure AD public key; expiry checked
- **Token must be from the correct tenant**: `iss` claim must match configured Azure AD tenant
- **Token audience must match app**: `aud` claim must match app registration ID
- **User oid must exist in Allow-List Entry**: If not found, return 403 regardless of token validity (prevents account enumeration)
- **Do not reveal allow-list membership**: Return generic "Access not granted" message; do not indicate whether account is known

---

## Contract 2: GET /api/auth/me

**Purpose**: Return the currently authenticated user's identity and current capabilities.

**Request**:

```http
GET /api/auth/me HTTP/1.1
Authorization: Bearer <access_token>
```

**Response (200 OK)** — User is authenticated and allowed:

```json
{
  "user_oid": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@outlook.com",
  "capabilities": ["Player", "Administrator"],
  "has_player": true,
  "has_administrator": true
}
```

**Response (401 Unauthorized)** — No valid token:

```http
HTTP/1.1 401 Unauthorized
Content-Type: application/json

{
  "error": "unauthenticated",
  "message": "No valid authentication token provided"
}
```

**Response (403 Forbidden)** — Token is valid but user is not on allow-list:

```http
HTTP/1.1 403 Forbidden
Content-Type: application/json

{
  "error": "access_denied",
  "message": "Access not granted"
}
```

### Purpose and Use Cases

- Called by frontend after login to populate menu
- Called before navigating to game or admin pages to check if user still has required capability
- Called on page refresh to detect any capability changes since last check
- Allows frontend to react to capability changes without requiring logout/login

---

## Contract 3: POST /api/auth/logout

**Purpose**: Clear the user's session on the backend (if any server-side state exists) and signal successful logout.

**Request**:

```http
POST /api/auth/logout HTTP/1.1
Authorization: Bearer <access_token>
```

**Response (200 OK)**:

```json
{
  "message": "Logged out successfully"
}
```

**Response (401 Unauthorized)** — No valid token:

```http
HTTP/1.1 401 Unauthorized
Content-Type: application/json

{
  "error": "unauthenticated"
}
```

### Notes

- Backend does not maintain server-side session state (per decision in research.md); this endpoint is primarily a signal to clear browser-side state
- Frontend will call MSAL's `logout()` method to clear browser localStorage
- Endpoint may be useful for future audit logging or cleanup if server state is added later

---

## Standard Error Response Format

All error responses follow this format:

```json
{
  "error": "<error_code>",
  "message": "<human_readable_message>",
  "details": "<optional_additional_context>"
}
```

**Standard Error Codes**:

| Code | HTTP Status | Meaning | Message to User |
|------|-------------|---------|-----------------|
| `unauthenticated` | 401 | No valid token provided | "No valid authentication token provided" |
| `invalid_token` | 401 | Token is malformed, expired, or invalid | "Authentication token is invalid or expired. Please sign in again." |
| `access_denied` | 403 | User is not on allow-list | "Access not granted" |
| `no_capabilities` | 403 | User is allowed but has no capabilities | "Access provisioned but no roles assigned. Contact your administrator." |
| `insufficient_permission` | 403 | User lacks required capability for endpoint | "You do not have permission to access this resource" |
| `internal_error` | 500 | Server-side error during auth check | "An error occurred while processing your request. Please try again." |

---

## Capability-Gated Endpoint Pattern

**All capability-gated endpoints** follow this pattern:

**Endpoint requiring Player capability**:

```http
POST /api/game/start HTTP/1.1
Authorization: Bearer <access_token>
```

**Response (200 OK)** — User has Player capability:

```json
{
  "game_id": "abc123",
  "started_at": "2026-08-28T20:00:00Z"
}
```

**Response (403 Forbidden)** — User lacks Player capability:

```http
HTTP/1.1 403 Forbidden
Content-Type: application/json

{
  "error": "insufficient_permission",
  "message": "You do not have permission to access this resource"
}
```

**Endpoint requiring Administrator capability**:

```http
POST /api/admin/stories/create HTTP/1.1
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "title": "My Story"
}
```

**Response (200 OK)** — User has Administrator capability:

```json
{
  "story_id": "story-123"
}
```

**Response (403 Forbidden)** — User lacks Administrator capability:

```http
HTTP/1.1 403 Forbidden
Content-Type: application/json

{
  "error": "insufficient_permission",
  "message": "You do not have permission to access this resource"
}
```

---

## Header Contract

**Request Headers** (all requests):

| Header | Required | Value |
|--------|----------|-------|
| `Authorization` | Yes (except login) | `Bearer <token>` |
| `Content-Type` | If body present | `application/json` |

**Response Headers** (all responses):

| Header | Value | Rationale |
|--------|-------|-----------|
| `Content-Type` | `application/json` | Indicates JSON response body |
| `Cache-Control` | `no-store` | Prevent caching of auth responses |
| `X-Content-Type-Options` | `nosniff` | Prevent MIME-sniffing attacks |
| `Strict-Transport-Security` | `max-age=31536000` | Enforce HTTPS |

---

## Response Status Codes

| Status | Meaning | When Used |
|--------|---------|-----------|
| `200 OK` | Request succeeded | Token valid, user allowed, capabilities fetched |
| `400 Bad Request` | Malformed request | Missing required fields, invalid JSON |
| `401 Unauthorized` | No valid authentication | No token, expired token, invalid signature |
| `403 Forbidden` | Valid auth but not authorized | User not on allow-list, lacks required capability |
| `500 Internal Server Error` | Server error | Database connection failed, token validation error, etc. |
| `503 Service Unavailable` | Temporary unavailability | Azure AD unreachable, database temporarily unavailable |

---

## Token Validation Algorithm (Backend)

1. Extract token from `Authorization: Bearer <token>` header
2. Verify token signature using Azure AD's public key from `.well-known/openid-configuration`
3. Verify token expiry (`exp` claim)
4. Verify token issuer (`iss` claim matches configured Azure AD tenant)
5. Verify token audience (`aud` claim matches app registration ID)
6. Extract user object ID (`oid` claim)
7. Query Allow-List Entry table for matching `user_oid` with `date_removed IS NULL`
   - If not found: return 403 Forbidden with "Access not granted"
   - If found: continue to step 8
8. Query Capability Assignment table for matching `user_oid` with `date_revoked IS NULL`
   - If no rows found: return 403 Forbidden with "no access provisioned yet" (optional; or allow access with empty capabilities)
   - If rows found: extract capability names
9. Return 200 OK with user identity and capabilities

---

## Implementation Notes

### Frontend (MSAL React)

```typescript
// Acquire token
const token = await msalInstance.acquireTokenSilent({
  scopes: ["api://<app-id>/.default"]
});

// Make authenticated request
const response = await fetch("/api/auth/me", {
  headers: {
    "Authorization": `Bearer ${token.accessToken}`
  }
});
```

### Backend (Python with PyJWT)

```python
from jwt import decode
from jwt.exceptions import InvalidTokenError

def verify_token(token: str):
    try:
        # Fetch Azure AD public key
        jwks_url = f"https://login.microsoftonline.com/{TENANT_ID}/discovery/v2.0/keys"
        
        # Decode and validate
        decoded = decode(
            token,
            key=get_signing_key(jwks_url),
            algorithms=["RS256"],
            audience=APP_ID,
            issuer=f"https://login.microsoftonline.com/{TENANT_ID}/v2.0"
        )
        
        return decoded.get("oid")
    except InvalidTokenError as e:
        raise AuthenticationError(str(e))
```

---

## Security Considerations

1. **No information disclosure**: Do not reveal whether a user is on the allow-list; return the same error for missing and denied users
2. **Token expiry**: Tokens are short-lived (default 1 hour); backend does not cache validation results
3. **HTTPS only**: All API communication must use HTTPS; redirect HTTP to HTTPS
4. **No session tokens**: Use bearer token from Azure AD; do not create custom session tokens
5. **Capability checks on destination**: Always verify capability at the endpoint level, not just in the menu
6. **Rate limiting**: Consider rate limiting on login endpoint to prevent brute force (future enhancement, not required for MVP)

---

## Future Extensions (Not in MVP Scope)

These capabilities are documented here for reference but are not required for the initial implementation:

- **Multi-factor authentication (MFA)**: Can be enforced via Azure AD app registration settings
- **Rate limiting**: Add to prevent brute force attempts
- **Audit logging**: Log all authentication and authorization decisions to Application Insights
- **Device compliance**: Require device to be registered/managed in Intune (future)
- **Conditional access**: Leverage Azure AD Conditional Access policies (future)
