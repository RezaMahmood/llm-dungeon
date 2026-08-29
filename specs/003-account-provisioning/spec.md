# Feature Specification: Account Provisioning

**Feature Branch**: `003-account-provisioning`

**Created**: 2026-08-28

**Status**: Implemented

**Input**: User description: "The application is seeded with an initial administrator account. Thereafter the administrator should have an interface that allows them to add more players or administrators to the system. minimum requirement is that it must be a microsoft account and we only match on emails."

## Clarifications

### Session 2026-08-29

- Q: How strict should the "well-formed" email check be when an administrator adds an entry (FR-005)? → A: Strict RFC 5322
- Q: When an email is stored or shown in the account list, whose letter-casing should be treated as authoritative — since matching itself is already case-insensitive (FR-007)? → A: Normalize to lowercase
- Q: `002-login-and-access-control` is already implemented and matches signed-in accounts by Microsoft object identifier (oid), not email — how should email-based matching coexist with the security benefit of oid? → A: Object identifier is more secure and should still be used, but email must also be stored so administrators can identify accounts by looking at the data directly.
- Q: Since a Microsoft object identifier cannot exist until an account's first sign-in, how should email (used for provisioning) and object identifier (used for ongoing security) combine? → A: Match by email only on an entry's first successful sign-in, and bind that account's Microsoft object identifier to the entry at that moment; every later sign-in for that entry MUST match on the bound object identifier, not email alone.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - System Is Seeded with an Initial Administrator Account (Priority: P1)

When the system is first deployed, one administrator account already exists — identified by a pre-configured email address — so that a real person can sign in as an Administrator from day one, without any circular dependency where an administrator would be needed to create the first administrator.

**Why this priority**: Without this, the system starts in a deadlock: no one can sign in with the Administrator capability needed to grant anyone else access, including the first administrator. Everything else in this feature depends on this bootstrap step.

**Independent Test**: Deploy the system fresh, with no accounts provisioned except the configured seed administrator email, sign in with a Microsoft account using exactly that email, and verify Administrator access is granted with no manual data setup.

**Acceptance Scenarios**:

1. **Given** a freshly deployed system with only the configured seed administrator entry present, **When** the seed administrator's Microsoft account signs in, **Then** they are recognized as an Administrator, reach the administration area, and that Microsoft account's object identifier is bound to the seed entry.
2. **Given** a freshly deployed system, **When** any Microsoft account other than the configured seed email signs in before any further accounts have been added, **Then** it is denied access exactly as any non-provisioned account would be (see `002-login-and-access-control`).
3. **Given** the seed administrator has already signed in once and their object identifier is bound to the seed entry, **When** a different Microsoft account presenting the same seed email but a different object identifier attempts to sign in, **Then** access is denied.

---

### User Story 2 - Administrator Adds a New Player or Administrator by Email (Priority: P2)

A signed-in Administrator uses an in-app interface to grant a new Microsoft account access to the system, by entering its email address and choosing whether it should have the Player capability, the Administrator capability, or both.

**Why this priority**: This is the actual ongoing mechanism by which access grows beyond the single seeded administrator — the core value of this feature.

**Independent Test**: Signed in as an administrator, add a new email with the Player capability and verify that email can subsequently sign in and reach the player menu; separately add another email with the Administrator capability and verify it reaches the administration menu.

**Acceptance Scenarios**:

1. **Given** a signed-in Administrator, **When** they submit a new email with the Player capability selected, **Then** a provisioned entry is created for that email granting Player access.
2. **Given** a signed-in Administrator, **When** they submit a new email with the Administrator capability selected, **Then** a provisioned entry is created for that email granting Administrator access.
3. **Given** a signed-in Administrator, **When** they submit a new email with both capabilities selected, **Then** the resulting entry grants both.
4. **Given** a signed-in Administrator, **When** they submit an email with no capability selected, **Then** the system rejects the submission and indicates that at least one role is required.
5. **Given** a signed-in Administrator, **When** they submit an email that is not well-formed, **Then** the system rejects the submission and indicates the email is invalid.

---

### User Story 3 - Administrator Views Existing Provisioned Accounts (Priority: P3)

Before or while adding a new account, an administrator can see the current list of provisioned emails and the capability role(s) each one holds.

**Why this priority**: This supports informed decisions — avoiding accidental duplicate entries and understanding who already has access — but it is a smaller capability layered on top of the seeding and adding flows already covered.

**Independent Test**: With at least two provisioned entries existing, view the account list and verify both are shown with their correct assigned roles.

**Acceptance Scenarios**:

1. **Given** one or more provisioned entries exist, **When** an Administrator views the account list, **Then** each entry's email and assigned capability role(s) are shown.
2. **Given** an Administrator adds an email that already appears in the list, but with an additional role, **When** the addition completes, **Then** the list reflects a single, updated entry for that email rather than two separate entries.

---

### Edge Cases

- An administrator adds an email that is already provisioned (whether the original seed administrator's email or one added earlier): the existing entry's roles are updated to include any newly selected role, rather than a duplicate entry being created.
- An administrator submits the same add request twice in a row without changes: the result is the same single entry, unchanged (a no-op).
- The email is entered with different letter casing than how it was originally provisioned (or than the case Microsoft later presents at sign-in): matching and duplicate detection both treat the email as the same regardless of case, and the stored/displayed entry is kept in lowercase.
- No account-removal or role-revocation capability is included in this feature; an administrator who needs to revoke someone's access must be handled by a future capability. This is a known, deliberate scope boundary, not a defect.
- The account-provisioning interface itself is accessed by a user who does not hold the Administrator capability (e.g., via a direct link): access is denied the same way any other administrator-only area is protected (see `002-login-and-access-control`).
- A provisioned entry has no bound Microsoft object identifier yet (no account has ever signed in against it): the next sign-in attempt for that entry's email is matched by email alone, and success binds that account's object identifier to the entry for all future sign-ins.
- A sign-in presents an email that matches a provisioned entry but a Microsoft object identifier that does not match that entry's already-bound object identifier: access is denied, the same as any other non-matching sign-in. Clearing or replacing an existing binding (e.g., because a user's Microsoft account was recreated) is not supported by this feature and would need a future capability, the same deliberate scope boundary as account removal.
- An administrator re-adds an email that already has a bound object identifier (e.g., to grant it an additional role): the roles are merged as usual and the existing object identifier binding is left unchanged.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST be seeded, at first deployment, with exactly one provisioned account entry holding the Administrator capability, identified by a pre-configured email address, so the system is never in a state where no one can sign in as an administrator.
- **FR-002**: System MUST provide an interface, reachable only by a signed-in user holding the Administrator capability, for adding a new provisioned account entry by email address.
- **FR-003**: System MUST require that at least one capability role (Player and/or Administrator) is selected when adding a provisioned account entry, and MUST reject a submission with none selected.
- **FR-004**: System MUST allow an Administrator to assign both the Player and Administrator capabilities to the same email in a single entry.
- **FR-005**: System MUST validate that a submitted email address is well-formed per the RFC 5322 address specification before creating or updating a provisioned account entry, and MUST reject one that is not.
- **FR-006**: System MUST match a signed-in Microsoft account to a provisioned account entry using the account's email address only for that entry's first successful sign-in, since no other Microsoft account attribute is available before an account has ever signed in; at that first successful sign-in, the system MUST bind the account's Microsoft object identifier to the matched entry.
- **FR-007**: For every sign-in after an entry's object identifier has been bound (per FR-006), the system MUST require the presented Microsoft account's object identifier to match the entry's bound object identifier before granting access; a matching email alone MUST NOT be sufficient once an entry has a bound object identifier.
- **FR-008**: Email matching (for an entry's first, not-yet-bound sign-in) and duplicate detection MUST both be case-insensitive, and the system MUST normalize a provisioned account entry's email address to lowercase for both storage and display, regardless of the casing used when it was submitted or the casing Microsoft presents at sign-in.
- **FR-009**: When an Administrator adds an email that already has a provisioned account entry, the system MUST update that entry's assigned capability roles to include any newly selected role, rather than creating a duplicate entry, and MUST leave that entry's existing bound Microsoft object identifier (if any) unchanged.
- **FR-010**: System MUST allow an Administrator to view the current list of provisioned account entries, including each entry's email and assigned capability role(s).
- **FR-011**: Each distinct provisioning outcome (initial seed present at first run, successful new-entry add for each role combination, successful role-merge on an already-provisioned email, rejected submission with no role selected, rejected malformed email, first sign-in binding a Microsoft object identifier to a provisioned entry, successful subsequent sign-in with a matching bound object identifier, and denied sign-in when the presented object identifier does not match the entry's bound object identifier) MUST have a corresponding automated test verifying its expected behavior.

### Key Entities

- **Provisioned Account Entry**: An email address together with the capability role(s) (Player and/or Administrator) granted to it, and the Microsoft object identifier bound to it once its first successful sign-in has occurred (absent until then). This is the concrete record behind the Allow-List Entry and Capability Role concepts described in `002-login-and-access-control` — a signed-in Microsoft account is matched against these entries by email on first sign-in (binding its object identifier), and by that bound object identifier on every sign-in thereafter, to determine both whether it may sign in at all and which capabilities it holds.
- **Initial Administrator Seed**: The one Provisioned Account Entry, holding the Administrator capability, that exists automatically from first deployment so the system is never without an administrator.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Immediately after first deployment, the seeded administrator's email can sign in and reach the administration area with no manual data setup step.
- **SC-002**: An administrator can grant a new Microsoft account either capability (or both), and that account can sign in with the corresponding access on its very next sign-in attempt, with no other manual configuration step.
- **SC-003**: 100% of attempts to add a provisioned account entry with no capability role selected are rejected in testing.
- **SC-004**: 100% of attempts to add an already-provisioned email in testing result in that single entry's roles being updated, never a duplicate entry.
- **SC-005**: 100% of sign-in matching in testing resolves correctly regardless of the letter case of the account's email.
- **SC-006**: 100% of first sign-ins for a provisioned email succeed and bind that account's Microsoft object identifier in testing, and 100% of subsequent sign-in attempts presenting a mismatched object identifier for an already-bound email are denied.

## Assumptions

- The seed administrator's email address is supplied as deployment-time configuration (consistent with the application-settings-based configuration approach in `007-azure-infrastructure-provisioning`), not entered through the application's own UI, since no administrator exists yet to enter it.
- This feature is the concrete mechanism implementing the allow-list and capability-role assignment that `002-login-and-access-control` assumed exists; it does not redefine sign-in itself, only how the underlying entries are created and matched.
- Removing an account or revoking a previously granted role is explicitly out of scope for this feature; only adding/granting is specified. A future feature would need to address revocation, including the risk of a system ending up with zero administrators.
- There is no defined limit on the number of provisioned account entries an administrator may create.
- Matching is based solely on the email address presented by Microsoft identity sign-in for an entry's first sign-in, consistent with "we only match on emails"; no verification beyond that (e.g., confirming ownership via a sent email) is performed at that point.
- After an entry's first sign-in, its bound Microsoft object identifier — not email — is the authoritative match for every later sign-in, since email alone cannot rule out a different Microsoft identity later presenting the same address; email remains stored on the entry so administrators can identify accounts by inspection.
- Clearing or replacing an entry's bound object identifier (e.g., because the underlying Microsoft account was deleted and recreated) is out of scope for this feature, the same deliberate scope boundary as account removal; a future capability would need to address rebinding.
