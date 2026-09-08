# Implementation Plan: Story Test Play

**Branch**: `010-story-test-play` | **Date**: 2026-09-08 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/010-story-test-play/spec.md`

## Summary

An administrator plays a draft story interactively against its current saved
configuration, using the same narrative generation as real gameplay; the session can be
aborted (with a warning) and, on reaching an ending, offers a confirmed publish or a
return to the wizard.

The backend core is narrower than the spec's surface suggests. `017-story-publish-test-play-gate`
has no plan or tasks, but its requirements are already merged: `Story.lastTestPlayedAt`,
`StoryService.can_publish()`, and the `409 test_play_required` response all exist in
`origin/main`. Nothing writes `lastTestPlayedAt`, so `can_publish()` is unsatisfiable and
**no story can currently be published**. This feature supplies the missing writer, which
makes publishing reachable for the first time.

Test-play sessions get their own Cosmos container so no player route can reach them
(FR-009), reusing `LLMService.generate_gameplay_turn()` and the completion-evaluation
rules rather than the player session lifecycle. On the frontend, test play is a new
administrator screen that reuses the existing presentational play components, and the
one existing publish control gains a confirmation — satisfying amended `005` FR-013 at
all three entry points at once.

## Technical Context

**Language/Version**: Python 3.11 (backend, per `.github/workflows/test.yml`);
JavaScript/JSX on React 19.2 (frontend)

**Primary Dependencies**: Azure Functions (Python v2 programming model), `azure-cosmos`,
`azure-identity`, `agent-framework-openai`, `azure-monitor-opentelemetry`; React 19,
`react-router-dom` 7, `@azure/msal-react` 5, `axios`

**Storage**: Azure Cosmos DB. Existing containers `stories` and `playSessions`
(partition key `/id`); one new container `testPlaySessions` (partition key `/id`) —
see Complexity Tracking

**Testing**: `pytest` (`pytest.ini`, `testpaths = src/backend/tests infrastructure/tests`)
with in-module `FakeCosmosService`/`FakeContainer` stubs and `MagicMock(spec=LLMService)`;
Vitest + React Testing Library with `vi.mock` on service modules

**Target Platform**: Azure Functions (Linux) backend; browser SPA frontend

**Project Type**: Web application — `src/backend` + `src/frontend`

**Performance Goals**: None specified (Principle IV). The existing per-session
`MIN_INTERACTION_INTERVAL_SECONDS = 2` is reused; the per-player 10-second session
creation throttle is deliberately not

**Constraints**: Test play must work on **unpublished** stories, so it cannot reuse the
`game/*` routes, which are hard-gated on `story.published` in three places. Test-play
state must be unreachable from every player route (FR-009), including by session id

**Scale/Scope**: One new backend service, model, and route group; one new frontend page
and service module; one amendment to the shared publish control. No new environment
(Principle XII)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design — still passing.*

| Principle | Status | How |
|---|---|---|
| I. Meaningful automated testing | Pass | FR-012 enumerates six outcomes, each getting a test (see quickstart.md). Cosmos and the LLM are stubbed locally — no live Azure resource, no manual step |
| II. Secure-by-default access | Pass | Every new route calls `authorize_admin(req)` server-side before any work. No anonymous path; the client never gates alone |
| III. Defined technology stack | Pass | Python Azure Functions + React only; no new runtime or framework |
| IV. Simplicity over premature scale | Pass, one item tracked | Reuses the existing turn generator, completion rules, and presentational components. The new container is justified below |
| V. Continuous integration gate | Pass | New tests run in the existing PR suite; no workflow change |
| VI. Observability & AI cost transparency | Pass | Test-play turns call `LLMService.generate_gameplay_turn()`, already instrumented with the `gen_ai.gameplay.turn` span carrying prompt, response, input/output tokens, `gen_ai.cost_usd`, and latency. Reuse means test-play spend is captured with no new sink |
| VII. Zero-trust Azure communication | Pass | Reuses `CosmosService`, which authenticates with `DefaultAzureCredential`/Managed Identity. The new container inherits the account's private networking |
| VIII. UI design system & accessibility | **Exception requested** | See below |
| IX. Playtesting-driven quality | Pass | The manual check in quickstart.md is explicitly optional and non-blocking |
| X. PII protection | Pass | Only the administrator's `oid` is stored, as everywhere else. No email, name, or PII in documents, logs, or telemetry |
| XI. Implementer design latitude | Pass | No pre-implementation design sign-off task |
| XII. Right-sized scope | Pass | No new environment, no role hierarchy beyond the existing `Administrator` check, no multi-tenancy or scaling infrastructure |
| XIII. AI agent division of labor | Pass | Branch synced with `origin/main` before this plan was written. Existing identifiers were read from the synced tree; proposed ones are marked **(proposed)** throughout the artifacts. `017`'s status is stated as fact, not assumed |
| XIV. Artifacts and code stay clean | Pass | Decisions are recorded with brief rationale, not narrative history |

### Principle VIII — explicit, justified exception (spec FR-011)

**Requested**: ship the test-play screen without a visual design pass — no mockup and no
bespoke layout.

**Justification**: FR-011 states an approved design is expected later; the spec's
Assumptions require this be raised here rather than treated as silently satisfied. This
mirrors the same deferral already granted to `012-story-editing-and-review` FR-012.

**Scope of the exception — appearance only.** Everything else in Principle VIII and the
UI Design System Requirements applies in full:

- Colors, fonts, spacing, radii, and shadows come from
  `src/frontend/src/styles/designTokens.css` (the vendored `specs/designs/styles.css`).
  No literal hex, bare font-family, or magic pixel value is introduced.
- Controls are existing design-system classes (`.btn`, `.input`, `.field`, `.dialog*`,
  `.tag`) and the existing presentational components `StoryPane`, `InstructionInput`,
  `SuggestedActions`, `StatusPanel` — no parallel reimplementation of a control the
  system provides.
- The four interaction states, keyboard operability, visible `:focus-visible` focus, and
  semantic HTML are required and verified (quickstart.md's accessibility check).
- FR-003's test/draft marking is conveyed as text, never color alone.

**Screen contract traceability**: Governance forbids shipping a screen traceable to no
screen contract. The test-play screen is traceable to the **Administrator
story-authoring wizard** contract (`specs/designs/04-admin-wizard.html`, step 05 "Test
play"), which the constitution already lists. No amendment is needed. The prototype's
"Flag this reply" button is deliberately unimplemented, recorded in
`specs/designs/README.md`.

### Dependency status (Principle XIII)

| Spec | Status in `origin/main` | Bearing on this plan |
|---|---|---|
| `005-story-publishing-done` | Merged | Publish/unpublish routes and `StoryPublishActions` exist. FR-013's publish confirmation is amended by this feature and is in-scope work here |
| `008-core-gameplay-done` | Merged | `LLMService.generate_gameplay_turn()` and the completion rules are reused |
| `012-story-editing-and-review` | Merged (`db8c33a`) | `/admin/stories/:storyId/edit` and `create_edit_draft` exist; FR-008 navigates to them |
| `017-story-publish-test-play-gate` | **Spec folder has no plan/tasks, but its FR-001/FR-002/FR-003 code is merged** | This feature writes the marker the merged gate reads. Not a blocker |
| `009-save-and-continue` | Merged (`2a8d352`) | Explicitly out of scope — test play has no checkpoints or resume |

## Project Structure

### Documentation (this feature)

```text
specs/010-story-test-play/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── api.md           # Phase 1 output
├── checklists/
│   └── requirements.md  # Existing
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/backend/
├── function_app.py                      # MODIFY — register 4 test-play routes
├── config.py                            # MODIFY — TEST_PLAY_SESSIONS_CONTAINER
├── api/admin/
│   ├── test_play.py                     # NEW — route handlers
│   └── stories.py                       # unchanged (publish gate already correct)
├── models/
│   └── test_play_session.py             # NEW — TestPlaySession, TestPlayExchange
├── services/
│   ├── test_play_session_service.py     # NEW — session lifecycle, turn processing
│   ├── play_session_service.py          # MODIFY — extract shared completion evaluation
│   └── story_service.py                 # MODIFY — record_test_play(story_id)
├── db/seed_data.py                      # MODIFY — new container in CONTAINER_PARTITION_KEY_PATHS
└── tests/
    ├── unit/test_test_play_session_service.py        # NEW
    └── integration/test_admin_test_play_endpoint.py  # NEW

src/frontend/src/
├── App.jsx                              # MODIFY — /admin/stories/:storyId/test-play
├── pages/
│   ├── AdminStoryTestPlayPage.jsx       # NEW — test-play + conclusion screen
│   └── AdminStoryWizardPage.jsx         # MODIFY — entry point to test play
├── components/
│   ├── Admin/StoryPublishActions.jsx    # MODIFY — publish confirmation + onPublished
│   └── Play/                            # REUSED unchanged
├── hooks/usePublishToggle.js            # MODIFY — publish confirmation state
└── services/testPlayService.js          # NEW

src/frontend/tests/
├── components/AdminStoryTestPlayPage.test.jsx   # NEW
├── components/StoryPublishActions.test.jsx      # MODIFY — confirmation
└── integration/admin_test_play_flow.test.jsx    # NEW

infrastructure/terraform/main.tf         # MODIFY — testPlaySessions container
```

**Structure Decision**: the repository's existing web-application layout — `src/backend`
(Azure Functions) and `src/frontend` (React SPA) — with backend tests split across
`src/backend/tests/unit` and `src/backend/tests/integration`, and frontend tests under
`src/frontend/tests`. No new top-level structure.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| New Cosmos container `testPlaySessions` (+1 Terraform resource) | FR-009 requires test-play state be unreachable from real play, including by session id | A discriminator on `playSessions` leaves a by-id leak: `PlaySessionService._read_item()` reads by id with no type predicate and authorizes only on `playerId`, so a dual-role account could pass its test-session id to `GET /api/game/sessions/{sessionId}` and continue it as real play. Closing that needs a guard on four queries plus every by-id read; a separate container makes the crossing structurally impossible |
| A second session service rather than extending `PlaySessionService` | The player path is hard-gated on `story.published` in `list_published_summaries`, `get_adventure`, and `create_session`; test play exists to run against **drafts** | Adding a "skip the published check" flag through the player lifecycle would put a bypass of the player gate on the real-play code path. The genuinely shared logic — turn generation and completion evaluation — is reused rather than duplicated |
