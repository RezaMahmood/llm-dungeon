# API Contract: Story Test Play

**Feature**: `010-story-test-play` | **Date**: 2026-09-08

All routes are **(proposed)** unless marked existing. Azure Functions prefixes every
route with `/api/`. Routes are registered in `src/backend/function_app.py` wrapped in
`_guarded(...)`, with handlers in `src/backend/api/admin/test_play.py` **(proposed)**.

Every handler begins with `is_authorized, user_oid, error = authorize_admin(req)`
(`src/backend/api/admin/middleware.py`) — administrator-only, enforced server-side
(Principle II). Auth travels in the `X-Custom-Authorization: Bearer <token>` header, as
everywhere else in this codebase.

Test-play routes sit under `manage/`, not `game/`, because the `game/*` surface is
hard-gated on `story.published` and requires the `Player` role.

## POST /api/manage/stories/{storyId}/test-play

Start a test-play session against the story's current saved configuration (FR-001).
Works on an **unpublished** story.

**Request**: no body.

**Response `201`**
```json
{
  "status": "success",
  "sessionId": "<id>",
  "characterType": "<from story.characterTypes[0]>",
  "narrative": {
    "turnNumber": 0,
    "narrativeText": "…",
    "suggestedActions": ["…"],
    "locationLabel": "…",
    "goalLabel": "…",
    "progress": {"current": 1, "total": 5}
  }
}
```

The `narrative` object matches `_narrative_dict()` in
`src/backend/api/game/sessions.py` exactly, so the reused presentational components
receive the shape they already expect.

**Errors**

| Status | `error` | When |
|---|---|---|
| `404` | `not_found` | Story does not exist |
| `502` | `narrative_unavailable` | `LLMOutputError`, `LLMRateLimitError`, or a filtered opening narrative |

No qualifying exchange occurs here, so `Story.lastTestPlayedAt` is **not** written
(research Decision 9).

## POST /api/manage/test-play-sessions/{sessionId}/interactions

Submit one test instruction and receive its narrative response — the Test Play Exchange
(FR-002, FR-004).

**Request**
```json
{ "input": "shout hello at the lighthouse" }
```

**Response `200`**
```json
{
  "status": "active | concluded",
  "narrative": { "…": "as above" },
  "completionReason": {"type": "success", "detail": "Find the keeper"}
}
```

`completionReason` is present only when the session concluded this turn (FR-006); it is
omitted while `status` is `"active"`, matching `submit_interaction`'s existing behavior.

**Side effect**: on success, `Story.lastTestPlayedAt` is stamped `_now()`.
`contentUpdatedAt` is untouched. This is the write that makes `can_publish()`
satisfiable.

**Errors**

| Status | `error` | When |
|---|---|---|
| `400` | `invalid_input` | Empty or whitespace-only `input` |
| `403` | `access_denied` | Session belongs to another administrator (FR-009) |
| `404` | `not_found` | Session, or its story, no longer exists |
| `409` | `session_concluded` | Session already concluded |
| `409` | `interaction_in_progress` | Single-flight claim held |
| `429` | `rate_limited` | Under the 2-second interaction interval |
| `502` | `narrative_unavailable` | LLM output or rate-limit failure |

A content-filtered turn is **not** an error: it returns `200` with an in-fiction
deflection, as real gameplay does, but records no safety flag against the administrator
(research Decision 4).

## DELETE /api/manage/test-play-sessions/{sessionId}

Abort and permanently delete the session (FR-005). The client shows the warning and
calls this only after the administrator confirms; the warning is a UI safeguard, not a
server-side precondition.

**Response `200`**
```json
{ "status": "deleted", "sessionId": "<id>" }
```

**Errors**: `403 access_denied` (another administrator's session); `404 not_found`.
Idempotent per document — a session that vanishes between read and delete is reported as
deleted rather than raising, following
`PlaySessionService.delete_active_sessions_for_adventure`.

**`Story.lastTestPlayedAt` is not cleared** (FR-010). A story test-played and then
aborted stays publishable.

## GET /api/manage/test-play-sessions/{sessionId}

Rehydrate a session (browser refresh). Returns `200` with `{"status": "success",
"session": {…}}` carrying the full `turns` list; `403`/`404` as above.

## Existing routes this feature depends on — unchanged

| Route | Handler | Use |
|---|---|---|
| `POST /api/manage/stories/{storyId}/publish` | `publish_story` | FR-007. Already returns `409 test_play_required` when `can_publish()` fails; unchanged, because the gate is already correct |
| `POST /api/manage/stories/{storyId}/edit-drafts` | `create_edit_draft` | FR-008. Already documented as never blocked by publish state or the test-play gate |
| `GET /api/manage/stories` | `list_stories` | FR-007's destination after publish |

**No backend change is required for FR-013's publish-confirmation amendment.** The
confirmation is client-side only (`005` FR-013), and both `005` FR-013 and `015` state a
confirmation MUST NOT become a server-side precondition.

## Frontend service contract **(proposed)**

Added to `src/frontend/src/services/`, following the existing per-module
`axios.create({ baseURL: "/api" })` + `X-Custom-Authorization` pattern. A new
`testPlayService.js` **(proposed)** keeps test play out of the player-facing
`gameService.js`, mirroring the backend's container-level separation:

| Function | Call |
|---|---|
| `startTestPlay(token, storyId)` | `POST /manage/stories/{storyId}/test-play` |
| `submitTestPlayInstruction(token, sessionId, input)` | `POST /manage/test-play-sessions/{sessionId}/interactions` |
| `deleteTestPlaySession(token, sessionId)` | `DELETE /manage/test-play-sessions/{sessionId}` |
| `getTestPlaySession(token, sessionId)` | `GET /manage/test-play-sessions/{sessionId}` |

## Frontend route contract **(proposed)**

| Route | Element | Guard |
|---|---|---|
| `/admin/stories/:storyId/test-play` | `AdminStoryTestPlayPage` **(proposed)** | `<ProtectedRoute capability="Administrator">` |

Navigation targets, all existing routes: FR-007 publish → `/admin`; FR-008 edit and
FR-005 abort → `/admin/stories/:storyId/edit`.

## Amended component contract — `StoryPublishActions`

`src/frontend/src/components/Admin/StoryPublishActions.jsx` gains publish confirmation
and an optional `onPublished` callback **(proposed)**, so the conclusion screen reuses
the one publish control rather than adding a path (FR-007).

| Prop | Status | Notes |
|---|---|---|
| `story`, `token`, `onStoryChange` | existing | Unchanged |
| `onPublished` | **(proposed)** | Optional. Called after a confirmed publish succeeds; the conclusion screen navigates to `/admin`. Omitted by the story list and `StepPublish`, which keep their in-place behavior |

`usePublishToggle` **(existing, amended)** gains `confirmingPublish`, `requestPublish`,
`confirmPublish`, and `cancelPublish`, mirroring its existing unpublish trio. Its
`gateMessage` already surfaces the `409 test_play_required` message and needs no change.
