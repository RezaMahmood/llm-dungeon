# Feature Specification: Persistent Navigation & Design Refresh

**Feature Branch**: `022-persistent-nav-redesign`

**Created**: 2026-08-30

**Status**: Draft

**Input**: User description: "the UI for admin and player should have a persistent navigation bar across the top. So if they are creating a story, they need the ability to navigate to other parts of the application. Designs have been updated in /workspaces/llmdungeon/specs/designs and there is a README in there with instructions - make use of chrome devtools to inspect these and also use the attached image as reference"

## Clarifications

### Session 2026-08-30

- Q: When an administrator clicks "Stories" in the nav bar, should it just land on the existing `/admin` placeholder page (no new content built), or does this feature need to build a minimal stories-list view there? → A: This feature must build a minimal stories-list view at `/admin` (title + list of existing stories), captured as FR-013/SC-007 (a standalone requirement, distinct from FR-010's five named screens).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Navigate away from an in-progress story without losing it (Priority: P1)

An administrator is partway through creating a new story in the multi-step wizard and needs to check something on the People screen, or peek at the existing Stories list, without abandoning or losing the draft they're building.

**Why this priority**: This is the concrete problem that triggered the feature — today, the wizard and other admin screens are dead ends reachable only through the hub menu, so leaving mid-task means backtracking and re-entering. It is the core value of "persistent navigation."

**Independent Test**: Start a new story in the wizard, fill in at least one step, click a different primary nav item (e.g. "People"), then click back into "New story." The previously entered wizard content is still present and no navigation required the browser back button or the hub menu.

**Acceptance Scenarios**:

1. **Given** an administrator is on any step of the story-creation wizard, **When** they click "Stories," "People," or "Player view" in the nav bar, **Then** they land on that section immediately, and any wizard progress already saved remains intact.
2. **Given** an administrator has just navigated away from the wizard mid-edit, **When** they return to "New story," **Then** the draft resumes with all previously saved fields populated.
3. **Given** an administrator is on the Stories, People, or Player view screen, **When** they look at the nav bar, **Then** the same nav bar (same items, same position) is present as it was on the wizard.

---

### User Story 2 - One consistent look across the app (Priority: P2)

A user (admin or player) moves between the sign-in screen, story select, an active story, the admin wizard, and the People screen, and experiences one coherent visual design throughout instead of a patchwork of styles.

**Why this priority**: The updated designs in `specs/designs` define a single shared design system (the "Modernist" reference: shared colors, typography, and layout primitives via `styles.css`). Delivering the nav bar on top of visually inconsistent screens would look unfinished; the redesign is what the nav bar is meant to sit inside of.

**Independent Test**: Visit each of the five primary screens (sign-in, story select, story play, admin wizard, People) and confirm each uses the shared color palette, typography, and component styling defined by the reference designs, with no screen left in the old styling.

**Acceptance Scenarios**:

1. **Given** a user visits the sign-in screen, **When** the page loads, **Then** it matches the visual language of `01-login.html` (typography, color tokens, layout).
2. **Given** a player views their story list, **When** the page loads, **Then** it matches `02-story-select.html`, including the persistent nav bar.
3. **Given** an administrator opens the story-creation wizard, **When** they view any step, **Then** the step content and stepper match `04-admin-wizard.html`'s styling.
4. **Given** an administrator opens the People screen, **When** they view accounts, **Then** the layout, add-account form, and per-row remove/confirm behavior match `05-admin-users.html` visually while keeping existing functionality.

---

### User Story 3 - See only the destinations you're allowed to use (Priority: P2)

A player-only user and an administrator both use the app, and each only sees nav items for the sections their account can actually access; a user who holds both capabilities can move freely between the player and admin experience.

**Why this priority**: The nav bar is the only wayfinding mechanism now, so it must not advertise destinations a user cannot open (matching today's existing permission model), while still making cross-role movement effortless for dual-capability accounts (e.g. an admin previewing the player experience).

**Independent Test**: Sign in as a player-only account and confirm no "Stories," "New story," "People," or "Admin" links appear. Sign in as an account with both capabilities and confirm the admin nav includes a "Player view" link, and the player nav includes an "Admin" link.

**Acceptance Scenarios**:

1. **Given** a signed-in user has only player capability, **When** they view the nav bar, **Then** it shows "My stories" and "Badges" only, with no admin-facing links.
2. **Given** a signed-in user has only administrator capability, **When** they view the nav bar, **Then** it shows "Stories," "New story," and "People," plus a "Player view" link.
3. **Given** a signed-in user has both capabilities, **When** they use "Player view" from the admin nav, **Then** they land on the player experience and can return via the "Admin" link shown there.

---

### User Story 4 - Always know where you are (Priority: P3)

Any signed-in user glances at the nav bar and can tell, without further clicking, which section of the app they're currently viewing.

**Why this priority**: A nav bar that doesn't indicate the current page reduces the wayfinding benefit it's meant to provide; this is a refinement on top of Story 1–3 rather than the core ask.

**Independent Test**: Load each primary screen in turn and confirm exactly one nav item is visually marked as current, matching the screen being viewed.

**Acceptance Scenarios**:

1. **Given** an administrator is on the "New story" wizard, **When** they view the nav bar, **Then** "New story" is visually distinguished as the current section.
2. **Given** a player is on "My stories," **When** they view the nav bar, **Then** "My stories" is visually distinguished as the current section.

---

### Edge Cases

- What happens when a user has neither player nor administrator capability? The nav bar shows only the brand mark, sign-out, and the user's name — no primary destination links, matching the current "no roles assigned yet" state.
- What happens to text the administrator typed on the active wizard step but had not yet saved when they click a nav item? Existing per-step save behavior is unchanged by this feature — only content already saved (via autosave or the explicit step Save action) is guaranteed to persist; this feature does not add a new unsaved-changes warning.
- How does the system handle a very long story title or a long user display name in the nav bar or the play-screen title bar? Text truncates/ellipsizes gracefully without breaking the bar's layout or pushing other controls out of view.
- What happens on the active story-play screen? The full nav bar is replaced by a compact title bar (story title + return-to-story-select + pause/exit), by design, to preserve the full-height reading area — this is not a missing nav bar, it's the documented exception.
- What happens if a user's session expires while they click a nav link? Existing authentication handling applies (redirect to sign-in), unchanged by this feature.
- What happens on the admin "Stories" list when no stories exist yet? An empty state is shown (no error), consistent with the list only ever growing as stories are generated via the wizard.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST display a persistent top navigation bar on every authenticated screen except the active story-play screen.
- **FR-002**: For administrators, the nav bar MUST provide links to "Stories," "New story," "People," and "Player view." "Stories" MUST be a distinct destination from "New story" (see FR-013), not an alias for the same wizard screen.
- **FR-003**: For players, the nav bar MUST provide links to "My stories" and "Badges," plus an "Admin" link when the signed-in account also holds administrator capability.
- **FR-004**: The nav bar MUST always show a "Sign out" control and the signed-in user's name, right-aligned.
- **FR-005**: Users MUST be able to reach any other primary section from within the story-creation wizard, at any step, without losing wizard progress that was already saved.
- **FR-006**: On the active story-play screen, the full nav bar MUST be replaced by a compact title bar (story title, return-to-story-select control, pause/exit) that preserves the full-height story reading area.
- **FR-007**: The nav bar MUST visually indicate which section is currently active (e.g., distinct styling and `aria-current` on the matching link).
- **FR-008**: Navigation items MUST be shown or hidden according to the signed-in user's granted capabilities, consistent with existing capability checks already enforced for each route.
- **FR-009**: The sign-in (unauthenticated) screen MUST NOT display the persistent nav bar.
- **FR-010**: All five primary screens (sign-in, story select, story play, story-creation wizard, People/account management) MUST be restyled to use the shared design system referenced in `specs/designs` (color palette, typography, spacing, and component styling), replacing current styling.
- **FR-011**: The People screen's existing one-account-at-a-time remove-with-confirmation behavior MUST be preserved through the redesign.
- **FR-012**: The redesign and nav bar addition MUST NOT change existing functional behavior (data operations, validations, capability enforcement) of any screen — this is a visual and navigational change only.
- **FR-013**: The "Stories" nav link MUST land on a minimal admin stories-list view (at `/admin`) showing at least each existing story's title and status, sourced from the existing admin story-listing capability. When no stories exist yet, the view MUST show an empty state rather than an error.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: From any admin screen, including any step of the story-creation wizard, a user can reach any other primary section in a single click, with no reliance on the browser back button.
- **SC-002**: 100% of authenticated screens except the active story-play screen present the same navigation bar, with the current section always visually identifiable.
- **SC-003**: Story-wizard progress that was already saved is never lost (0% data loss) when a user leaves via the nav bar and later returns to the wizard.
- **SC-004**: Across player-only, admin-only, and dual-capability accounts, nav items outside a user's granted capabilities never appear.
- **SC-005**: All five primary screens present one consistent visual design language (shared color palette and typography), eliminating the prior visual inconsistency between screens.
- **SC-006**: Players in an active story session retain the same usable story-reading area as before this change, with no reduction caused by the new title bar.
- **SC-007**: From the admin nav, "Stories" and "New story" lead to two visibly different screens — a list of existing stories versus the creation wizard — with the list reflecting the current set of stories with no manual refresh workaround needed beyond a normal page load.

## Assumptions

- The HTML/CSS files and README in `specs/designs` (the "Modernist" reference design system, vendored `styles.css`, Archivo typeface) are the authoritative visual and structural reference for both the nav bar and the wider screen redesign.
- Desktop/web browser viewport is the primary target; this feature does not add responsive/mobile-specific behavior beyond what the app already supports.
- Existing story-wizard save behavior (autosave plus the explicit per-step Save action) is unchanged; the nav bar only makes it possible to leave and return to the wizard, it does not alter when or how draft content is persisted.
- Capability-based visibility of nav items reuses the existing capability model already enforced by the app's route protections; this feature introduces no new permission logic.
- The story-play screen's compact title bar (in place of the full nav bar) is an intentional, documented exception, not a gap in the persistent-nav requirement.
