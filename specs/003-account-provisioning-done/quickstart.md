# Quickstart: Validate Account Provisioning

**Date**: 2026-08-29

**Feature**: Account Provisioning (003-account-provisioning)

This guide provides step-by-step validation scenarios confirming account provisioning works end-to-end. See [contracts/api.md](contracts/api.md) for exact request/response shapes and [data-model.md](data-model.md) for the entry schema.

---

## Prerequisites

1. Cosmos DB `provisionedAccountEntries` container exists (per `007-azure-infrastructure-provisioning` and data-model.md's Storage Model).
2. Backend deployed (or running locally) with `/api/auth/login`, `/api/auth/me`, `/api/manage/accounts` (POST + GET).
3. A configured seed administrator email (deployment configuration, per spec.md's Assumptions) — the container is empty except for this one entry on first run.
4. At least two test Microsoft accounts available: the seed administrator's account, and one other account to be newly provisioned.
5. Frontend running with the Administration → Accounts screen reachable by a signed-in Administrator.

---

## Scenario 1: Seed Administrator Bootstraps the System (User Story 1, FR-001, FR-006)

**Objective**: A freshly deployed system has exactly one working Administrator, with no manual data setup.

**Steps**:
1. Deploy fresh (or reset the `provisionedAccountEntries` container to contain only the seed entry, per `src/backend/db/seed_data.py`).
2. Confirm via `GET /api/manage/accounts` (once signed in — see step 3) that exactly one entry exists, with `roles: ["Administrator"]` and `bound: false`.
3. Sign in with the seed administrator's Microsoft account.

**Expected**:
- Sign-in succeeds; `/api/auth/me` returns `capabilities.hasAdministrator: true`.
- The seed entry's `objectId` is now bound (re-querying `GET /api/manage/accounts` shows `bound: true` for that email).
- Signing in again with the same account still succeeds (bound-oid match).

**Passing criteria**: No manual database edit was needed beyond deployment configuration (SC-001).

---

## Scenario 2: A Different Account Cannot Claim the Seed Email (FR-007, SC-006)

**Objective**: Once bound, an entry's email alone is not sufficient to sign in.

**Precondition**: Scenario 1 completed (seed entry is bound).

**Steps**:
1. Attempt to sign in with a token carrying the seed administrator's email but a different `oid` (a test double / integration test fixture, since this cannot be produced with a real Microsoft account under normal circumstances).

**Expected**: Sign-in is denied with the standard `access_denied` response (contracts/api.md) — identical to the response for an entirely unprovisioned account, so no information about the mismatch is leaked.

---

## Scenario 3: Administrator Adds a New Player (User Story 2, FR-002/003/004)

**Objective**: An Administrator grants a new Microsoft account Player access by email.

**Steps**:
1. Signed in as the seed administrator, submit `POST /api/manage/accounts` with `{"email": "<new player's email>", "roles": ["Player"]}`.
2. Confirm the 200 response shows `roles: ["Player"], bound: false`.
3. Sign in with that second test Microsoft account (using exactly that email).

**Expected**:
- Sign-in succeeds; `/api/auth/me` shows `hasPlayer: true`, `hasAdministrator: false`.
- The entry is now bound to that account's `oid` (SC-002).

Repeat with `roles: ["Administrator"]` on a third email to confirm the Administrator-only path, and `roles: ["Player", "Administrator"]` to confirm both are granted in one entry (Acceptance Scenarios 2-3 in spec.md's User Story 2).

---

## Scenario 4: Rejected Submissions (FR-003, FR-005, SC-003)

**Steps**:
1. `POST /api/manage/accounts` with `{"email": "someone@example.com", "roles": []}` → expect 400 `role_required`.
2. `POST /api/manage/accounts` with `{"email": "not-an-email", "roles": ["Player"]}` → expect 400 `invalid_email`.

**Expected**: Neither request creates or modifies an entry — confirm via `GET /api/manage/accounts` that the count is unchanged.

**Note (live-validated 2026-08-30)**: an address like `2343.3ddasdf@outlook.com.asd` is accepted, not rejected — this is correct as designed: FR-005/research.md's clarification chose strict RFC 5322 grammar validation only, explicitly not deliverability/domain-existence checking (`pyisemail` makes no network call). Verifying the domain actually exists (e.g. an MX/DNS lookup) is a possible future enhancement, not a defect in this feature.

---

## Scenario 5: Adding an Already-Provisioned Email Merges Roles (User Story 3, FR-009, SC-004)

**Steps**:
1. With the Player-only entry from Scenario 3 already provisioned and bound (that account has signed in once), submit `POST /api/manage/accounts` with the same email and `roles: ["Administrator"]`.
2. `GET /api/manage/accounts` and find that email's entry.

**Expected**:
- Exactly one entry for that email, now with `roles: ["Player", "Administrator"]` (union, not a second entry).
- `bound` is still `true` — the existing `objectId` binding is untouched (FR-009), confirmed by that account still being able to sign in without any denial.
3. Resubmit the exact same request (`roles: ["Administrator"]`) a second time → same 200 response, no change (no-op, per spec.md Edge Cases).

---

## Scenario 6: View Provisioned Accounts (User Story 3, FR-010)

**Steps**:
1. Signed in as an Administrator, call `GET /api/manage/accounts`.

**Expected**: Every entry created in the prior scenarios is listed, each with its email and current `roles`; no duplicates for the merged email from Scenario 5.

---

## Scenario 7: Non-Administrator Cannot Reach the Interface (Edge Case, Principle II)

**Steps**:
1. Signed in as the Player-only account from Scenario 3, call `POST /api/manage/accounts` or `GET /api/manage/accounts` directly (bypassing the UI).

**Expected**: 403 `insufficient_permission` — the same server-side enforcement pattern as `manage/stories/*` (Constitution Principle II: server-side check, not just a hidden menu item).

---

## Scenario 8: Granting Access Invites an Entra ID Guest (FR-011, added 2026-08-30)

**Objective**: An account with no prior presence in the application's Entra ID tenant can actually sign in after being granted access — closing the live-validation gap found while first running this quickstart (an entry with no tenant guest user hits `AADSTS50020` at sign-in even though it is correctly provisioned).

**Steps**:
1. Signed in as an Administrator, submit `POST /api/manage/accounts` with the email of a Microsoft account that has never signed in to, or been invited to, this application's Entra ID tenant.
2. Check the tenant's Entra ID users list (Azure Portal or `GET /v1.0/users` via Graph Explorer) for that email.
3. Have that account accept the invitation (link sent to its inbox, or via the tenant's pending-invitations list) and sign in.

**Expected**:
- A guest user for that email appears in the tenant immediately after step 1 (FR-011).
- Submitting the same email again (e.g. adding a second role) does not create a duplicate guest invitation — `EntraDirectoryService.invite_guest` no-ops when the email is already a tenant member.
- The account can sign in and bind its `objectId`, exactly as in Scenario 3.

---

## Scenario 9: Administrator Removes an Account (User Story 3 — Removal, FR-012/FR-013, added 2026-08-30)

**Objective**: Removing a provisioned account revokes both application access and Entra ID tenant membership, except for protected accounts.

**Steps**:
1. Signed in as an Administrator, on the Accounts screen, click "Remove" on a previously granted Player or Administrator account (not your own row, not the seed administrator's row — those rows have no Remove action, per `specs/designs/05-admin-users.html`).
2. Confirm the dialog ("Remove {email}?" / "Remove account").
3. Attempt `DELETE /api/manage/accounts` directly (bypassing the UI) with your own signed-in email.
4. Attempt `DELETE /api/manage/accounts` with the seed administrator's email.
5. Attempt `DELETE /api/manage/accounts` with an email that has no provisioned entry.

**Expected**:
- Step 2: the entry disappears from `GET /api/manage/accounts`, the account can no longer sign in (`access_denied`, same as never-provisioned), and its guest user is gone from the Entra ID tenant (SC-008).
- Step 3: 400 `self_removal`.
- Step 4: 400 `seed_admin_removal`, regardless of who is signed in.
- Step 5: 404 `not_found`.

---

## Automated Test Coverage Cross-Reference

Every scenario above corresponds to at least one automated test required by FR-011:

| Scenario | Backend test location |
|---|---|
| 1 | `src/backend/tests/integration/test_login_endpoint.py` (seed + first-bind case) |
| 2 | `src/backend/tests/integration/test_login_endpoint.py` (oid-mismatch case) |
| 3 | `src/backend/tests/integration/test_admin_accounts_endpoint.py`, `test_login_endpoint.py` |
| 4 | `src/backend/tests/unit/test_account_provisioning_service.py` |
| 5 | `src/backend/tests/integration/test_admin_accounts_endpoint.py` |
| 6 | `src/backend/tests/integration/test_admin_accounts_endpoint.py` |
| 7 | `src/backend/tests/integration/test_admin_accounts_endpoint.py` |
| 8 | `src/backend/tests/unit/test_entra_directory_service.py`, `test_account_provisioning_service.py` (invite-on-grant wiring) |
| 9 | `src/backend/tests/integration/test_admin_accounts_endpoint.py` (DELETE cases), `test_login_endpoint.py` (post-removal denial) |

Frontend equivalents live in `src/frontend/tests/components/{AccountForm,AccountList}.test.jsx` and `src/frontend/tests/integration/admin_accounts.test.jsx`.

**Live-validation status (T070/T071)**: Completed 2026-08-30 by the requesting user against the deployed environment (see issue #32). Scenarios 3, 5, 6, 7, 8, 9 passed via the UI. Scenario 4 passed for malformed-email rejection; its domain-existence behavior is as-designed (see note above), not a defect. Scenario 9's `self_removal` rejection was not exercised live — the UI has no self-remove action to trigger it by design — but is covered by `test_admin_accounts_endpoint.py` (T068).
