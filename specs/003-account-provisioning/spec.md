# Feature Specification: Account Provisioning

**Feature Branch**: `003-account-provisioning`

**Created**: 2026-08-28

**Status**: Draft

**Input**: User description: "The application is seeded with an initial administrator account. Thereafter the administrator should have an interface that allows them to add more players or administrators to the system. minimum requirement is that it must be a microsoft account and we only match on emails."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - System Is Seeded with an Initial Administrator Account (Priority: P1)

When the system is first deployed, one administrator account already exists — identified by a pre-configured email address — so that a real person can sign in as an Administrator from day one, without any circular dependency where an administrator would be needed to create the first administrator.

**Why this priority**: Without this, the system starts in a deadlock: no one can sign in with the Administrator capability needed to grant anyone else access, including the first administrator. Everything else in this feature depends on this bootstrap step.

**Independent Test**: Deploy the system fresh, with no accounts provisioned except the configured seed administrator email, sign in with a Microsoft account using exactly that email, and verify Administrator access is granted with no manual data setup.

**Acceptance Scenarios**:

1. **Given** a freshly deployed system with only the configured seed administrator entry present, **When** the seed administrator's Microsoft account signs in, **Then** they are recognized as an Administrator and reach the administration area.
2. **Given** a freshly deployed system, **When** any Microsoft account other than the configured seed email signs in before any further accounts have been added, **Then** it is denied access exactly as any non-provisioned account would be (see `002-login-and-access-control`).

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
- The email is entered with different letter casing than how it was originally provisioned (or than the case Microsoft later presents at sign-in): matching and duplicate detection both treat the email as the same regardless of case.
- No account-removal or role-revocation capability is included in this feature; an administrator who needs to revoke someone's access must be handled by a future capability. This is a known, deliberate scope boundary, not a defect.
- The account-provisioning interface itself is accessed by a user who does not hold the Administrator capability (e.g., via a direct link): access is denied the same way any other administrator-only area is protected (see `002-login-and-access-control`).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST be seeded, at first deployment, with exactly one provisioned account entry holding the Administrator capability, identified by a pre-configured email address, so the system is never in a state where no one can sign in as an administrator.
- **FR-002**: System MUST provide an interface, reachable only by a signed-in user holding the Administrator capability, for adding a new provisioned account entry by email address.
- **FR-003**: System MUST require that at least one capability role (Player and/or Administrator) is selected when adding a provisioned account entry, and MUST reject a submission with none selected.
- **FR-004**: System MUST allow an Administrator to assign both the Player and Administrator capabilities to the same email in a single entry.
- **FR-005**: System MUST validate that a submitted email address is well-formed before creating or updating a provisioned account entry, and MUST reject one that is not.
- **FR-006**: System MUST match a signed-in Microsoft account to a provisioned account entry using the account's email address only — no other Microsoft account attribute (e.g., tenant or object identifier) is used as the matching key.
- **FR-007**: Email matching and duplicate detection MUST both be case-insensitive.
- **FR-008**: When an Administrator adds an email that already has a provisioned account entry, the system MUST update that entry's assigned capability roles to include any newly selected role, rather than creating a duplicate entry.
- **FR-009**: System MUST allow an Administrator to view the current list of provisioned account entries, including each entry's email and assigned capability role(s).
- **FR-010**: Each distinct provisioning outcome (initial seed present at first run, successful new-entry add for each role combination, successful role-merge on an already-provisioned email, rejected submission with no role selected, rejected malformed email) MUST have a corresponding automated test verifying its expected behavior.

### Key Entities

- **Provisioned Account Entry**: An email address together with the capability role(s) (Player and/or Administrator) granted to it. This is the concrete record behind the Allow-List Entry and Capability Role concepts described in `002-login-and-access-control` — a signed-in Microsoft account is matched against these entries by email to determine both whether it may sign in at all and which capabilities it holds.
- **Initial Administrator Seed**: The one Provisioned Account Entry, holding the Administrator capability, that exists automatically from first deployment so the system is never without an administrator.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Immediately after first deployment, the seeded administrator's email can sign in and reach the administration area with no manual data setup step.
- **SC-002**: An administrator can grant a new Microsoft account either capability (or both), and that account can sign in with the corresponding access on its very next sign-in attempt, with no other manual configuration step.
- **SC-003**: 100% of attempts to add a provisioned account entry with no capability role selected are rejected in testing.
- **SC-004**: 100% of attempts to add an already-provisioned email in testing result in that single entry's roles being updated, never a duplicate entry.
- **SC-005**: 100% of sign-in matching in testing resolves correctly regardless of the letter case of the account's email.

## Assumptions

- The seed administrator's email address is supplied as deployment-time configuration (consistent with the application-settings-based configuration approach in `007-azure-infrastructure-provisioning`), not entered through the application's own UI, since no administrator exists yet to enter it.
- This feature is the concrete mechanism implementing the allow-list and capability-role assignment that `002-login-and-access-control` assumed exists; it does not redefine sign-in itself, only how the underlying entries are created and matched.
- Removing an account or revoking a previously granted role is explicitly out of scope for this feature; only adding/granting is specified. A future feature would need to address revocation, including the risk of a system ending up with zero administrators.
- There is no defined limit on the number of provisioned account entries an administrator may create.
- Matching is based solely on the email address presented by Microsoft identity sign-in; no verification beyond that (e.g., confirming ownership via a sent email) is performed, consistent with "we only match on emails."
