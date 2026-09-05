# API Contracts: Account Listing

**Date**: 2026-09-05

**Feature**: Account Listing (014-account-listing)

This feature changes **no endpoint shape or route**. It documents the one behavior change (response ordering) to an existing endpoint created by `003-account-provisioning-done`. See that feature's `contracts/api.md` for the full existing contract (auth, error shapes, `POST`/`DELETE`).

---

## Changed (ordering only): GET /api/manage/accounts

**Purpose**: List every Provisioned Account Entry (FR-001, FR-002).

**Authorization**: Administrator capability required (`authorize_admin` middleware, unchanged) — FR-003.

**Request** (unchanged):

```http
GET /api/manage/accounts HTTP/1.1
Authorization: Bearer <access_token>
```

**Response (200 OK)** — same shape as `003`'s contract; entries are now guaranteed sorted ascending by `email` (FR-001):

```json
{
  "status": "success",
  "accounts": [
    { "email": "admin@example.com", "roles": ["Administrator"], "bound": true, "isSeedAdmin": true },
    { "email": "newplayer@example.com", "roles": ["Player"], "bound": false, "isSeedAdmin": false }
  ]
}
```

- `bound: false` is the signal the frontend renders as the "pending first sign-in" indicator (FR-005) — no new field.
- A role-merge on an already-provisioned email (per `003`'s add flow) continues to appear as a single entry with its full role set, never as separate rows (FR-002).
- No pagination — full list returned every time (Constitution Principle IV; consistent with `003`'s contract).

**Response (401 / 403)** — unchanged shared shapes (FR-003).

### Validation Rules (new in this feature)

- The `accounts` array MUST be ordered ascending by `email` (case-insensitive is moot — `email` is already stored lowercase).
