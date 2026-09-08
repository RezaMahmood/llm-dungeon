# Feature Specification: Story Editing and Review

**Feature Branch**: `012-story-editing-and-review`

**Created**: 2026-08-28

**Status**: Draft

**Reorganized from**: originally User Story 8 within `003-game-setup-and-authoring`, split out as its own domain since ongoing content maintenance (reviewing, editing, viewing) is a distinct workflow from initial creation or import.

**Input**: User description: "Edit an existing game: view list of games/stories that are available - need to also see published status. Work with the LLM to update the story. Ability to Download the story config for manual editing and then allow re-upload and overwrite. The entire story configuration file should be viewable by the administrator."

## Clarifications

### Session 2026-09-06

- Q: When an administrator asks the LLM to change an existing story, what does that interaction actually look like on screen? → A: Reuse the existing story wizard in "edit" mode, pre-filled with the saved story; LLM help stays exactly as in creation — the per-field one-shot "Suggest" action, with no new chat surface.
- Q: When an administrator downloads a story's configuration file, does the file contain only the authored story content, or also the system-managed fields the app keeps about that story? → A: Authored content only, plus the story's id so the file can be saved back to the story it came from. On re-upload, an id present means update that story; no id means create a new one. Published status, timestamps, creating/updating administrator, and test-play status are excluded from the download and never taken from an uploaded file.
- Q: If an administrator saves an edit to a story while a player is part-way through playing it, which version does that in-flight session use from its next turn onward? → A: The edited one — in-flight sessions pick up the updated configuration from their next turn. No per-session snapshot of the story is kept; a story has exactly one current version.
- Q: If two administrators open the same story and both save, should the second save be rejected as a conflict, or just win? → A: Rejected. The wizard sends back the version it loaded; if the story changed meanwhile, the save fails and the administrator is told to reload and reapply their change. A re-upload still fully replaces the target, since the administrator explicitly confirms that overwrite.
- Q: When an administrator opens a story to view its complete configuration, what do they see? → A: The raw configuration file itself — byte-for-byte what the download produces — shown formatted in a read-only viewer, with the download action beside it. The structured field-by-field rendering already exists in the wizard's edit mode.
- Q: How much visual design work do this feature's new screens need before they can ship? (raised directly by the requesting user) → A: None for now — the story list and configuration viewer may ship as plain, unstyled pages. Visual styling is deliberately deferred to follow-up work; accessibility and semantic markup still apply.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Administrator Reviews Existing Stories (Priority: P1)

An administrator views the list of all existing stories, each shown with its published/unpublished status, and can open any one of them to view its entire configuration file exactly as it would be downloaded.

**Why this priority**: Reviewing what already exists is a prerequisite for every other maintenance action, and is valuable on its own as a way to audit content.

**Independent Test**: With at least one published and one unpublished story existing, view the story list and confirm both are shown with correct status, then open one and confirm the configuration file shown matches, byte for byte, what downloading that story produces.

**Acceptance Scenarios**:

1. **Given** an administrator views the list of stories, **When** the list is displayed, **Then** each story shows its published/unpublished status alongside its identifying details.
2. **Given** an administrator selects an existing story, **When** they choose to view it, **Then** the story's complete configuration file is shown in a read-only viewer, identical in content to the file the download action produces, with the download action available alongside it.

---

### User Story 2 - Administrator Edits an Existing Story (Priority: P2)

An administrator updates an existing story either by reopening it in the story wizard — pre-filled with its saved configuration, with the same per-field one-shot "Suggest" LLM action available as during creation (`004-story-creation-done`) — and saving, or by downloading the story's configuration file, editing it manually, and re-uploading it to overwrite the original.

**Why this priority**: Content needs upkeep after it exists, but this depends on User Story 1 (finding and viewing the story to edit) and on stories already existing via creation or import.

**Independent Test**: With one existing story, reopen it in the wizard, change at least one field using the LLM "Suggest" action, hit Save, and verify the change is reflected in the story's configuration; separately, download that story's configuration, edit it, re-upload choosing to overwrite, and verify the change is reflected.

**Acceptance Scenarios**:

1. **Given** an administrator reopens an existing story in the wizard, **When** they change one or more fields — optionally using the per-field "Suggest" LLM action — and hit Save, **Then** the story's saved configuration is updated in place, leaving fields they did not change untouched.
2. **Given** an administrator downloads a story's configuration file, **When** the download completes, **Then** the file carries the story's id and accurately represents its current, complete authored configuration.
3. **Given** an administrator edits a downloaded configuration file and re-uploads it choosing to overwrite, **When** the upload passes validation, **Then** the story's configuration is replaced with the edited version.

---

### Edge Cases

- An administrator downloads a story configuration, makes no changes, and re-uploads it: the overwrite succeeds and results in an equivalent story (a no-op update).
- An administrator clears a required element while editing in the wizard (e.g., removes every character type): the save is rejected with a specific reason rather than persisting a story that would be left incomplete.
- Two administrators open the same story and both save: the first save succeeds; the second is rejected as a conflict, with the second administrator told to reload the story and reapply their change. Neither set of changes is silently discarded.
- An administrator views a story's full configuration for one that has never been edited since creation: the view reflects exactly what was originally generated or imported.
- An administrator views a story's configuration and then downloads it without editing anything: the downloaded file's content is identical to what the viewer displayed.
- An administrator uploads a configuration file whose id matches no existing story (e.g., the story was deleted, or the file came from elsewhere): the upload is rejected with a specific reason rather than silently creating a story under that id; the administrator may remove the id and upload it as a new story instead.
- An administrator removes the id from a downloaded file and uploads it: it is treated as a brand-new story, requiring a title and defaulting to unpublished per `011-story-import` FR-005 and FR-007, leaving the story it was downloaded from untouched.
- An administrator edits a story that is currently published: the story stays published (FR-007), but its test-play status resets, so the next publish attempt after any later unpublish is gated again per `017-story-publish-test-play-gate`.
- An administrator saves an edit while a player is mid-session in that story: the player's session continues and uses the edited configuration from its next turn; the session is neither ended nor pinned to the pre-edit version.
- A player resumes a saved session (`009-save-and-continue`) for a story that was edited since they last played: the resumed session uses the story's current configuration, not the one in force when the session began.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow an administrator to view a list of all stories. Each row MUST show, at minimum, the story's name and its published/unpublished status, with the status conveyed as text rather than by color alone, and MUST offer an affordance that opens that story's full configuration view (FR-002) in a single action. The list MUST also carry the entry point for uploading a story configuration file (FR-005), so an edited file can be re-uploaded without first opening the story it came from. Other identifying details (e.g. when it was created or last published) MAY be shown but are not required.
- **FR-002**: System MUST allow an administrator to view any existing story's complete configuration file in a read-only viewer, rendering exactly the content FR-004's download produces (same serialization, formatted for reading). No second, separately maintained rendering of the story's fields is required — the wizard's edit mode already presents them field by field.
- **FR-003**: System MUST allow an administrator to reopen an existing story in the story wizard, pre-filled with that story's saved configuration, and update it there — including via the same per-field one-shot "Suggest" LLM action available during creation (`004-story-creation-done`). No separate chat or multi-turn editing surface is required.
- **FR-004**: System MUST allow an administrator to download an existing story's complete authored configuration as a file. The file MUST contain the story's id and all authored content (name, cover reference, world/setting, rules, tone, reading level, session length, character types, completion criteria, narrative guidance, starting point — the last two revised 2026-09-08, #270/#271), and MUST NOT contain system-managed fields — published status, created/last-updated timestamps, the creating or last-updating administrator's identity, or test-play status.
- **FR-005**: System MUST allow an administrator to re-upload an edited configuration file from the story list (FR-001), subject to the same validation as any other import (see `011-story-import`). A file carrying a story id MUST update that story, still requiring the explicit confirmation of the overwrite target that `011-story-import` FR-006 mandates; a file with no id MUST be treated as a new story, requiring an administrator-supplied title per `011-story-import` FR-005.
- **FR-006**: System MUST detect a wizard save made against a stale version of a story and reject it, telling the administrator the story changed since they opened it and that they must reload and reapply their change — a stale save MUST NOT overwrite the newer saved state. A re-upload overwrite is exempt: the administrator confirms the target explicitly (`011-story-import` FR-006), so it fully replaces the story's current configuration.
- **FR-007**: Editing a story MUST NOT change its published/unpublished status; that remains governed exclusively by `005-story-publishing-done`. Because published status is neither downloaded nor read back from an uploaded file, a re-upload can never flip it.
- **FR-008**: Each distinct maintenance action (list view, full-configuration view, wizard edit save, rejected stale save, download, re-upload overwrite of the id-matched story, and upload of an id-less file as a new story) MUST have a corresponding automated test verifying its expected behavior.
- **FR-009**: An edit (wizard save or re-upload) MUST preserve the target story's id and its creation audit trail, MUST stamp it with the editing administrator's identity and a new last-updated timestamp, and MUST reset its test-play status per `017-story-publish-test-play-gate` FR-003.
- **FR-010**: A story MUST have exactly one current configuration; play sessions MUST NOT retain their own copy of it. A session already in progress when an edit is saved MUST use the edited configuration from its next turn onward (see `008-core-gameplay-done`, `009-save-and-continue`).
- **FR-011**: The story list defined by FR-001 MUST expose the publish/unpublish action for each story, enforcing the same preconditions as the wizard's publish step, since `005-story-publishing-done` FR-010 names this list as one of that action's two required entry points. Triggering publish/unpublish from the list is a publishing action governed by `005-story-publishing-done`, not an edit, and is unaffected by FR-007.
- **FR-012**: This feature's new screens (the story list and the read-only configuration viewer) MAY ship as plain, unstyled pages — no visual design pass, no mockup, and no bespoke layout are required before they are considered complete. They MUST still be accessible and semantically marked up (headings, labelled controls, keyboard operability, meaningful link/button text), and MUST NOT introduce off-system colors, fonts, or spacing values. The deferral covers appearance only: both screens remain bound by the **Administrator — stories & configuration** screen contract (constitution v2.3.0, added 2026-09-07 so this feature ships no screen traceable to no contract), and the configuration viewer's content MUST scroll within its own region rather than forcing the page to scroll sideways. Visual styling is explicitly deferred to follow-up work. The wizard reached via FR-003 is unaffected — it keeps the styling it already has from `004-story-creation-done`.

### Key Entities

- **Story**: The existing adventure being reviewed or edited; its identifying details, published status, and complete configuration are all visible to an administrator.
- **Story Configuration File**: The downloadable, re-uploadable representation of a Story's authored configuration plus its id, produced by the download action and consumed by the re-upload/overwrite action. It carries no system-managed fields (published status, timestamps, administrator identities, test-play status); the id is what routes a re-upload back to its originating story.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Any existing story's full configuration file is reachable in a single action from its row in the story list (FR-001), and the content shown there matches the downloaded file exactly.
- **SC-002**: 100% of downloaded story configuration files in testing can be re-uploaded and successfully overwrite their originating story — matched by the id in the file — with no loss of authored content and no change to the story's published status or creation audit trail.
- **SC-003**: 100% of wizard edits in testing are reflected in the story's configuration without altering elements the administrator did not change.
- **SC-004**: 100% of wizard saves made against a stale version of a story are rejected in testing, with the newer saved state left intact.

## Assumptions

- This spec reuses the validation and overwrite rules defined in `011-story-import` for the re-upload path rather than defining a separate set. Because `011-story-import` has no implementation plan, the shared mechanism those rules describe — the configuration file format, its validator, and the create-or-overwrite import endpoint — is built by this feature, conforming to `011`'s requirements; see `plan.md`'s Sequencing note and `011-story-import`'s Delivery Status section (recorded 2026-09-06). There is exactly one such mechanism, and `011-story-import` MUST NOT define a second.
- This spec reuses the story wizard built by `004-story-creation-done` for the edit path rather than defining a second authoring surface; an ongoing multi-turn conversation with the LLM about a story remains future scope, consistent with that spec's one-shot "Suggest" model.
- There is no version history requirement; each edit (wizard save or re-upload) replaces the prior configuration rather than being tracked as a separate revision.
- Concurrent-edit conflicts are surfaced, not merged: the stale save is rejected and the administrator reapplies their change by hand. No field-level merge or merge-conflict resolution UI is required at this stage.
- Mid-session narrative inconsistency caused by editing a story that is actively being played is accepted rather than engineered away; per-session configuration snapshots are deliberately not built (constitution Principles IV and XII), and any resulting oddity is expected to surface through playtesting (Principle IX).
- Excluding the creating/updating administrator's identity from the downloaded file keeps administrator email addresses out of an artifact that leaves the application's access-controlled data store, consistent with constitution Principle X (PII Protection by Design).
- Shipping this feature's screens unstyled (FR-012) is a deliberate, user-approved decision taken on 2026-09-06 to keep MVP velocity, and is the kind of deviation constitution Principle VIII expects to be raised as "an explicit, justified exception" in the implementation plan's Constitution Check — the plan MUST record it there rather than treat the design-system requirement as silently satisfied. Unstyled markup adds no ad hoc colors, fonts, or spacing, so nothing off-system is introduced that a later styling pass would have to undo; that later pass is follow-up work, not part of this feature.
