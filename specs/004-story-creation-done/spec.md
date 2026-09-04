# Feature Specification: Story Creation

**Feature Branch**: `004-story-creation`

**Created**: 2026-08-28

**Status**: Draft

**Reorganized from**: merges the conversational story-creation capability originally described in `001-adventure-game` (User Story 2) with the guided-wizard framing originally described in `003-game-setup-and-authoring` (User Story 5) — both described the same underlying capability (administrator answers guiding questions, LLM produces a persisted story) at different levels of detail.

**Input**: User description (combined): "An administrator opens the application, starts a new story-creation conversation, and describes their idea in plain language. The system asks guiding questions (setting, characters, plot, win/lose conditions) to draw out a complete story, then persists the resulting story. ... In-App Wizard approach: Answer a set of questions that every story should have; LLM generates a story config file; story config files are automatically persisted."

**Design Reference**: [specs/designs/04-admin-wizard.html](../designs/04-admin-wizard.html), steps 01–04 (name & cover, world & setting, tone & reading level, session length) (see [specs/designs/README.md](../designs/README.md)). These four steps, reachable in any order, are the UI structure for this feature; see Clarifications for how they relate to the guiding-question conversation and where character types and completion criteria are captured.

## Clarifications

### Session 2026-08-29

- Q: Should story creation be built as the four-step wizard shown in the design reference (name & cover, world & setting, tone & reading level, session length — reachable in any order), with the administrator's plain-language description and the system's guiding questions used to fill in each step's fields, or should it be a fully open-ended conversation where the wizard screen doesn't dictate structure at all? → A: Wizard frame + conversational fill-in — the four named steps are the UI structure, reachable in any order; the administrator's plain-language description and the system's guiding-question conversation fill in each step's fields.
- Q: The four wizard steps assigned to this spec (name & cover, world & setting, tone & reading level, session length) have no visible field for character types or completion criteria, both of which FR-002 and SC-003 require to be elicited and persisted — how should these be captured? → A: The wizard needs new, dedicated fields for character types and completion criteria (added to the existing steps or a new step), beyond what the current design mockup shows.
- Q: `008-core-gameplay` already defines "Completion Criteria" as a maximum duration, success condition(s), failure condition(s), and an any/all combination rule, and states this shape is authored in `004-story-creation` — should the new completion-criteria field (FR-008) require that same structured shape? → A: Yes — match `008-core-gameplay`'s structured shape (optional max duration, one or more success conditions, optional failure conditions, and an any/all rule when more than one condition is defined).
- Q: `specs/designs/README.md` flags tone, reading level, session-length target, and chapter count (collected by this spec's wizard steps) as story metadata not yet named as Key Entity attributes anywhere — should this spec add them as explicit Story attributes now? → A: No — left undocumented for a later spec/pass; not resolved by this clarification session.
- Q: Can one administrator have more than one story-creation wizard in progress at the same time, or does starting a new session require finishing/discarding any other in-progress one first? → A: Multiple concurrent drafts allowed — an administrator may have any number of in-progress creation sessions open at once; starting a new one never affects others.

### Session 2026-08-30

- Q: Is the story persisted automatically once the LLM produces a complete configuration, or via an explicit administrator action? → A: Explicit **Save**. The wizard is a 4-tab flow (name & cover, world & setting, tone & reading level, session length). Save is available from any tab at any time and is what persists the story — nothing is written to the database purely because the LLM produced output. The first Save for a new story creates the database record (name at minimum); every later Save updates that same record.
- Q: What does Tab 01 (name & cover) collect, and how is the cover image handled? → A: A required story name and an optional cover image. The image is uploaded from the administrator's desktop; on Save it is written to blob storage and the story record stores a reference to it, so it can be shown to players when they're choosing a story.
- Q: If the administrator switches tabs before saving, is unsaved input lost? → A: No. Field values entered in any tab MUST survive navigating to another tab, up until a Save actually persists them. The wizard uses browser local storage to hold this in-progress, unsaved state.
- Q: What does Tab 02 (world & setting) do, and how does the LLM participate? → A: It offers an optional "Suggest" action — the administrator gives an idea or guiding question, and the LLM asynchronously returns a suggested outline that is injected into an editable, scrollable outline text box. This is a single one-shot suggestion, not an ongoing back-and-forth chat; interactive, multi-turn world-building is future scope, not part of this spec. Tab 02 also has a separate, independently editable box for rules the story must keep (character types, completion criteria, and success/failure conditions are captured elsewhere per FR-008 and are out of scope for this box). Tab 02's fields are covered by the same Save-from-anywhere behavior as the rest of the wizard.
- Q: Tabs 03 (tone & reading level) and 04 (session length)? → A: No changes — they remain as already specified/designed.
- Q: Does a persisted story need to record who created/changed it and when? → A: Yes. Every persisted story record MUST track its creation timestamp, last-updated timestamp, and the identity (by email address) of the administrator who created it and who last updated it, taken from the currently authenticated admin session.
- Q: Can an administrator back out of story creation entirely, and what happens to anything already saved? → A: Yes — an "Abandon" action, available on every tab regardless of wizard state, prompts for confirmation. On confirming, all unsaved (local-storage) input is discarded, and if the story had already been persisted by an earlier Save, that record is deleted from the datastore rather than left orphaned. The administrator is then redirected to the main admin page.
- Q: How does an administrator signal they're done with a creation session (as opposed to abandoning it)? → A: A "Finished" action, also available across the wizard, ends the creation session — whether the wizard was fully filled in or only partially. After confirmation, the administrator is redirected to the page listing all stories (a future spec).

## Open Questions — Flagged During T033 Acceptance Walkthrough (2026-08-30)

These surfaced while the requesting user manually verified the implemented wizard against this spec. They are **not resolved** — implementation should not change until the user has refined the intended flow. T033 (user-verified acceptance, `tasks.md`) was accepted on 2026-09-04 on the core conversational-wizard-to-generated-story flow (P1) without waiting on these; resolving them is tracked separately in [#205](https://github.com/RezaMahmood/llm-dungeon/issues/205).

- **Auto-generation pre-empting the wizard — partially fixed (2026-08-31, #33)**: generation used to fire automatically as a side effect of whichever `PATCH`/message write happened to complete the draft (worldPrompt + ≥1 character type + ≥1 completion criterion), so an ordinary field blur could jump straight from that write to the finished, generated-story screen with no warning — reported directly by the requesting user as "navigating out of one of the boxes... seems to auto submit and redirect to the story." That specific symptom is fixed: writes now only report `readyToGenerate`, and generation happens exclusively via a new explicit "Generate story" action (`POST .../generate`, contracts/api.md) the administrator clicks deliberately. **Still not resolved**: this is a narrower fix than the Session 2026-08-30 Clarifications below actually call for — those describe explicit **Save** (persisting whatever is filled in, from any tab, with no completeness requirement), plus separate **Abandon** and **Finished** actions, local-storage-backed unsaved state, and blob-uploaded cover images. None of that broader redesign (Save-not-Generate semantics, Abandon, Finished, cover-image upload) has been implemented; FR-004 and User Story 1 below still describe that target state, not the current one. T033 remains blocked pending that fuller redesign.
- **Cover image URL — no defined meaning**: `data-model.md`'s `coverImageUrl` field (Name & cover step) has never had its expected content specified — is it a direct link to an externally-hosted image, an uploaded/managed asset reference, or something else? Session 2026-08-30's Clarifications answer this (blob-uploaded on Save, with the record storing a reference) but the field's actual storage/upload mechanics are not yet implemented — still needs a decision on rollout before the field can be considered correctly implemented.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Administrator Creates a New Story Through Guided Conversation (Priority: P1)

An administrator starts a new story-creation session inside the administrator wizard (name & cover, world & setting, tone & reading level, session length — reachable in any order) and describes their idea in plain language. Within that wizard, the system asks a structured set of guiding questions — covering, at minimum, setting/plot, character types, and completion criteria, each with dedicated fields for the administrator to define them — to draw out a complete story. The administrator persists the story by hitting Save; Save is available at any point in the wizard, not only once every field is filled in.

**Why this priority**: Without this, the catalog of playable stories cannot grow. It is the entire content pipeline for the product — nothing else in story authoring matters if new stories can't be created.

**Independent Test**: As an administrator, start a creation session from an empty state, fill in the name and any other fields, hit Save, and verify a story record is created in the database — including who created it and when.

**Acceptance Scenarios**:

1. **Given** an administrator starts a new story-creation session, **When** they describe an initial idea, **Then** the system asks guiding questions to elicit the missing elements of a complete story (setting, character types, plot, and completion criteria).
2. **Given** an in-progress creation session with at least a story name entered, **When** the administrator hits Save, **Then** the system creates the story record in the database, stamped with the creation timestamp and the creating administrator's email.
3. **Given** a previously saved story, **When** the administrator changes further wizard fields and hits Save again, **Then** the existing story record is updated in place, stamped with a new last-updated timestamp and the updating administrator's email.
4. **Given** an administrator abandons a creation session before ever hitting Save, **When** the session ends, **Then** no story record is persisted from that attempt.
5. **Given** an administrator wants to try again after an abandoned, never-saved session, **When** they start a new creation session, **Then** it begins fresh and does not attempt to resume the abandoned one.

---

### User Story 2 - Administrator Navigates Between Wizard Tabs Without Losing Work (Priority: P1)

An administrator fills in fields on one wizard tab (e.g., name & cover), switches to another tab (e.g., world & setting) without saving, then returns. The values already entered are still there, because the wizard has been holding the in-progress, unsaved state in the browser (local storage) the whole time. Nothing is written to the database until the administrator explicitly hits Save from wherever they are in the wizard.

**Why this priority**: A wizard that loses in-progress work on tab navigation is unusable for any story of nontrivial length; this guarantee is what makes it safe to explore other tabs before committing.

**Independent Test**: Enter a story name and cover image URL on Tab 01, switch to Tab 02 and enter an outline, switch back to Tab 01, and verify the name and cover image URL are still present — all before ever hitting Save.

**Acceptance Scenarios**:

1. **Given** an administrator has entered field values on the current tab, **When** they navigate to a different tab without saving, **Then** the values entered on the tab they left remain intact if they navigate back.
2. **Given** an administrator has unsaved changes held in local storage, **When** they hit Save from any tab, **Then** all unsaved values across all tabs are persisted to the database together.
3. **Given** a story has just been saved successfully, **When** the administrator continues editing, **Then** the wizard's local-storage draft reflects the newly saved state going forward.

---

### User Story 3 - Administrator Abandons or Finishes a Creation Session (Priority: P1)

From any tab of the wizard, at any point, an administrator can either Abandon or mark themselves Finished. Abandon discards everything: any unsaved local-storage draft is thrown away, and if the story had already reached the database via an earlier Save, that record is deleted so no orphaned story is left behind; the administrator confirms first, then lands on the main admin page. Finished simply ends the session — whatever has been saved so far (fully complete or only partial) stays saved — and, after confirmation, sends the administrator to the page listing all stories.

**Why this priority**: Without a clean way to back out, every experimental or abandoned Save leaves an orphaned, unpublished story behind; without a clean way to stop, administrators have no defined exit from the wizard once they're satisfied.

**Independent Test**: Start a session, hit Save at least once (so a story record exists), then hit Abandon and confirm — verify the story record no longer exists in the database and the administrator lands on the main admin page. Separately, start a session, hit Save, then hit Finished and confirm — verify the story record still exists and the administrator lands on the stories list page.

**Acceptance Scenarios**:

1. **Given** an administrator is on any tab of the wizard, **When** they choose Abandon, **Then** the system prompts for confirmation before doing anything else.
2. **Given** an administrator confirms Abandon and the story was never saved, **When** the confirmation completes, **Then** the unsaved local-storage draft is discarded, no story record exists in the database, and the administrator is redirected to the main admin page.
3. **Given** an administrator confirms Abandon and the story had already been saved at least once, **When** the confirmation completes, **Then** the existing story record is deleted from the datastore, the local-storage draft is discarded, and the administrator is redirected to the main admin page.
4. **Given** an administrator chooses Abandon but does not confirm, **When** they dismiss the confirmation prompt, **Then** nothing is discarded or deleted and they remain in the wizard.
5. **Given** an administrator is on any tab of the wizard, **When** they choose Finished, **Then** the system prompts for confirmation, and upon confirming, the administrator is redirected to the page listing all stories, with whatever was already saved (complete or partial) left intact.

---

### Edge Cases

- An administrator provides contradictory answers across the conversation (e.g., changes the setting partway through): the system reflects the most recent answer for that element the next time it is saved.
- An administrator supplies only a single character type: the system accepts it — a story is not required to offer more than one character type, though offering a choice is expected to be the common case.
- The LLM's suggested outline (Tab 02) fails to generate or returns something malformed: the system surfaces the problem to the administrator without touching the existing outline text box contents, so the administrator can retry Suggest or type the outline manually.
- An administrator hits Save with no cover image supplied: the system saves the story without a cover image reference; the cover image field is optional.
- An administrator's browser local storage is cleared or unavailable (e.g., private browsing) between visits: only unsaved, in-progress changes are at risk — anything already persisted via a prior Save is unaffected.
- An administrator hits Abandon on a story that was never saved (no database record yet): confirmation still occurs, but the delete step is a no-op since there is nothing to delete; the local-storage draft is still discarded and the redirect to the main admin page still happens.
- An administrator hits Finished without ever hitting Save: the session simply ends with no story record persisted (equivalent in effect to abandoning, since nothing was saved) and they are still redirected to the stories list page.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow an administrator to start a new story-creation session and describe their idea in plain, natural language.
- **FR-002**: System MUST present the story-creation experience as a 4-tab wizard — Tab 01 name & cover, Tab 02 world & setting, Tab 03 tone & reading level, Tab 04 session length — reachable in any order, and MUST ask guiding questions within that flow to elicit, at minimum, a story's setting/plot, its character types, and its completion criteria.
- **FR-003**: On Tab 02 (world & setting), the system MUST provide an optional "Suggest" action that, given an idea or guiding question supplied by the administrator, asynchronously calls an LLM to generate a suggested story outline and injects the result into an editable, scrollable outline text box; the administrator remains free to edit that text before saving. This suggestion MUST be a single, one-shot generation — no ongoing interactive/chat-based refinement at this stage (interactive world-building is a future capability, out of scope here).
- **FR-004**: System MUST persist story data only when the administrator explicitly hits Save. Save MUST be available from any tab of the wizard at any point, and MUST NOT require every wizard field to be filled in first. The first successful Save for a new story MUST create the story record in the database (at minimum, the story name); every subsequent Save MUST update that same existing record.
- **FR-005**: System MUST NOT persist any story record from a creation session the administrator abandons before ever hitting Save.
- **FR-006**: A newly created story configuration MUST default to unpublished, so it is not visible to players until an administrator explicitly publishes it (see `005-story-publishing`).
- **FR-007**: Each distinct step of the story-creation flow (eliciting setting/plot, eliciting character types, eliciting completion criteria, the Tab 02 outline suggestion, Save/create, Save/update, cross-tab draft persistence, Abandon, Finished) MUST have a corresponding automated test verifying its expected behavior.
- **FR-008**: System MUST provide dedicated fields — within the existing wizard steps or an additional step — for the administrator to define one or more character types and the story's completion criteria: an optional maximum session duration, one or more success conditions, optionally one or more failure conditions, and — when more than one condition is defined — a rule for whether any one or all of them must be met to end the game (this shape is enforced during play by `008-core-gameplay`). These MUST NOT be captured only as unstructured free text embedded in another field's prose.
- **FR-009**: Tab 01 (name & cover) MUST require a story name and MUST allow an optional cover image, uploaded from the administrator's local device. On Save, an uploaded cover image MUST be written to blob storage and the story record MUST store a reference to it, so the image can be shown to players when they are selecting a story.
- **FR-010**: The wizard MUST hold in-progress, unsaved field values (across all tabs) in browser local storage so that navigating between tabs before saving does not lose already-entered data. This draft state MUST persist until a Save successfully writes it to the database.
- **FR-011**: Tab 02 (world & setting) MUST provide a field, separate from the outline text box, for the administrator to enter rules the story must keep. This field is independently editable and is covered by the same Save-from-anywhere and local-storage-draft behavior as the rest of the wizard.
- **FR-012**: Every persisted story record MUST track its creation timestamp, its last-updated timestamp, the administrator who created it, and the administrator who last updated it — identifying the administrator by the email address of the currently authenticated admin session.
- **FR-013**: System MUST provide an "Abandon" action, available on every wizard tab regardless of wizard state, that prompts the administrator for confirmation before taking any action.
- **FR-014**: On confirmed Abandon, the system MUST discard the unsaved local-storage draft and, if the story had already been persisted by a prior Save, MUST delete that story record from the datastore so no orphaned record remains. On confirmed Abandon, the system MUST redirect the administrator to the main admin page.
- **FR-015**: System MUST provide a "Finished" action, available on every wizard tab regardless of wizard state, that prompts the administrator for confirmation and, once confirmed, ends the creation session — whether the story is fully complete or only partially filled in — without discarding or deleting anything already saved, and MUST redirect the administrator to the page listing all stories (see future story-listing spec).

### Key Entities

- **Story**: A complete adventure narrative — name, optional cover image reference, setting/outline, rules the story must keep, character types, and completion criteria — along with whatever guidance is needed to keep the LLM's later narration consistent with it. Newly created in an unpublished state (see `005-story-publishing`). Tracks createdAt, updatedAt, createdBy, and updatedBy (the latter two identified by administrator email).
- **Story-Creation Exchange**: A single turn in the conversation between an administrator and the system while building a Story — the atomic unit of the elicitation process.
- **Character Type**: An option, scoped to the Story being created, that a player will later choose from when setting up a new game against it (see `006-adventure-and-character-setup`).
- **Completion Criteria**: The conditions authored for a Story that determine when a play session ends — an optional maximum duration, one or more success conditions, and optionally one or more failure conditions, together with a rule for whether any one or all configured conditions must be met when more than one is defined. Authored here; enforced during play by `008-core-gameplay`.
- **Wizard Draft**: The in-progress, unsaved state of a story-creation session, held in the administrator's browser (local storage) across all four tabs until a Save persists it to the Story record.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An administrator with no prior training can go from starting a creation session to having a persisted story within a single sitting, using natural language and the wizard's fields alone (no direct editing of structured data or code).
- **SC-002**: 100% of abandoned creation sessions in testing (sessions that never hit Save) result in no story record being persisted.
- **SC-003**: 100% of completed creation sessions in testing produce a story configuration with at least one character type and at least one completion criterion.
- **SC-004**: 100% of tab switches performed before a Save, in testing, retain every previously entered field value when the administrator navigates back to that tab.
- **SC-005**: 100% of saved story records in testing carry a correct creation timestamp, last-updated timestamp, and creator/updater email matching the administrator session that performed the Save.
- **SC-006**: 100% of confirmed Abandon actions in testing, for sessions that had a persisted story record, result in that record no longer existing in the datastore (zero orphaned records).

## Assumptions

- This spec covers only the guided/conversational creation path. Direct upload of a pre-built configuration file is a separate capability (see `011-story-import`).
- Making a created story visible to players is a separate, explicit action, not part of this feature (see `005-story-publishing`).
- There is no requirement to resume an abandoned creation session; an administrator who wants to try again starts a fresh session.
- There is no defined limit on the number of stories an administrator may create.
- An administrator may have multiple story-creation sessions in progress concurrently; starting a new session does not require completing or abandoning any other in-progress session.
- Tone, reading level, target session length, and chapter count are collected by the wizard steps in scope for this feature (per the design reference) but are deliberately left undocumented as Key Entity attributes here; naming them is deferred to a later spec/pass (see `specs/designs/README.md`'s tracked gap).
- Browser local storage is a temporary, client-side holding area for unsaved wizard input only; it is not the system of record. Once a Save succeeds, the database is authoritative for that story.
- Cover images are stored in blob storage rather than the database directly; the story record holds a reference (URL/identifier) to the blob, not the image bytes.
- "Currently logged-in admin" for createdBy/updatedBy purposes relies on whatever administrator authentication mechanism the platform already provides; this spec does not define authentication itself.
- The page listing all stories, which the Finished action redirects to, is a separate, future spec; this spec only requires that the redirect target exists conceptually, not that the listing page itself is built here.
- The `specs/designs/` HTML mockups belong to a different, concurrently in-progress session and are out of scope for this spec; any changes to them should be committed independently rather than bundled with this spec's changes.
