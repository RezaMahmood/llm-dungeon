# Quickstart: Validate Story Creation

**Date**: 2026-08-29

**Feature**: Story Creation (004-story-creation)

This guide provides step-by-step validation scenarios confirming story creation works end-to-end. See [contracts/api.md](contracts/api.md) for exact request/response shapes and [data-model.md](data-model.md) for the draft/story schema.

---

## Prerequisites

1. Cosmos DB `storyDrafts` (TTL-enabled) and `stories` containers exist (per `007-azure-infrastructure-provisioning` and data-model.md's Storage Model).
2. Backend deployed (or running locally) with `/api/admin/stories/drafts` (POST/GET/PATCH), `/api/admin/stories/drafts/{id}/messages` (POST), `/api/admin/stories` (GET), `/api/admin/stories/{id}` (GET).
3. The Azure AI Foundry deployed model is reachable from the backend (Managed Identity, per `007-azure-infrastructure-provisioning`); locally, `llm_service.py` can be run against a real Foundry endpoint the developer has access to, or exercised via its mocked unit tests only.
4. A signed-in Administrator account (per `002-login-and-access-control` / `003-account-provisioning`).
5. Frontend running with the "New story" wizard reachable from the admin story list.

---

## Scenario 1: Complete a Story Through the Guided Wizard (User Story 1, FR-001–FR-004, FR-008)

**Objective**: An administrator goes from an empty state to a complete, persisted, unpublished story in one sitting, using natural language plus the dedicated character-type/completion-criteria fields.

**Steps**:
1. As the Administrator, start a new story-creation session: `POST /api/admin/stories/drafts` with `{"idea": "A half-abandoned lighthouse on a cold northern cove in 1908..."}`.
2. Confirm the response includes a `draft.id`, a merged `worldPrompt` reflecting the idea, and a system guiding question in `exchanges`.
3. Answer the guiding question(s) via `POST /api/admin/stories/drafts/{draftId}/messages` until the system stops asking about setting/plot.
4. Add at least one character type and the story's completion criteria via `PATCH /api/admin/stories/drafts/{draftId}` (per contracts/api.md's example body).
5. Observe that the same `PATCH` response (once `worldPrompt`, `characterTypes`, and `completionCriteria.successConditions` are all non-empty) returns `"status": "generated"` with a `storyId`.
6. Fetch `GET /api/admin/stories/{storyId}` and confirm: `published: false`, `characterTypes` has ≥1 entry, `completionCriteria.successConditions` has ≥1 entry, and `narrativeGuidance` is non-empty.

**Expected**: A `Story` document exists in Cosmos with `published: false`; no manual "save" action was taken beyond answering questions and filling the two dedicated fields (FR-004). Corresponds to Acceptance Scenarios 1–2 and SC-001/SC-003.

---

## Scenario 2: Abandoned Session Persists Nothing (FR-005, SC-002)

**Objective**: Starting a session and walking away never produces a `Story`.

**Steps**:
1. `POST /api/admin/stories/drafts` with a partial idea (no character types or completion criteria supplied).
2. Confirm `GET /api/admin/stories` does not list anything derived from this draft.
3. Do not send any further requests for this draft. Wait past the draft's TTL window (or, in a test environment, use a shortened TTL override — research.md §3).
4. `GET /api/admin/stories/drafts/{draftId}` now returns `404 Not Found`.

**Expected**: No `Story` was ever created for this session, and the draft itself is gone (Edge Cases: abandoned session; Acceptance Scenario 3).

---

## Scenario 3: Starting Fresh Does Not Resume an Abandoned Session (Acceptance Scenario 4)

**Steps**:
1. Repeat Scenario 2 steps 1–2 (start a draft, do not complete it, do not wait for TTL expiry yet).
2. `POST /api/admin/stories/drafts` again (a second, independent call, with a different or empty `idea`).

**Expected**: The second call returns a **new** `draft.id`, distinct from the first, with empty fields (or only what the new `idea` seeded) — it does not surface or merge the first draft's exchanges/fields, and per Clarifications, both drafts may coexist simultaneously without either affecting the other.

---

## Scenario 4: Malformed LLM Output Is Never Persisted (Edge Cases)

**Objective**: If the Foundry generation call fails validation, no broken `Story` reaches Cosmos.

**Steps**:
1. Bring a draft to the point where the Completeness Rule is met (Scenario 1, steps 1–4), but with the Foundry client's generation call mocked/forced to return an empty or schema-invalid response (test-only setup — see research.md §4).
2. Submit the completing `PATCH` or `messages` call.

**Expected**: Response is `502 Bad Gateway` with `error: "generation_failed"`; `GET /api/admin/stories` shows no new entry; `GET /api/admin/stories/drafts/{draftId}` still returns the draft, unchanged, so the administrator can retry (e.g., by resubmitting the same completing call once the underlying issue is resolved).

---

## Scenario 5: Single Character Type Is Accepted (Edge Cases)

**Steps**:
1. Bring a draft to completeness with exactly one `characterTypes` entry.

**Expected**: Generation succeeds; the persisted `Story.characterTypes` has exactly one entry — a story is not required to offer a choice of more than one.
