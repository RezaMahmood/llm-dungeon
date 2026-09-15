# Quickstart: A Player-Authored Avatar Replaces the Character-Type Picker

## Prerequisites

- Backend: Python environment for `src/backend` set up per its existing test instructions.
- Frontend: `npm install` in `src/frontend` (existing setup, unchanged).
- No live Cosmos DB or LLM endpoint required — all tests below run against mocks/fakes, per
  Constitution Principle I.

## Backend

```bash
cd src/backend
pytest tests/unit/test_play_session_service.py -k avatar
pytest tests/unit/test_llm_service.py -k gameplay_turn_prompt
pytest tests/unit/test_test_play_session_service.py -k avatar
pytest tests/unit/test_story_service.py -k avatar_validation
```

**Expected outcomes**:

1. A valid 20–500 character avatar description passes the cost-free checks and reaches the
   model-backed check exactly once (Acceptance Scenario 1 & 3, FR-001, FR-006, FR-010).
2. A blank, too-short, or too-long description is rejected with no model call made (Acceptance
   Scenario 6, Edge Cases, FR-006, FR-010, SC-006, SC-009).
3. A description that reads as an instruction to the narration is rejected (Acceptance Scenario 6,
   FR-007, SC-007), and a suite of known prompt-injection patterns is rejected the same way
   (FR-008).
4. A model-backed check that times out or errors is treated as no verdict, rejects, and blocks
   session creation (Acceptance Scenario 8, FR-011, FR-012, SC-008).
5. Repeated model-backed attempts against the same story increment and eventually hit the cap,
   producing the plain-language cap message (FR-014, SC-011); cost-free rejections never count
   toward it (SC-009).
6. Validation tokens land on `Story.totalTokens` and never on any `PlaySession.totalTokens`,
   rejections included (FR-016, SC-013).
7. The built gameplay-turn prompt carries the avatar description as the player's identity from
   turn 1 onward, and turn 0 is unaffected (Acceptance Scenario 4 & 5, FR-018, FR-021, SC-004,
   SC-005).
8. A pre-change-style session (no `avatarDescription`, a `characterType` present) still builds a
   valid prompt, falling back to the character name alone (Acceptance Scenario from User Story 3,
   FR-026, FR-027, SC-014).
9. Administrator test play starts with the fixed tester avatar description and no derived
   character type (Acceptance Scenario, FR-024).

## Frontend

```bash
cd src/frontend
npm run test -- AvatarDescriptionStep
npm run test -- GamePage
```

**Expected outcomes**:

1. No character-type choice is rendered anywhere in the setup flow (Acceptance Scenario 1, FR-002,
   SC-003).
2. Missing avatar description blocks play with the field identified (Acceptance Scenario 2,
   FR-004).
3. A pending indication (no countdown/estimate) is shown while the check runs, and resubmission is
   disabled meanwhile (Acceptance Scenario 7, FR-013).
4. Changing the selected adventure retains the character name and does not silently discard typed
   avatar text (Acceptance Scenario 9, FR-005).

## Full regression check

```bash
cd src/backend && pytest
cd src/frontend && npm run test
```

Expected: both suites green — confirming no other backend or frontend behavior changed, and that
every pre-existing adventure and saved session (SC-014, SC-015) is unaffected.
