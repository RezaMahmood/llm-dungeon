---

description: "Implementation plan for A Player-Authored Avatar Replaces the Character-Type Picker"
---

# Implementation Plan: A Player-Authored Avatar Replaces the Character-Type Picker

**Branch**: `032-story-archetypes-player-avatar` | **Date**: 2026-09-15 | **Spec**:
[spec.md](./spec.md)

**Input**: Feature specification from `/specs/032-story-archetypes-player-avatar/spec.md`

## Summary

The character-type picker is removed from player setup and replaced with a required, validated
free-text avatar description (20–500 characters) that becomes the player's identity in the
narration from their first turn onward — turn 0 stays verbatim. Validation runs cost-free checks
(blank, length) before a model-backed story-relevance / anti-injection check with a 10-second
fail-closed timeout and a capped number of attempts per setup. The administrator-authored roster
stops being player-selectable anywhere (setup, resume, test play) and is reworded to describe the
story's cast; test play uses a fixed tester avatar. Pre-existing sessions resume unchanged, keeping
their character name and dropping the old character type rather than converting it.

## Technical Context

**Language/Version**: Python 3.13 (backend, Azure Functions); JavaScript/JSX with React 19
(frontend) — matches the existing project, no change.

**Primary Dependencies**: Backend — existing `agent_framework`/`agent_framework_openai`/`openai`
LLM-call plumbing already in `llm_service.py` (no new dependency for the model-backed check);
`azure-cosmos` (existing) for the new `avatarSetupAttempts` container and the widened
`PlaySession`/`TestPlaySession` fields. Frontend — existing React component/design-system
libraries; no new package.

**Storage**: Azure Cosmos DB. One new container (`avatarSetupAttempts`); two existing containers'
documents gain fields (`playSessions`, `testPlaySessions` — `characterType` widened to optional,
`avatarDescription` added). No change to any other container.

**Testing**: pytest (backend, mocked LLM client and Cosmos service, matching every existing service
test in this codebase); Vitest (frontend, existing `*.test.jsx` pattern).

**Target Platform**: Azure Functions (backend), browser SPA (frontend) — unchanged.

**Project Type**: Web application (frontend + backend), matching the existing repository layout.

**Performance Goals**: No new goal beyond the spec's own bound — the model-backed check must
resolve or be abandoned within 10 seconds (FR-011, SC-010). No throughput target (Constitution
Principle IV — this is not a scaled system).

**Constraints**: The model-backed check MUST run behind an explicit timeout and fail closed
(FR-012); cost-free checks MUST run first and spend no tokens (FR-010, SC-009); rejected avatar
text MUST NOT be persisted anywhere (FR-015).

**Scale/Scope**: One new backend service module, one new Cosmos container, edits to two existing
models/services (`PlaySession`/`play_session_service.py`, `TestPlaySession`/
`test_play_session_service.py`), one prompt-construction edit (`llm_service.py`), one new frontend
setup-step component replacing an existing one, wording edits across the admin wizard/config
surfaces, and wording amendments to six already-shipped specs. No change to unrelated features.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design — no new violation
introduced by the design below.*

- **I. Meaningful, Automated Testing**: PASS. FR-030 enumerates every behavior requiring a test;
  `quickstart.md` maps each to a concrete pytest/Vitest invocation. All backend tests mock the LLM
  client and Cosmos service (existing pattern, no live dependency — no stub/emulator needed since
  nothing here calls a live Azure resource in tests).
- **II. Secure-by-Default Access**: PASS/N/A. No change to authentication or authorization; the
  existing Entra ID-gated endpoints are extended, not newly exposed.
- **III. Defined Technology Stack**: PASS. Python/Azure Functions backend, React frontend —
  unchanged, no new language or framework.
- **IV. Right-Sized Scope — YAGNI**: PASS. The attempt-cap mechanism (research.md Decision 3) is
  the smallest new container this codebase's own patterns support — no TTL machinery, no new
  service tier, no distributed rate-limiter; explicitly a guard rail, not infrastructure for scale
  that hasn't been asked for.
- **V. Observability & AI Cost Transparency**: PASS. The model-backed validation call goes through
  the same `LLMService` call plumbing every other LLM call already uses, so it is captured by the
  same OpenTelemetry/Application Insights instrumentation and token/cost recording (FR-016 adds
  *where* the tokens are attributed — the adventure total — not a new telemetry path).
- **VI. Zero-Trust Azure Resource Communication**: PASS/N/A. No new Azure-to-Azure communication
  path; the new container uses the same Cosmos client/Managed Identity as every existing one.
- **VII. UI Design System & Accessibility Compliance**: PASS, verified at implementation —
  `AvatarDescriptionStep.jsx` (Decision 7) uses the existing design-token layer and shared form
  controls, including the existing pending/disabled affordance for "cannot resubmit while
  checking" (FR-013), not a bespoke one.
- **VIII. PII Protection by Design**: PASS. Avatar descriptions are player-authored fictional
  character text, not PII; FR-015 additionally ensures a *rejected* description is never recorded
  anywhere, which is stricter than the constitution requires, not merely compliant with it.
- **IX. Implementer Design Latitude**: N/A — noted, not a gate; no pre-implementation mockup is
  required or sought for `AvatarDescriptionStep.jsx`.
- **X. AI Agent Division of Labor**: PASS. This plan and all downstream artifacts are local
  spec-related work; the branch will be synced with `origin/main` before implementation begins,
  per the mandatory `before_implement` hook.
- **XI. Artifacts and Code Stay Clean**: PASS. `research.md` states decisions with brief rationale,
  no narrative of alternatives explored and discarded beyond a short "alternatives considered"
  line per decision, matching the format the constitution requires.

No violation requires justification; **Complexity Tracking is not needed.**

## Project Structure

### Documentation (this feature)

```text
specs/032-story-archetypes-player-avatar/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output
├── quickstart.md         # Phase 1 output
└── tasks.md              # Phase 2 output (/speckit-tasks — not created by /speckit-plan)
```

No `contracts/` directory: this slice changes an existing internal request/response shape
(session-creation payload gains `avatarDescription`, loses the required `characterType`) rather
than introducing a new externally-facing interface; the exact field-level shape is `tasks.md`'s
concern, consistent with `033`'s precedent of skipping `contracts/` for an internal-only change.

### Source Code (repository root)

```text
src/backend/
├── models/
│   ├── play_session.py            # characterType → Optional; add avatarDescription
│   └── test_play_session.py       # same widening
├── services/
│   ├── avatar_validation_service.py   # NEW — cost-free + model-backed checks
│   ├── play_session_service.py        # setup validation wired to AvatarValidationService
│   ├── test_play_session_service.py   # fixed tester avatar constant
│   ├── story_service.py               # new token-accrual method (mirrors record_test_play)
│   └── llm_service.py                 # _build_gameplay_turn_prompt: avatar in the Character line
├── config.py                          # AVATAR_SETUP_ATTEMPTS_CONTAINER constant
└── tests/unit/
    ├── test_avatar_validation_service.py   # NEW
    ├── test_play_session_service.py
    ├── test_test_play_session_service.py
    ├── test_story_service.py
    └── test_llm_service.py

src/frontend/
├── src/
│   ├── components/GameSetup/
│   │   ├── AvatarDescriptionStep.jsx   # NEW — replaces CharacterTypeStep.jsx
│   │   └── CharacterNameStep.jsx       # unchanged
│   ├── components/Admin/StoryWizard/CharacterTypeList.jsx   # wording only
│   └── pages/GamePage.jsx              # avatarDescription setup state, not characterTypes
└── tests/components/GameSetup/
    ├── AvatarDescriptionStep.test.jsx  # NEW
    └── CharacterNameStep.test.jsx

specs/006-adventure-and-character-setup/   # wording amendments (spec.md)
specs/004-story-creation-done/             # wording amendment (spec.md)
specs/008-core-gameplay-done/              # wording amendments (spec.md, data-model.md)
specs/009-save-and-continue/               # wording amendment (data-model.md)
specs/010-story-test-play-done/            # wording amendments (spec.md, research.md)
specs/012-story-editing-and-review/        # wording amendment (spec.md)
```

**Structure Decision**: Existing web-application layout (`src/backend`, `src/frontend`), unchanged.
This slice touches both sides plus six sibling spec directories' prose; no new top-level directory.

## Complexity Tracking

No violations — this section is not needed.
