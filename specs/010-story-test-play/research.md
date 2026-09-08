# Research: Story Test Play

**Feature**: `010-story-test-play` | **Date**: 2026-09-08 | **Spec**: [spec.md](./spec.md)

All existing identifiers below were read from this branch after it was synced with
`origin/main` (Principle XIII). Identifiers this feature proposes to create are marked
**(proposed)**.

## Decision 1 — The publish gate this feature feeds already exists; only the writer is missing

**Decision**: Do not build a publish gate. Record `Story.lastTestPlayedAt` on each
qualifying exchange and let the merged gate consume it.

**Rationale**: `017-story-publish-test-play-gate` has no `plan.md`/`tasks.md`, but its
FR-001/FR-002/FR-003 are already merged in `origin/main` as part of the `005` publishing
work:

| Requirement | Existing code |
|---|---|
| 017 FR-001 (track status per story) | `src/backend/models/story.py:87` — `Story.lastTestPlayedAt` |
| 017 FR-002 (block publish) | `src/backend/services/story_service.py:195` — `StoryService.can_publish()`; `src/backend/api/admin/stories.py:221` — `409 test_play_required` |
| 017 FR-003 (reset on content save) | `story_service.py:256` — `_replaced_story()` bumps `contentUpdatedAt=_now()` and carries `lastTestPlayedAt` forward, so the `>=` comparison re-arms |

`grep -rn lastTestPlayedAt src/` confirms the field is read, compared, serialized, and
preserved — and **never written**. `can_publish()` is therefore unsatisfiable today and
no story can be published at all. Supplying the writer is this feature's backend core.

**Consequence for FR-007**: the shared preconditions already exist server-side; the
conclusion screen calls the existing `POST /api/manage/stories/{storyId}/publish`.

**Consequence for FR-010**: satisfied by construction — the marker lives on the Story,
not the session, so deleting a session cannot reset it.

**Alternatives rejected**: implementing a gate here (already merged); making `017` a
blocking prerequisite (its code has landed).

## Decision 2 — Test-play sessions get their own container, not a flag on `playSessions`

**Decision**: New Cosmos container `testPlaySessions` **(proposed)**, partition key
`/id`, with a `TestPlaySession` model **(proposed)** and `TestPlaySessionService`
**(proposed)**.

**Rationale**: FR-009 requires test sessions be invisible to real play. Reusing
`playSessions` with a discriminator leaves a by-id leak that no query filter closes:
`PlaySessionService._read_item(session_id)` reads by id with no type predicate, and
`get_session_for_player` then authorizes on `session.playerId != player_id`. A dual-role
account (roles are additive — `src/backend/tests/integration/test_dual_role_user.py`)
could pass its own test-session id to `GET /api/game/sessions/{sessionId}` and continue
it as real play. Closing that by discriminator means guarding four queries plus every
by-id read; a separate container makes the crossing structurally impossible.

**Cost**: one `azurerm_cosmosdb_sql_container` resource in
`infrastructure/terraform/main.tf`, one entry in `CONTAINER_PARTITION_KEY_PATHS`
(`src/backend/db/seed_data.py:36`), one constant in `src/backend/config.py`. Recorded in
Complexity Tracking.

**Alternatives rejected**: `entityType` discriminator in `playSessions` (leak above);
reusing `PlaySessionService` wholesale (the real-play path is hard-gated on
`story.published` in three places — `list_published_summaries`, `get_adventure`, and
`create_session` — so a draft story is unreachable through it).

## Decision 3 — Reuse the turn machinery, not the player session lifecycle

**Decision**: Reuse `LLMService.generate_gameplay_turn()` and the completion-evaluation
logic; do not reuse the player lifecycle behaviors.

**Rationale**: `generate_gameplay_turn(story, session, player_input, concluding_reason=None)`
is the whole narrative generator and already carries Principle VI telemetry (span
`gen_ai.gameplay.turn` with `gen_ai.prompt`, `gen_ai.response`,
`gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`, `gen_ai.cost_usd`,
`gen_ai.latency_ms`), so FR-002 and the observability principle are satisfied by reuse.
Completion evaluation (`_evaluate_completion` / `_rule_satisfied`, reading
`newlySatisfiedSuccessConditions` / `newlySatisfiedFailureConditions` index lists) is
extracted to a shared module-level helper **(proposed)** so FR-004 enforces identical
rules rather than a second implementation.

Three player behaviors are deliberately **not** reused, each an FR-009 interference
vector:

- `_deactivate_other_active_sessions(player_id, ...)` — would flip `isActiveForPlayer`
  on a dual-role admin's own real play session.
- `MIN_SESSION_CREATION_INTERVAL_SECONDS = 10`, computed by `_most_recent_session_start`
  across all of that player's sessions — would couple test play to real play.
- `PlayerContentSafetyStandingService.record_flag()` — see Decision 4.

`MIN_INTERACTION_INTERVAL_SECONDS = 2` and the `_etag` +
`MatchConditions.IfNotModified` claim are reused, being per-session, not per-player.

## Decision 4 — Content safety screens, but does not accrue against the administrator

**Decision**: Screening behaves as in real gameplay (the `LLMContentFilteredError`
deflection turn is produced), but no flag is recorded and no lockout is enforced.

**Rationale**: FR-002 asks for the same screening behavior; FR-009 forbids interfering
with real play. `record_flag()` writes `playerContentSafetyStandings` keyed on the same
oid the administrator plays with, and three flags trigger a one-hour lockout — so
testing a story would lock the administrator out of their own gameplay. Precedent
exists: `create_session` already declines to record a flag when the opening narrative is
filtered, on the grounds that it is the story's content and not the player's. Test play
is that case throughout.

## Decision 5 — Test play is its own screen, not a wizard step

**Decision**: New route `/admin/stories/:storyId/test-play` **(proposed)**, reached from
the wizard's terminal screen.

**Rationale**: the spec's own navigation settles this. FR-005 returns the administrator
"to the edit story page" and FR-008 returns them "to the story wizard" — both incoherent
if test play were itself a wizard step. It also needs a persisted `storyId`, which
`AdminStoryWizardPage`'s `STEPS` do not have: those render from `draft`, and in create
mode no Story exists until `handleGenerate()`. Both exits therefore navigate to
`/admin/stories/:storyId/edit`; FR-007's publish navigates to `/admin`.

**Screen contract**: traceable to the **Administrator story-authoring wizard** contract
(`specs/designs/04-admin-wizard.html`, step 05 "Test play"), so Governance's
"no screen untraceable to a screen contract" holds despite FR-011's deferral.

**Alternatives rejected**: a fifth `STEPS` entry (no `storyId` in create mode; makes
FR-005/FR-008 circular); a story-list row entry point (not required by any FR — left to
follow-up).

## Decision 6 — Test play needs a character; take it from the story

**Decision**: Default the session's character to the first entry of
`story.characterTypes` with a fixed name literal `"Tester"`.

**Rationale**: `PlaySession` requires `characterName`/`characterType`, but neither the
spec nor the prototype offers the administrator a character-setup step, and adding one
would exceed scope. The prototype labels the administrator's line `Tester:`.
`Story.__post_init__` guarantees at least one character type exists.

## Decision 7 — One publish control, extended with confirmation

**Decision**: Add publish confirmation to `usePublishToggle`
(`src/frontend/src/hooks/usePublishToggle.js`) and its dialog in
`StoryPublishActions.jsx`, then reuse that component on the conclusion screen via a new
optional `onPublished` prop **(proposed)**.

**Rationale**: FR-007 requires the same publish action as every other entry point,
"never a separate publish path". Both existing entry points — the story-list row in
`AdminPage.jsx` and `StepPublish.jsx` in the wizard — already render
`StoryPublishActions`, so amended `005` FR-013 lands in all three at once. Today publish
fires immediately from `handlePublish` with no confirmation, while unpublish already
routes through `requestUnpublish`/`confirmUnpublish`/`cancelUnpublish` — the amendment
mirrors that existing state machine rather than inventing one.

**Dialog markup**: no shared confirmation-dialog component exists; six screens each
inline the design-system `.dialog-backdrop` / `.dialog` / `.dialog-title` /
`.dialog-body` / `.dialog-actions` markup. Follow that established pattern rather than
introducing a component the design system does not have.

## Decision 8 — Reuse the presentational play components

**Decision**: Reuse `StoryPane`, `InstructionInput`, `SuggestedActions`, and
`StatusPanel` from `src/frontend/src/components/Play/`. Do not reuse `PauseDialog` or
`PlayPage`.

**Rationale**: the four are pure presentational components importing no service or
context, so reusing them satisfies Principle VIII's ban on reimplementing a control the
system already provides. `PlayPage` hard-wires `submitInteraction`/`resumeSession`/
`saveCheckpoint` and publishes to `PlayTitleContext`; `PauseDialog`'s copy is
player-specific save-and-exit. Test play needs neither checkpoints nor autosave.

## Decision 9 — The marker is written on the first exchange, not on session start

**Decision**: Write `Story.lastTestPlayedAt` after a turn is successfully generated and
persisted; never at session creation, and never for the opening turn.

**Rationale**: `017` Acceptance Scenario 5 requires that an administrator who starts a
session but takes no action stays blocked. The opening narrative (turn 0,
`playerInput is None`) is not a submitted instruction, so it is not a Test Play Exchange
per this spec's Key Entities. Writing the marker must not touch `contentUpdatedAt`, or
it would re-arm the very gate it satisfies.
