# Data Model: Story Editing and Review

**Date**: 2026-09-06

**Feature**: Story Editing and Review (`012-story-editing-and-review`)

This feature adds **no new container**. It modifies two existing persisted entities and
introduces one transient (never-persisted) structure — the configuration file itself.

Containers in play (all existing, per `config.py`): `stories`, `storyDrafts`.

---

## Story (MODIFY — `src/backend/models/story.py`, container `stories`)

Existing fields are unchanged. Two fields are added.

| Field | Type | New? | Notes |
|---|---|---|---|
| `id` | string (uuid) | — | Partition key. **Never changes on an edit** (FR-009). |
| `name` | string \| null | — | Authored. In the config file. |
| `coverImageUrl` | string \| null | — | Authored. In the config file. |
| `tone` | string \| null | — | Authored. In the config file. |
| `readingLevel` | string \| null | — | Authored. In the config file. |
| `sessionLengthMinutes` | int \| null | — | Authored. In the config file. |
| `chapters` | int \| null | — | Authored. In the config file. |
| `worldPrompt` | string (required) | — | Authored. In the config file. |
| `rules` | string \| null | — | Authored. In the config file. |
| `characterTypes` | CharacterType[] (≥1) | — | Authored. In the config file. |
| `completionCriteria` | CompletionCriteria | — | Authored. In the config file. |
| `narrativeGuidance` | string (required) | — | Authored. In the config file (revised 2026-09-08, #270); regenerated on a content write only when the file omits it (research.md §5). |
| `startingPoint` | StartingPoint \| null | **NEW** | Authored. In the config file (#271); regenerated from `narrativeGuidance` on a content write only when the file omits it. `null` only for rows persisted before it existed. |
| `published` | bool | — | System-managed. Never written by this feature (FR-007). |
| `lastPublishedAt` | string \| null | — | System-managed, owned by `005-story-publishing-done`. |
| `createdBy` | string (oid) | — | Preserved on edit (FR-009). |
| `createdAt` | string (ISO-8601 Z) | — | Preserved on edit (FR-009). |
| `contentUpdatedAt` | string (ISO-8601 Z) | — | **Set to now on every content write** — this is what re-arms the `017` publish gate (FR-009). |
| `lastUpdatedBy` | string (oid) \| null | **NEW** | The administrator who last wrote content. `oid`, never an email (Principle X). `null` for a story never edited since creation. |
| `contentVersion` | int | **NEW** | Stale-save token (FR-006). Reads as `1` for rows persisted before this field existed; incremented on every content write; **not** touched by publish/unpublish. |
| `lastTestPlayedAt` | string \| null | — | System-managed, owned by `010`/`017`. Never written here; the gate resets implicitly via `contentUpdatedAt`. |
| `entityType` | `"Story"` | — | Constant. |

**Validation** (enforced in `__post_init__`): `worldPrompt` non-empty, `characterTypes`
non-empty, `narrativeGuidance` non-empty; `CompletionCriteria` requires at least one
`successConditions` entry and a `rule` of `any`/`all` when more than one condition exists in
total; a present `StartingPoint` requires non-empty `narrativeText`, `locationLabel`, and at
least one `suggestedActions` entry.

### Content write (the one operation this feature adds)

Applied identically by a wizard edit save and by an id-matched overwrite import:

```
preserve:  id, createdBy, createdAt, published, lastPublishedAt, lastTestPlayedAt
replace:   name, coverImageUrl, tone, readingLevel, sessionLengthMinutes, chapters,
           worldPrompt, rules, characterTypes, completionCriteria
take from the file, else regenerate: narrativeGuidance, startingPoint
stamp:     lastUpdatedBy = acting admin oid
           contentUpdatedAt = now
           contentVersion  = contentVersion + 1
```

`replace` is a full replacement of the authored set, not a merge — an overwrite import leaves
no residue of the previous configuration (`011` SC-003). The wizard's edit draft is seeded with
the full current configuration, so "fields the administrator did not change" survive by having
been carried through the draft unchanged (FR-003 Acceptance Scenario 1).

The write is guarded by the row's `_etag`. A precondition failure re-reads the story and
re-applies this operation to the fresh row before retrying once — which is what keeps a
publish that landed mid-write from being clobbered *or* misreported as staleness
(`contentVersion` is not touched by publish/unpublish). A second failure is
`409 write_conflict` (contracts/api.md → Write conflicts).

### State transitions

| Trigger | `contentVersion` | `contentUpdatedAt` | `published` | Publish gate afterwards |
|---|---|---|---|---|
| Wizard edit save (version matches) | +1 | now | unchanged | blocked until a new test play |
| Wizard edit save (version stale) | unchanged | unchanged | unchanged | unchanged — nothing is written (FR-006) |
| Overwrite import (confirmed) | +1 | now | unchanged | blocked until a new test play |
| New-story import (no `id`) | starts at 1 | = `createdAt` | `false` (`011` FR-007) | blocked until a test play |
| Publish / unpublish | unchanged | unchanged | flipped | n/a |

---

## StoryDraft (MODIFY — `src/backend/models/story_draft.py`, container `storyDrafts`)

Two nullable fields turn the existing creation draft into an edit draft. Everything else —
`PATCH`-per-field, the `Suggest` exchange, the Completeness Rule, the 24h TTL — is untouched
and behaves identically in both modes.

| Field | Type | New? | Notes |
|---|---|---|---|
| `sourceStoryId` | string \| null | **NEW** | `null` ⇒ creation draft (generates a new Story). Set ⇒ edit draft (saves back to that Story). |
| `baseContentVersion` | int \| null | **NEW** | The `Story.contentVersion` observed when the draft was seeded; echoed back on save for the FR-006 check. `null` on a creation draft. |

**Lifecycle**: an edit draft is created seeded from the story, lives under the same TTL, and is
**deleted on a successful save** (mirroring `generate_story`'s delete-on-generate). A rejected
stale save leaves the draft intact so the administrator can copy their wording out before
reloading. An abandoned edit draft expires by TTL and never touches the story.

**Mode rules**: an edit draft MUST NOT be passed to `generate_story` (that would mint a second
story), and a creation draft MUST NOT be passed to the save endpoint. Both are enforced
server-side (`422 wrong_draft_mode`).

---

## StoryConfiguration (NEW — transient, `src/backend/services/story_config_file.py`)

The parsed, validated in-memory form of a Story Configuration File. Never persisted, never
stored in Cosmos; it exists only between "parse an upload" and "apply a content write", and as
the input to serialization.

An upload arrives as **raw text** (`configurationText`), so `story_config_file` owns both steps:
`parse_text(text)` turns bytes into JSON — a `json.JSONDecodeError` becomes an
`invalid_configuration` naming the position — and `parse(payload)` applies the field rules
below. Malformed JSON is therefore a server-side rejection, not something only the browser can
catch. The SPA repeats a subset of these checks before uploading for immediate feedback
(contracts/api.md → the import endpoint), but the server re-validates everything it is sent and
trusts none of it.

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string \| null | no | Present ⇒ overwrite that story; absent ⇒ new story (FR-005). |
| `name` | string | yes on overwrite | Non-empty when `id` is present, else `invalid_configuration` naming `name`. `Story.__post_init__` does **not** validate `name`, so the file validator is the only thing standing between an overwrite and a nameless story — one the wizard's own Completeness Rule would then refuse to save. On a new-story upload the administrator-supplied `title` provides it (`011` FR-005) and wins over any `name` in the file, so the file's `name` is optional on that path. |
| `coverImageUrl` | string \| null | no | |
| `tone` | string \| null | no | |
| `readingLevel` | string \| null | no | |
| `sessionLengthMinutes` | int \| null | no | Positive integer when present. |
| `chapters` | int \| null | no | Positive integer when present. |
| `worldPrompt` | string | yes | Non-empty. |
| `rules` | string \| null | no | |
| `characterTypes` | CharacterType[] | yes | ≥1; each needs a non-empty `name`; names unique case-insensitively (`011` Edge Cases). |
| `completionCriteria` | CompletionCriteria | yes | ≥1 `successConditions`; `rule` ∈ {`any`,`all`} required when >1 condition in total. |
| `narrativeGuidance` | string \| null | no | Absent, null, or empty ⇒ regenerate it on the write; otherwise persisted verbatim (#270). |
| `startingPoint` | StartingPoint \| null | no | Absent or null ⇒ regenerate it from the resulting `narrativeGuidance`; otherwise persisted verbatim (#271). A present object must be complete — it is replayed as every session's turn 0 and is never repaired at play time — so a partial one is `invalid_configuration` naming `startingPoint`. |

**Serialization contract** (FR-002, FR-004, SC-001): keys are emitted in exactly the table's
order, `indent=2`, `ensure_ascii=False`, one trailing newline. `id` is emitted first and only
when the story exists. This byte sequence is what the viewer displays, what the download saves,
and what the importer accepts.

**Excluded keys** — never emitted, and accepted-but-ignored on upload (never read):
`published`, `lastPublishedAt`, `createdBy`, `createdAt`, `contentUpdatedAt`, `lastUpdatedBy`,
`lastTestPlayedAt`, `contentVersion`, `entityType`. Any **other** unrecognised key is a
validation failure naming that key (research.md §7).

### Example

```json
{
  "id": "9f2a7c14-3f5e-4a21-9d0b-6c1f2b8e77aa",
  "name": "The Sunken Library",
  "coverImageUrl": null,
  "tone": "wry",
  "readingLevel": "age 9-11",
  "sessionLengthMinutes": 30,
  "chapters": 3,
  "worldPrompt": "A flooded library beneath a coastal town...",
  "rules": "No violence against the librarians.",
  "characterTypes": [
    { "name": "Archivist", "description": "Knows where everything was." }
  ],
  "completionCriteria": {
    "maxDurationMinutes": 30,
    "successConditions": ["Recover the tide ledger"],
    "failureConditions": ["The last lamp goes out"],
    "rule": "any"
  },
  "narrativeGuidance": "Keep the water rising slowly; the librarians are never in real danger.",
  "startingPoint": {
    "narrativeText": "Water laps at the lowest shelves...",
    "suggestedActions": ["Wade in", "Call out"],
    "locationLabel": "Library steps",
    "goalLabel": "Recover the tide ledger",
    "progress": null
  }
}
```

---

## Relationships

```
Story 1 ──< StoryDraft (sourceStoryId — zero or more edit drafts may be in flight;
                             the Story is only ever written by an explicit save)
Story 1 ──  StoryConfiguration (serialized view of its authored fields + id)
Story 1 ──< PlaySession (adventureId) — sessions hold NO copy of the configuration (FR-010)
```

Nothing in this feature writes `PlaySession`. FR-010 is satisfied by the existing read path
(`PlaySessionService` re-reads the Story every turn), covered by a regression test rather than
a change (research.md §9).
