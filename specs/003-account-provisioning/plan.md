# Implementation Plan: Account Provisioning

**Branch**: `003-account-provisioning` | **Date**: 2026-08-29 | **Spec**: `specs/003-account-provisioning/spec.md`

**Input**: Feature specification from `/specs/003-account-provisioning/spec.md`

## Summary

Give a signed-in Administrator an in-app screen to grant new Microsoft accounts Player and/or Administrator access by email, seed the system with one Administrator entry at first deployment, and let an Administrator view who currently has access. Because the account's Microsoft object identifier (oid) does not exist until that account's first sign-in, matching is two-phase: an entry's first successful sign-in matches by email alone and binds the account's oid to the entry; every sign-in after that must match the bound oid (FR-006/FR-007) — email stays on the entry purely so an administrator can identify accounts by inspection.

**This supersedes part of the already-implemented `002-login-and-access-control` backend.** That backend currently keys two Cosmos DB containers (`allowListEntries`, `capabilityAssignments`) by Microsoft `user_oid` and treats email as a non-authoritative display field. This plan replaces both containers with a single `provisionedAccountEntries` container keyed by lowercased email, and changes the sign-in path (`login.py`, `me.py`, `middleware.py`, `auth_service.py`) to extract the token's email claim and apply the bind-on-first-sign-in logic above. This is a deliberate, spec-driven change (FR-006/FR-007), not scope creep — see research.md §4 for the migration rationale and blast radius.

## Technical Context

**Language/Version**: Python 3.11+ (Azure Functions backend, existing); JavaScript (ES2022) + React 18 via Vite (frontend, existing)

**Primary Dependencies**:
- Backend (existing): `azure-functions`, `azure-cosmos`, `azure-identity`, `PyJWT[crypto]`, `python-dotenv`, `requests`
- Backend (new): `pyisemail` — full RFC 5322/5321 grammar validation for FR-005 (resolved in research.md §1)
- Frontend (existing): React 18, `@azure/msal-browser`/`@azure/msal-react` (via `authService.js`/`msalConfig.js`), `axios`

**Storage**: Azure Cosmos DB, serverless (per `007-azure-infrastructure-provisioning`) — one container, `provisionedAccountEntries`, partition key `/email` (lowercased), replacing 002's `allowListEntries` + `capabilityAssignments` containers (resolved in research.md §4)

**Testing**: pytest (backend `backend/tests/unit`, `backend/tests/integration`, existing convention); Vitest + React Testing Library (frontend `frontend/tests`, existing convention)

**Target Platform**: Azure Functions (Python, Flex Consumption) + Azure Static Web App (React SPA), per `007-azure-infrastructure-provisioning`

**Project Type**: Web application (existing `backend/` + `frontend/` structure)

**Performance Goals**: N/A — no throughput/latency target specified or needed (Principle IV); sign-in adds a single Cosmos point read by partition key, no worse than 002's existing point read by oid

**Constraints**: No account-removal/role-revocation UI (explicit scope boundary); no limit on entry count; no rebind capability for a changed Microsoft oid (explicit scope boundary, same as removal)

**Scale/Scope**: Same ~5-10 named users as `007-azure-infrastructure-provisioning`; three screens/flows (seed bootstrap — no UI, add-account form, account list)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I – Meaningful, Automated Testing (NON-NEGOTIABLE)
**Status**: ✓ MET — FR-011 enumerates every distinct outcome requiring a test (seed present, each add/role combination, merge, two rejection cases, first-sign-in bind, matched-oid sign-in, mismatched-oid denial). Phase 1 contracts define the request/response shapes these tests assert against.

### Principle II – Secure-by-Default Access (NON-NEGOTIABLE)
**Status**: ✓ MET — The add/view interface is gated by the existing `authorize_admin` middleware pattern (Administrator capability required, enforced server-side); FR-007's oid-binding is a strengthening of authorization, not a weakening.

### Principle III – Defined Technology Stack (NON-NEGOTIABLE)
**Status**: ✓ MET — No new language, framework, or hosting model; `pyisemail` is a library addition within the existing Python stack, not a stack deviation.

### Principle IV – Simplicity Over Premature Scale (YAGNI)
**Status**: ✓ MET — Single Cosmos container, no pagination/search on the account list (no stated scale requirement), no rebind/removal machinery built ahead of a feature that needs it.

### Principle V – Continuous Integration Gate
**Status**: ✓ MET — New/changed tests run in the existing pytest (backend) and Vitest (frontend) suites already wired into CI; no new CI configuration needed.

### Principle VI – Observability & AI Cost Transparency (NON-NEGOTIABLE)
**Status**: N/A — This feature makes no LLM calls.

### Principle VII – Zero-Trust Azure Resource Communication (NON-NEGOTIABLE)
**Status**: ✓ MET — Continues to use `CosmosService`'s existing Managed-Identity (`DefaultAzureCredential`) authentication; no new Azure resource dependency, no shared keys introduced.

### Principle VIII – UI Design System & Accessibility Compliance (NON-NEGOTIABLE)
**Status**: ✓ MET, with a gap noted — The new add-account form and account list reuse existing vendored primitives (`.field`, `.input`, `.btn*`, `.table`, `.tag*` in `frontend/src/styles/designTokens.css`); no ad hoc components. No hi-fi mockup exists for this screen in `specs/designs/` (that set covers login, story-select, play, and the admin story-wizard, not account provisioning) — layout will follow the constitution's non-negotiable visual rules (flush-left, zero radius, visible dividers, sparing accent use) directly, the same way `specs/designs/README.md` already tracks other screen gaps.

### Security & Access Control Requirements (constitution, non-principle section)
**Status**: ✓ MET — Adding an account remains an explicit, auditable, admin-only action (entry carries `dateAdded`/`addedBy`); no self-service or implicit grant path is introduced.

No unjustified violations — Complexity Tracking table is not needed.

## Project Structure

### Documentation (this feature)

```text
specs/003-account-provisioning/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── api.md
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created by /speckit-plan)
```

### Source Code (repository root)

**Structure Decision**: Existing web-application layout (`backend/` Python Azure Functions + `frontend/` React SPA, established by `002-login-and-access-control`). This feature adds new files under both and modifies the sign-in/authorization path in `backend/`.

```text
backend/
├── config.py                              # MODIFY: replace ALLOW_LIST_CONTAINER/CAPABILITY_CONTAINER
│                                           #   with PROVISIONED_ACCOUNTS_CONTAINER
├── models/
│   ├── provisioned_account_entry.py       # NEW: replaces allow_list_entry.py + capability_assignment.py
│   ├── allow_list_entry.py                # REMOVE (superseded)
│   └── capability_assignment.py           # REMOVE (superseded)
├── services/
│   ├── account_provisioning_service.py    # NEW: replaces allow_list_service.py + capability_service.py
│   │                                       #   (lookup by email, bind-oid-on-first-sign-in, add/merge, list)
│   ├── allow_list_service.py              # REMOVE (superseded)
│   ├── capability_service.py              # REMOVE (superseded)
│   ├── auth_service.py                    # MODIFY: extract email claim alongside oid
│   └── cosmos_service.py                  # unchanged
├── api/
│   ├── auth/
│   │   ├── middleware.py                  # MODIFY: authenticate() also returns email
│   │   ├── login.py                       # MODIFY: email-first-match + oid-bind/verify flow
│   │   └── me.py                          # MODIFY: same flow as login.py
│   └── admin/
│       ├── middleware.py                  # MODIFY: authorize_admin() uses new service
│       └── accounts.py                    # NEW: POST (add/merge) + GET (list) endpoints
├── db/
│   └── seed_data.py                       # MODIFY: seed one Administrator ProvisionedAccountEntry
│                                           #   from deployment configuration (FR-001)
├── function_app.py                        # MODIFY: register admin/accounts routes
└── tests/
    ├── unit/
    │   ├── test_account_provisioning_service.py   # NEW
    │   ├── test_models.py                          # MODIFY
    │   ├── test_auth_service.py                    # MODIFY
    │   ├── test_middleware.py                      # MODIFY
    │   ├── test_allow_list_service.py               # REMOVE (superseded)
    │   └── test_capability_service.py               # REMOVE (superseded)
    └── integration/
        ├── test_login_endpoint.py                  # MODIFY: add bind/mismatch cases
        ├── test_me_endpoint.py                     # MODIFY
        ├── test_dual_role_user.py                  # MODIFY
        └── test_admin_accounts_endpoint.py         # NEW

frontend/
├── src/
│   ├── pages/
│   │   ├── AdminPage.jsx                  # MODIFY: link/route to the accounts screen
│   │   └── AdminAccountsPage.jsx          # NEW: hosts the form + list
│   ├── components/
│   │   └── Admin/
│   │       ├── AccountForm.jsx            # NEW: email + role checkboxes, uses .field/.input/.btn-primary
│   │       └── AccountList.jsx            # NEW: uses .table + .tag* for role chips
│   └── services/
│       └── accountService.js              # NEW: calls /api/admin/accounts (POST/GET)
└── tests/
    ├── components/
    │   ├── AccountForm.test.jsx           # NEW
    │   └── AccountList.test.jsx           # NEW
    └── integration/
        └── admin_accounts.test.jsx        # NEW
```

## Post-Design Constitution Check

*Re-evaluated after Phase 1 (data-model.md, contracts/, quickstart.md).*

No new violations surfaced during design. Two items worth confirming explicitly now that the schema and contracts are concrete:

- **Principle IV (YAGNI)**: data-model.md's Provisioned Account Entry deliberately omits soft-delete/audit-revocation fields (`dateRemoved`, `revokedBy`, etc.) that 002 had built for a revocation capability that still doesn't exist — dropping unused scaffolding rather than carrying it forward. Still ✓ MET.
- **Principle II (Secure-by-Default) / Security & Access Control Requirements**: contracts/api.md's oid-mismatch case returns the identical `access_denied` body as an unprovisioned email (no enumeration), and both new admin endpoints reuse the existing `authorize_admin` gate rather than introducing a parallel authorization path. Still ✓ MET.

Constitution Check gate: **PASS**. Proceed to `/speckit-tasks`.
