# API Contracts: Story Editing and Review

**Date**: 2026-09-06

**Feature**: Story Editing and Review (`012-story-editing-and-review`)

All endpoints live in `src/backend/api/admin/stories.py` (URL prefix `manage/stories`, per
`function_app.py`'s route registration) and require an authenticated Administrator via the
existing `authorize_admin` middleware — the same `unauthorized()` /
`forbidden_access_not_granted()` / `forbidden_insufficient_permission()` shapes as every other
admin endpoint apply and are not repeated per-endpoint below. Response bodies use
`src/backend/api/utils.py`'s `json_response` / `error_response`, matching
`004-story-creation-done/contracts/api.md` and `005-story-publishing/contracts/api.md`.

**Unchanged and reused as-is**: `GET /api/manage/stories` (the list, FR-001 — already returns
`id`, `name`, `published`, `lastPublishedAt`, `createdAt`), `POST /api/manage/stories/{storyId}/publish`
and `.../unpublish` (FR-011 reuses them from the list with no behavioral change),
`GET|PATCH /api/manage/stories/drafts/{draftId}` and `POST .../drafts/{draftId}/world-prompt`
(the wizard's per-field autosave and one-shot `Suggest`, used unchanged in edit mode, FR-003;
the suggest route was `.../messages` until #227 made it one-pass, 2026-09-08).

---

## GET /api/manage/stories/{storyId}

**Change**: the existing endpoint's `story` object gains `contentVersion` and `lastUpdatedBy`.
No handler change is needed — it already returns `story.to_dict()`, so both appear as soon as
the model emits them; the work is asserting that, not writing it.

These are exposed for visibility and for tests, **not** as a token the client round-trips:
FR-006's staleness check runs entirely server-side against the edit draft's
`baseContentVersion` (see `…/edit-drafts` below). The SPA never sends `contentVersion` back.

---

## GET /api/manage/stories/{storyId}/configuration

**Purpose**: The story's complete authored configuration as a file (FR-002, FR-004). The exact
bytes of this response are what the read-only viewer renders and what the download saves —
there is no second serializer (research.md §2).

**Request**: No body.

**Response (200 OK)** — `Content-Type: application/json; charset=utf-8`. The body is the file:
2-space indented, fixed key order, one trailing newline, no system-managed fields
(see data-model.md → StoryConfiguration).

```json
{
  "id": "9f2a7c14-3f5e-4a21-9d0b-6c1f2b8e77aa",
  "name": "The Sunken Library",
  "coverImageUrl": null,
  "tone": "wry",
  "readingLevel": "age 9-11",
  "sessionLengthMinutes": 30,
  "chapters": 3,
  "worldPrompt": "A flooded library beneath a coastal town...",
  "rules": "No violence against the librarians.",
  "characterTypes": [
    { "name": "Archivist", "description": "Knows where everything was." }
  ],
  "completionCriteria": {
    "maxDurationMinutes": 30,
    "successConditions": ["Recover the tide ledger"],
    "failureConditions": ["The last lamp goes out"],
    "rule": "any"
  }
}
```

**Response (404 Not Found)**: `{ "error": "not_found", "message": "Story not found" }`

**Client note**: the SPA MUST request this as raw text (axios `transformResponse: (r) => r`)
and reuse that same string for both the viewer and the downloaded `Blob`, so FR-002's
"identical to the downloaded file" holds by construction.

---

## POST /api/manage/stories/{storyId}/edit-drafts

**Purpose**: Open an existing story in the wizard (FR-003). Creates a `StoryDraft` seeded from
the story's current authored configuration, bound to it by `sourceStoryId` and pinned to the
version it was seeded from (`baseContentVersion`).

**Request**: No body.

**Response (201 Created)**:
```json
{
  "status": "success",
  "draft": {
    "id": "1c3e...",
    "createdBy": "<admin oid>",
    "sourceStoryId": "9f2a7c14-3f5e-4a21-9d0b-6c1f2b8e77aa",
    "baseContentVersion": 4,
    "name": "The Sunken Library",
    "worldPrompt": "A flooded library beneath a coastal town...",
    "characterTypes": [{ "name": "Archivist", "description": "Knows where everything was." }],
    "completionCriteria": { "successConditions": ["Recover the tide ledger"], "failureConditions": ["The last lamp goes out"], "rule": "any", "maxDurationMinutes": 30 },
    "…": "remaining StoryDraft fields as in 004's contract"
  },
  "readyToGenerate": true
}
```

**Response (404 Not Found)**: `{ "error": "not_found", "message": "Story not found" }`

Editing is never blocked by publish state or by the test-play gate (`017` FR-004): a published
story opens for editing exactly like an unpublished one.

---

## POST /api/manage/stories/drafts/{draftId}/save

**Purpose**: Apply an edit draft back to its source story (FR-003, FR-006, FR-009). This is
edit mode's terminal action, replacing creation mode's `…/generate`.

**Request**: No body — the draft already carries `sourceStoryId` and `baseContentVersion`.

**Behavior**: validates the Completeness Rule → checks `baseContentVersion` against the story's
current `contentVersion` → carries over any `narrativeGuidance`/`startingPoint` named in the
story's `adminEditedFields` and regenerates the rest (the draft carries neither) → writes the
story (preserving `id`,
`createdBy`, `createdAt`, `published`, `lastPublishedAt`; stamping `lastUpdatedBy`,
`contentUpdatedAt`; incrementing `contentVersion`) → deletes the draft.

**Response (200 OK)**:
```json
{ "status": "saved", "storyId": "9f2a…", "story": { "id": "9f2a…", "contentVersion": 5, "published": true, "…": "full Story shape" } }
```

**Response (409 Conflict)** — FR-006, the story changed since the draft was seeded. Nothing is
written; the draft is left intact:
```json
{
  "error": "stale_story",
  "message": "This story changed since you opened it. Reload it and reapply your change."
}
```

**Response (422 Unprocessable Entity)**:
- `{ "error": "not_ready", "message": "name, worldPrompt, characterTypes, and completionCriteria are all required before saving" }` — Completeness Rule unmet (the "cleared a required element" edge case).
- `{ "error": "wrong_draft_mode", "message": "This draft is not an edit of an existing story" }` — a creation draft was posted here.

**Response (404 Not Found)**: draft missing/expired, or its source story no longer exists —
`{ "error": "not_found", "message": "Draft not found" }` / `"Story not found"`.

**Response (502 / 429)**: `generation_failed` / `rate_limited`, same shapes and messages as
`…/drafts/{draftId}/generate` (`004`'s contract). The story is left unchanged in both cases.

**Related change (existing endpoint)**: `POST /api/manage/stories/drafts/{draftId}/generate` —
today `generate_story_from_draft` in `src/backend/api/admin/stories.py` — now returns
`{ "error": "wrong_draft_mode", "message": "This draft is an edit of an existing story" }` with
status `422` if the draft carries a `sourceStoryId`, so an edit can never mint a second story.
This is a **modification to a handler this feature does not otherwise touch**; it needs both the
service guard and the handler's error mapping, and is asserted in
`test_admin_story_edit_endpoint.py`, not only at the service level.

---

## POST /api/manage/stories/import

**Purpose**: Re-upload an edited configuration file (FR-005), covering both routes: a file
carrying an `id` overwrites that story, a file with no `id` creates a new one. Implements
`011-story-import` FR-002/003/004/005/006/007 (research.md §1).

**Request**:
```json
{
  "configurationText": "{\n  \"id\": \"9f2a7c14-…\",\n  \"name\": \"The Sunken Library\",\n  …\n}\n",
  "confirmOverwriteStoryId": "9f2a7c14-3f5e-4a21-9d0b-6c1f2b8e77aa",
  "title": "The Sunken Library"
}
```
- `configurationText` — the uploaded file's **raw text**, exactly as read from disk. The server
  parses it, so malformed JSON is a server-side rejection like every other one and no file is
  accepted merely because the client looked at it first. Sending the text rather than a parsed
  object also keeps the round trip symmetric with `GET …/configuration`: the same bytes the
  server serialized are what come back to it.
- `confirmOverwriteStoryId` — **required** when the file's `id` is present; MUST equal it
  (`011` FR-006's explicit confirmation of the overwrite target). Ignored otherwise.
- `title` — **required** when the file's `id` is absent (`011` FR-005). It is the transport
  name for the story's `name` field: it becomes the new story's `name`, overriding any `name`
  in the file. Ignored otherwise. There is no separate "title" attribute on `Story` — the file
  format and the model both call it `name`.

**Validation runs on both sides, with the server authoritative:**

- **Server** — parses `configurationText` and applies every rule in data-model.md →
  StoryConfiguration. Nothing is persisted on any failure, and a direct API call that bypasses
  the SPA entirely hits exactly the same checks. This is the only tier that decides anything.
- **Client** — the upload component parses the file locally anyway, to know whether to confirm
  an overwrite target or prompt for a title, so it reports the fast, unambiguous failures before
  spending a round trip: not valid JSON (naming the position), not a JSON object, and a required
  key missing or empty (`name` on the overwrite path, `worldPrompt`, `characterTypes`,
  `completionCriteria.successConditions`). These are a strict **subset** of the server's rules —
  the client never accepts what the server would reject, and never produces a rejection reason
  the server would not also produce for the same file.

The client tier is a courtesy, not a gate, and it deliberately stops short of the content rules
(unknown-key naming, case-insensitive character-type uniqueness, `rule` vs. condition count,
positive integers). Those stay in the one validator (research.md §1, §7) so there is nothing to
drift out of sync; every server rejection message is surfaced verbatim by the client either way.

**Response (200 OK)** — overwrite of the id-matched story. Full replacement of the authored
set; `published`/`lastPublishedAt`/`createdBy`/`createdAt` are preserved (FR-007, FR-009);
no `contentVersion` precondition applies (FR-006's exemption):
```json
{ "status": "updated", "storyId": "9f2a…", "story": { "…": "full Story shape" } }
```

**Response (201 Created)** — new story from an id-less file; `published` is `false`
(`011` FR-007) and the story it was downloaded from is untouched:
```json
{ "status": "created", "storyId": "b71d…", "story": { "…": "full Story shape" } }
```

**Response (404 Not Found)** — the file's `id` matches no existing story. Nothing is created
under that id:
```json
{
  "error": "story_not_found",
  "message": "No story exists with the id in this file. Remove the id to upload it as a new story."
}
```

**Response (422 Unprocessable Entity)** — nothing is persisted and any existing story is left
untouched (`011` FR-003). `message` always names the offending field or element:
```json
{ "error": "invalid_configuration", "message": "characterTypes: at least one character type is required" }
```
Other `422` cases, same shape:
- `{ "error": "confirmation_required", "message": "Confirm the story this file will overwrite before uploading." }` — missing or mismatched `confirmOverwriteStoryId`.
- `{ "error": "title_required", "message": "A title is required to create a new story from this file." }` — id-less file with no `title`.
- `invalid_configuration` also covers: `configurationText` that is not valid JSON (message names
  the parser's position — e.g. `"The file is not valid JSON (line 12, column 3)"`), a payload
  that parses to something other than a JSON object, an unrecognised key (named in
  the message), duplicate character type names, a missing/empty `worldPrompt`, a missing/empty
  `name` **on the overwrite path** (`{ "error": "invalid_configuration", "message": "name: a
  name is required when overwriting an existing story" }` — on the id-less path `title` supplies
  it, so the file's `name` is optional there), missing `completionCriteria` or
  `successConditions`, a `rule` outside `any`/`all` when more than one condition exists, and a
  non-positive `sessionLengthMinutes`/`chapters`.

**Response (502 / 429)**: `generation_failed` / `rate_limited` from the `narrativeGuidance`
or `startingPoint` regeneration (research.md §5), same shapes as above. Nothing is persisted.

---

## Write conflicts (both writing endpoints)

`apply_content_write` writes with the `_etag` read alongside the story
(`MatchConditions.IfNotModified`, as `play_session_service.py` does). On a precondition
failure the service re-reads the story and branches on what actually changed:

- **`contentVersion` changed** — another content write landed. On
  `POST …/drafts/{draftId}/save` this is FR-006 staleness: `409 stale_story`, nothing
  written, the draft left intact. On `POST …/import` FR-006 does not apply (the
  administrator confirmed the target explicitly), so the write is re-applied against the
  freshly read row and retried once.
- **`contentVersion` unchanged** — the concurrent write was a publish/unpublish, which
  never touches `contentVersion`. The content write is re-applied against the freshly read
  row, so the new `published`/`lastPublishedAt` survive, and retried once — on **both**
  endpoints. A publish MUST NOT surface as a stale-save conflict (plan.md → Summary).

If the single retry also fails its precondition, both endpoints return, with nothing
persisted and the story left as the concurrent writer left it:

```json
{
  "error": "write_conflict",
  "message": "Another change to this story landed at the same time. Try again."
}
```

Status `409`. This is distinct from `stale_story`: it says nothing about the
administrator's copy being out of date, and the action is simply to repeat it. The retry
costs no extra LLM call — `narrativeGuidance` and `startingPoint` are resolved before the
write.

---

## Route registration (`src/backend/function_app.py`)

```python
@app.route(route="manage/stories/{storyId}/configuration", methods=["GET"])
@app.route(route="manage/stories/{storyId}/edit-drafts",   methods=["POST"])
@app.route(route="manage/stories/drafts/{draftId}/save",   methods=["POST"])
@app.route(route="manage/stories/import",                  methods=["POST"])
```

Each is wrapped by the existing `_guarded` span helper, so `http.route` stays a
low-cardinality template (Principle VI).

---

## Frontend service surface (`src/frontend/src/services/storyDraftService.js`)

| Function | Endpoint | Notes |
|---|---|---|
| `getStoryConfiguration(token, storyId)` | `GET …/{storyId}/configuration` | Returns the **raw text**, not a parsed object. |
| `createEditDraft(token, storyId)` | `POST …/{storyId}/edit-drafts` | |
| `saveDraftToStory(token, draftId)` | `POST …/drafts/{draftId}/save` | 409 ⇒ show the reload-and-reapply message. |
| `importStoryConfiguration(token, body)` | `POST …/import` | `body` = `{ configurationText, confirmOverwriteStoryId?, title? }` — the file's raw text, not a re-serialized object. |

Existing `listStories`, `getStory`, `publishStory`, `unpublishStory`, `getDraft`,
`patchDraft`, `suggestWorldPrompt` (`postMessage` until #227) are reused unchanged.
