# Feature Specification: Login and Access Control

**Feature Branch**: `002-login-and-access-control`

**Created**: 2026-08-28

**Status**: Draft

**Reorganized from**: originally `002-role-based-login`, renumbered to lead the spec set as the foundational, entry-point capability every other feature depends on.

**Input**: User description: "Login. Login will be done using a player's Microsoft account - something like emailname@outlook.com or emailname@gmail.com - the actual email address shouldn't matter as long as it is connected to Microsoft. The application will have to identify whether the logged in user is a player or an administrator. If they are an administrator they need to be able to see a menu item that leads them to an administration page. If they are a player they need to be able to see a menu item that leads them to start or continue a game."

**Design Reference**: [specs/designs/01-login.html](../designs/01-login.html) (see [specs/designs/README.md](../designs/README.md))

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Player Signs In and Reaches the Game Menu (Priority: P1)

A person with a Microsoft account and Player access signs in to the application and is taken to a menu that lets them start a new game or continue one already in progress.

**Why this priority**: This is the primary path for the application's main audience. Without it, no player can ever reach the game.

**Independent Test**: With one allow-listed Microsoft account granted the Player capability, sign in and verify a menu item to start/continue a game is shown, and no administration menu item is shown.

**Acceptance Scenarios**:

1. **Given** a Microsoft account that is allow-listed and holds the Player capability, **When** the person signs in, **Then** the system authenticates them and shows a menu item leading to starting or continuing a game.
2. **Given** a signed-in user with only the Player capability, **When** they view the application menu, **Then** no administration menu item is shown.
3. **Given** a signed-in Player who has an in-progress game, **When** they select the game menu item, **Then** they are taken to continue that in-progress game rather than being forced to start over.

---

### User Story 2 - Administrator Signs In and Reaches the Administration Page (Priority: P2)

A person with a Microsoft account and Administrator access signs in and is shown a menu item that leads them to an administration page.

**Why this priority**: Administration capability is required to manage the application (e.g., story content), but it serves fewer people than gameplay and depends on the same sign-in mechanism proven in User Story 1.

**Independent Test**: With one allow-listed Microsoft account granted the Administrator capability, sign in and verify a menu item to the administration page is shown.

**Acceptance Scenarios**:

1. **Given** a Microsoft account that is allow-listed and holds the Administrator capability, **When** the person signs in, **Then** the system authenticates them and shows a menu item leading to the administration page.
2. **Given** a signed-in user who holds both the Player and Administrator capabilities, **When** they view the application menu, **Then** both the game menu item and the administration menu item are shown.

---

### User Story 3 - Unauthorized Microsoft Account Is Denied Access (Priority: P3)

A person with a valid, working Microsoft account that is not on the application's allow-list attempts to sign in and is denied access.

**Why this priority**: This enforces the project's no-public-access requirement. It is tested last because it depends on the sign-in mechanism from User Story 1/2 existing, but the denial behavior itself is a hard requirement, not an optional enhancement.

**Independent Test**: Attempt sign-in with a valid Microsoft account that has not been added to the allow-list and verify access is denied and no menu (game or administration) is ever shown.

**Acceptance Scenarios**:

1. **Given** a Microsoft account not on the allow-list, **When** the person attempts to sign in, **Then** the system denies access and displays a clear message rather than showing any part of the application.
2. **Given** a denied sign-in attempt, **When** the response is shown to the person, **Then** it does not reveal whether their specific account is known to the system, only that access is not granted.

---

### Edge Cases

- A signed-in, allow-listed user holds neither the Player nor the Administrator capability: the system shows a clear message that no access has been provisioned for them yet, rather than an empty or broken menu.
- A user's capability assignment changes (e.g., Administrator access is added or removed) while they are signed in: the change takes effect on their next sign-in or menu refresh, not necessarily mid-session.
- The Microsoft sign-in step itself fails or is cancelled by the user (e.g., they close the identity provider's login window): the application returns them to a pre-login state with the option to try again, rather than an error page.
- A user attempts to reach the administration page or the game menu directly (e.g., via a bookmarked link) without the corresponding capability: access is denied the same as if the menu item were never shown.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow a person to sign in using a Microsoft account, regardless of whether the account's email domain is a Microsoft-operated domain (e.g., outlook.com) or a non-Microsoft domain (e.g., gmail.com) federated through Microsoft identity sign-in.
- **FR-002**: System MUST deny sign-in access to any Microsoft account that is not on the application's pre-approved allow-list, and MUST NOT expose any application content, menu, or page to a denied account.
- **FR-003**: System MUST determine, for each successfully authenticated user, which capability role(s) — Player, Administrator, or both — are assigned to that identity.
- **FR-004**: System MUST show a menu item leading to starting or continuing a game to any signed-in user who holds the Player capability.
- **FR-005**: System MUST show a menu item leading to the administration page to any signed-in user who holds the Administrator capability.
- **FR-006**: System MUST NOT show the administration menu item to a signed-in user who does not hold the Administrator capability.
- **FR-007**: System MUST NOT show the game start/continue menu item to a signed-in user who does not hold the Player capability.
- **FR-008**: System MUST show both menu items to a signed-in user who holds both capabilities.
- **FR-009**: System MUST enforce capability-based access at the destination (administration page, game menu) as well as at the menu display, so a user cannot reach a page by bypassing the menu without holding the matching capability.
- **FR-010**: System MUST display a clear, human-readable message when a successfully authenticated user holds neither capability, and a clear, human-readable message when sign-in is denied because the account is not allow-listed.
- **FR-011**: System MUST maintain the user's authenticated session across normal in-application navigation, so moving between menu items does not require signing in again.
- **FR-012**: Each distinct login outcome (Player-only sign-in, Administrator-only sign-in, dual-capability sign-in, no-capability sign-in, and denied/unauthorized sign-in) MUST have a corresponding automated test verifying its expected behavior.

### Key Entities

- **User Identity**: A Microsoft account that has successfully signed in to the application; may hold zero or more Capability Roles.
- **Capability Role**: Either "Player" or "Administrator" — determines which menu items and application areas a User Identity is permitted to reach. A single User Identity may hold one, both, or (transiently) neither.
- **Allow-List Entry**: The record that determines whether a given Microsoft account may sign in to the application at all, independent of which Capability Role(s) it has been granted.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user with the Player capability sees the game start/continue menu item immediately after completing Microsoft sign-in, with no additional manual steps.
- **SC-002**: A user with the Administrator capability sees the administration menu item immediately after completing Microsoft sign-in, with no additional manual steps.
- **SC-003**: 100% of sign-in attempts from Microsoft accounts not on the allow-list are denied, with zero instances of a denied account reaching any menu, page, or application content in testing.
- **SC-004**: Across all tested capability combinations (Player only, Administrator only, both, neither), a user is never shown a menu item for a capability they do not hold.
- **SC-005**: A user holding both capabilities can reach both the administration page and the game start/continue flow in the same session without signing in more than once.

## Assumptions

- Player and Administrator are independently assignable capabilities on the same Microsoft identity — a user may hold one, both, or (until provisioned) neither.
- Being on the sign-in allow-list only grants the ability to authenticate; it does not by itself grant either capability. Capability assignment is a separate, explicit step performed by whoever administers access (consistent with the project's access-control principles).
- "Connected to Microsoft" is satisfied by completing Microsoft's identity sign-in flow, whether the underlying account is a Microsoft-operated address (e.g., outlook.com, hotmail.com) or another email address federated through Microsoft identity sign-in (e.g., a Gmail address used to sign in with a Microsoft account or as an invited external identity).
- Standard web session duration/expiry practices apply; no specific session length was requested.
- Menu item labels and administration-page contents beyond "leads to the administration page" are out of scope for this feature and are defined by the features that build those destinations (see `005-story-publishing`, `012-story-editing-and-review`, and related specs).
