# Research: Story Editing and Review

**Date**: 2026-09-06

**Feature**: Story Editing and Review (`012-story-editing-and-review`)

**Input**: [`spec.md`](./spec.md) (all six clarifications resolved in Session 2026-09-06 — no
`NEEDS CLARIFICATION` markers remain in Technical Context)

All decisions below were taken against the code as it exists on `main` today
(`004-story-creation-done`, `005-story-publishing-done`, `008-core-gameplay-done` are implemented;
`010-story-test-play-done`, `011-story-import`, `017-story-publish-test-play-gate` are spec-only).

---

## 1. Where the re-upload/overwrite mechanism gets built (`011-story-import` is not yet implemented)

**Decision**: Build the story-configuration file format, its validator, and the
create-or-overwrite import endpoint **in this feature**, conforming to `011-story-import`'s
FR-002/003/004/005/006/007 rather than inventing separate rules. `011-story-import` then
reduces to its own entry surface and any additional acceptance tests it wants; it MUST NOT
define a second format or a second validator.

**Rationale**: `012` FR-005 and User Story 2 put download → manual edit → re-upload inside
this feature's independent test, and FR-008 requires automated tests for both the
id-matched overwrite and the id-less new-story upload. The mechanism therefore has to exist
here. `011`'s spec already anticipates this direction ("The file format and schema … are
defined by whichever process also produces them via guided creation, so an exported/
downloaded story can always be re-imported here").

**Alternatives considered**:
- *Block `012` until `011` ships* — rejected: it would stall a feature whose spec is fully
  clarified behind one that has no plan, and `011` would still need `012`'s serializer to
  define the file it imports.
- *A `012`-only "re-upload" path that skips `011`'s validation rules* — rejected by
  `012` FR-005 ("subject to the same validation as any other import") and by the spec's
  Assumptions.

**Consequence to carry forward**: `011-story-import`'s spec now records this in a *Delivery
Status* section (added 2026-09-06): its FR-001/002/003/005/006/007/008 are delivered by `012`, and
it MUST NOT define a second format, validator, or import endpoint. Its eventual plan, if any, is
limited to additional entry surfaces or acceptance coverage on top of this mechanism.

**Resolved divergence**: `011` FR-004 originally required the administrator to *choose* create-new
versus overwrite, which `012`'s clarified routing (the file's id decides) forecloses. On 2026-09-06
the user resolved this in `011`'s favour of `012`: the story id inside the file is the sole
identifier, there is no chooser, and an id matching nothing is **rejected** rather than re-minted
under a fresh id (`011` FR-004 as revised; `012` Edge Cases, unchanged). `011` FR-005's
title requirement therefore applies to the id-less path only.

---

## 2. Canonical serialization — one function feeding viewer, download, and import

**Decision**: A single module, `src/backend/services/story_config_file.py`, owns
`serialize(story) -> str` and `parse(payload) -> StoryConfiguration`. `serialize` emits
JSON with a fixed key order, `indent=2`, `ensure_ascii=False`, and a trailing newline.
One endpoint (`GET /api/manage/stories/{storyId}/configuration`) returns that string as its
raw body, and the frontend uses **the exact response text** both for the read-only viewer
and for the downloaded blob.

**Rationale**: FR-002 requires the viewer to render "byte-for-byte what the download
produces", and SC-001 asserts it. The only way to guarantee that without a second
comparison test surface is to have one producer and one transport, with the client never
re-serializing. The frontend must therefore request it as text (axios
`transformResponse: (r) => r`), because axios's default JSON parse would discard the exact
bytes and a re-`JSON.stringify` would not reproduce them.

**Alternatives considered**:
- *Return the parsed object and let the browser pretty-print it* — rejected: `JSON.stringify`
  key order/spacing on the client is a second serializer that FR-002/SC-001 would have to
  police forever.
- *Two endpoints (one "view", one "download" with `Content-Disposition`)* — rejected: the SPA
  fetches with a bearer token via XHR, so `Content-Disposition` is inert; the filename is set
  client-side on the object URL. Two endpoints would double the thing that must stay identical.

---

## 3. File contents — authored fields plus `id`, no system-managed fields

**Decision** (revised 2026-09-08, #270/#271): The file carries exactly `id` (optional),
`name`, `coverImageUrl`, `tone`, `readingLevel`, `sessionLengthMinutes`, `chapters`,
`worldPrompt`, `rules`, `characterTypes`, `completionCriteria`, `narrativeGuidance`,
`startingPoint`. It never carries `published`, `lastPublishedAt`, `createdBy`, `createdAt`,
`contentUpdatedAt`, `lastUpdatedBy`, `lastTestPlayedAt`, `contentVersion`, or `entityType`.

**Rationale**: FR-004 enumerates the authored set and the exclusions; FR-007 depends on
`published` being absent so a re-upload can never flip it; the spec's Assumptions tie the
exclusion of administrator identity to Principle X (PII stays inside the access-controlled
store, out of a file that leaves it). `narrativeGuidance` and `startingPoint` are LLM-authored
but they are story content — the guidance that anchors every session's narration and the
opening scene every player starts from — so the file is the place an administrator reviews and
edits them; omitting a field asks for it to be regenerated (§5). The exclusions above are
system state, which the file never carries.

**Alternatives considered**:
- *Keep `narrativeGuidance`/`startingPoint` out as purely derived values* — rejected 2026-09-08
  (#270, #271): an administrator had no way to review or correct either, and a download →
  upload round-trip silently rewrote them.
- *Add a `schemaVersion` marker* — rejected for now under Principle IV (YAGNI): there is one
  format and no migration requirement. Validation is by required fields, and an unknown key is
  rejected with a specific reason (§7), which is what a wrong-format file actually looks like.

---

## 4. Wizard "edit" mode — an edit draft seeded from the story

**Decision**: Reopening a story in the wizard creates a `StoryDraft` seeded from that story
(`POST /api/manage/stories/{storyId}/edit-drafts`), carrying two new fields
(`sourceStoryId`, `baseContentVersion`). Every existing wizard interaction — per-field
`PATCH`, the `Suggest` action (`POST …/drafts/{id}/world-prompt`; `POST …/drafts/{id}/messages`
until #227 replaced it, 2026-09-08), field validation — is reused
unchanged. The wizard's terminal action in edit mode is `POST …/drafts/{draftId}/save`, which
applies the draft to its source story and deletes the draft.

**Rationale**: The 2026-09-06 clarification requires "the existing story wizard in 'edit'
mode … LLM help stays exactly as in creation". The one-shot `Suggest` action is implemented
today as a one-pass world-prompt suggestion (`StoryDraftService._apply_world_prompt_suggestion`;
`_apply_exchange` merging `fieldUpdates` until #227), so it
only works against a draft. Seeding a draft is what makes "exactly as in creation" literally
true rather than approximately true, and it inherits draft autosave, cross-tab persistence,
and the 24h TTL that garbage-collects an abandoned edit with no cleanup code.

**Alternatives considered**:
- *Edit the `Story` document directly with a single `PUT` and no draft* — rejected: it would
  need a new draftless suggest endpoint (a second LLM surface), and would lose per-field
  autosave, giving edit mode different behavior from creation.
- *A distinct `StoryEdit` entity* — rejected under Principles IV/XII: a `StoryDraft` with two
  nullable fields is the same shape with none of the duplication.

**Note**: an abandoned edit draft expiring by TTL leaves the story untouched, which is the
correct outcome — the story is only written by an explicit save.

---

## 5. `narrativeGuidance` and `startingPoint` on save and on import

**Decision** (revised 2026-09-08, #270/#271): On **every** content write — wizard edit save,
id-matched overwrite import, and id-less new-story import — a value the configuration carries
is persisted verbatim, and one it omits is generated from the resulting configuration by
reusing `LLMService.generate_story_config` and `LLMService.generate_starting_point`, exactly as
creation does. `startingPoint` is generated from the `narrativeGuidance` that ends up on the
story, whether that guidance was supplied or generated. A generation failure fails the whole
save (502 `generation_failed` / 429 `rate_limited`) and leaves the story unchanged.

A supplied value that differs from what the story already holds is the administrator's own:
the write records it in `Story.adminEditedFields`, and it stays recorded while later writes
resubmit it unchanged. A field named there is **never** regenerated over. Because a wizard edit
draft carries neither field, a wizard save seeds them from the story for exactly the fields
named there and regenerates the rest — so hand-edited text survives a wizard edit, while text
the system generated is refreshed against the edited world. Omitting a key from an uploaded
file asks for a fresh generation and hands ownership of that field back to the system.

**Rationale**: Both are derived from `worldPrompt`, `rules`, `characterTypes`, and
`completionCriteria` unless an administrator deliberately writes them. Keeping a *generated*
value after the world it describes was replaced would leave gameplay narrating the pre-edit
story, which is a worse failure than a rejected save; silently regenerating over an
administrator's own words is a worse failure still, and there is no way to tell the two apart
without recording which is which. Reusing the creation path keeps one prompt and one telemetry
shape per call (Principle VI).

**Alternatives considered**:
- *Never regenerate on a wizard save* — simpler, no provenance to track, but an administrator
  who edits the world in the wizard would silently keep guidance and an opening scene
  describing the story they replaced.
- *Compare against a fresh generation to detect hand edits* — rejected: generation is
  non-deterministic, so it cannot answer the question, and it costs a call per write.

**Alternatives considered**:
- *Regenerate only when a narrative-affecting field changed* — a real LLM-cost saving, but it
  adds a change-detection branch and a class of "stale guidance" bugs for a low-frequency
  administrator action. Rejected under Principle IV; revisit if edit-save cost ever shows up in
  the Principle VI cost telemetry.
- *Preserve the existing guidance on edit* — rejected: incoherent after a world change, and
  impossible for a new import (there is nothing to preserve).

---

## 6. Stale-save detection (FR-006) — an explicit `contentVersion`

**Decision**: Add an integer `contentVersion` to `Story` (existing rows read as `1`), returned
by `GET /api/manage/stories/{storyId}`, captured into the edit draft as `baseContentVersion`,
and checked on save: a mismatch is rejected with `409 stale_story` and the story is not
written. Content writes increment it. The write itself additionally uses the Cosmos `_etag`
with `MatchConditions.IfNotModified`, the pattern already used in `play_session_service.py`,
so the read-check-write window cannot silently lose an update either. A precondition
failure is resolved rather than surfaced raw: the story is re-read, a changed
`contentVersion` becomes `409 stale_story` on the save path (the exempt import path
re-applies instead), and an unchanged one — i.e. a publish landed mid-write — is re-applied
to the fresh row and retried once, so the publish survives and does not read as staleness.
A second failure is `409 write_conflict` (contracts/api.md → Write conflicts).

**Rationale**: FR-006 requires rejecting a save "made against a stale version". A dedicated
content counter is deterministic, trivially assertable in tests against the in-memory Cosmos
stub, and — critically — is **not** bumped by publish/unpublish. Using the raw `_etag` as the
administrator-visible token would make an unrelated publish (from the wizard's own "Publish &
assign" step, or from the story list per FR-011) turn the next content save into a false
conflict.

**Alternatives considered**:
- *Reuse `contentUpdatedAt` as the token* — rejected: it is second-granularity, and raising its
  precision would break the lexicographic `lastTestPlayedAt >= contentUpdatedAt` comparison that
  `StoryService.can_publish` relies on.
- *Cosmos `_etag` alone as the client-visible version* — rejected for the false-conflict reason
  above.
- *Last-write-wins* — rejected by FR-006 and SC-004.

**Exemption**: a re-upload overwrite deliberately does **not** carry a version check
(FR-006, `011` FR-006) — the administrator confirms the target story explicitly instead.

---

## 7. Upload validation and rejection reasons

**Decision**: Validation reuses the `Story`/`CharacterType`/`CompletionCriteria` dataclass
rules already enforced at creation, plus four file-level checks: (a) the uploaded text parses
as JSON at all; (b) the payload is a JSON object; (c) unknown keys are rejected by name, while
the known system-managed keys are accepted-and-ignored (never read — FR-004/FR-007);
(d) character type names must be unique case-insensitively (`011` Edge Cases). Plus `name` is
required on the overwrite path, where no `title` supplies it. Every rejection returns `422` with
a message naming the offending field, and nothing is persisted.

**Both tiers, one authority** (revised 2026-09-07): the endpoint takes the file's **raw text**
rather than a client-parsed object, so *every* rejection — malformed JSON included — has a
server-side path and holds against a caller that never runs the SPA. The upload component also
validates before posting, because it parses the file anyway to choose between confirming an
overwrite target and prompting for a title, and because a hand-editing administrator should not
wait on a round trip to learn they left a trailing comma. Its checks are deliberately a strict
**subset** — parseable, is an object, required keys present and non-empty — and it never
re-implements the content rules (unknown-key naming, case-insensitive uniqueness, `rule` vs.
condition count, positive integers).

**Rationale for the subset line**: two full validators in two languages drift, and the drift is
silent in the direction that matters (a client that accepts what the server rejects is a
confusing error; a client that rejects what the server would accept is an unfixable file). A
subset cannot drift that way as long as the rule holds, and `011`'s "MUST NOT define a second
validator" (§1) stays intact — the browser tier is fast feedback on rules the server also
enforces, never an independent definition of the format.

**Alternative considered**: *client-side parse only, everything else server-side* — rejected on
review 2026-09-07: it left malformed JSON as a rejection that only the browser could produce,
which is single-sided validation on the one input most likely to be hand-mangled.

**Rationale**: `011` FR-002/FR-003 require structure *and* content validation with a specific
reason, and `012`'s Edge Cases require naming a missing required element. Rejecting unknown
keys catches the realistic hand-edit failure (a typo'd key silently dropping content) that a
lenient parser would swallow; ignoring the known system-managed keys keeps a pasted full story
document usable without letting it write `published`.

**Routing rules** (FR-005 and `012` Edge Cases):

| File `id` | Existing story | Outcome |
|---|---|---|
| present | matches | overwrite, requires `confirmOverwriteStoryId` echoing that id |
| present | no match | `404 story_not_found` — nothing is persisted, neither under the file's id nor under a newly generated one (`011` FR-004 as revised 2026-09-06) |
| absent | — | new story; `title` required (`011` FR-005), defaults unpublished (`011` FR-007) |

---

## 8. Audit stamping and the test-play gate reset (FR-009)

**Decision**: A content write preserves `id`, `createdBy`, and `createdAt`; sets
`lastUpdatedBy` (a **new** `Story` field holding the administrator's `oid`, never an email)
and a fresh `contentUpdatedAt`; increments `contentVersion`; and leaves `published` /
`lastPublishedAt` untouched. The test-play reset required by `017` FR-003 needs no new
mechanism: `StoryService.can_publish` already gates on
`lastTestPlayedAt >= contentUpdatedAt`, so bumping `contentUpdatedAt` re-arms the gate.

**Rationale**: FR-007 (published status untouched), FR-009 (audit trail + reset), and `017`
FR-003/FR-004 are all satisfied by the fields `005-story-publishing-done` already added. Storing
`oid` rather than an email keeps Principle X satisfied and matches `createdBy`.

---

## 9. In-flight play sessions (FR-010) — already satisfied, nothing to build

**Decision**: No work. Verified in code: `PlaySessionService._generate_and_persist_turn`
re-reads the story via `self._stories.get_story(session.adventureId)` on every turn, and
`PlaySession` stores no copy of the configuration. An edit therefore reaches an in-flight or
resumed session from its next turn, which is exactly the clarified behavior.

**Rationale**: FR-010 forbids per-session snapshots; the existing design already forbids them.
The plan records a regression test rather than a change, so a later refactor cannot reintroduce
a snapshot unnoticed.

---

## 10. Downloading a file from an authenticated SPA

**Decision**: The download action fetches the configuration endpoint with the bearer token,
wraps the raw response text in a `Blob`, and triggers a temporary object-URL anchor named
`story-<id>.json`, revoking the URL afterwards.

**Rationale**: Every endpoint requires `Authorization` (Principle II), so a plain `<a href>` to
the API cannot work. Reusing the already-fetched text also guarantees FR-002's "downloaded file
is identical to what the viewer displayed" without a second request.

---

## 11. Publish/unpublish from the story list (FR-011) — extract, don't duplicate

**Decision**: Lift the publish/unpublish logic and its confirmation dialog out of
`StepPublish.jsx` into a shared `StoryPublishActions` component; the wizard step and each story
list row both render it.

**Rationale**: `005` FR-010 requires both entry points to enforce the identical precondition,
and Principle VIII forbids a parallel screen-specific reimplementation of a control the system
already provides. Both entry points then hit the same `publish`/`unpublish` endpoints, so the
409 gate explanation (`005` FR-011) and the client-side unpublish confirmation (`005` FR-013)
are enforced once.

---

## 12. Unstyled screens (FR-012) — a recorded Principle VIII exception

**Decision**: The story list and the configuration viewer ship as plain pages built from
existing design-system classes (`.table`, `.tag`, `.btn*`, `.field`, `.hr`, `.dialog*`) and
token-based inline styles only, with no bespoke layout and no visual design pass. This is
recorded as an explicit, justified exception in the plan's Constitution Check, as the spec's
Assumptions require.

**Rationale**: The requesting user approved shipping these screens unstyled on 2026-09-06 for
MVP velocity. Principle VIII permits "an explicit, justified exception" recorded in the plan's
Constitution Check; it does **not** permit off-system colors, fonts, or spacing, so introducing
none is what keeps the later styling pass a pure addition. Accessibility and semantic markup
(headings, labelled controls, keyboard operability, meaningful button text) are **not** part of
the exception and still apply in full.

**Follow-up (2026-09-07, from the cross-artifact analysis)**: the styling exception did not
cover two separate Governance obligations, both now closed.

- *Screen-contract traceability*. Governance forbids shipping a screen traceable to no screen
  contract, and the viewer was one. Rather than stack a second exception, the constitution was
  amended to **v2.3.0** with an "Administrator — stories & configuration" contract, and that
  section now explicitly allows a contract to exist without a prototype screen where a spec
  defers visual design. The contract fixes the screens' purpose, affordances, and entry points;
  FR-012 defers only how they look.
- *The layout/scroll contract*. The fixed-viewport shell is a play-surface rule in this codebase
  — `src/frontend/src/index.css` carries no page-wide `overflow: hidden`, with a recorded reason
  (it clipped the wizard's growing steps). So the viewer adds no page-level scroll rule; its
  `<pre>` gets its own keyboard-focusable `overflow: auto` container with `white-space: pre`
  intact, which keeps the on-screen text byte-exact (FR-002) while stopping a long line from
  scrolling the page sideways.
