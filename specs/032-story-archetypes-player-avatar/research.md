# Research: A Player-Authored Avatar Replaces the Character-Type Picker

## Decision 1 — `PlaySession`/`TestPlaySession` field evolution

**Decision**: Add `avatarDescription: Optional[str] = None` to both `PlaySession`
(`models/play_session.py:78`) and `TestPlaySession`. Change `characterType: str` (required, no
default) to `characterType: Optional[str] = None` on both, read via `data.get("characterType")` in
`from_dict` instead of `data["characterType"]`. New sessions never set `characterType`; it is
populated only when reading a pre-existing document that still carries one (FR-025–FR-028).

**Rationale**: `characterType` is currently required with no default, so a document written under
the old model already satisfies the new dataclass unchanged; making it optional is the only change
needed for backward compatibility, matching this file's own established pattern for optional
fields (`status`, `endedAt`, `summary` already use `.get(..., default)`). No migration script or
schema version field exists anywhere in this codebase (confirmed: none found), so this slice
introduces none either.

**Alternatives considered**: A migration pass rewriting existing documents — rejected; the
codebase has no such mechanism and `009-save-and-continue`'s existing precedent is exactly
"old field absent, code copes," not "old data rewritten."

## Decision 2 — Avatar validation pipeline

**Decision**: A new `AvatarValidationService` (`services/avatar_validation_service.py`) runs, in
order: (1) cost-free checks — blank/whitespace-only, then the 20–500 character bounds (FR-006,
FR-010) — raising immediately on failure with no model call; (2) a model-backed story-relevance /
not-an-instruction check (FR-007, FR-008) issued through `LLMService`'s existing call plumbing
(`_call`/`_get_response_with_retry`, `llm_service.py:288,337`), wrapped in `asyncio.wait_for(...,
timeout=10)` (FR-011) so a hung call is abandoned rather than left open-ended. A timeout or any
other exception from step 2 is treated as "no verdict" and rejected (FR-012) — the same code path
as an explicit "non-conforming" verdict, but with a distinguishable player-facing message.

**Rationale**: No existing helper in this codebase already does "model call behind a timeout with
fail-closed semantics" (confirmed by dedicated research — the closest analogues,
`player_content_safety_standing_service.py`'s bounded Cosmos-write retries and
`entra_directory_service.py`'s HTTP timeout, are both fail-*open* or unrelated to model calls), so
this is new. Ordering cost-free checks first is required directly by FR-010 and is free to
implement — it is just an early return before any LLM call is constructed.

**Alternatives considered**: Running the relevance check via the same content-filter path gameplay
turns already use (`LLMContentFilteredError`) — rejected; that path fires on the *provider's*
moderation of a turn already being generated, not a dedicated yes/no judgment on a standalone
string, and conflating the two would make FR-008 (defence in depth independent of FR-007)
impossible to reason about separately.

## Decision 3 — Model-backed attempt cap

**Decision**: A new small Cosmos container `avatarSetupAttempts` (config constant
`AVATAR_SETUP_ATTEMPTS_CONTAINER`), one document per `(playerId, storyId)` pair keyed by
`f"{playerId}:{storyId}"`, holding a single `modelBackedAttempts: int` counter incremented
immediately before each model-backed check (never for a cost-free rejection, per FR-010/FR-014).
The document is deleted once a session is successfully created for that pair, so a later, separate
setup against the same adventure starts the count fresh. Reaching the cap raises a new
`AvatarValidationAttemptsExceededError`, mapped to the plain-language message FR-014 requires.

**Rationale**: The cap must survive across separate HTTP requests for the same in-progress setup
(a player edits and resubmits), which rules out in-memory state in a horizontally-scaled Azure
Functions app. A dedicated container mirrors this codebase's existing pattern of a small,
narrowly-scoped counter document (`playerContentSafetyStandings` is the closest precedent: one
document per player, incremented on a triggering event, read-modify-write with the same bounded
`_etag`-retry loop already used throughout `story_service.py` and
`player_content_safety_standing_service.py`). No Cosmos-native TTL is used anywhere in this
codebase (confirmed by search) — expiry, where it matters, is always an explicit field checked in
application code — so this slice follows suit rather than introducing TTL as a new pattern; a
stale attempts document left behind by an abandoned setup is harmless (Assumption: "a guard rail,
not a quota to tune") and is cleared the next time that player successfully starts a session
against that story.

**Alternatives considered**: Piggybacking on `playerContentSafetyStandings` — rejected; that
container's semantics are a long-lived, cross-session policy-violation count with a lockout
consequence, not a short-lived per-setup retry count, and conflating them would make one
feature's cap tune the other's lockout threshold by accident. Client-side-only enforcement —
rejected; FR-014 requires the system to cap attempts, and a client-side-only cap is not a system
guarantee.

**Exact cap value**: left to the tasks/implementation phase to pick a concrete integer (the spec's
own Assumption defers this); this plan fixes only the mechanism.

## Decision 4 — Token attribution for validation calls

**Decision**: Each model-backed validation attempt's token usage is added to `Story.totalTokens`
via a new `StoryService` method mirroring `record_test_play` (`story_service.py:393`) — same
bounded 3-attempt `_etag` read-modify-write, but stamping no `lastTestPlayedAt`-equivalent field
(nothing else on `Story` needs updating). It is never added to any `PlaySession.totalTokens`,
because no session exists yet when validation runs, satisfying FR-016 automatically rather than by
extra bookkeeping.

**Rationale**: `record_test_play` is the exact existing precedent for "tokens spent outside a
session accrue to the adventure total via the same guarded read-modify-write every other
`Story.totalTokens` writer in this file uses." Reusing that shape keeps this addition consistent
with the file's own conventions rather than inventing a second accrual style.

## Decision 5 — Prompt construction change

**Decision**: In `_build_gameplay_turn_prompt` (`llm_service.py:454`), change line 472 from
`f"Character: {session.characterName} ({session.characterType})"` to a line built from
`session.avatarDescription` when present (`f"Character: {session.characterName} — {session.avatarDescription}"`),
falling back to the name alone when it is `None` (a resumed pre-existing session, FR-026–FR-027).
The `033`-merged Cast block (lines 474–485) is unchanged in code; only its lead-in prose
("distinct from the player's own character above") is re-verified to still read correctly against
the new line's wording.

**Rationale**: This is the minimal change that satisfies FR-018 (avatar supplied as who the player
is, every turn) without touching the Cast block `033` just shipped, and it reuses the same
`lines.append` structure already in place.

**Alternatives considered**: Adding a separate `lines.append` line for the avatar rather than
folding it into the existing `Character:` line — rejected as an unnecessary structural change; the
existing line already carries "who the player is" and needs only its bracketed detail replaced.

## Decision 6 — Fixed tester avatar

**Decision**: A new module-level constant `TESTER_AVATAR_DESCRIPTION` in
`test_play_session_service.py`, alongside the existing `TESTER_CHARACTER_NAME`, replaces
`characterType=story.characterTypes[0].name` with `avatarDescription=TESTER_AVATAR_DESCRIPTION`
(and `characterType` left `None`) at line 142.

**Rationale**: Directly matches FR-024 and the existing `TESTER_CHARACTER_NAME` precedent one line
above it — same file, same construction call, same "fixed, not derived" shape.

## Decision 7 — Frontend setup step

**Decision**: Replace `CharacterTypeStep.jsx` with a new `AvatarDescriptionStep.jsx` (free-text
textarea, client-side length hint, pending indication while the model-backed check runs, and the
existing design-system disabled/pending affordances for "cannot resubmit while pending" — FR-013).
`GamePage.jsx` stops fetching/passing `characterTypes` into a picker and instead holds
`avatarDescription` in its setup state, retaining it across an adventure change per FR-005 exactly
as `characterName` already is.

**Rationale**: `CharacterTypeStep.jsx` has no client-side content validation today (it is a plain
radio-select), so nothing there is reusable for the new field's validation; a new component keeps
`CharacterNameStep.jsx` (kept unchanged) independent of the replaced step, matching the existing
one-component-per-setup-step structure.

## Decision 8 — Six-spec wording amendments

**Decision**: Edit the already-identified passages in place (per Constitution Principle XI — no
narrative of the change, just the corrected text) in `006` (FR-003, FR-003a, FR-004, FR-004a, the
Character Type key entity, SC-001, SC-002), `004` (Character Type key entity), `008` (Independent
Test line, session-setup reference, `data-model.md`'s `characterType` row and validation-trust
note), `009` (`data-model.md`'s resume-carried-fields note), `010` (spec.md's Independent Test
wording; the tester-avatar derivation rationale in `010`'s own `research.md` "Decision 6"), and
`012` (FR-004's roster-export wording, in light of `032`'s FR-023 cast framing). None of these
touch that repo's stored data shapes — only prose.

**Rationale**: These are the exact locations the dedicated codebase research identified; editing
in place rather than appending a note matches Principle XI directly.
