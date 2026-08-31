# Quickstart: Validate Story Creation

**Date**: 2026-08-29 | **Revised**: 2026-08-31 (Session 2026-08-30 Clarifications: explicit Save/Abandon/Finished, local-storage draft, blob-stored cover image)

**Feature**: Story Creation (004-story-creation)

This guide provides step-by-step validation scenarios confirming story creation works end-to-end. See [contracts/api.md](contracts/api.md) for exact request/response shapes and [data-model.md](data-model.md) for the `Story` schema.

---

## Prerequisites

1. Cosmos DB `stories` container exists (per `007-azure-infrastructure-provisioning` and data-model.md's Storage Model). There is no `storyDrafts` container in this design.
2. Backend deployed (or running locally) with `POST/GET /api/manage/stories`, `GET/PATCH/DELETE /api/manage/stories/{storyId}`, `POST /api/manage/stories/{storyId}/cover-image`, `POST /api/manage/stories/suggest-outline`.
3. The Azure OpenAI deployed model is reachable from the backend (Managed Identity, per `007-azure-infrastructure-provisioning`) for Tab 02's one-shot outline suggestion; locally, `llm_service.py` can be run against a real endpoint the developer has access to, or exercised via its mocked unit tests only.
4. The blob storage account + `assets` container (also provisioned by `007`) are reachable via Managed Identity, for cover image uploads.
5. A signed-in Administrator account (per `002-login-and-access-control` / `003-account-provisioning-done`).
6. Frontend running with the "New story" wizard reachable from `/admin` (the Stories page).

---

## Scenario 1: Save Creates, Then Updates, a Story (User Story 1, FR-001–FR-004, FR-012)

**Objective**: An administrator goes from an empty state to a persisted, unpublished story using explicit Save, and a later Save updates the same record.

**Steps**:
1. As the Administrator, open `/admin/stories/new`. Enter a story name on Tab 01 and hit **Save**.
2. Confirm the response is `POST /api/manage/stories` → `201 Created`, with a `story.id`, `story.createdBy`/`story.updatedBy` equal to the signed-in administrator's email, and `story.published: false`.
3. Switch to Tab 02, fill in an outline (typed directly, or via **Suggest** — see Scenario 4), rules, at least one character type, and at least one completion criterion. Hit **Save** again.
4. Confirm this second Save is a `PATCH /api/manage/stories/{storyId}` → `200 OK`, using the *same* `story.id` from step 2, with `updatedAt` refreshed and `characterTypes`/`completionCriteria` populated.
5. `GET /api/manage/stories/{storyId}` and confirm the full configuration matches what was entered.

**Expected**: A single `Story` document exists in Cosmos, created on the first Save and updated (never re-created) on the second (FR-004; Acceptance Scenarios 2–3).

---

## Scenario 2: Tab Switching Never Loses Unsaved Work (User Story 2, FR-010)

**Objective**: Field values entered on one tab survive navigating to another tab and back, before any Save.

**Steps**:
1. On Tab 01, enter a story name. Do not hit Save.
2. Switch to Tab 02 and enter an outline. Do not hit Save.
3. Switch back to Tab 01.
4. Reload the page entirely (simulating a browser refresh).

**Expected**: The name (step 1) and outline (step 2) are both still present after step 3 and after the reload in step 4 — held the whole time in browser local storage (`llmdungeon.storyWizard.draft`), not sent to the backend until Save (SC-004). No `POST`/`PATCH` request has been made yet at any point in this scenario.

---

## Scenario 3: Abandon Discards Everything; Finished Leaves Saved Data Alone (User Story 3, FR-013–FR-015)

**Objective**: Abandon and Finished have the effects spec.md describes, each behind a confirmation.

**Steps (Abandon, previously saved)**:
1. Save a story at least once (so a `Story` record exists), then hit **Abandon**.
2. Confirm a confirmation prompt appears; dismissing it (e.g. "Keep working") leaves the record untouched and the administrator still in the wizard.
3. Hit **Abandon** again and confirm it this time.

**Expected**: `DELETE /api/manage/stories/{storyId}` is called, `GET /api/manage/stories/{storyId}` now returns `404`, the local-storage draft is cleared, and the administrator is redirected to `/admin` (SC-006, Acceptance Scenarios 1–4).

**Steps (Abandon, never saved)**:
1. Start a fresh wizard session, type into a field, but never hit Save. Hit **Abandon** and confirm.

**Expected**: No `DELETE` request is meaningfully destructive (no story ever existed to delete — the endpoint is idempotent regardless), the local-storage draft is cleared, and the administrator is redirected to `/admin` (Edge Cases).

**Steps (Finished)**:
1. Save a story (fully or only partially filled in). Hit **Finished** and confirm.

**Expected**: Nothing is deleted — `GET /api/manage/stories/{storyId}` still returns the saved story — the local-storage draft is cleared, and the administrator is redirected to `/admin` (which doubles as the stories list; Acceptance Scenario 5).

---

## Scenario 4: Tab 02's One-Shot Outline Suggestion (FR-003)

**Objective**: Suggest is a single generation, not an ongoing conversation, and never destroys existing input on failure.

**Steps**:
1. On Tab 02, type an idea or guiding question into the Suggest input and click **Suggest**.
2. Confirm `POST /api/manage/stories/suggest-outline` is called once, and its `outline` response replaces the outline text box's contents.
3. Edit the outline text further by hand — it remains freely editable.
4. Repeat with the Foundry/Azure OpenAI call mocked/forced to fail.

**Expected**: Step 2 is a single request/response pair with no follow-up turns. In step 4, the existing outline text box contents are left untouched and an error is surfaced, per Edge Cases.

---

## Scenario 5: Single Character Type Is Accepted (Edge Cases)

**Steps**:
1. Save a story with exactly one `characterTypes` entry.

**Expected**: Save succeeds; the persisted `Story.characterTypes` has exactly one entry — a story is not required to offer a choice of more than one.

---

## Scenario 6: Cover Image Upload (FR-009)

**Steps**:
1. On Tab 01, select an image file from the administrator's device and hit **Save**.
2. Confirm the field Save (`POST`/`PATCH /api/manage/stories`) happens first (creating the story if it didn't already exist), then `POST /api/manage/stories/{storyId}/cover-image` uploads the file.
3. `GET /api/manage/stories/{storyId}` and confirm `coverImageUrl` is a blob storage URL.

**Expected**: The story record never stores a raw client-supplied URL or the image bytes — only the blob reference the backend itself produced after the upload.
