# Feature Specification: Story Import

**Feature Branch**: `011-story-import`

**Created**: 2026-08-28

**Status**: Draft — mechanism delivered by `012-story-editing-and-review` (see Delivery Status below)

**Reorganized from**: originally User Story 6 within `003-game-setup-and-authoring`, split out as its own domain since uploading a pre-built configuration is a distinct capability from guided/conversational creation (`004-story-creation-done`).

**Input**: User description: "Upload story config file: Allow manual upload of story config file. Validate config file for structure and content. Select whether to overwrite existing story or create new. If new then provide name for story/game - this is the title that becomes visible for Players."

## Delivery Status

**Recorded 2026-09-06.** `012-story-editing-and-review` requires download → manual edit →
re-upload inside its own scope (`012` FR-005, FR-008), and its spec defers to this one for the
validation and overwrite rules. Because this feature had no plan when `012` was planned, the
shared mechanism — the story configuration file format, its validator, and the
create-or-overwrite import endpoint — is being **built by `012`**, conforming to the
requirements below rather than defining separate rules. See
[`specs/012-story-editing-and-review/research.md`](../012-story-editing-and-review/research.md) §1.

| Requirement | Delivered by `012` |
|---|---|
| FR-001 upload a file directly | ✅ upload control on the administrator's story list |
| FR-002 validate structure and content before persisting | ✅ shared validator |
| FR-003 reject with a specific reason, leaving existing stories untouched | ✅ |
| FR-004 routing by the file's story id (as revised 2026-09-06) | ✅ |
| FR-005 administrator-supplied title on every create | ✅ |
| FR-006 explicit confirmation of the overwrite target | ✅ |
| FR-007 imported story defaults to unpublished | ✅ |
| FR-008 automated test per import outcome | ✅ tests live under `012`'s test files |

**What remains for this feature**: nothing functional. This spec MUST NOT define a second file
format, a second validator, or a second import endpoint. If it is planned later, it is limited to
additional entry surfaces or acceptance coverage layered on `012`'s mechanism.

## Clarifications

### Session 2026-09-06

- Q: Should the administrator choose "create new" vs "overwrite" in the UI, or should the uploaded file decide? → A: The file decides — the story id inside the uploaded document is the sole identifier of the story it refers to, and there is no separate chooser. No id means a new story (with an administrator-supplied title); an id matching an existing story means an upsert of that story, after explicit confirmation of the target. This is the simplest rule for what is an inherently manual, occasional import.
- Q: When the uploaded file carries an id that matches no existing story, should the system generate a fresh id and import it as a new story anyway? → A: No — reject it with a specific reason, consistent with `012-story-editing-and-review`'s edge case. An id that matches nothing usually means a real mistake (the wrong file, or a story that was deleted); importing it silently would hide that. The administrator removes the id and uploads it again to create a new story, which is a one-line, explicit statement of intent. Nothing is ever persisted under an id that does not already exist.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Administrator Imports a Story via Configuration File (Priority: P1)

An administrator who already has a story configuration file uploads it directly. The system validates its structure and content, then routes it by the story id inside the file: no id creates a brand-new story under a title the administrator provides, an id matching an existing story overwrites that story once the administrator confirms the target, and an id matching nothing is rejected rather than imported.

**Why this priority**: This is the alternate, power-user content pipeline alongside guided creation — valuable for administrators who already have content prepared outside the app, or who want to move a story between environments.

**Independent Test**: Upload one valid id-less story configuration file with a provided title and verify a new story results; separately upload a valid file whose id matches an existing story, confirm the target, and verify that story is overwritten; then upload one deliberately invalid file and verify it is rejected with a specific reason.

**Acceptance Scenarios**:

1. **Given** an administrator uploads a story configuration file, **When** the system checks it, **Then** it is validated for correct structure and content before anything is persisted.
2. **Given** an uploaded file fails validation, **When** validation completes, **Then** the system rejects the upload, leaves any existing story untouched, and reports specifically what is wrong.
3. **Given** an uploaded file passes validation and carries no story id, **When** the administrator uploads it, **Then** the system requires a title for that story and persists it as a new, distinct, unpublished adventure.
4. **Given** an uploaded file passes validation and carries a story id matching an existing story, **When** the administrator confirms that overwrite target, **Then** the system replaces that story's configuration with the uploaded one.
5. **Given** an uploaded file passes validation and carries a story id that matches no existing story, **When** the administrator uploads it, **Then** the system rejects it with a specific reason and creates nothing — neither under the id in the file nor under a newly generated one — telling the administrator they can remove the id to upload it as a new story.

---

### Edge Cases

- An administrator's uploaded file uses a valid structure but references character types inconsistently (e.g., duplicate names): validation rejects it with a specific reason.
- An administrator attempts to overwrite an existing story with an uploaded file whose content is for a fundamentally different adventure: the system still permits the overwrite (it does not attempt to judge topical consistency) but requires explicit confirmation of the overwrite target before proceeding.
- An administrator uploads a file that is well-formed but missing a required element (e.g., no completion criteria defined): validation rejects it and names the missing element.
- An administrator uploads a file whose id matches no existing story (the story was deleted, or the file came from elsewhere): the upload is rejected with a specific reason rather than imported under that id or under a new one; removing the id and uploading again creates a new story.
- An administrator uploads the exact same file twice in a row as two separate new stories: both are accepted as distinct stories provided each is given its own title.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow an administrator to upload a story configuration file directly.
- **FR-002**: System MUST validate an uploaded file's structure and content before persisting anything from it.
- **FR-003**: System MUST reject an uploaded file that fails validation, leave any existing story unmodified, and report the specific reason for rejection.
- **FR-004**: System MUST route an uploaded file that passes validation by the story id inside the file, which is the sole identifier of the story it refers to; there MUST NOT be a separate create-new-versus-overwrite chooser (revised 2026-09-06). Specifically: no id in the file MUST create a new story; an id matching an existing story MUST overwrite (upsert) that story; and an id matching no existing story MUST be rejected with a specific reason, persisting nothing — not under the id in the file, and not under a newly generated one.
- **FR-005**: System MUST require a title (to be shown to players) when an uploaded file with no story id creates a new story.
- **FR-006**: System MUST require explicit confirmation of the overwrite target before replacing an existing story's configuration.
- **FR-007**: A story newly created via import MUST default to unpublished, so it is not visible to players until an administrator explicitly publishes it (see `005-story-publishing-done`).
- **FR-008**: Each distinct import outcome (successful new-story import from an id-less file, successful overwrite import of an id-matched story, unmatched-id rejection, validation rejection, missing-title rejection, missing-overwrite-confirmation rejection) MUST have a corresponding automated test verifying its expected behavior.

### Key Entities

- **Story Configuration File**: A complete, structured definition of an adventure — setting, plot, character types, and completion criteria — suitable for upload, that must pass validation before being persisted as a Story. It optionally carries the story id that routes it per FR-004; that id is the sole identifier of the story it refers to. Its concrete format is the one produced by `012-story-editing-and-review`'s download (see Delivery Status).
- **Story**: The persisted adventure that results from a successful import, either newly created (with an administrator-supplied title) or as an overwritten existing story.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of uploaded story configuration files that fail validation in testing are rejected with a specific, actionable reason, and never leave an existing story partially modified.
- **SC-002**: 100% of successful new-story imports in testing require and retain an administrator-supplied title before the story exists in the catalog.
- **SC-003**: 100% of successful overwrite imports in testing fully replace the target story's prior configuration with no residual data from the previous version.

## Assumptions

- Validation covers structural correctness (required fields, correct format) and basic content consistency (e.g., no duplicate character type names); it does not evaluate narrative quality.
- The file format and schema for a story configuration are defined by whichever process also produces them — in practice `012-story-editing-and-review`'s download of a story created via guided creation (`004-story-creation-done`) — so an exported/downloaded story can always be re-imported here.
- Routing is decided entirely by the file's story id (FR-004, revised 2026-09-06); the administrator is never asked to pick create-versus-overwrite, and the system never guesses a target by matching titles or content.
- This spec covers the import mechanism itself; making an imported story visible to players is a separate, explicit action (see `005-story-publishing-done`).
