# Feature Specification: Story Import

**Feature Branch**: `011-story-import`

**Created**: 2026-08-28

**Status**: Draft

**Reorganized from**: originally User Story 6 within `003-game-setup-and-authoring`, split out as its own domain since uploading a pre-built configuration is a distinct capability from guided/conversational creation (`004-story-creation`).

**Input**: User description: "Upload story config file: Allow manual upload of story config file. Validate config file for structure and content. Select whether to overwrite existing story or create new. If new then provide name for story/game - this is the title that becomes visible for Players."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Administrator Imports a Story via Configuration File (Priority: P1)

An administrator who already has a story configuration file uploads it directly. The system validates its structure and content, and the administrator chooses whether it becomes a brand-new story (providing the title players will see) or overwrites an existing one.

**Why this priority**: This is the alternate, power-user content pipeline alongside guided creation — valuable for administrators who already have content prepared outside the app, or who want to move a story between environments.

**Independent Test**: Upload one valid story configuration file as a new story with a provided title, and separately upload a second valid file chosen to overwrite an existing story, verifying each outcome; then upload one deliberately invalid file and verify it is rejected with a specific reason.

**Acceptance Scenarios**:

1. **Given** an administrator uploads a story configuration file, **When** the system checks it, **Then** it is validated for correct structure and content before anything is persisted.
2. **Given** an uploaded file fails validation, **When** validation completes, **Then** the system rejects the upload, leaves any existing story untouched, and reports specifically what is wrong.
3. **Given** an uploaded file passes validation, **When** the administrator chooses to create a new story from it, **Then** the system requires a title for that story and persists it as a new, distinct, unpublished adventure.
4. **Given** an uploaded file passes validation, **When** the administrator chooses to overwrite an existing story, **Then** the system replaces that story's configuration with the uploaded one.

---

### Edge Cases

- An administrator's uploaded file uses a valid structure but references character types inconsistently (e.g., duplicate names): validation rejects it with a specific reason.
- An administrator attempts to overwrite an existing story with an uploaded file whose content is for a fundamentally different adventure: the system still permits the overwrite (it does not attempt to judge topical consistency) but requires explicit confirmation of the overwrite target before proceeding.
- An administrator uploads a file that is well-formed but missing a required element (e.g., no completion criteria defined): validation rejects it and names the missing element.
- An administrator uploads the exact same file twice in a row as two separate new stories: both are accepted as distinct stories provided each is given its own title.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow an administrator to upload a story configuration file directly.
- **FR-002**: System MUST validate an uploaded file's structure and content before persisting anything from it.
- **FR-003**: System MUST reject an uploaded file that fails validation, leave any existing story unmodified, and report the specific reason for rejection.
- **FR-004**: System MUST, for an uploaded file that passes validation, let the administrator choose to either create a new story or overwrite an existing one.
- **FR-005**: System MUST require a title (to be shown to players) when an administrator creates a new story from an uploaded file.
- **FR-006**: System MUST require explicit confirmation of the overwrite target before replacing an existing story's configuration.
- **FR-007**: A story newly created via import MUST default to unpublished, so it is not visible to players until an administrator explicitly publishes it (see `005-story-publishing`).
- **FR-008**: Each distinct import outcome (successful new-story import, successful overwrite import, validation rejection, missing-title rejection) MUST have a corresponding automated test verifying its expected behavior.

### Key Entities

- **Story Configuration File**: A complete, structured definition of an adventure — setting, plot, character types, and completion criteria — suitable for upload, that must pass validation before being persisted as a Story.
- **Story**: The persisted adventure that results from a successful import, either newly created (with an administrator-supplied title) or as an overwritten existing story.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of uploaded story configuration files that fail validation in testing are rejected with a specific, actionable reason, and never leave an existing story partially modified.
- **SC-002**: 100% of successful new-story imports in testing require and retain an administrator-supplied title before the story exists in the catalog.
- **SC-003**: 100% of successful overwrite imports in testing fully replace the target story's prior configuration with no residual data from the previous version.

## Assumptions

- Validation covers structural correctness (required fields, correct format) and basic content consistency (e.g., no duplicate character type names); it does not evaluate narrative quality.
- The file format and schema for a story configuration are defined by whichever process also produces them via guided creation (`004-story-creation`), so an exported/downloaded story (see `012-story-editing-and-review`) can always be re-imported here.
- This spec covers the import mechanism itself; making an imported story visible to players is a separate, explicit action (see `005-story-publishing`).
