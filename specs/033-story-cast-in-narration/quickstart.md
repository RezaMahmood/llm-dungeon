# Quickstart: The Story's Cast Reaches the Narration

Validates the slice end-to-end via the existing unit test suite — no manual UI steps, since FR-005
keeps the player-facing flow unchanged and this is a backend prompt-construction change.

## Prerequisites

- Python environment for `src/backend` set up per the repo's existing backend test instructions
  (see `src/backend/tests/unit/test_llm_service.py` for current fixture patterns).

## Run

```bash
cd src/backend
pytest tests/unit/test_llm_service.py -k gameplay_turn_prompt
```

## Expected outcomes (mapped to Acceptance Scenarios / FR-006)

1. **Cast reaches the prompt, distinctly labelled** — a `Story` fixture with several
   `CharacterType` entries produces a built prompt containing a cast block separate from the
   `Character: {name} ({type})` player line (Acceptance Scenario 1).
2. **Description travels with the name** — a `CharacterType` with a `description` renders that
   description in the cast block; one without a description still renders by name alone
   (Acceptance Scenario 4, Edge Case).
3. **Precedence instruction is present** — the built prompt contains the instruction directing the
   narration to prefer a fitting cast entry over inventing a named character (Acceptance
   Scenario 2, FR-002).
4. **Pre-existing stories are unaffected** — a `Story` fixture shaped like a pre-change roster
   (e.g. player-class-style names, no description) still builds a valid prompt with no error and
   its roster present as cast (Acceptance Scenario 5, FR-004, SC-003).

## Full backend suite (regression check)

```bash
cd src/backend
pytest
```

Expected: full suite green, confirming FR-005 — no other backend behavior (setup flow, session
handling, publication precondition) changed.
