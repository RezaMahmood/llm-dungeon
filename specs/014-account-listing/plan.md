# Implementation Plan: Account Listing

**Branch**: `014-account-listing` | **Date**: 2026-09-05 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/014-account-listing/spec.md`

## Summary

Administrators need to see the current set of provisioned account entries — email, roles, and whether the account has completed its first sign-in — before or while adding a new one. This is a read-only view over the `ProvisionedAccountEntry` data and endpoint that `003-account-provisioning-done` already created (`GET /api/manage/accounts`, `AccountProvisioningService.list_all`, `AccountList.jsx`). No new data, endpoint, or mutation is introduced. The delta this feature actually adds, per the 2026-09-05 clarifications:

1. **Deterministic sort order**: `list_all` currently returns rows in whatever order the Cosmos query happens to yield; FR-001 requires alphabetical-by-email ascending. Sort explicitly in the service layer (small, fixed-size list — no query-level `ORDER BY` needed per Principle IV).
2. **"Pending first sign-in" indicator**: the existing UI already renders a bound/unbound status column ("Signed in" / "Not yet signed in"), but the spec's clarification requires the exact "pending first sign-in" framing to be a stated requirement (FR-005) with its own test (FR-004), not just incidental copy. Update `AccountList.jsx`'s unbound-state label to say "Pending first sign-in" and add the missing sort/indicator test coverage on both backend and frontend.

No new dependency, storage, endpoint, or architecture is introduced.

## Technical Context

**Language/Version**: Python 3.12 (Azure Functions backend, existing), Node.js LTS / React 18 (frontend, existing) — per Constitution Principle III; unchanged by this feature.

**Primary Dependencies**: Backend: `azure-functions`, `azure-cosmos`, `pyisemail` (all already in use by `003-account-provisioning-done`, no new dependency). Frontend: existing React app, `AccountList.jsx`/`accountService.js` (no new dependency).

**Storage**: Azure Cosmos DB (via `CosmosService`), same `PROVISIONED_ACCOUNTS_CONTAINER` container as `003-account-provisioning-done`. No schema change — no new fields, no new container.

**Testing**: pytest (backend unit/integration, against the Cosmos DB emulator per Constitution Principle I), Vitest/Testing Library (frontend component tests) — both already configured in this repo.

**Target Platform**: Same as the rest of the app — Azure Functions (Linux) backend, browser-based React frontend.

**Project Type**: Web application (existing `src/backend` + `src/frontend` structure).

**Performance Goals**: N/A — no new performance requirement; list size stays in the ~5-10 provisioned-account range assumed by `007-azure-infrastructure-provisioning`.

**Constraints**: No pagination, search, or filtering (spec Assumptions) — full list returned every time, consistent with the existing `GET /api/manage/accounts` contract.

**Scale/Scope**: ~5-10 provisioned accounts (per spec Assumptions). One existing endpoint gets a sort-order fix; one existing component gets a label change. No new screens.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle I (Automated Testing)**: FR-004 explicitly requires a test per listing outcome. Plan adds: (1) a backend unit test asserting `list_all` returns entries sorted alphabetically by email; (2) a backend integration test asserting the `GET /api/manage/accounts` response preserves that order and reflects role-merges as a single entry (already partially covered by `003`'s `test_list_accounts_returns_every_entry_with_email_and_roles` — extend rather than duplicate); (3) a frontend test asserting the "Pending first sign-in" label renders for an unbound account. All run locally against the existing Cosmos emulator setup — no new external dependency introduced. PASS.
- **Principle II (Secure-by-Default Access)**: No auth change. The existing `authorize_admin` check on `list_accounts` already rejects non-administrators (FR-003); this feature adds no new endpoint so no new surface to secure. PASS.
- **Principle III (Defined Technology Stack)**: Same Python/Azure Functions + ReactJS stack, no deviation. PASS.
- **Principle IV (Simplicity/YAGNI)**: In-memory sort of an already-fetched (~5-10 row) list rather than a Cosmos `ORDER BY`, index change, or pagination — matches the project's stated scale. PASS.
- **Principle V (CI Gate)**: New/changed tests run in the existing pytest/Vitest CI jobs; no new workflow needed. PASS.
- **Principle VIII (UI Design System)**: The only UI change is a text label ("Not yet signed in" → "Pending first sign-in") inside the existing `table`/`tag`-based `AccountList.jsx`, which already uses design-system classes. No new component, color, or visual-style class is introduced. PASS.
- **Principle IX (User-Verified Acceptance)**: `tasks.md` (next command) MUST end with an explicit user-verified acceptance task against the deployed/most-representative environment, per this principle — not satisfied by this plan alone.
- **Principle X (PII Protection)**: No new PII field or surface; emails already live only in Cosmos DB / the authenticated admin UI, unchanged. PASS.
- **Principle XI (UI Design Pre-Agreement)**: This feature changes user-facing copy (the pending-sign-in indicator wording) on an existing screen (`specs/designs/05-admin-users.html`), which does not currently depict that indicator. Per this principle, `tasks.md` MUST include an explicit design-agreement/sign-off task — covering just this one label/indicator change, sequenced before the implementation task that changes `AccountList.jsx` — confirmed by the requesting user before that task is built. Not an exception; flagged so `/speckit-tasks` includes the gate.
- **Principle XII (Right-Sized Scope)**: No pagination/search/filtering/new roles/environments added, consistent with the spec's Assumptions. PASS.
- **Principle XIII (AI Agent Division of Labor)**: Standard local-dev-then-PR flow; no change. PASS.

No violations requiring Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/014-account-listing/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/backend/
├── api/admin/accounts.py                       # list_accounts handler (existing) — no change to shape, only ordering
├── services/account_provisioning_service.py    # list_all — add explicit alphabetical-by-email sort
├── models/provisioned_account_entry.py         # unchanged (no new fields)
└── tests/
    ├── unit/test_account_provisioning_service.py       # add sort-order test
    └── integration/test_admin_accounts_endpoint.py     # extend list coverage (order, merge-reflected-once)

src/frontend/
├── src/components/Admin/AccountList.jsx        # unbound-status label -> "Pending first sign-in"
└── tests/components/AccountList.test.jsx       # update/extend label assertion
```

**Structure Decision**: Existing web-application layout (`src/backend` Azure Functions API + `src/frontend` React app). This feature modifies two existing files per side (service + handler on the backend, component + test on the frontend) and adds no new files, directories, endpoints, or models.

## Complexity Tracking

*No violations — table omitted.*
