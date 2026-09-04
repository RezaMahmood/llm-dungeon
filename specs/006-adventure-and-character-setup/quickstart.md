# Quickstart: Adventure and Character Setup

**Feature**: 006-adventure-and-character-setup | **Date**: 2026-08-31

Validates the setup flow end-to-end: listing published adventures, entering a character name,
choosing a character type, and being blocked from starting play until all three are valid.
See [contracts/api.md](./contracts/api.md) for exact request/response shapes and
[data-model.md](./data-model.md) for field definitions.

## Prerequisites

- Backend running locally (Azure Functions Core Tools) or against the deployed dev environment,
  with a Cosmos `Stories` container reachable.
- At least one seeded `Story` with `published: true` and ≥2 `characterTypes` (per the spec's
  Independent Test scenario). Use the existing admin story-creation + publish flow
  (`004-story-creation-done` / `005-story-publishing`) to produce one, or seed directly via
  `StoryService`.
- A test account with the `Player` role in the account-provisioning allow-list
  (`003-account-provisioning`).

## Backend validation (contract-level)

1. **List adventures** — `GET /api/game/adventures` as an authenticated Player. Expect 200 with
   the seeded published adventure present; its `characterTypes` must NOT appear in this
   response (list is intentionally light — see contracts/api.md).
2. **Adventure detail** — `GET /api/game/adventures/{adventureId}` for the seeded adventure.
   Expect 200 with its `characterTypes` array populated.
3. **Unpublished/nonexistent adventure** — `GET /api/game/adventures/{someOtherId}` for an id
   that is either nonexistent or belongs to an unpublished story. Expect 404
   `{"error": "not_found", ...}` in both cases (indistinguishable, by design).
4. **Non-Player caller** — repeat step 1 with a token for an account that has no `Player` role.
   Expect 403 `forbidden_insufficient_permission()`.
5. **Complete, valid setup** — `POST /api/game/start` with the seeded adventure's id, a
   non-blank name ≤50 chars, and one of its character type names. Expect 200 with the echoed
   fields.
6. **Incomplete setup** — `POST /api/game/start` omitting `characterType`. Expect 400 with
   `fields.characterType` present.
7. **Name too long** — `POST /api/game/start` with a 51-character `characterName`. Expect 400
   with `fields.characterName` naming the length problem.
8. **Blank name** — `POST /api/game/start` with `characterName: "   "`. Expect 400 with
   `fields.characterName` naming the blank problem.
9. **Character type from a different adventure** — seed a second published adventure with a
   disjoint set of character type names; `POST /api/game/start` for adventure A using a type
   name that only exists on adventure B. Expect 400 with `fields.characterType`.
10. **Zero published adventures** — with a Cosmos state where no story has `published: true`,
    repeat step 1. Expect 200 with `adventures: []` (frontend renders the empty-state message;
    this call itself still succeeds).

## Frontend validation (manual, end-to-end)

Run the frontend dev server against the backend from the steps above, signed in as a Player.

1. From the main menu, choose "start a new game" → lands on `/game`.
2. Confirm only published adventures are listed, each distinguishable by name (FR-001); if none
   are published, confirm the clear "nothing available yet" message appears instead of an empty
   or broken list (FR-006).
3. Confirm character name entry and character type selection are not reachable before an
   adventure is selected (FR-003a).
4. Select an adventure → confirm the character-name field and that adventure's character types
   (and only that adventure's) appear.
5. Enter a name over 50 characters, or leave it blank, and attempt to proceed → confirm a
   rejection message asking for a valid/shorter name (edge cases).
6. Select a character type, then go back and change the selected adventure → confirm the
   character type selection is cleared while the character name is retained (FR-004a).
7. Attempt to start play with any one of the three fields still missing → confirm play is
   blocked and the missing item(s) are identified to the player (FR-004, FR-005).
8. Supply all three (adventure, valid name, character type) and confirm → confirm setup
   succeeds (per contracts/api.md's 200 response); full play-session behavior beyond this point
   is `008-core-gameplay`'s scope, not verified here.

## Expected Outcome

All ten backend steps and eight frontend steps behave as described, matching
[spec.md](./spec.md)'s Acceptance Scenarios 1–5 and the Edge Cases section. This quickstart does
not replace the automated test suite (Constitution Principle I) — it is a manual/exploratory
cross-check plus the basis for `tasks.md`'s final user-verified acceptance task
(Constitution Principle IX).
