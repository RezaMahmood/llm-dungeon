# Research: Remembering and Showing a Player's Avatar

## Decision 1 — Storage shape for the remembered description

**Decision**: A new Cosmos container `storedAvatarDescriptions` (config constant
`STORED_AVATAR_DESCRIPTIONS_CONTAINER`), one document per `(playerId, storyId)` pair, keyed and
partitioned by `id = f"{playerId}:{storyId}"` — the exact shape `avatarSetupAttempts`
(`032-story-archetypes-player-avatar`) already established for the same key pair.

**Rationale**: `avatarSetupAttempts` is the closest and most recent precedent in this codebase for
"one small document per `(playerId, storyId)` pair, upserted via a bounded `_etag` read-modify-
write." Reusing its exact key convention (`avatar_setup_attempts_service.py::_doc_id`) makes the
new service's shape immediately legible against a pattern already in the codebase, and its
single-document-per-pair design directly satisfies FR-005 ("at most one stored description per
player per adventure, replaced").

**Alternatives considered**: Storing the description as a new field on `PlayerContentSafetyStanding`
or another existing per-player document — rejected; that container's semantics are unrelated
(policy-violation standing), and conflating them would tie this feature's lifecycle (deleted with
the adventure, FR-009) to that container's own. Storing it directly on the `Story` document (a map
keyed by `playerId`) — rejected; every story write already goes through wizard-edit conflict
handling (`_write_published`, contentVersion bumps), and a per-player field would grow that
document unboundedly and unrelated to its own content-versioning concerns.

## Decision 2 — Where the write happens

**Decision**: `PlaySessionService.create_session` stores the validated, trimmed avatar description
against `(player_id, story.id)` immediately after the session document is successfully created —
the same point `clear_attempts` already runs at (`play_session_service.py`, end of
`create_session`). It replaces (via upsert, not append) whatever was previously stored for that
pair.

**Rationale**: FR-012 requires the write to happen "when a session is started, not while it is
being typed" — `create_session` is the one place in the codebase where a description is already
known to have passed both cost-free and model-backed validation and a session now exists for it.
Placing it after the session document's own successful write (not before) means a failed session
creation — adventure not found, rate limited, content-safety lockout — never stores a description
for a session that doesn't exist.

**Alternatives considered**: Writing from `AvatarValidationService.validate` — rejected; that
service runs on every validation attempt, including ones where the caller (e.g. this same flow, or
a future one) never goes on to create a session, which would violate FR-012 directly.

## Decision 3 — Where the read (prefill) happens

**Decision**: `GET /game/adventures/{adventureId}` (`api/game/adventures.py::get_adventure`) reads
the caller's own stored description for that `(user_oid, adventureId)` pair and includes it in the
response as `adventure.avatarDescription` (`None` when none exists). No new endpoint.

**Rationale**: `GamePage.jsx` already calls `getAdventure` once, on mount, for the single adventure
Home handed it in route state (`research.md` of `028-home-page-redesign`, Decision 10 — there is no
in-page adventure picker to react to a "changed selection" against; FR-007's "follows the selected
adventure" is satisfied trivially because each `GamePage` mount is already scoped to exactly one
adventure id). Reusing this call avoids a second round trip and keeps the read naturally scoped to
the authenticated caller (`authorize_player` already resolves `user_oid`), directly satisfying
FR-011 without a new authorization path to get right.

**Alternatives considered**: A dedicated `GET /game/adventures/{id}/avatar-description` endpoint —
rejected as an unnecessary second network call and a second place to enforce the same
per-player scoping `get_adventure` already enforces.

## Decision 4 — Showing the description during play

**Decision**: `PlaySessionService.get_session_detail_for_player` adds `avatarDescription` (the
session's own, already-stored field — `None` for a pre-`032` session) to the response shape
alongside `characterType`/`status`/`completionReason`. `GamePage.jsx` also threads the
description it already holds locally straight through to `PlayPage` on fresh session creation, so
neither path requires an extra round trip. `StatusPanel.jsx` renders it read-only in a new section
guarded by the same `{value && (...)}` pattern the panel already uses for `goalLabel`/`progress`,
so a session with none renders no empty/broken area (FR-003).

**Rationale**: `PlaySession.avatarDescription` already exists (`032`); this is purely a matter of
including an already-stored field in an already-existing response shape and rendering it with the
component's own established conditional-section idiom — no new pattern.

**Alternatives considered**: A separate "my character" fetch from the play surface — rejected;
`get_session_detail_for_player` and the resume path already exist specifically to rebuild the play
surface's full state in one call (`032`, FR-006 of `008`), and adding a second call for one string
field would be the extra round trip Decision 3 already rejected for the same reason.

## Decision 5 — Story-deletion cascade

**Decision**: `StoredAvatarDescriptionService.delete_for_story(story_id)` queries
`storedAvatarDescriptions` by `storyId` and deletes each matching row, tolerating a
`CosmosResourceNotFoundError` per row exactly as `PlaySessionService.delete_active_sessions_for_adventure`
already does. Called from `api/admin/stories.py::delete_story`, alongside the existing
`sessions.delete_active_sessions_for_adventure(story_id)` call — composed at the handler level, not
inside `StoryService`, for the same reason `025-story-delete-done`'s research.md Decision 6 gives
for the existing call: avoiding a circular import between `StoryService` and the deleted-alongside
service.

**Rationale**: Directly matches the existing, already-reviewed cascade pattern for the exact same
trigger (a story delete) in the exact same handler — no new composition style introduced.

**Alternatives considered**: A Cosmos change-feed/trigger-based cascade — rejected; this codebase
has no such mechanism anywhere (confirmed by search) and introducing one for a single new
container would be exactly the enterprise-grade machinery Constitution Principle IV rules out.

## Decision 6 — Session-deletion independence

**Decision**: No code change. `PlaySessionService.delete_session_as_administrator` (session admin
delete) and the player's own `deleteSession` path both only ever touch the `playSessions`
container; neither is extended to read or write `storedAvatarDescriptions`. This is FR-010
("deleting a session must not alter the stored description") holding by construction rather than
by an added guard.

**Rationale**: The two containers are already fully decoupled — the stored description lives
against `(playerId, storyId)`, independent of any one session's id — so satisfying FR-010 requires
writing no new code, only *not* wiring the new container into the session-delete path. Recorded
here so a future change to that path doesn't accidentally couple the two without reading this
requirement first.

## Decision 7 — The `characterType`/`avatarDescription` destructuring bug

**Decision**: Fix `gameService.js::createSession`'s parameter destructuring
(`{ adventureId, characterName, characterType }`, a leftover from before `032` renamed the field)
to `{ adventureId, characterName, avatarDescription }`, and its request body to send
`avatarDescription` instead of the now-always-`undefined` `characterType`.

**Rationale**: Found while tracing how a player-typed description reaches the backend for this
slice's prefill/store loop: `GamePage.jsx` already calls `createSession(token, { adventureId,
characterName, avatarDescription })`, but the destructuring in `gameService.js` silently drops any
key it doesn't name, so the network request has always sent `avatarDescription: undefined` since
`032` shipped. This slice's own acceptance tests (a description round-tripping through storage) are
unwritable, let alone passable, while this bug stands — it is a prerequisite fix, not new scope.

**Alternatives considered**: None — this is a one-line correction of an existing, unintentional
defect with an obvious right answer (match the field name the caller already sends and the backend
already expects).
