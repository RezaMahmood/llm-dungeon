# Feature Specification: Story Editing and Review

**Feature Branch**: `012-story-editing-and-review`

**Created**: 2026-08-28

**Status**: Draft

**Reorganized from**: originally User Story 8 within `003-game-setup-and-authoring`, split out as its own domain since ongoing content maintenance (reviewing, editing, viewing) is a distinct workflow from initial creation or import.

**Input**: User description: "Edit an existing game: view list of games/stories that are available - need to also see published status. Work with the LLM to update the story. Ability to Download the story config for manual editing and then allow re-upload and overwrite. The entire story configuration file should be viewable by the administrator."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Administrator Reviews Existing Stories (Priority: P1)

An administrator views the list of all existing stories, each shown with its published/unpublished status, and can open any one of them to view its entire configuration.

**Why this priority**: Reviewing what already exists is a prerequisite for every other maintenance action, and is valuable on its own as a way to audit content.

**Independent Test**: With at least one published and one unpublished story existing, view the story list and confirm both are shown with correct status, then open one and confirm its full configuration is displayed.

**Acceptance Scenarios**:

1. **Given** an administrator views the list of stories, **When** the list is displayed, **Then** each story shows its published/unpublished status alongside its identifying details.
2. **Given** an administrator selects an existing story, **When** they choose to view it, **Then** the entire story configuration is shown to them.

---

### User Story 2 - Administrator Edits an Existing Story (Priority: P2)

An administrator updates an existing story either conversationally, describing the change they want and having the LLM apply it, or by downloading the story's configuration file, editing it manually, and re-uploading it to overwrite the original.

**Why this priority**: Content needs upkeep after it exists, but this depends on User Story 1 (finding and viewing the story to edit) and on stories already existing via creation or import.

**Independent Test**: With one existing story, make an edit via the LLM-assisted flow and verify the change is reflected in the story's configuration; separately, download that story's configuration, edit it, re-upload choosing to overwrite, and verify the change is reflected.

**Acceptance Scenarios**:

1. **Given** an administrator selects an existing story to edit conversationally, **When** they describe the change they want, **Then** the system updates the story's configuration accordingly using the LLM.
2. **Given** an administrator downloads a story's configuration file, **When** the download completes, **Then** the file accurately represents that story's current, complete configuration.
3. **Given** an administrator edits a downloaded configuration file and re-uploads it choosing to overwrite, **When** the upload passes validation, **Then** the story's configuration is replaced with the edited version.

---

### Edge Cases

- An administrator downloads a story configuration, makes no changes, and re-uploads it: the overwrite succeeds and results in an equivalent story (a no-op update).
- An administrator's conversational edit request is ambiguous or would remove a required element (e.g., "delete all character types"): the system asks for confirmation or clarification rather than silently applying a change that would leave the story incomplete.
- An administrator attempts to edit a story that another administrator is concurrently editing: the system ensures the two sets of changes do not silently overwrite one another (e.g., the second edit is applied on top of the latest saved state, not a stale copy).
- An administrator views a story's full configuration for one that has never been edited since creation: the view reflects exactly what was originally generated or imported.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow an administrator to view a list of all stories showing, at minimum, each story's identifying details and its published/unpublished status.
- **FR-002**: System MUST allow an administrator to view the complete configuration of any existing story.
- **FR-003**: System MUST allow an administrator to update an existing story's configuration through an LLM-assisted conversational edit.
- **FR-004**: System MUST allow an administrator to download an existing story's complete configuration as a file.
- **FR-005**: System MUST allow an administrator to re-upload an edited configuration file to overwrite the story it came from, subject to the same validation as any other import (see `011-story-import`).
- **FR-006**: System MUST apply an edit (conversational or re-upload) on top of the story's current saved state, so concurrent edits do not silently discard one another's changes.
- **FR-007**: Editing a story MUST NOT change its published/unpublished status; that remains governed exclusively by `005-story-publishing`.
- **FR-008**: Each distinct maintenance action (list view, full-configuration view, conversational edit, download, re-upload overwrite) MUST have a corresponding automated test verifying its expected behavior.

### Key Entities

- **Story**: The existing adventure being reviewed or edited; its identifying details, published status, and complete configuration are all visible to an administrator.
- **Story Configuration File**: The downloadable, re-uploadable representation of a Story's complete configuration, produced by the download action and consumed by the re-upload/overwrite action.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An administrator can locate any existing story and view its full configuration in two actions or fewer from the story list.
- **SC-002**: 100% of downloaded story configuration files in testing can be re-uploaded and successfully overwrite their originating story without data loss.
- **SC-003**: 100% of conversational edits in testing are reflected in the story's configuration without altering elements the administrator did not ask to change.

## Assumptions

- This spec reuses the validation and overwrite mechanism defined in `011-story-import` for the re-upload path rather than defining a separate one.
- There is no version history requirement; each edit (conversational or re-upload) replaces the prior configuration rather than being tracked as a separate revision.
- Concurrent-edit conflicts are resolved by last-write-wins on top of the latest saved state, with no merge-conflict UI required at this stage.
