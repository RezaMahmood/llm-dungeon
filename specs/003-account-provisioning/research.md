# Research: Account Provisioning

**Date**: 2026-08-29 | **Status**: Research Phase Complete

## 1. Email Format Validation (FR-005)

**Unknown**: Which Python library validates an email address against the strict RFC 5322 grammar chosen during clarification (not a loose regex, not deliverability checking).

**Decision**: `pyisemail` (a Python port of Dominic Sayers' `is_email`) — validates against the full RFC 5321/5322 address grammar, including quoted local parts and IP-literal domains, with no network/deliverability check.

**Rationale**: The clarified requirement is grammar strictness, not deliverability. `pyisemail` implements the grammar directly and returns a diagnosis (valid / category of invalidity) without making a network call, which keeps validation synchronous and side-effect-free inside the add-account request handler.

**Alternatives considered**:
- `email-validator` (PyPI): widely used, but deliberately deviates from strict RFC grammar in places and defaults to DNS/deliverability checks (would need to be disabled, and still isn't the same grammar).
- Hand-rolled regex: cannot faithfully cover RFC 5322's grammar (quoted strings, comments, IP-literal domains) without effectively reimplementing a parser; rejected as needlessly risky.
- `django-email-validator` / framework-bundled validators: pulls in an unrelated framework dependency for one function.

**Validation**: Unit tests assert acceptance of RFC 5322 edge cases (quoted local part, IP-literal domain) and rejection of malformed input (missing `@`, empty local part, no domain) per FR-011.

---

## 2. Extracting Email from the Microsoft Entra ID Token

**Unknown**: Which JWT claim reliably carries the signed-in account's email address, for both Microsoft-native accounts and non-Microsoft accounts (e.g., Gmail) federated through Microsoft identity sign-in — needed because `backend/services/auth_service.py` today only extracts `oid` and ignores email entirely.

**Decision**: Read the `email` claim from the validated ID token. The frontend's MSAL login request (`frontend/src/services/msalConfig.js`) already requests the `email` OIDC scope, which is what causes Entra ID to populate this claim for both work/school and personal Microsoft accounts, and for guest/federated identities (their invited email carries through). `AuthService.validate_token` will be extended to return `(is_valid, user_oid, email, error)`, and callers will lowercase the email before using it as a lookup key (per FR-008).

**Rationale**: `preferred_username` is present more often but is not guaranteed to be an email address in every account type (it can be a phone number or a non-routable local identifier for some personal-account flows); `email` is the claim Microsoft's identity platform documents as carrying an actual email address when the `email` scope has been requested and consented, which this app registration already does.

**Alternatives considered**:
- `preferred_username`: rejected as primary source (format not guaranteed to be an email address); could serve as a documented fallback if `email` is ever absent, but no observed case in this project's supported sign-in paths lacks it once the `email` scope is granted, so no fallback is implemented now (YAGNI — add one if a real gap surfaces).
- Calling Microsoft Graph `/me` for the email post-authentication: adds a network round-trip and a new external dependency on every sign-in for data already available in the token; rejected.

**Validation**: Integration tests construct a token fixture with an `email` claim and assert it is extracted and lowercased; a token fixture missing `oid` is already covered by existing 002 tests and continues to deny access.

---

## 3. Reconciling Email-Based Matching with the Already-Implemented oid-Based 002 Backend

**Unknown**: 002's shipped backend keys `allowListEntries` and `capabilityAssignments` by Microsoft `user_oid`; 003's spec (FR-006/FR-007, set during clarification) requires email-based matching for an entry's first sign-in and oid-based matching thereafter. How should the plan reconcile a spec requirement with already-shipped, tested code?

**Decision**: Replace both 002 containers with a single `provisionedAccountEntries` container, partitioned and keyed by lowercased email (see data-model.md). Sign-in resolves the entry by the token's email claim first; if the entry has no bound `objectId` yet, the sign-in succeeds and binds `objectId` to the token's `oid`; if it already has a bound `objectId`, the token's `oid` must match it or the sign-in is denied.

**Rationale**: FR-006 is explicit and non-negotiable ("no other Microsoft account attribute... is used as the matching key" for an entry's first sign-in) — email must be the lookup key at least at first sign-in, and an admin provisioning a new player by email has no oid to store yet regardless. Keeping 002's oid-keyed containers as the source of truth would make FR-006 impossible to satisfy (there would be nothing to look up by email before a first sign-in occurs). Consolidating into one container also matches 003's own Key Entities section, which already describes a single "Provisioned Account Entry" as the concrete record behind 002's two concepts.

**Alternatives considered**:
- Keep 002's two oid-keyed containers and add a separate email-keyed index/container just for the admin UI, translating between them at sign-in: rejected — still requires the sign-in path to resolve by email first (to find *any* record before an oid exists), so it doesn't avoid touching `login.py`/`me.py`/`middleware.py`, while leaving two containers to keep consistent for no benefit.
- Leave 002 entirely alone and layer 003 as a read-only "view" over it: rejected — cannot satisfy FR-002/FR-008/FR-009 (add/merge/view by email as the entry's own identity) without the entry being keyed by email.

**Blast radius (for the record, not a design question)**: `backend/models/allow_list_entry.py`, `capability_assignment.py`, `backend/services/allow_list_service.py`, `capability_service.py`, `backend/services/auth_service.py`, `backend/api/auth/{login,me,middleware}.py`, `backend/api/admin/middleware.py`, `backend/db/seed_data.py`, and their existing unit/integration tests. Enumerated fully in plan.md's Project Structure.

**Validation**: Existing 002 integration tests (`test_login_endpoint.py`, `test_me_endpoint.py`, `test_dual_role_user.py`) are updated in place to seed via the new model and are extended with the bind/match/mismatch cases from FR-011; a regression in existing Player/Administrator/dual-role/no-capability/denied outcomes would fail CI (Principle V) before this could ship.

---

## 4. Cosmos DB Partitioning for the Consolidated Container

**Unknown**: What partition key gives efficient point reads for both the sign-in path (lookup by email) and the admin list view (read all entries), at this project's scale (~5-10 users, per `007-azure-infrastructure-provisioning`).

**Decision**: Partition key `/email` (the same lowercased value as the document `id`), one document per provisioned account.

**Rationale**: The sign-in path's only query is a point read by email — the highest-frequency, latency-sensitive operation — which this key serves optimally (single-partition point read, ~1 RU, matching 002's existing oid-keyed point-read cost). The admin list view is a cross-partition query, but at ~5-10 total entries this is negligible RU cost, consistent with 002's own `data-model.md` accepting cross-partition queries for admin-only, low-frequency operations.

**Alternatives considered**:
- A synthetic constant partition key (e.g., `/entityType`) to make the list view a single-partition scan: rejected — would make the sign-in path's point read effectively a partition-scoped query returning every user on every sign-in, worse for the hot path to optimize a cold, low-volume admin view.

**Validation**: `data-model.md` documents both query shapes and their expected RU cost, mirroring the format 002 already established.
