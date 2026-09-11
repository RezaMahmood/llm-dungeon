# API Contracts: Story and Session Token Usage Tracking

**Date**: 2026-09-11

**Feature**: Story and Session Token Usage Tracking (026-token-usage)

Adds one new endpoint (`GET /api/manage/sessions`) and extends the response
of one existing endpoint (`GET /api/manage/stories`). Response shapes
follow `src/backend/api/utils.py`'s `json_response`/`error_response`
helpers, matching existing conventions. No request/response shape for any
gameplay or test-play endpoint changes — token capture there is entirely
server-internal (data-model.md).

---

## Changed: GET /api/manage/stories

**Purpose (unchanged)**: List every story's summary for the admin stories
list (`004-story-creation-done`). This feature adds one field per row.

**Response (200 OK)**:
```json
{
  "status": "success",
  "stories": [
    {
      "id": "9f2a...",
      "name": "The Salt Mines",
      "published": true,
      "lastPublishedAt": "2026-09-01T12:00:00Z",
      "createdAt": "2026-08-20T09:30:00Z",
      "totalTokens": 48213
    }
  ]
}
```

`totalTokens` is `0` for a story with no tracked LLM usage (FR-004),
including every story persisted before this feature shipped.

---

## New: GET /api/manage/sessions

**Purpose**: List every gameplay session — both real player sessions and
admin test-play sessions — with the story it belongs to, its token total,
and the email of whoever ran it (FR-015). Read-only (FR-016): no other
method is defined on this route. Requires an authenticated Administrator
(`authorize_admin`), returning the same `unauthorized()`/
`forbidden_access_not_granted()`/`forbidden_insufficient_permission()`
shapes as existing admin endpoints on failure — no narrower permission
tier is introduced (spec.md Assumptions).

**Request**: No body, no query parameters (no pagination/filtering/sorting
in v1 — spec.md Assumptions).

**Response (200 OK)**:
```json
{
  "status": "success",
  "sessions": [
    {
      "sessionId": "b7e1...",
      "sessionType": "player",
      "storyId": "9f2a...",
      "storyName": "The Salt Mines",
      "totalTokens": 6420,
      "email": "player@example.com"
    },
    {
      "sessionId": "c3d9...",
      "sessionType": "test",
      "storyId": "9f2a...",
      "storyName": "The Salt Mines",
      "totalTokens": 1180,
      "email": "admin@example.com"
    }
  ]
}
```

Always 200, even with zero sessions (`"sessions": []`) — an empty result is
a success, not a 404, matching the existing `GET /api/game/sessions`
convention.

### Validation Rules

- Every request MUST pass `authorize_admin` (Constitution Principle II) —
  no anonymous access, and no capability beyond the existing Administrator
  role.
- `storyName` is `"(deleted story)"` when the referenced story no longer
  exists (data-model.md → Session Overview Row); the row is never omitted.
- `email` is `"(no longer provisioned)"` when no `ProvisionedAccountEntry`
  currently has a matching `objectId`; the row is never omitted.
- `totalTokens` is `0` for a session with no recorded turns yet (FR-018),
  never a missing field.
- Every `PlaySession`/`TestPlaySession` row is included regardless of
  `status` (`active` or `concluded`).
