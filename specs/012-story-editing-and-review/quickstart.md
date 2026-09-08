# Quickstart: Validating Story Editing and Review

**Date**: 2026-09-06

**Feature**: Story Editing and Review (`012-story-editing-and-review`)

How to run and prove this feature end to end. Shapes are not repeated here — see
[`contracts/api.md`](./contracts/api.md) for request/response detail and
[`data-model.md`](./data-model.md) for the field rules each scenario asserts.

## Prerequisites

- The worktree's devcontainer (`bin/wt 012-story-editing-and-review`), per
  [`docs/WORKTREE_CONTAINER_WORKFLOW.md`](../../docs/WORKTREE_CONTAINER_WORKFLOW.md).
- Backend deps: `pip install -r src/backend/requirements.txt -r src/backend/requirements-dev.txt`
- Frontend deps: `npm --prefix src/frontend ci`
- No Azure resources are needed: backend tests drive the handlers directly with the existing
  in-memory Cosmos and LLM stubs (`src/backend/tests/`), per Principle I.

## Run the automated suites

```bash
# Backend — whole suite
pytest

# Backend — this feature's tests only
pytest src/backend/tests/unit/test_story_config_file.py \
       src/backend/tests/unit/test_story_service.py \
       src/backend/tests/unit/test_story_draft_service.py \
       src/backend/tests/integration/test_admin_story_configuration_endpoint.py \
       src/backend/tests/integration/test_admin_story_import_endpoint.py \
       src/backend/tests/integration/test_admin_story_edit_endpoint.py

# Frontend — whole suite / this feature's tests
npm --prefix src/frontend test
npm --prefix src/frontend test -- admin_story_edit_flow admin_story_configuration_view admin_story_import_flow
npm --prefix src/frontend run lint
```

Expected: all green, no skips. A failing run blocks merge (Principle V).

## Validation scenarios

Each row is one of FR-008's required maintenance actions. "Where" names the automated test
that owns it; the manual column is the equivalent check against a running app.

| # | Scenario (FR / SC) | Automated test | Expected outcome |
|---|---|---|---|
| 1 | Story list shows every story with published status (FR-001) | `tests/integration/admin_stories_list.test.jsx` (extend) | Both a published and an unpublished story appear, status paired with text, not color alone. |
| 2 | Publish/unpublish from the list (FR-011) | `tests/integration/admin_story_publish_flow.test.jsx` (extend) | Same endpoints, same 409 gate explanation and unpublish confirmation as the wizard step. |
| 3 | Read-only configuration viewer matches the download byte-for-byte (FR-002, SC-001) | `test_admin_story_configuration_endpoint.py` + `admin_story_configuration_view.test.jsx` | The viewer renders the response text verbatim; the download saves that same string. |
| 4 | Download contains `id` + authored fields and **no** system-managed fields (FR-004) | `test_story_config_file.py` | `published`, timestamps, `createdBy`/`lastUpdatedBy`, `lastTestPlayedAt` are absent; `id`, `narrativeGuidance` and `startingPoint` are present (revised 2026-09-08, #270/#271). |
| 5 | Wizard edit save updates in place, untouched fields survive (FR-003, FR-009, SC-003) | `test_admin_story_edit_endpoint.py` + `admin_story_edit_flow.test.jsx` | `id`/`createdBy`/`createdAt`/`published` preserved; `lastUpdatedBy`/`contentUpdatedAt` stamped; `contentVersion` +1. |
| 6 | Stale wizard save is rejected (FR-006, SC-004) | `test_admin_story_edit_endpoint.py` | Second save returns `409 stale_story`; the first save's state is intact; the draft survives. |
| 7 | Cleared required element is rejected with a reason (Edge Cases) | `test_admin_story_edit_endpoint.py` | `422 not_ready`; the story is unchanged. |
| 8 | Re-upload with a matching `id` overwrites, confirmation required (FR-005, SC-002) | `test_admin_story_import_endpoint.py` + `admin_story_import_flow.test.jsx` | Confirmed ⇒ `200 updated`; unconfirmed ⇒ `422 confirmation_required` and no write. |
| 9 | Round-trip with no edits is a clean no-op (Edge Cases) | `test_admin_story_import_endpoint.py` | Download → re-upload → download produces a **byte-identical** file — the audit stamps that move (`lastUpdatedBy`, `contentUpdatedAt`, `contentVersion`) are on the Story, never in the file. |
| 10 | Id-less file uploads as a new story, title required (FR-005, `011` FR-005/007) | `test_admin_story_import_endpoint.py` | No title ⇒ `422 title_required`; with a title ⇒ `201 created`, `published: false`, source story untouched. |
| 11 | File whose `id` matches nothing is rejected (Edge Cases) | `test_admin_story_import_endpoint.py` | `404 story_not_found`; nothing is created under that id. |
| 12 | Invalid file is rejected with a specific reason (`011` FR-002/003) | `test_story_config_file.py` + `test_admin_story_import_endpoint.py` + `StoryConfigUpload.test.jsx` | Malformed JSON, non-object payload, duplicate character type names, missing `completionCriteria`, unknown key, nameless overwrite — each names the offending element; nothing persisted. Every one of them is rejected **server-side**; the client additionally rejects the parse/shape cases (malformed JSON, non-object, a missing or empty required key) ahead of the request as fast feedback, and defers the content rules to the server (contracts/api.md → Validation runs on both sides). |
| 13 | Editing a published story leaves it published and re-arms the gate (FR-007, FR-009, `017` FR-003/004) | `test_story_service.py` | `published` stays `true`; `can_publish` is `false` again until a new test play. |
| 14 | An in-flight session picks up the edit on its next turn (FR-010) | `tests/unit/test_play_session_service.py` (regression) | The next turn narrates from the edited configuration; no snapshot is stored on the session. |
| 15 | A **resumed** session picks up an edit made while it was away (FR-010, `009-save-and-continue`) | `tests/unit/test_play_session_service.py` (regression) | A session saved before the edit and resumed after it narrates from the current configuration, not the one in force when it began. |
| 16 | Every new endpoint refuses an unauthenticated or non-administrator caller (Principle II) | `test_admin_story_configuration_endpoint.py`, `test_admin_story_edit_endpoint.py`, `test_admin_story_import_endpoint.py` | The standard `authorize_admin` unauthorized/forbidden shapes, asserted on the three writing endpoints as well as the read one. |
| 17 | A concurrent write is resolved, not misreported (FR-006, contracts/api.md → Write conflicts) | `test_admin_story_edit_endpoint.py` + `test_admin_story_import_endpoint.py` | A publish landing mid-save is re-applied and the save succeeds with the new published state; a repeated `_etag` precondition failure returns `409 write_conflict` with nothing persisted. |

## Manual walkthrough (optional, non-blocking — Principle IX)

```bash
# Terminal 1
cd src/backend && func start
# Terminal 2
npm --prefix src/frontend run dev
```

1. Sign in as an administrator → **Stories**. Confirm each story shows its status, and that
   publish/unpublish works from the row (unpublish asks first).
2. Open a story → the configuration viewer. Click **Download**, open the saved file, and
   confirm it matches the screen exactly.
3. Click **Edit** → the wizard opens pre-filled. Use **Suggest** on the world & setting step,
   then **Save changes**. Reopen the viewer and confirm the change landed and nothing else moved.
4. Open the same story in two browser tabs, save in the first, then save in the second →
   the second is refused with the reload-and-reapply message.
5. Edit the downloaded file, upload it from the story list, confirm the named overwrite target,
   and check the viewer reflects the edit.
6. Delete the `"id"` line from the file, upload again, supply a title → a new, unpublished story
   appears and the original is unchanged.

Per Principle IX this walkthrough is informational: the automated suites above are what gate
completion.

## Definition of done

- Every row in the scenario table has a passing automated test (FR-008, Principle I).
- `pytest`, `npm --prefix src/frontend test`, and `npm --prefix src/frontend run lint` are green.
- The new screens introduce no off-system color, font, or spacing values, and are keyboard
  operable with semantic markup (FR-012 — the styling exception does not extend to accessibility).
  The accessibility bar is asserted in the frontend tests (T043), not only reviewed by eye: roles
  and accessible names for every control, status as text, and a keyboard-reachable viewer.
- The viewer's configuration pane scrolls within itself and is keyboard-focusable; no
  configuration, however long or wide, makes the page scroll horizontally (plan.md → Constraints).
