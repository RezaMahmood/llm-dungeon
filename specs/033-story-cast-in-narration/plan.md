# Implementation Plan: The Story's Cast Reaches the Narration

**Branch**: `033-story-cast-in-narration` | **Date**: 2026-09-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/033-story-cast-in-narration/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

`CharacterType` (name + optional description) is already persisted on every `Story` and already
required to have at least one entry, but `_build_gameplay_turn_prompt` in `llm_service.py` only
ever reads it back as `session.characterType`, a bare name string used for the player's own
label. The story's roster never reaches the narration as anything else. This slice adds a
distinctly labelled "cast" block to the per-turn prompt — every `CharacterType` on the story,
described and separated from the player's own character line — and adds an instruction directing
the narration to prefer a cast entry over an invented character for named or story-significant
roles. No model, storage, or validation shape changes; this is a prompt-construction change plus
its test.

## Technical Context

**Language/Version**: Python 3.13 (backend), matches existing Azure Functions runtime

**Primary Dependencies**: None new — reads the existing `Story.characterTypes` already loaded by
`_build_gameplay_turn_prompt` (`llm_service.py`); no new package

**Storage**: No change. `Story.characterTypes` (`src/backend/models/story.py`) keeps its existing
shape — a name and optional description — and its existing "at least one entry" validation in
`Story.__post_init__` and `story_config_file.py`

**Testing**: pytest, per Constitution Principle I — a new automated test per FR-006 behaviour,
added alongside the existing gameplay-turn-prompt tests in
`src/backend/tests/unit/test_llm_service.py`

**Target Platform**: Azure Functions (Python backend), unchanged

**Project Type**: Web application (existing `backend` + `frontend` structure); this slice touches
`backend` only

**Performance Goals**: None beyond current prompt-construction cost — the cast block adds a bounded
number of lines proportional to `characterTypes` length, already loaded per turn

**Constraints**: Must not change the player's setup flow, identity, or the administrator's
authoring surfaces (FR-005); must accept every existing story unchanged (FR-004)

**Scale/Scope**: One method (`_build_gameplay_turn_prompt`) in one service file, plus its test;
no new endpoint, no new persisted field

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Meaningful, Automated Testing** — PASS. FR-006 requires an automated test per behaviour
  (cast reaches narration, description travels, precedence instruction present, pre-existing
  story plays unchanged); these are pure prompt-construction unit tests, no external dependency
  to stub.
- **II. Secure-by-Default Access** — N/A. No new endpoint or access surface.
- **III. Defined Technology Stack** — PASS. Change is confined to the existing Python backend.
- **IV. Right-Sized Scope (YAGNI)** — PASS. No new persisted field, no new configuration surface;
  reuses the roster exactly as authored today.
- **V. Observability & AI Cost Transparency** — PASS. The cast block becomes part of the existing
  per-turn prompt already captured by LLM-call telemetry; no new telemetry surface needed.
- **VI. Zero-Trust Azure Resource Communication** — N/A. No new inter-resource call.
- **VII. UI Design System & Accessibility** — N/A. No frontend change; FR-005 explicitly keeps the
  player's setup flow and UI untouched.
- **VIII. PII Protection by Design** — PASS. Roster entries are administrator-authored fictional
  content, not PII; no new data leaves the access-controlled store.
- **IX. Implementer Design Latitude** — N/A. No UI.
- **X. AI Agent Division of Labor** — Followed: branch cut from synced `origin/main` in a worktree,
  work stays local through plan/tasks/implement, PR opened by the agent, merge left to the user.
- **XI. Artifacts and Code Stay Clean** — Followed in this plan and will be followed in the
  resulting code comments/tests.

No violations; Complexity Tracking is not needed.

## Project Structure

### Documentation (this feature)

```text
specs/033-story-cast-in-narration/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

No `contracts/` directory: this slice adds no external interface (no new endpoint, no new request
or response shape) — it changes the internal prompt string sent to the LLM, which is not a
contract this project documents separately from the code that builds it.

### Source Code (repository root)

```text
backend/
└── src/backend/
    ├── models/
    │   └── story.py                 # CharacterType, Story — read only, unchanged
    ├── services/
    │   ├── llm_service.py           # _build_gameplay_turn_prompt — the change
    │   └── story_config_file.py     # roster parsing/validation — read only, unchanged
    └── tests/unit/
        └── test_llm_service.py      # new assertions/tests for the cast block
```

**Structure Decision**: Existing web-application layout (`backend` Azure Functions + `frontend`
React). This slice is backend-only: one method in `src/backend/services/llm_service.py` changes,
with new tests in `src/backend/tests/unit/test_llm_service.py`. No frontend file is touched, per
FR-005.

## Complexity Tracking

*No violations — this section is not needed.*
