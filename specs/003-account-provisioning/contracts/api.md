# API Contracts: Account Provisioning

**Date**: 2026-08-29

**Feature**: Account Provisioning (003-account-provisioning)

This document defines the two new admin endpoints this feature adds, and the behavior change to the two existing sign-in endpoints from `002-login-and-access-control`. Response shapes follow the helpers actually shipped in `src/backend/api/utils.py` (`json_response`, `error_response`), not the earlier snake_case examples in `002`'s own contract doc, which predate its implementation.

---

## Changed: POST /api/auth/login and GET /api/auth/me

**Purpose (unchanged)**: Validate the bearer token and return the signed-in user's identity and capabilities.

**Behavior change**: Both handlers now resolve the Provisioned Account Entry by the token's lowercased `email` claim (not by `oid`), then apply the bind/verify rule:

- If the entry's `objectId` is `null` (first sign-in): bind `objectId` to the token's `oid`, persist, and proceed as allowed.
- If the entry's `objectId` equals the token's `oid`: proceed as allowed.
- If the entry's `objectId` is set and differs from the token's `oid`: deny access (same generic response as "not provisioned" — no enumeration).
- If no entry exists for that email: deny access, as today.

**Response (200 OK)** — unchanged shape:

```json
{
  "status": "success",
  "user": { "oid": "550e8400-e29b-41d4-a716-446655440000", "email": "player@example.com" },
  "capabilities": { "hasPlayer": true, "hasAdministrator": false }
}
```

**Response (401 Unauthorized)** — unchanged (`unauthorized()` helper):

```json
{ "error": "unauthenticated", "message": "No valid authentication token provided" }
```

**Response (403 Forbidden)** — unchanged generic shape (`forbidden_access_not_granted()` helper), now also returned for the oid-mismatch case:

```json
{ "error": "access_denied", "message": "Access not granted" }
```

### Validation Rules

- Token's `email` claim MUST be present; if absent, treat as `unauthenticated` (a token this app issues should always carry it — research.md §2 — so this is a defensive branch, not an expected path).
- Email is lowercased before lookup (FR-008).
- A bound `objectId` mismatch returns the exact same response as "no entry for this email" — the client cannot distinguish "unknown account" from "known account, wrong device/identity" (no enumeration, consistent with 002's existing rule).

---

## New: POST /api/manage/accounts

**Purpose**: Create a new Provisioned Account Entry, or merge roles into an existing one (FR-002/FR-003/FR-004/FR-005/FR-009).

**Authorization**: Administrator capability required (`authorize_admin` middleware, same pattern as `manage/stories/create`).

**Request**:

```http
POST /api/manage/accounts HTTP/1.1
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "email": "NewPlayer@Example.com",
  "roles": ["Player"]
}
```

**Response (200 OK)** — created or merged; body reflects the entry's current, post-merge state:

```json
{
  "status": "success",
  "account": {
    "email": "newplayer@example.com",
    "roles": ["Player"],
    "bound": false
  }
}
```

`bound` is `true` once the entry has a non-null `objectId` (i.e., that account has signed in at least once) — surfaced so the admin list (below) can show it without exposing the raw `objectId`.

**Response (400 Bad Request)** — no role selected:

```json
{ "error": "role_required", "message": "Select at least one role (Player and/or Administrator)." }
```

**Response (400 Bad Request)** — malformed email (FR-005):

```json
{ "error": "invalid_email", "message": "Enter a valid email address." }
```

**Response (401 / 403)** — same `unauthorized()` / `forbidden_access_not_granted()` / `forbidden_insufficient_permission()` shapes used by every other admin endpoint.

### Validation Rules

- `email` MUST pass RFC 5322 validation via `pyisemail` (research.md §1) before any further processing.
- `roles` MUST be a non-empty array drawn only from `["Player", "Administrator"]`; anything else is a 400 with `role_required` (empty) — an unrecognized role string is also rejected the same way, since the UI only ever offers these two.
- Idempotent: resubmitting the same `email` + `roles` twice in a row yields the same 200 response and does not change the stored entry (spec.md Edge Cases).
- Merging never touches `objectId`/`dateBound` (FR-009).

---

## New: GET /api/manage/accounts

**Purpose**: List every Provisioned Account Entry (FR-010).

**Authorization**: Administrator capability required.

**Request**:

```http
GET /api/manage/accounts HTTP/1.1
Authorization: Bearer <access_token>
```

**Response (200 OK)**:

```json
{
  "status": "success",
  "accounts": [
    { "email": "admin@example.com", "roles": ["Administrator"], "bound": true },
    { "email": "newplayer@example.com", "roles": ["Player"], "bound": false }
  ]
}
```

No pagination — list is returned in full (Constitution Principle IV; no stated scale requirement, see plan.md Technical Context).

**Response (401 / 403)** — same shared shapes as above.

---

## New: DELETE /api/manage/accounts

**Purpose**: Remove an existing Provisioned Account Entry by email, revoking its access and deleting its corresponding Entra ID tenant guest user (FR-012, FR-013). Added 2026-08-30 alongside spec.md's User Story 3.

**Authorization**: Administrator capability required.

**Request**:

```http
DELETE /api/manage/accounts HTTP/1.1
Authorization: Bearer <access_token>
Content-Type: application/json

{ "email": "player@example.com" }
```

**Response (200 OK)**:

```json
{ "status": "success" }
```

**Response (400 Bad Request)** — self-removal or seed-administrator removal rejected:

```json
{ "error": "self_removal", "message": "Administrators cannot remove their own account." }
```

```json
{ "error": "seed_admin_removal", "message": "The seed administrator's account cannot be removed." }
```

**Response (404 Not Found)** — no provisioned entry exists for the submitted email:

```json
{ "error": "not_found", "message": "No provisioned account entry exists for this email." }
```

**Response (401 / 403)** — same shared shapes as above.

### Validation Rules

- `email` (lowercased/normalized per FR-008) MUST match an existing Provisioned Account Entry, or the request is rejected with `not_found` (404) — removing a never-provisioned email is not a silent no-op (spec.md Edge Cases).
- `email` MUST NOT equal the signed-in Administrator's own email — rejected with `self_removal` (400), regardless of the acting administrator's roles (FR-012).
- `email` MUST NOT equal the deployment-configured seed administrator email — rejected with `seed_admin_removal` (400), regardless of who is signed in (FR-012), so the system can never end up with zero administrators via this path.
- On success, the entry is deleted from `provisionedAccountEntries` and `EntraDirectoryService.remove_guest` (T056) is called for the same email; a removal succeeds even if no matching Entra guest user is found (FR-013, spec.md Edge Cases).

---

## Standard Error Response Format (unchanged from 002)

```json
{ "error": "<error_code>", "message": "<human_readable_message>" }
```

| Code | HTTP Status | Meaning |
|------|-------------|---------|
| `unauthenticated` | 401 | No valid token provided |
| `access_denied` | 403 | Not on the provisioned list, or bound object identifier does not match |
| `insufficient_permission` | 403 | Authenticated and provisioned, but lacks Administrator capability |
| `role_required` | 400 | Add/merge submitted with no valid role selected |
| `invalid_email` | 400 | Add/merge submitted with a non-RFC-5322 email |
| `self_removal` | 400 | Removal submitted for the signed-in Administrator's own email |
| `seed_admin_removal` | 400 | Removal submitted for the seed administrator's email |
| `not_found` | 404 | Removal submitted for an email with no provisioned entry |
| `internal_error` | 500 | Unexpected server-side error |
