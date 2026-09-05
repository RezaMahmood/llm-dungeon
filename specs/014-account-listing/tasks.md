---

description: "Task list for Account Listing (014-account-listing)"
---

# Tasks: Account Listing

**Input**: Design documents from `/workspaces/.worktrees/014-account-listing/specs/014-account-listing/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, quickstart.md

**Tests**: Included — FR-004 explicitly requires an automated test for each distinct listing outcome, and Constitution Principle I is NON-NEGOTIABLE for this repo.

**Organization**: This feature has a single user story (US1 — Administrator Views Existing Provisioned Accounts, P1). Most of the underlying endpoint/component already exists from `003-account-provisioning-done`; tasks below are the actual remaining delta plus the constitution's required design-agreement and acceptance gates.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Maps the task to US1
- File paths are exact, relative to the repo root (`/workspaces/.worktrees/014-account-listing`)

---

## Phase 1: Setup

No new project setup is required — this feature modifies two existing files (`account_provisioning_service.py`, `AccountList.jsx`) in the existing `003-account-provisioning-done` backend/frontend structure. Nothing to do in this phase.

---

## Phase 2: Foundational

No new blocking infrastructure — the `GET /api/manage/accounts` endpoint, `AccountProvisioningService`, and `ProvisionedAccountEntry` model already exist and require no schema/index change (see `data-model.md`). Nothing to do in this phase.

---

## Phase 3: User Story 1 - Administrator Views Existing Provisioned Accounts (Priority: P1) 🎯 MVP

**Goal**: An administrator sees every provisioned account's email and role(s), sorted alphabetically by email, with a "pending first sign-in" indicator on any entry that hasn't completed sign-in yet, and non-administrators are denied access.

**Independent Test**: With at least two provisioned entries (one bound, one unbound) seeded, sign in as an Administrator, view the account list, and verify: both entries appear with correct roles, they're in alphabetical-by-email order, the unbound one shows "Pending first sign-in", and a non-administrator hitting the same interface/endpoint is denied.

### Design agreement (Constitution Principle XI — MUST precede implementation below)

- [X] T001 [US1] Get explicit user/product-owner sign-off on the "Pending first sign-in" label wording and its placement in the existing status column of `src/frontend/src/components/Admin/AccountList.jsx` (replacing "Not yet signed in"), since `specs/designs/05-admin-users.html` does not currently depict this indicator. Record the agreed copy before starting T004. Do not proceed to T004 until this is confirmed.
  - Confirmed by requesting user 2026-09-05: use "Pending first sign-in", same status cell/column, no placement change.

### Tests for User Story 1 (write first; confirm they fail before implementing T003/T004)

- [X] T002 [P] [US1] Add `test_list_all_sorts_entries_alphabetically_by_email` to `src/backend/tests/unit/test_account_provisioning_service.py` (near the existing `test_list_all_returns_every_entry` in the `# --- list_all ---` section): seed the mocked `cosmos.query.return_value` with entries out of order (e.g. `"zed@example.com"`, `"admin@example.com"`, `"mid@example.com"`) and assert `service.list_all()` returns them ascending by `.email`.
- [X] T003 [P] [US1] Extend `test_list_accounts_returns_every_entry_with_email_and_roles` in `src/backend/tests/integration/test_admin_accounts_endpoint.py` (or add a new adjacent test) to assert the `accounts` array in the `GET /api/manage/accounts` response is alphabetically ordered by `email` when the underlying service returns entries out of order — since `list_accounts` calls `service.list_all()` (mocked here), set `service.list_all.return_value` in an unsorted order matching what a real sorted `list_all` would return, and assert the response preserves that order (this locks in the contract from `contracts/api.md`, not just the service unit).
- [X] T004 [P] [US1] Update the existing test `shows bound status as Signed in / Not yet signed in` in `src/frontend/tests/components/AccountList.test.jsx` to assert `"Pending first sign-in"` (per T001's agreed copy) instead of `"Not yet signed in"` for a `bound: false` account, and rename the test to match (e.g. `"shows bound status as Signed in / Pending first sign-in"`).

### Implementation for User Story 1

- [X] T005 [US1] In `src/backend/services/account_provisioning_service.py`, update `list_all()` to return entries sorted ascending by `.email` (e.g. `return sorted((ProvisionedAccountEntry.from_dict(row) for row in results), key=lambda e: e.email)`), satisfying FR-001 and T002/T003. (Depends on T002, T003 existing and failing first.)
- [X] T006 [US1] In `src/frontend/src/components/Admin/AccountList.jsx`, change the status cell's unbound-state text from `"Not yet signed in"` to `"Pending first sign-in"` (the `account.bound ? "Signed in" : "Not yet signed in"` line), satisfying FR-005 and T004. (Depends on T001, T004.)

### Verification for User Story 1

- [X] T007 [US1] Run `cd src/backend && pytest tests/unit/test_account_provisioning_service.py tests/integration/test_admin_accounts_endpoint.py -v` and confirm all tests pass, including T002/T003.
- [X] T008 [US1] Run `cd src/frontend && npm test -- AccountList` and confirm all tests pass, including T004.
- [ ] T009 [US1] Run through `quickstart.md`'s "Frontend validation" and "Access-control validation" steps manually in a local browser session (sorted order, pending indicator, non-administrator denial) to confirm end-to-end behavior beyond the automated suites.

**Checkpoint**: User Story 1 is fully functional and independently testable — the account list is sorted, shows the pending indicator, and access is still gated to administrators.

---

## Phase 4: Polish & Final Acceptance

- [X] T010 Update `specs/designs/README.md` and/or a short note alongside `specs/designs/05-admin-users.html` if the T001 sign-off changes what that screen contract documents about the status column, so the screen contract stays traceable per the constitution's Governance section (only if T001's agreed wording/placement differs from what's already implicit in the mockup — skip if no doc drift exists).
- [ ] T011 Final user-verified acceptance (Constitution Principle IX, NON-NEGOTIABLE): the requesting user or product owner signs in as an Administrator against the real deployed (or most representative available) environment, views the account list, and confirms alphabetical ordering, the "Pending first sign-in" indicator, and non-administrator denial all behave as intended. This task is not complete until the requesting user/product owner has explicitly confirmed it — not on the strength of the implementing agent's own testing (T007-T009).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: None — no tasks.
- **Foundational (Phase 2)**: None — no tasks.
- **User Story 1 (Phase 3)**: T001 (design agreement) MUST precede T004 and T006. T002/T003/T004 (tests) MUST be written and failing before T005/T006 (implementation). T007-T009 (verification) depend on T005/T006.
- **Polish (Phase 4)**: T010 depends on T001's outcome. T011 depends on Phase 3 being fully complete (T001-T009).

### Within User Story 1

- T001 → T004, T006
- T002, T003, T004 → T005, T006 (respectively — T002/T003 gate the backend sort change in T005; T004 gates the frontend copy change in T006)
- T005, T006 → T007, T008, T009

### Parallel Opportunities

- T002, T003, T004 can all run in parallel (different files: two backend test files, one frontend test file) once T001 is resolved (T004 needs T001's agreed copy; T002/T003 don't depend on T001 and can start immediately).
- T005 and T006 can run in parallel once their respective tests exist (different files, backend vs. frontend).

---

## Parallel Example: User Story 1

```bash
# After T001 sign-off, launch all three test-writing tasks together:
Task: "Add test_list_all_sorts_entries_alphabetically_by_email in src/backend/tests/unit/test_account_provisioning_service.py"
Task: "Extend list-accounts ordering assertion in src/backend/tests/integration/test_admin_accounts_endpoint.py"
Task: "Update AccountList.test.jsx bound-status test to expect 'Pending first sign-in'"

# Then launch both implementation tasks together:
Task: "Sort list_all() by email in src/backend/services/account_provisioning_service.py"
Task: "Change unbound-status label in src/frontend/src/components/Admin/AccountList.jsx"
```

---

## Implementation Strategy

### MVP First (and Only) Scope

This feature has a single P1 user story with no smaller MVP slice available — the sort-order fix and the pending-indicator wording are both required by FR-001/FR-005 and both are small. Deliver Phase 3 in full, then Phase 4's acceptance gate.

1. Complete T001 (design sign-off) — required before any implementation.
2. Write T002-T004 (tests), confirm they fail.
3. Implement T005-T006.
4. Verify via T007-T009.
5. Close with T010 (if needed) and T011 (user-verified acceptance) before considering the feature done.
