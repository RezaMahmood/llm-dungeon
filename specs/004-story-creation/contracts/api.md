# API Contracts: Story Creation

**Date**: 2026-08-29

**Feature**: Story Creation (004-story-creation)

All endpoints require an authenticated Administrator (`authorize_admin`, per `src/backend/api/admin/middleware.py`), returning the same `unauthorized()`/`forbidden_access_not_granted()`/`forbidden_insufficient_permission()` shapes as existing admin endpoints on failure. Response shapes follow `src/backend/api/utils.py`'s `json_response`/`error_response` helpers.

`src/backend/api/manage/stories.py`'s existing `create_story`/`list_stories` placeholders are replaced by the endpoints below; `POST /api/manage/stories/create` is renamed in place to draft-creation semantics (no external caller exists yet — the route was a placeholder returning "not yet implemented").

---

## POST /api/manage/stories/drafts

**Purpose**: Start a new story-creation session (FR-001). Optionally accepts an initial plain-language idea, which is immediately sent through the guiding-question exchange (research.md §1, §4).

**Request**:
```json
{ "idea": "A half-abandoned lighthouse on a cold northern cove..." }
```
`idea` is optional; an empty body starts a blank draft.

**Response (201 Created)**:
```json
{
  "status": "success",
  "draft": {
    "id": "5b1e...",
    "name": null, "coverImageUrl": null, "tone": null, "readingLevel": null,
    "sessionLengthMinutes": null, "chapters": null,
    "worldPrompt": null, "rules": null,
    "characterTypes": [], "completionCriteria": null,
    "exchanges": [
      { "role": "administrator", "message": "A half-abandoned lighthouse...", "timestamp": "2026-08-29T20:00:00Z" },
      { "role": "system", "message": "Who is the player in this story, and what draws them to the lighthouse?", "timestamp": "2026-08-29T20:00:01Z" }
    ]
  }
}
```
If `idea` was supplied, the Foundry exchange call (research.md §4) has already merged any `fieldUpdates` it extracted (e.g., `worldPrompt`) before this response is returned.

---

## GET /api/manage/stories/drafts/{draftId}

**Purpose**: Reload a draft's current state — used when navigating between wizard steps or resuming within the TTL window.

**Response (200 OK)**: Same `draft` shape as above.

**Response (404 Not Found)** — draft never existed or its TTL already expired:
```json
{ "error": "not_found", "message": "Draft not found" }
```

---

## PATCH /api/manage/stories/drafts/{draftId}

**Purpose**: Directly edit structured fields from any wizard step (name & cover, tone & reading level, session length, character types, completion criteria) without going through the conversational exchange (FR-008 — dedicated fields, not only free text).

**Request** (any subset of draft fields; unspecified fields are left unchanged):
```json
{
  "characterTypes": [
    { "name": "Curious Cousin", "description": "Visiting for the summer, unafraid to ask questions." },
    { "name": "Local Kid", "description": "Knows the village, skeptical of ghost stories." }
  ],
  "completionCriteria": {
    "maxDurationMinutes": 20,
    "successConditions": ["The player learns what really happened to the keeper."],
    "failureConditions": ["The player leaves the cove without investigating."],
    "rule": "any"
  }
}
```

**Response (200 OK)** — updated draft, plus whether this write met the Completeness Rule:
```json
{
  "status": "success",
  "draft": { "...": "updated draft shape" },
  "readyToGenerate": true
}
```

If `readyToGenerate` is `true`, the server has already attempted generation as part of this same request (FR-004 — no separate manual save step) and the response instead takes the generated shape below.

**Response (200 OK, generation succeeded on this write)**:
```json
{
  "status": "generated",
  "storyId": "9f2a...",
  "story": { "...": "see GET /api/manage/stories/{storyId}" }
}
```

**Response (422 Unprocessable Entity)** — a field fails validation (e.g., `completionCriteria.successConditions` empty, `rule` missing with 2+ conditions):
```json
{ "error": "invalid_field", "message": "completionCriteria.successConditions must have at least one entry" }
```

**Response (502 Bad Gateway)** — the Completeness Rule was met but the Foundry generation call failed or returned output that failed validation (Edge Cases: malformed LLM output is never persisted); the draft is left unchanged and intact for another attempt:
```json
{ "error": "generation_failed", "message": "Story generation did not produce a usable configuration; please try again" }
```

---

## POST /api/manage/stories/drafts/{draftId}/messages

**Purpose**: Append one plain-language administrator message to the conversation (FR-001, FR-002) and receive the system's next guiding question or acknowledgment, with any extracted field updates already merged (research.md §4).

**Request**:
```json
{ "message": "Make it 1908, and nobody actually gets hurt in the story." }
```

**Response (200 OK)**: Same three-shape family as `PATCH` above (`{"status":"success","draft":...,"readyToGenerate":false}`, or the `"generated"` shape, or a `502` on a failed generation attempt) — a message can itself be the write that completes the draft.

---

## GET /api/manage/stories

**Purpose**: List all persisted stories (existing placeholder, now returning real data).

**Response (200 OK)**:
```json
{
  "status": "success",
  "stories": [
    { "id": "9f2a...", "name": "The Lighthouse at Gullwing Cove", "published": false, "createdAt": "2026-08-29T20:04:00Z" }
  ]
}
```
List entries are summaries (`id`, `name`, `published`, `createdAt`); full detail is fetched via the endpoint below.

---

## GET /api/manage/stories/{storyId}

**Purpose**: Fetch one persisted story's full configuration (needed by the wizard to display what was generated, and by `005-story-publishing`/`012-story-editing-and-review` later).

**Response (200 OK)**:
```json
{
  "status": "success",
  "story": {
    "id": "9f2a...",
    "name": "The Lighthouse at Gullwing Cove",
    "coverImageUrl": null, "tone": null, "readingLevel": null,
    "sessionLengthMinutes": 20, "chapters": 5,
    "worldPrompt": "A half-abandoned lighthouse...", "rules": "Nobody gets hurt...",
    "characterTypes": [ { "name": "Curious Cousin", "description": "..." } ],
    "completionCriteria": { "maxDurationMinutes": 20, "successConditions": ["..."], "failureConditions": [], "rule": null },
    "narrativeGuidance": "...LLM-authored consistency guidance...",
    "published": false,
    "createdBy": "550e8400-e29b-41d4-a716-446655440000",
    "createdAt": "2026-08-29T20:04:00Z"
  }
}
```

**Response (404 Not Found)**:
```json
{ "error": "not_found", "message": "Story not found" }
```

### Validation Rules (all endpoints)

- Every request MUST pass `authorize_admin` (Constitution Principle II) — no anonymous access to any draft or story data, including a draft's own conversation history.
- A draft's `characterTypes`/`completionCriteria` writes are validated against the Shared Structures in data-model.md before merge; the first invalid field short-circuits the write with a `422` (no partial merge of a rejected field alongside accepted ones in the same request).
- `readyToGenerate`/generation is evaluated after every successful merge, on every `PATCH` and every `messages` call — the boundary that makes a draft "complete" is the Completeness Rule in data-model.md, not a separate explicit action (FR-004).
