---

description: "Task list for Account Provisioning (003-account-provisioning)"
---

# Tasks: Account Provisioning

**Input**: Design documents from `/specs/003-account-provisioning/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, quickstart.md

**Tests**: Explicitly required — spec.md's FR-011 and the constitution's Principle I (Meaningful, Automated Testing, NON-NEGOTIABLE) both mandate an automated test for every distinct outcome. Test tasks are included throughout.

**Organization**: Tasks are grouped by user story (spec.md: US1 = P1 seed bootstrap, US2 = P2 add account, US3 = P3 view accounts). Foundational work also migrates the already-shipped `002-login-and-access-control` backend off its oid-only data model, per plan.md's Summary and research.md §3 — this is required by FR-006/FR-007, not incidental scope creep.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no same-phase dependency)
- **[Story]**: US1 / US2 / US3 — omitted for Setup, Foundational, and Polish tasks

## Path Conventions

Existing web-application layout: `src/backend/` (Python Azure Functions) + `src/frontend/` (React/Vite), per plan.md's Project Structure.

---

## Phase 1: Setup

**Purpose**: Add the one new dependency and the two new configuration values this feature needs.

- [X] T001 [P] Add `pyisemail` to `src/backend/requirements.txt` (RFC 5322 email validation — research.md §1)
- [X] T002 [P] Add `PROVISIONED_ACCOUNTS_CONTAINER = "provisionedAccountEntries"` and `SEED_ADMIN_EMAIL = os.environ.get("SEED_ADMIN_EMAIL", "")` to `src/backend/config.py`; leave the existing `ALLOW_LIST_CONTAINER`/`CAPABILITY_CONTAINER` constants in place for now (removed in Polish, once nothing references them)

**Checkpoint**: Dependency and configuration available for Foundational work.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Introduce the consolidated `ProvisionedAccountEntry` model and `AccountProvisioningService`, and migrate every existing consumer of 002's oid-keyed `AllowListService`/`CapabilityService` onto it (data-model.md, research.md §3). This must complete before any user story is wired up to real request handlers.

**⚠️ CRITICAL**: No user-story implementation task may run until this phase is complete.

- [X] T003 [P] Create `ProvisionedAccountEntry` in `src/backend/models/provisioned_account_entry.py` per data-model.md's schema: `email`/`id` (lowercased, identical), `roles` (non-empty list drawn from `Player`/`Administrator`), `objectId` (nullable), `dateAdded`, `addedBy`, `dateBound` (nullable); include `to_dict`/`from_dict` matching the existing model style (see `src/backend/models/allow_list_entry.py` for the pattern being replaced)
- [X] T004 Create `AccountProvisioningService` in `src/backend/services/account_provisioning_service.py` with `get_by_email(email) -> ProvisionedAccountEntry | None` (point read by lowercased email) and `authorize_sign_in(email, oid) -> tuple[bool, ProvisionedAccountEntry | None]` implementing FR-006/FR-007's bind-on-first-sign-in / verify-bound-oid logic (no entry → `(False, None)`; entry with `objectId is None` → bind `objectId`/`dateBound`, persist, return `(True, entry)`; entry with matching `objectId` → `(True, entry)`; entry with mismatched `objectId` → `(False, None)`), and `ensure_seed_administrator(email) -> None` (FR-001: create-if-absent only — a point read first, skip silently if an entry already exists, so it never clobbers roles an admin has since merged in) — depends on T003
- [X] T005 [P] Modify `src/backend/services/auth_service.py`: extract the `email` claim from the validated token alongside `oid`; `validate_token` now returns `(is_valid, user_oid, email, error_message)` (research.md §2 — use the `email` claim, not `preferred_username`)
- [X] T006 Modify `src/backend/api/auth/middleware.py`: add `authenticate_with_email(req) -> tuple[bool, str|None, str|None, str|None]` (is_valid, user_oid, email, error) built on T005's new `validate_token` return shape; keep the existing `authenticate(req)` (3-tuple: is_valid, user_oid, error) unchanged and working, so unrelated call sites outside this feature's scope (e.g. `src/backend/api/manage/stories.py`) need no changes — depends on T005
- [X] T007 Modify `src/backend/api/admin/middleware.py`: `authorize_admin()` now calls `authenticate_with_email` (T006) and `AccountProvisioningService.authorize_sign_in(email, oid)` (T004) in place of `AllowListService`/`CapabilityService`, checking `"Administrator" in entry.roles`; keep its external return shape `(is_authorized, user_oid, error_response)` unchanged so `src/backend/api/manage/stories.py` needs no changes — depends on T004, T006
- [X] T008 Modify `src/backend/api/game/start.py` (unrelated `008-core-gameplay` placeholder, updated only because this feature removes the services it currently imports): replace its direct `AllowListService`/`CapabilityService` usage with `authenticate_with_email` (T006) + `AccountProvisioningService.authorize_sign_in` (T004), checking `"Player" in entry.roles` — depends on T004, T006
- [X] T009 Modify `src/backend/function_app.py`: call `AccountProvisioningService().ensure_seed_administrator(config.SEED_ADMIN_EMAIL)` once at module load (Function App cold start), guarded so a blank `SEED_ADMIN_EMAIL` is a no-op (FR-001) — depends on T002, T004
- [X] T010 [P] Add unit tests for `ProvisionedAccountEntry` validation (empty `roles` rejected, `email`/`id` lowercased and identical) in `src/backend/tests/unit/test_models.py`
- [X] T011 [P] Add unit tests for `AccountProvisioningService.get_by_email`, `authorize_sign_in` (first-sign-in bind, matching-oid success, mismatched-oid denial), and `ensure_seed_administrator` (creates once, no-ops and does not overwrite an already-merged entry on a second call) in `src/backend/tests/unit/test_account_provisioning_service.py` (new file)
- [X] T012 [P] Update `src/backend/tests/unit/test_auth_service.py` for `validate_token`'s new `(is_valid, user_oid, email, error)` return shape
- [X] T013 [P] Update `src/backend/tests/unit/test_middleware.py` to cover `authenticate_with_email` alongside the existing `authenticate` tests
- [X] T014 [P] Update `src/backend/tests/unit/test_admin_capability.py` to exercise `AccountProvisioningService` role checks instead of the removed `CapabilityService`
- [X] T015 [P] Update `src/backend/tests/unit/test_unauthorized_user.py` to exercise `AccountProvisioningService.get_by_email`/`authorize_sign_in` instead of the removed `AllowListService`
- [X] T016 [P] Update `src/backend/tests/integration/test_access_denial.py`: replace its `patch("backend.api.admin.middleware.AllowListService"/"CapabilityService")` mocks with `AccountProvisioningService` mocks matching T007/T008's new implementation
- [X] T017 [P] Update `src/backend/tests/integration/test_authorization_enforcement.py` with the same mock replacement as T016

**Checkpoint**: Model, service, and every existing consumer of the old oid-keyed services compile and pass their tests. `login.py`/`me.py` still use the pre-existing (unchanged) flow — wiring them up is User Story 1's job, next.

---

## Phase 3: User Story 1 - System Is Seeded with an Initial Administrator Account (Priority: P1) 🎯 MVP

**Goal**: A freshly deployed system has exactly one working Administrator, matched by email on its first sign-in, then pinned to that account's Microsoft object identifier for every sign-in after (FR-001, FR-006, FR-007).

**Independent Test**: Deploy fresh with only the seed administrator configured; sign in with that Microsoft account and reach the administration area with no manual data setup; a second sign-in attempt presenting the same email but a different object identifier is denied.

### Tests for User Story 1

- [X] T018 [P] [US1] Add integration tests to `src/backend/tests/integration/test_login_endpoint.py`: (a) the seed administrator's first sign-in succeeds and binds `objectId`, (b) any other email is denied before further accounts exist, (c) a second sign-in with the now-bound, matching `objectId` succeeds while a mismatched `objectId` for that same email is denied
- [X] T019 [P] [US1] Update `src/backend/tests/integration/test_me_endpoint.py` for the email-first-match-then-bind flow (mirrors T018's login-endpoint cases for `/api/auth/me`)

### Implementation for User Story 1

- [X] T020 [P] [US1] Update `src/backend/api/auth/login.py` to call `authenticate_with_email` (T006) and `AccountProvisioningService.authorize_sign_in(email, oid)` (T004) in place of the oid-only `AllowListService`/`CapabilityService` lookup, reading capabilities from the returned entry's `roles`
- [X] T021 [P] [US1] Update `src/backend/api/auth/me.py` with the same resolution flow as T020
- [X] T022 [P] [US1] Update `src/backend/db/seed_data.py`'s local-dev test-user helper (`seed()`) to create `ProvisionedAccountEntry` records via the new model — this is the manual local-dev convenience script, distinct from T009's automatic production bootstrap

**Checkpoint**: User Story 1 is independently functional — a fresh deploy's seed administrator can sign in, is bound, and stays pinned to that Microsoft identity.

---

## Phase 4: User Story 2 - Administrator Adds a New Player or Administrator by Email (Priority: P2)

**Goal**: A signed-in Administrator can grant a new Microsoft account Player and/or Administrator access by email (FR-002, FR-003, FR-004, FR-005).

**Independent Test**: Signed in as an administrator, add a new email with the Player capability and verify that email can subsequently sign in and reach the player menu; separately add another email with the Administrator capability.

### Tests for User Story 2

- [X] T023 [P] [US2] Create `src/backend/tests/integration/test_admin_accounts_endpoint.py` with tests for `POST /api/manage/accounts`: creates an entry for `["Player"]`, `["Administrator"]`, and `["Player", "Administrator"]`; returns 400 `role_required` for an empty roles list; returns 400 `invalid_email` for a malformed email (per contracts/api.md)
- [X] T024 [P] [US2] Add an integration test to `src/backend/tests/integration/test_login_endpoint.py`: an email newly added via `POST /api/manage/accounts` can subsequently sign in and binds its `objectId` (ties US2's add flow to US1's sign-in flow)

### Implementation for User Story 2

- [X] T025 [P] [US2] Implement `add_or_merge(email, roles, added_by) -> ProvisionedAccountEntry` in `src/backend/services/account_provisioning_service.py`: validate `email` via `pyisemail` (T001, FR-005) and `roles` as a non-empty subset of `Player`/`Administrator` (FR-003/FR-004), raising distinguishable errors the endpoint maps to `invalid_email`/`role_required`; on an existing email, union the roles and leave `objectId`/`dateBound` untouched (FR-009); resubmitting identical roles is a no-op
- [X] T026 [US2] Create `src/backend/api/manage/accounts.py` with `add_account(req)` handling `POST /api/manage/accounts`: gated by `authorize_admin` (T007), calls `add_or_merge` (T025), returns the shapes in contracts/api.md — depends on T025
- [X] T027 [US2] Register the `POST /api/manage/accounts` route in `src/backend/function_app.py` — depends on T026
- [X] T028 [P] [US2] Create `src/frontend/src/services/accountService.js` with `addAccount(token, email, roles)` calling `POST /api/manage/accounts` (mirrors the pattern in `src/frontend/src/services/authService.js`)
- [X] T029 [US2] Create `src/frontend/src/components/Admin/AccountForm.jsx`: email input + Player/Administrator checkboxes, built from the vendored design system's `.field`/`.input`/`.btn-primary` classes (no ad hoc styles — Constitution Principle VIII), surfacing `role_required`/`invalid_email` errors from T028 — depends on T028
- [X] T030 [US2] Add `src/frontend/tests/components/AccountForm.test.jsx` — depends on T029
- [X] T031 [US2] Create `src/frontend/src/pages/AdminAccountsPage.jsx` hosting `AccountForm` — depends on T029
- [X] T032 [US2] Link an "Accounts" entry point from `src/frontend/src/pages/AdminPage.jsx` to `AdminAccountsPage` (T031) — depends on T031

**Checkpoint**: User Stories 1 and 2 are both independently functional — an administrator can grant Player/Administrator access by email, and the granted account can sign in.

---

## Phase 5: User Story 3 - Administrator Views Existing Provisioned Accounts (Priority: P3)

**Goal**: An administrator can see every provisioned email and its role(s), and confirm that adding an already-provisioned email merges into one entry rather than duplicating it (FR-009, FR-010).

**Independent Test**: With at least two provisioned entries existing, view the account list and verify both are shown with their correct assigned roles; re-adding an existing email with an extra role updates that one entry.

### Tests for User Story 3

- [X] T033 [P] [US3] Add tests to `src/backend/tests/integration/test_admin_accounts_endpoint.py`: `GET /api/manage/accounts` lists every entry with its email and roles; re-adding an already-provisioned email with an additional role results in one merged entry (not two) with its bound `objectId` unchanged; resubmitting an identical add request twice is a no-op; a non-Administrator caller gets 403 `insufficient_permission` from both `POST` and `GET /api/manage/accounts`

### Implementation for User Story 3

- [X] T034 [P] [US3] Implement `list_all() -> list[ProvisionedAccountEntry]` in `src/backend/services/account_provisioning_service.py` (FR-010)
- [X] T035 [US3] Add `list_accounts(req)` handling `GET /api/manage/accounts` to `src/backend/api/manage/accounts.py`, gated by `authorize_admin`, returning the shape in contracts/api.md — depends on T026, T034
- [X] T036 [US3] Register the `GET /api/manage/accounts` route in `src/backend/function_app.py` — depends on T035
- [X] T037 [P] [US3] Add `listAccounts(token)` to `src/frontend/src/services/accountService.js` (created in T028)
- [X] T038 [US3] Create `src/frontend/src/components/Admin/AccountList.jsx` using the design system's `.table` and `.tag*` classes for role chips — depends on T037
- [X] T039 [US3] Add `src/frontend/tests/components/AccountList.test.jsx` — depends on T038
- [X] T040 [US3] Render `AccountList` (T038) alongside `AccountForm` in `src/frontend/src/pages/AdminAccountsPage.jsx` (T031) — depends on T038

**Checkpoint**: All three user stories are independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Retire the code this feature supersedes and confirm the whole feature end-to-end.

- [X] T041 [P] Update `src/backend/tests/integration/test_dual_role_user.py` to seed via `ProvisionedAccountEntry` instead of the removed `AllowListEntry`/`CapabilityAssignment`
- [X] T042 [P] Add `src/frontend/tests/integration/admin_accounts.test.jsx` covering the add → list → re-add-merges flow end-to-end
- [X] T043 [P] Remove `src/backend/models/allow_list_entry.py` (superseded by T003)
- [X] T044 [P] Remove `src/backend/models/capability_assignment.py` (superseded by T003)
- [X] T045 [P] Remove `src/backend/services/allow_list_service.py` (superseded by T004)
- [X] T046 [P] Remove `src/backend/services/capability_service.py` (superseded by T004)
- [X] T047 [P] Remove `src/backend/tests/unit/test_allow_list_service.py` (superseded by T011/T015)
- [X] T048 [P] Remove `src/backend/tests/unit/test_capability_service.py` (superseded by T011/T014)
- [X] T049 Remove the now-unused `ALLOW_LIST_CONTAINER`/`CAPABILITY_CONTAINER` constants from `src/backend/config.py` — depends on T043, T044, T045, T046
- [ ] T050 Run quickstart.md's 7 validation scenarios end-to-end (locally or against a deployed environment) and confirm each passes
- [X] T051 Grep the repository for any remaining reference to `allowListEntries`, `capabilityAssignments`, `AllowListEntry`, `CapabilityAssignment`, `AllowListService`, or `CapabilityService` and resolve any found — depends on T049

**Found by `/speckit-analyze` (post-merge)**: tasks.md never included infrastructure tasks for this feature's storage/config, despite plan.md's Storage section and Assumptions requiring them — the gap was discovered only because the deployed `SEED_ADMIN_EMAIL` app setting was observed empty. T052/T053 document the fix retroactively; T054/T055 close a constitution gap and a Success Criterion coverage gap the same analysis surfaced.

- [X] T052 Update `infrastructure/terraform/main.tf`: replace the `allow_list_entries`/`capability_assignments` Cosmos SQL containers with a single `provisioned_account_entries` container (`provisionedAccountEntries`, partition key `/email`) backing `AccountProvisioningService` (data-model.md's Storage Model) — depends on T049
- [X] T053 Wire `SEED_ADMIN_EMAIL` (FR-001) to the deployed Function App: add the `seed_admin_email` Terraform variable (`infrastructure/terraform/variables.tf`), reference it in the Function App's `app_settings` (`main.tf`), and inject it into `terraform-apply.yml`'s apply step as `TF_VAR_seed_admin_email` from a `production-infra` environment secret (not `terraform.tfvars`, which is committed and explicitly excludes secrets) — depends on T052
- [X] T054 Fix Constitution Principle VIII gap: restyle `AccountForm.jsx`'s Player/Administrator role checkboxes from unstyled native `<input type="checkbox">` (left at browser defaults — a review blocker per the constitution's Interaction States section) to the vendored `.seg`/`.seg-opt` segmented-toggle pattern already used elsewhere (`specs/designs/04-admin-wizard.html`'s session-length control), which ships all four themed states — depends on T029
- [X] T055 Close SC-005's coverage gap: add an integration test to `test_login_endpoint.py` proving sign-in matches end-to-end regardless of the token email claim's letter case (prior coverage was unit-level only: `get_by_email` lowercasing and model-construction lowercasing, not the full `authorize_sign_in`/login-endpoint path) — depends on T020

**Note**: this file's spec.md cross-references above (the Tests line's "FR-011", Phase 5's "FR-010"/"User Story 3") predate the 2026-08-29 `014-account-listing` split and are not reconciled with current `spec.md` numbering — that renumbering is pre-existing drift, out of scope for this pass. `spec.md`'s current User Story 3 (below) is a **different, newly added** story (account removal), unrelated to this file's Phase 5 (view accounts, already shipped, now specified in `014-account-listing`). New tasks below use `[Removal]` as their story tag to avoid colliding with this file's existing `[US3]` tag.

---

## Live-validation gap + spec amendment (2026-08-30)

**Found while manually validating T050 (live quickstart run) against the deployed environment**: granting Player access to an account with no existing presence in the application's Entra ID tenant created an allow-list entry that could never actually sign in (`AADSTS50020` — tenant membership is a Microsoft-enforced prerequisite to sign-in that this feature never established). Recorded in `spec.md`'s Edge Cases as FR-011.

**Also amended**: `spec.md` now specifies an account-removal capability (User Story 3, FR-012/FR-013) — administrators can revoke a Player/Administrator entry, removing it from both the allow-list and the Entra tenant, except their own entry or the seed administrator's.

T056-T071 below implement both amendments. **Not yet implemented** — this update only records them, per FR-011/FR-012/FR-013 in `spec.md`.

- [X] T056 **UI design agreement/sign-off** (Constitution Principle XI, NON-NEGOTIABLE): the requesting user or product owner reviews the removal screen design at `specs/designs/05-admin-users.html` — per-row "Remove" action, one account at a time, always behind the confirmation dialog (`.confirm.show`: "Remove {name}?" / "Remove account" / "Keep it"), no bulk removal — and confirms it as the design for T064's implementation. This task is not complete until that confirmation is given; the design artifact existing is not sufficient. **Gates all UI implementation tasks below (T062, T064, T065).**
- [X] T057 [P] Create `EntraDirectoryService` in `src/backend/services/entra_directory_service.py` (DI-mockable per the existing `cosmos_service` injection pattern in `account_provisioning_service.py`) exposing `invite_guest(email) -> None` (Microsoft Graph `POST /invitations`, no-op if the email is already a tenant member) and `remove_guest(email) -> None` (Graph user delete, no-op if no matching guest is found) — uses `DefaultAzureCredential` (`azure-identity`, already a dependency) against `https://graph.microsoft.com/.default`, matching `cosmos_service.py`/`llm_service.py`'s existing Managed Identity pattern
- [X] T058 Add the `azuread` Terraform provider (`infrastructure/terraform/versions.tf` currently configures only `azurerm`) and grant the Function App's system-assigned managed identity (`infrastructure/terraform/identity.tf`) the Microsoft Graph application permissions T057 needs (e.g. `User.Invite.All` plus a scoped delete permission such as `User.ReadWrite.All`) via `azuread_app_role_assignment`, with admin consent — infra concern per spec.md's Assumptions, no existing precedent for a Graph app-role grant in this repo
- [X] T059 [US2] Wire `EntraDirectoryService.invite_guest` (T057) into `add_or_merge` (`account_provisioning_service.py`) so a new grant, or a role-merge onto a not-yet-tenant-member email, invites the account (FR-011) — depends on T057
- [X] T060 [Removal] Implement `remove_account(email, requested_by_email, seed_admin_email) -> None` in `AccountProvisioningService`: reject if `email == requested_by_email` or `email == seed_admin_email` (FR-012), else delete the Cosmos entry and call `EntraDirectoryService.remove_guest` (T057, FR-013) — depends on T057
- [X] T061 [Removal] Add `remove_account(req)` handling `DELETE /api/manage/accounts` to `src/backend/api/manage/accounts.py`, gated by `authorize_admin`, mapping the self/seed-admin rejection to `self_removal`/`seed_admin_removal` (400) and a missing entry to `not_found` (404), per `contracts/api.md`'s `DELETE /api/manage/accounts` contract — depends on T060
- [X] T062 [Removal] Register the `DELETE /api/manage/accounts` route in `src/backend/function_app.py` — depends on T061
- [X] T063 [P] [Removal] Add `removeAccount(token, email)` to `src/frontend/src/services/accountService.js`
- [X] T064 [Removal] Add a delete action to `src/frontend/src/components/Admin/AccountList.jsx`: clicking "Remove" opens a confirmation dialog (built from the vendored `.dialog-backdrop`/`.dialog` primitives, matching `specs/designs/05-admin-users.html`'s `.confirm` pattern) stating the account will lose access and cannot be undone from there; only the dialog's confirm action calls `removeAccount` (T063). The action is disabled/hidden for the signed-in administrator's own row and the seed administrator's row (client-side convenience only — T061's server-side check is the actual enforcement, per Constitution Principle II) — depends on T056, T063
- [X] T065 [P] [Removal] Add `src/frontend/tests/components/AccountList.test.jsx` cases for the delete action: confirmation dialog opens before removal, confirming calls `removeAccount`, cancelling ("Keep it") does not, and the disabled self/seed-admin cases — depends on T064
- [X] T066 [P] Add unit tests for `EntraDirectoryService` (mocked Graph client/HTTP) in `src/backend/tests/unit/test_entra_directory_service.py` — depends on T057
- [X] T067 [P] Add unit tests for `AccountProvisioningService.remove_account` (self-rejection, seed-admin-rejection, success) in `src/backend/tests/unit/test_account_provisioning_service.py` — depends on T060
- [X] T068 [P] Add integration tests to `src/backend/tests/integration/test_admin_accounts_endpoint.py` for `DELETE /api/manage/accounts`: success, self-removal 400, seed-admin-removal 400, not-found 404, non-Administrator caller 403 — depends on T061
- [X] T069 [P] Add an integration test to `src/backend/tests/integration/test_login_endpoint.py` proving a removed account is denied sign-in immediately after removal — depends on T060
- [ ] T070 Add 1-2 new scenarios to `quickstart.md` covering Entra-invite-on-grant and the removal flow, and re-run T050's live validation once T057-T069 are implemented — depends on T059, T060
- [ ] T071 **User-verified acceptance** (Constitution Principle IX, NON-NEGOTIABLE): the requesting user or product owner — not the implementing agent — signs in as an Administrator against the real deployed environment (or the most representative environment available) and manually runs quickstart.md's full scenario set end-to-end, including the Entra-guest-invite-on-grant and account-removal scenarios added by T070 (confirming a newly granted account with no prior tenant presence can sign in, and a removed account cannot). This task is not complete until that confirmation is given; a passing T070/T050 agent-run validation does not satisfy it — depends on T070

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup. **Blocks all user stories** — this is where 002's oid-keyed backend is migrated.
- **User Story 1 (Phase 3)**: Depends on Foundational only.
- **User Story 2 (Phase 4)**: Depends on Foundational only; T024's test also exercises US1's login endpoint, so run after Phase 3 for a clean pass, though the add-account functionality itself has no code dependency on US1.
- **User Story 3 (Phase 5)**: Depends on Foundational and on US2's `src/backend/api/manage/accounts.py`/`src/frontend/src/services/accountService.js`/`AdminAccountsPage.jsx` existing (T026, T028, T031) — extends files US2 created rather than duplicating them.
- **Polish (Phase 6)**: Depends on all three user stories being complete (the old services can only be deleted once nothing references them).

### Within Each User Story

- Tests are written before the implementation they cover, per Constitution Principle I.
- Service-layer changes precede endpoint handlers; endpoint handlers precede route registration; backend contract precedes frontend consumption.

### Parallel Opportunities

- Setup: T001, T002.
- Foundational leaf tasks: T003, T005; all Foundational test tasks: T010-T017.
- User Story 1: T018-T022 are all mutually independent files.
- User Story 2: T023/T024 (tests); T025 and T028 (independent leaf implementation tasks).
- User Story 3: T034 and T037 (independent leaf implementation tasks).
- Polish: T041-T048.
- Different user stories could be staffed in parallel by different people once Foundational is complete, with US3 starting its file-creation tasks only after US2's T026/T028/T031 land.

---

## Parallel Example: Foundational Phase

```bash
# Two independent leaf tasks:
Task: "Create ProvisionedAccountEntry in src/backend/models/provisioned_account_entry.py"
Task: "Modify src/backend/services/auth_service.py to extract the email claim"

# Once their prerequisites land, all eight test-update tasks run independently:
Task: "Unit tests for ProvisionedAccountEntry in src/backend/tests/unit/test_models.py"
Task: "Unit tests for AccountProvisioningService in src/backend/tests/unit/test_account_provisioning_service.py"
Task: "Update src/backend/tests/unit/test_auth_service.py"
Task: "Update src/backend/tests/unit/test_middleware.py"
Task: "Update src/backend/tests/unit/test_admin_capability.py"
Task: "Update src/backend/tests/unit/test_unauthorized_user.py"
Task: "Update src/backend/tests/integration/test_access_denial.py"
Task: "Update src/backend/tests/integration/test_authorization_enforcement.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 (Setup) and Phase 2 (Foundational) — this migrates 002's sign-in path onto the new model, which is required before anything else can work.
2. Complete Phase 3 (User Story 1).
3. **STOP and VALIDATE**: run quickstart.md Scenarios 1-2 — a fresh deploy's seed administrator signs in, binds, and stays pinned.
4. This is a real, demoable MVP: the system is never without a working administrator, and 002's regression risk from the migration is already covered by Phase 2's test updates.

### Incremental Delivery

1. Setup + Foundational → the migration is done and CI-green before any new user-facing behavior ships.
2. + User Story 1 → seed bootstrap works (MVP).
3. + User Story 2 → administrators can grant access to new accounts.
4. + User Story 3 → administrators can see and safely re-grant to existing accounts.
5. Polish → old 002 code paths removed once nothing depends on them.
