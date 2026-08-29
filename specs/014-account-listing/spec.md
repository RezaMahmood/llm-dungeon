# Feature Specification: Account Listing

**Feature Branch**: `014-account-listing`

**Created**: 2026-08-29

**Status**: Draft

**Input**: Split out of `003-account-provisioning` on 2026-08-29, so that spec covers at most two user stories. This spec covers the third user story originally specified there — "Administrator Views Existing Provisioned Accounts" — unchanged in substance, with its own Requirements/Success Criteria/Assumptions scoped to viewing only.

**Split**: This spec depends entirely on `003-account-provisioning` for the underlying Provisioned Account Entry data and the seed/add mechanics that create and update it. It adds no new way of creating or changing an entry — only of seeing what already exists.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Administrator Views Existing Provisioned Accounts (Priority: P1)

Before or while adding a new account, an administrator can see the current list of provisioned emails and the capability role(s) each one holds.

**Why this priority**: This supports informed decisions — avoiding accidental duplicate entries and understanding who already has access — layered on top of the seeding and adding flows specified in `003-account-provisioning`.

**Independent Test**: With at least two provisioned entries existing, view the account list and verify both are shown with their correct assigned roles.

**Acceptance Scenarios**:

1. **Given** one or more provisioned entries exist, **When** an Administrator views the account list, **Then** each entry's email and assigned capability role(s) are shown.
2. **Given** an Administrator adds an email that already appears in the list, but with an additional role (per `003-account-provisioning`'s role-merge behavior), **When** the addition completes, **Then** the list reflects a single, updated entry for that email rather than two separate entries.

---

### Edge Cases

- No provisioned account entries exist yet beyond the initial administrator seed: the list shows exactly that one entry, not an empty or broken state.
- The account-listing interface itself is accessed by a user who does not hold the Administrator capability (e.g., via a direct link): access is denied the same way any other administrator-only area is protected (see `002-login-and-access-control`).
- An entry's email was stored in lowercase per `003-account-provisioning`'s normalization: the list displays it in that normalized, lowercase form, regardless of the casing originally submitted.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow an Administrator to view the current list of provisioned account entries, including each entry's email and assigned capability role(s).
- **FR-002**: The list MUST reflect the current, deduplicated state of provisioned account entries as maintained by `003-account-provisioning` — a merged entry appears once, with its full set of roles, never as separate entries per role or per add action.
- **FR-003**: System MUST reject access to the account-listing interface for any user who does not hold the Administrator capability, consistent with `002-login-and-access-control`.
- **FR-004**: Each distinct listing outcome (list shown with one or more entries, list correctly reflects a role-merge on an already-provisioned email, access denied to a non-administrator) MUST have a corresponding automated test verifying its expected behavior.

### Key Entities

- **Provisioned Account Entry**: Defined and created in `003-account-provisioning`; this spec only reads and displays it, adding no new fields or state.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An administrator can view every currently provisioned email and its assigned role(s) in one place, with no manual data inspection required.
- **SC-002**: 100% of role-merges performed via `003-account-provisioning`'s add flow are reflected in the list as a single updated entry, in testing.

## Assumptions

- This spec adds no new data or mutation capability; it is a read-only view over the Provisioned Account Entry data defined and maintained by `003-account-provisioning`.
- There is no pagination, search, or filtering requirement specified here, consistent with the small expected number of provisioned entries (see `007-azure-infrastructure-provisioning`'s ~5-10 user scale assumption); a future feature would need to address it if that scale assumption changes.
