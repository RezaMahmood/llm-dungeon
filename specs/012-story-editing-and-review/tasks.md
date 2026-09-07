---

description: "Task list for Story Editing and Review (012-story-editing-and-review)"
---

# Tasks: Story Editing and Review

**Input**: Design documents from `/specs/012-story-editing-and-review/`

**Prerequisites**: [`plan.md`](./plan.md), [`spec.md`](./spec.md), [`research.md`](./research.md), [`data-model.md`](./data-model.md), [`contracts/api.md`](./contracts/api.md), [`quickstart.md`](./quickstart.md)

**Tests**: Test tasks ARE included — spec **FR-008** explicitly requires an automated test for
every distinct maintenance action, and constitution Principle I makes automated testing
non-negotiable. Within each phase, write the tests first and confirm they fail before the
implementation tasks in that phase.

**Organization**: Tasks are grouped by user story so each story can be implemented, tested, and
delivered independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: `[US1]` / `[US2]` — maps the task to a user story in [`spec.md`](./spec.md)
- Every task names the exact file path it touches

## Path Conventions

Existing web-application layout (plan.md → Structure Decision): `src/backend/` (Python Azure
Functions) and `src/frontend/` (React 19 + Vite SPA). No new container, no new service boundary,
no new runtime dependency in `requirements.txt` or `package.json`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm the working environment and put the one shared test helper in place.

- [X] T001 Verify dev dependencies and record a green baseline per [`quickstart.md`](./quickstart.md) — `pip install -r src/backend/requirements.txt -r src/backend/requirements-dev.txt`, `npm --prefix src/frontend ci`, then `pytest`, `npm --prefix src/frontend test`, `npm --prefix src/frontend run lint`
- [X] T002 Promote the local `_story(**overrides)` factory from `src/backend/tests/unit/test_story_service.py` into a shared fixture/helper in `src/backend/tests/conftest.py` so the four new test modules build valid `Story` objects one way. **Runs after T001** — the baseline must be recorded against an unmodified suite, which is why this is deliberately not `[P]`

**Checkpoint**: Baseline suites green; shared story factory importable from `conftest.py`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The persisted model fields and the single canonical configuration-file
serializer/validator that BOTH user stories depend on (research.md §2, §3, §6).

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### Tests for Foundational ⚠️

> Write these first and confirm they fail before the implementation tasks below.

- [X] T003 [P] Write unit tests for the new model fields in `src/backend/tests/unit/test_models.py` — `Story.contentVersion` defaults to `1` and `Story.lastUpdatedBy` to `None` when absent from a persisted dict (back-compat, data-model.md → Story); `StoryDraft.sourceStoryId`/`baseContentVersion` default to `None` and survive `to_dict`/`from_dict`
- [X] T004 [P] Write unit tests for the configuration file in `src/backend/tests/unit/test_story_config_file.py` — exact serialization (fixed key order, `indent=2`, `ensure_ascii=False`, one trailing newline), `id` emitted first and only when present, every excluded key absent (`published`, `lastPublishedAt`, `createdBy`, `createdAt`, `contentUpdatedAt`, `lastUpdatedBy`, `lastTestPlayedAt`, `contentVersion`, `entityType`, `narrativeGuidance`), and every rejection reason from contracts/api.md (text that is not valid JSON, with the position named; non-object payload, unrecognised key named in the message, empty `worldPrompt`, empty/missing `characterTypes`, duplicate character type names case-insensitively, missing `completionCriteria`/`successConditions`, `rule` outside `any`/`all` with >1 condition, non-positive `sessionLengthMinutes`/`chapters`, and a missing/empty `name` when the payload carries an `id` — the overwrite path only, since an id-less upload takes its name from the administrator-supplied `title`; `Story.__post_init__` does not validate `name`, so this validator is the only guard against a nameless overwrite) — quickstart.md scenarios 4 and 12. Written before T005/T007/T008 and expected to fail; note its excluded-key assertions only fail *for the right reason* once T005 has put `lastUpdatedBy`/`contentVersion` on `Story` (before that they fail at construction)

### Implementation for Foundational

- [X] T005 [P] Add `lastUpdatedBy: Optional[str] = None` and `contentVersion: int = 1` to `Story` in `src/backend/models/story.py`, including `to_dict` emission and `from_dict` reads with back-compat defaults (mirroring the existing `contentUpdatedAt` precedent)
- [X] T006 [P] Add `sourceStoryId: Optional[str] = None` and `baseContentVersion: Optional[int] = None` to `StoryDraft` in `src/backend/models/story_draft.py`, including `to_dict`/`from_dict`
- [X] T007 Create `src/backend/services/story_config_file.py` with the `StoryConfiguration` dataclass and `serialize(story) -> str` producing the canonical bytes defined in data-model.md → StoryConfiguration
- [X] T008 Add `parse_text(text) -> StoryConfiguration` (JSON-decode first, turning a `JSONDecodeError` into the field-naming error with the parser's position) and `parse(payload) -> StoryConfiguration` with its validation to `src/backend/services/story_config_file.py` — accept-and-ignore the known system-managed keys, reject any other unknown key by name, enforce the `Story`/`CharacterType`/`CompletionCriteria` rules plus case-insensitive character-type name uniqueness and the overwrite-path `name` requirement, raising an error carrying the field-naming message (research.md §7); depends on T007 (same file)

**Checkpoint**: Model fields persist with back-compat defaults, and one module owns the file
format for the viewer, the download, and the importer. User story work can now begin.

---

## Phase 3: User Story 1 - Administrator Reviews Existing Stories (Priority: P1) 🎯 MVP

**Goal**: An administrator sees every story with its published status, can publish/unpublish
from that list (FR-011), and can open any story in one action to view its complete configuration
file read-only with a download beside it — byte-identical to what the download saves (FR-001,
FR-002, FR-004, SC-001).

**Independent Test**: With one published and one unpublished story present, load the story list
and confirm both appear with correct status conveyed as text; open one **in a single action from
its row**, confirm the viewer's content matches the downloaded file exactly; publish/unpublish a
row and confirm it hits the same endpoints and preconditions as the wizard's publish step.

**Ships alone**: this phase must leave no dead affordance behind — the per-row **Edit** link
belongs to US2 (T042), because its route only exists once T041 lands.

### Tests for User Story 1 ⚠️

> Write these first and confirm they fail before the implementation tasks below.

- [X] T009 [P] [US1] Backend integration test in `src/backend/tests/integration/test_admin_story_configuration_endpoint.py` — `GET /api/manage/stories/{storyId}/configuration` returns `200` with the exact `serialize()` bytes and `application/json; charset=utf-8`, `404 not_found` for a missing story, and the standard `authorize_admin` unauthorized/forbidden shapes (quickstart.md scenario 3)
- [X] T010 [P] [US1] Frontend component test in `src/frontend/tests/components/StoryPublishActions.test.jsx` — publish, unpublish-with-confirmation (`005` FR-013), and the `409` publish-gate explanation (`005` FR-011) all render from the shared component
- [X] T011 [P] [US1] Frontend integration test in `src/frontend/tests/integration/admin_story_configuration_view.test.jsx` — the viewer renders the response text verbatim and the Download action builds its `Blob` from that same string (FR-002, SC-001)
- [X] T012 [P] [US1] Extend `src/frontend/tests/integration/admin_stories_list.test.jsx` — every story row shows the story's name and its published/unpublished status as text (not color alone), and carries a View affordance that navigates straight to that story's configuration view in one action (FR-001, SC-001, quickstart.md scenario 1). The per-row Edit link is asserted in T042's phase, not here
- [X] T013 [P] [US1] Extend `src/frontend/tests/integration/admin_story_publish_flow.test.jsx` — publishing/unpublishing from a list row exercises the same endpoints, gate explanation, and confirmation as the wizard step (FR-011, quickstart.md scenario 2)

### Implementation for User Story 1

- [X] T014 [US1] Add the `get_story_configuration` handler to `src/backend/api/admin/stories.py`, returning `story_config_file.serialize(story)` as the raw response body (`404 not_found` when absent) per contracts/api.md
- [X] T015 [US1] Confirm the existing `get_story` response carries `contentVersion` and `lastUpdatedBy` — `src/backend/api/admin/stories.py` already returns `story.to_dict()`, so T005 delivers this with no handler change; add the assertion to `src/backend/tests/integration/test_admin_stories_endpoint.py` rather than new production code. These fields are exposed for visibility and tests only: the FR-006 staleness check runs server-side off the draft's `baseContentVersion` and the client never sends a version back (contracts/api.md → `GET …/{storyId}`)
- [X] T016 [US1] Register `@app.route(route="manage/stories/{storyId}/configuration", methods=["GET"])` through the existing `_guarded` wrapper in `src/backend/function_app.py`
- [X] T017 [US1] Add `getStoryConfiguration(token, storyId)` to `src/frontend/src/services/storyDraftService.js` using axios `transformResponse: (r) => r` so the raw text is preserved (research.md §2)
- [X] T018 [P] [US1] Extract the publish/unpublish logic and its confirmation dialog from `src/frontend/src/components/Admin/StoryWizard/StepPublish.jsx` into a new shared `src/frontend/src/components/Admin/StoryPublishActions.jsx` (research.md §11 — extract, do not duplicate)
- [X] T019 [US1] Update `src/frontend/src/components/Admin/StoryWizard/StepPublish.jsx` to render `StoryPublishActions` instead of its own inline implementation (depends on T018)
- [X] T020 [US1] Create `src/frontend/src/pages/AdminStoryConfigurationPage.jsx` — read-only viewer rendering the fetched text verbatim in a semantic `<pre>` with a heading, plus a Download action that wraps that same string in a `Blob` and triggers a `story-<id>.json` object-URL anchor, revoking the URL afterwards (research.md §10). The `<pre>` sits inside its own `overflow: auto` scroll container that is keyboard-focusable (`tabindex="0"` with an accessible name, so a keyboard-only administrator can scroll it) and keeps `white-space: pre` — the text on screen stays the file's exact bytes, and no long line forces a horizontal page scroll (plan.md → Constraints; constitution → Layout and scroll contract). Use a token-based style or the narrowly-scoped scroll-container utility the design-token rules permit — no new visual class. **Depends on T017** for `getStoryConfiguration`, which is why it is not `[P]`
- [X] T021 [US1] Add the lazy, `Administrator`-gated route `/admin/stories/:storyId` for `AdminStoryConfigurationPage` in `src/frontend/src/App.jsx` (**depends on T020** — the lazy import needs the page module to exist)
- [X] T022 [US1] Update `src/frontend/src/pages/AdminPage.jsx` — show each story's status as text, relabelling the current `Draft` tag to `Unpublished` so the UI matches the spec's vocabulary and does not collide with the `StoryDraft` entity; add a per-row **View** link to `/admin/stories/:storyId`; and render `StoryPublishActions` per row (FR-001, FR-011). The Edit link is deliberately **not** added here — it lands with its route in T042. **Depends on T018** (it renders the extracted component) **and T021** — the per-row View link must not ship before the route it points at, the same rule this file already applies to T042/T041

**Checkpoint**: User Story 1 is fully functional and independently testable — the list, the
viewer, the download, and publish/unpublish from the list all work without any US2 work, and
every affordance on the list points somewhere that exists.

---

## Phase 4: User Story 2 - Administrator Edits an Existing Story (Priority: P2)

**Goal**: An administrator updates a story either by reopening it in the wizard (pre-filled,
same per-field one-shot `Suggest`) and saving — with a stale save rejected — or by downloading
the configuration file, editing it, and re-uploading it to overwrite the original (or, with the
`id` removed, to create a new story) (FR-003, FR-005, FR-006, FR-007, FR-009, FR-010).

**Independent Test**: Reopen an existing story in the wizard, change a field via `Suggest`, save,
and confirm only that field moved while `id`/`createdBy`/`createdAt`/`published` survived; save
again from a stale copy and confirm the rejection; then download that story's configuration, edit
it, re-upload with the overwrite confirmed, and confirm the change landed.

### Tests for User Story 2 ⚠️

> Write these first and confirm they fail before the implementation tasks below.

- [X] T023 [P] [US2] Extend `src/backend/tests/unit/test_story_service.py` — a content write preserves `id`/`createdBy`/`createdAt`/`published`/`lastPublishedAt`, replaces the authored set wholesale, regenerates `narrativeGuidance`, stamps `lastUpdatedBy` (an `oid`, never an email) and `contentUpdatedAt`, increments `contentVersion`, and leaves `can_publish` `False` again for a published story (FR-007, FR-009; quickstart.md scenario 13)
- [X] T024 [P] [US2] Extend `src/backend/tests/unit/test_story_draft_service.py` — `create_edit_draft` seeds every authored field plus `sourceStoryId`/`baseContentVersion`; `save_draft_to_story` applies and deletes the draft; a stale `baseContentVersion` raises without writing and leaves the draft intact; `generate_story` rejects an edit draft and `save_draft_to_story` rejects a creation draft (data-model.md → Mode rules)
- [X] T025 [P] [US2] Backend integration test in `src/backend/tests/integration/test_admin_story_edit_endpoint.py` — `POST …/{storyId}/edit-drafts` → `201`; `POST …/drafts/{draftId}/save` → `200 saved`; `409 stale_story` on a second save with the first's state intact; `422 not_ready` when a required element was cleared; `422 wrong_draft_mode` on saving a *creation* draft **and** on posting an *edit* draft to the existing `…/drafts/{draftId}/generate` endpoint (contracts/api.md → Related change — an edit must never mint a second story); `404` for a missing draft or story; `409 write_conflict` when the `_etag` precondition fails twice; a publish landing between the draft's seeding and its save still saving normally (never `409 stale_story`), with the new published state preserved; plus the standard `authorize_admin` unauthorized/forbidden shapes on both new endpoints (quickstart.md scenarios 5, 6, 7, 16; SC-003, SC-004)
- [X] T026 [P] [US2] Backend integration test in `src/backend/tests/integration/test_admin_story_import_endpoint.py` — `POST /api/manage/stories/import` takes the file's raw `configurationText` and returns `422 invalid_configuration` for text that is not valid JSON and for text that parses to a non-object (the server rejects these itself, without help from the SPA), `200 updated` for a confirmed id-matched overwrite, `422 confirmation_required` without a matching `confirmOverwriteStoryId`, `201 created` + `published: false` for an id-less file with a `title`, `422 title_required` without one, `404 story_not_found` for an unmatched id, `422 invalid_configuration` naming `name` for an id-carrying file whose `name` is missing or empty, and a download → re-upload → download round trip whose two files are byte-identical (the audit stamps that move live on the Story, never in the file); `409 write_conflict` when the `_etag` precondition fails twice, with nothing persisted; plus the standard `authorize_admin` unauthorized/forbidden shapes (quickstart.md scenarios 8, 9, 10, 11, 16; SC-002)
- [X] T027 [P] [US2] Extend `src/backend/tests/unit/test_play_session_service.py` with the FR-010 regression — a story edited mid-session is narrated from the edited configuration on the next turn; a session **saved before the edit and resumed after it** (`009-save-and-continue`) likewise narrates from the current configuration, not the one in force when it began; and `PlaySession` holds no copy of the configuration (quickstart.md scenarios 14 and 15; research.md §9). **The one exception to this section's fail-first rule**: FR-010 already holds in the shipped code, so T027 MUST PASS the moment it is written — a red T027 means the behavior regressed, not that an implementation task is outstanding
- [X] T028 [P] [US2] Frontend component test in `src/frontend/tests/components/StoryConfigUpload.test.jsx` — file picker, overwrite confirmation naming the target story, title prompt for an id-less file, each server rejection message surfaced verbatim, and the client's pre-flight tier rejecting — with a specific reason and no request sent — a file that is not valid JSON (naming the position), one that parses to a non-object, and one missing or emptying a required key (`name` on the overwrite path, `worldPrompt`, `characterTypes`, `completionCriteria.successConditions`). Assert the subset rule too: the component does **not** reject the content-rule cases (unknown key, duplicate character-type names, bad `rule`, non-positive integers) — it posts them and shows what the server says (contracts/api.md → Validation runs on both sides)
- [X] T029 [P] [US2] Frontend integration test in `src/frontend/tests/integration/admin_story_edit_flow.test.jsx` — reopen a story in the wizard pre-filled, use `Suggest`, `Save changes`, and see the reload-and-reapply message on a `409` (FR-003, FR-006)
- [X] T030 [P] [US2] Frontend integration test in `src/frontend/tests/integration/admin_story_import_flow.test.jsx` — upload with overwrite confirmation, id-less upload with a supplied title, and the rejection paths (FR-005)

### Implementation for User Story 2

- [X] T031 [US2] Add `apply_content_write(story, configuration, admin_oid, narrative_guidance)` and `StaleStoryError` to `src/backend/services/story_service.py` — preserve/replace/regenerate/stamp/increment per data-model.md → Content write, writing with the Cosmos `_etag` and `MatchConditions.IfNotModified` as `play_session_service.py` does (research.md §6). On `CosmosAccessConditionFailedError`, re-read the story and branch per contracts/api.md → Write conflicts: a changed `contentVersion` raises `StaleStoryError` on the save path (the import path re-applies instead, being exempt from FR-006), an unchanged one re-applies the write to the freshly read row — preserving a `published` flip that landed meanwhile — and retries once; a second precondition failure raises `WriteConflictError`, which T036 maps to `409 write_conflict`
- [X] T032 [US2] Add `import_configuration(configuration, admin_oid, confirm_overwrite_story_id, title)` to `src/backend/services/story_service.py` — route on the file's `id` per research.md §7's table (overwrite / `story_not_found` / create new with `published=False`), regenerating `narrativeGuidance` via `LLMService.generate_story_config` on every path (research.md §5). The create path builds the `Story` here directly, mirroring `create_story`'s field mapping (`published=False`, `contentUpdatedAt = createdAt`, `contentVersion = 1`, `lastUpdatedBy = None`), rather than widening `create_story(draft: StoryDraft, …)` — an import has no draft to give it; depends on T031
- [X] T033 [US2] Add `create_edit_draft(story, created_by)` to `src/backend/services/story_draft_service.py`, seeding the draft from the story's authored fields and pinning `sourceStoryId`/`baseContentVersion`
- [X] T034 [US2] Add `save_draft_to_story(draft_id, admin_oid)` to `src/backend/services/story_draft_service.py` — enforce the Completeness Rule, check `baseContentVersion` against the story's `contentVersion`, regenerate `narrativeGuidance`, call `apply_content_write`, then delete the draft; leave the draft intact on a stale rejection (depends on T031, T033)
- [X] T035 [US2] Add the draft-mode guards in `src/backend/services/story_draft_service.py` — `generate_story` refuses a draft carrying `sourceStoryId`, `save_draft_to_story` refuses a draft without one (depends on T034)
- [X] T036 [US2] Add the `create_edit_draft`, `save_draft`, and `import_story` handlers to `src/backend/api/admin/stories.py`, with `import_story` decoding the posted `configurationText` through `story_config_file.parse_text` (so malformed JSON is rejected here, server-side, not only in the browser) and mapping service errors to the exact `200`/`201`/`404`/`409 stale_story`/`409 write_conflict`/`422 not_ready`/`422 wrong_draft_mode`/`422 invalid_configuration`/`422 confirmation_required`/`422 title_required`/`502 generation_failed`/`429 rate_limited` shapes in contracts/api.md — **and** update the existing `generate_story_from_draft` handler in the same file to map T035's guard to `422 wrong_draft_mode` when the draft carries a `sourceStoryId` (the one pre-existing handler this feature changes; asserted by T025)
- [X] T037 [US2] Register `manage/stories/{storyId}/edit-drafts` (POST), `manage/stories/drafts/{draftId}/save` (POST), and `manage/stories/import` (POST) through the existing `_guarded` wrapper in `src/backend/function_app.py`
- [X] T038 [US2] Add `createEditDraft(token, storyId)`, `saveDraftToStory(token, draftId)`, and `importStoryConfiguration(token, body)` — `body` = `{ configurationText, confirmOverwriteStoryId?, title? }`, posting the file's own text rather than a re-serialized object — to `src/frontend/src/services/storyDraftService.js`
- [X] T039 [P] [US2] Create `src/frontend/src/components/Admin/StoryConfigUpload.jsx` — labelled file input; read the file as text and keep that text as what gets posted (`configurationText`), parsing a copy locally to drive the flow; run the pre-flight tier from contracts/api.md (not valid JSON with position, non-object, required key missing/empty) reporting a specific plain-language reason with no request sent; confirm the named overwrite target; prompt for a title when the file has no `id`; and surface every server rejection message verbatim. Keep the pre-flight a strict subset — no unknown-key, uniqueness, `rule`, or integer checks here; those belong to the one server-side validator
- [X] T040 [US2] Add edit mode to `src/frontend/src/pages/AdminStoryWizardPage.jsx` — open via `createEditDraft`, render the existing steps unchanged, replace the terminal action with `Save changes` calling `saveDraftToStory`, and show the reload-and-reapply message on `409 stale_story` (depends on T038)
- [X] T041 [US2] Add the lazy, `Administrator`-gated route `/admin/stories/:storyId/edit` in `src/frontend/src/App.jsx`
- [X] T042 [US2] Wire `StoryConfigUpload` and the per-row **Edit** link (to `/admin/stories/:storyId/edit`) into `src/frontend/src/pages/AdminPage.jsx` (FR-001, FR-005 — the story list is the upload entry point), and extend `src/frontend/tests/integration/admin_stories_list.test.jsx` with the Edit affordance assertion T012 deliberately left out (depends on T012 — same test file — on T022 and T039 — same page file as T022 — and on T041, which registers the route the link points at)

**Checkpoint**: Both user stories work independently — reviewing (US1) and editing via both the
wizard and the file round trip (US2).

---

## Phase 5: Polish & Cross-Cutting Concerns

- [X] T043 [P] Accessibility pass over `src/frontend/src/pages/AdminPage.jsx` and `src/frontend/src/pages/AdminStoryConfigurationPage.jsx` — semantic headings, labelled controls, keyboard operability, visible focus, meaningful button/link text, status conveyed as text not color alone (FR-012 — the styling exception explicitly does **not** cover accessibility). Per Principle I this is **asserted, not eyeballed**: add the assertions to the existing `admin_stories_list.test.jsx` and `admin_story_configuration_view.test.jsx` — every control reachable by role and accessible name (`getByRole`, never a test id or class selector), the viewer's scroll container focusable with an accessible name, and each row's status readable as text
- [X] T044 [P] Design-system **review** (a read of the diff, not a test) of the new/changed frontend files (`AdminPage.jsx`, `AdminStoryConfigurationPage.jsx`, `StoryPublishActions.jsx`, `StoryConfigUpload.jsx`) — confirm only existing classes (`.table`, `.tag`, `.btn*`, `.field`, `.hr`, `.dialog*`) and token-based styles are used, that the sole non-design-system addition is T020's permitted narrowly-scoped scroll-container rule, and that no off-system color, font, spacing, or radius value is introduced (plan.md → Complexity Tracking). It does **not** gate on anyone's judgment of visual quality — that is exactly what FR-012 defers
- [ ] T045 [P] Optional, **non-blocking** (Principle IX): walk quickstart.md's six-step manual walkthrough against a locally running app. This MUST NOT gate completion and may run at any point after Phase 4
- [X] T046 Run the full gate from [`quickstart.md`](./quickstart.md) → Definition of done — `pytest`, `npm --prefix src/frontend test`, `npm --prefix src/frontend run lint`, all green with no skips. **This is the last task in the feature** — every other task except T045 must be complete before it runs

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — **BLOCKS both user stories**
- **User Story 1 (Phase 3)**: Depends on Foundational only
- **User Story 2 (Phase 4)**: Depends on Foundational and is independently testable, but its final
  wiring task T042 depends on US1's T012 and T022 (the same two files) as well as on T041, so a
  single implementer working sequentially runs US2 after US1. See User Story Dependencies below
  for every file the two stories share
- **Polish (Phase 5)**: Depends on the user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: No dependencies on other stories. Delivers the MVP.
- **User Story 2 (P2)**: No *behavioral* dependency on US1 — its endpoints and services stand on
  their own. It does share four files with US1, so those edits are sequential rather than
  parallel: `src/backend/api/admin/stories.py` (T014 → T036), `src/backend/function_app.py`
  (T016 → T037), `src/frontend/src/services/storyDraftService.js` (T017 → T038), and
  `src/frontend/src/pages/AdminPage.jsx` (T022 → T042). Only T042 is a true ordering constraint
  (its Edit link needs T041's route); the other three are additive and collide at the file level
  only, so a two-implementer split must not put both stories' backends on one file at once.

### Key Within-Story Dependencies

- **Setup**: T002 after T001 — the green baseline is recorded before any test file is refactored
- **Phase 2**: T008 after T007 (same module). T003/T004 are written before T005–T008, but T004's
  excluded-key assertions only fail for the right reason once T005 lands
- **US1 backend**: T014 → T016 (register the route the handler backs). T015 asserts behavior T005
  already delivered — it needs no production code and passes as soon as Phase 2 is done
- **US1 frontend — strictly sequential, no `[P]` inside it**: T017 → T020 → T021 → T022.
  T019 after T018 (StepPublish renders the extracted component); T022 also after T018
- **US2 backend**: T032 after T031; T034 after T031 and T033; T035 after T034; T036 after
  T031–T035 (the handlers call the services); T037 after T036
- **US2 frontend**: T040 after T038; T042 after T012, T022, T039 **and T041** — neither the
  upload control nor the per-row Edit link may ship before the route it points at, which is what
  keeps US1 deliverable on its own
- **Polish**: T043 after T042 (it adds assertions to the same test files T011/T012/T042 touch);
  T046 last of everything

### Parallel Opportunities

- **Phase 2**: T003, T004 (tests) in parallel; then T005, T006 in parallel; T007→T008 sequential
- **Phase 3**: all five tests (T009–T013) in parallel; T018 in parallel with the backend tasks
  T014–T016. The frontend chain T017 → T020 → T021 → T022 is sequential — only T018 is `[P]`
- **Phase 4**: all eight tests (T023–T030) in parallel; T033 may run alongside T031 (different
  service modules, both waiting only on Phase 2); T039 in parallel with the backend chain
  T031–T037
- **Phase 5**: T043, T044, T045 in parallel; T046 last
- **Across stories**: with two implementers, one can take US1's frontend while the other takes
  US2's backend chain immediately after Phase 2

---

## Parallel Example: User Story 1

```bash
# Launch all User Story 1 tests together:
Task: "Backend integration test in src/backend/tests/integration/test_admin_story_configuration_endpoint.py"
Task: "Component test in src/frontend/tests/components/StoryPublishActions.test.jsx"
Task: "Integration test in src/frontend/tests/integration/admin_story_configuration_view.test.jsx"
Task: "Extend src/frontend/tests/integration/admin_stories_list.test.jsx"
Task: "Extend src/frontend/tests/integration/admin_story_publish_flow.test.jsx"

# Then the genuinely independent implementation work. The viewer is NOT in here:
# T017 → T020 → T021 → T022 is a sequential chain, not a parallel batch.
Task: "Extract src/frontend/src/components/Admin/StoryPublishActions.jsx from StepPublish.jsx"
Task: "Add the get_story_configuration handler in src/backend/api/admin/stories.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Phase 1: Setup (T001–T002)
2. Phase 2: Foundational (T003–T008) — **blocks everything**
3. Phase 3: User Story 1 (T009–T022) — five tests in parallel, then T014–T016 and T018/T019
   alongside the sequential viewer chain T017 → T020 → T021 → T022
4. **STOP and VALIDATE**: story list with status, publish/unpublish from the list, the read-only
   viewer, and a download whose bytes match the viewer (SC-001)
5. Demo/deploy if ready — reviewing and auditing content is valuable on its own

### Incremental Delivery

1. Setup + Foundational → the file format and model fields exist
2. + User Story 1 → review, view, download, publish from the list (**MVP**)
3. + User Story 2 → wizard edit with stale-save rejection, and the download/edit/re-upload round trip
4. + Polish → accessibility and design-system audits, full green gate

---

## Notes

- `[P]` = different files, no dependencies on incomplete tasks
- Tests are required here by FR-008 and Principle I — write them first in each phase and confirm
  they fail before implementing
- No new runtime dependency is added to `src/backend/requirements.txt` or
  `src/frontend/package.json`; no new Cosmos container is created
- FR-010 needs no production code — T027 is a regression test pinning behavior that already holds
  (research.md §9)
- Per Principle IX, **no blocking human-acceptance gate** applies to this feature; T045 is
  informational only
- This feature's two screens are traceable to the **Administrator — stories & configuration**
  screen contract added in constitution v2.1.0 (2026-09-07); FR-012 defers their styling, not
  their required affordances or the accessibility bar
- Commit after each task or logical group; stop at either checkpoint to validate a story
