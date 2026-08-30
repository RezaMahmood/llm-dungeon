# Data Model: In-App Screen Refresh & Reload Resilience

**Date**: 2026-08-30

**Feature**: In-App Screen Refresh & Reload Resilience (019-spa-refresh-button)

This feature introduces no persisted entity, database container, or backend schema change (see research.md §6). Its "data model" is entirely ephemeral, client-side UI state, scoped to a single browser tab/session and never sent to storage. It is documented here for completeness and to give the Phase 1 contracts a shared vocabulary.

---

## Concept: Refreshable Data State

**Definition**: The state a screen holds while using the shared `useRefreshable` hook to load or reload its data.

**Scope**: In-memory only, per mounted component instance; discarded on unmount or a full browser reload (a browser reload re-runs the initial fetch from scratch, which is the correct, expected behavior — there is nothing to restore here beyond what FR-007's session/route restoration already covers).

### Properties

| Property | Type | Required | Value | Rationale |
|----------|------|----------|-------|-----------|
| `data` | any (screen-specific) | No | The last successfully fetched payload, or `null` before the first successful fetch | What the screen renders; unchanged on a failed refresh so the screen keeps showing its last good state instead of going blank (FR-005) |
| `loading` | boolean | Yes | `true` while a fetch is in flight | Drives the visible in-progress indication (FR-004) and disables the refresh control to prevent overlap |
| `error` | Error or null | Yes | The most recent fetch failure, cleared at the start of the next attempt | Drives the inline, non-blocking error message + retry affordance (FR-005) |
| `refresh` | function | Yes | Stable callback; no-ops if `loading` is already `true` | The single entry point every screen and the shared `RefreshButton` calls (FR-002/FR-004) |

### State Transitions

```text
idle (data=null, loading=false, error=null)
  → refresh() called → loading=true, error=null
    → fetch succeeds → data=<payload>, loading=false, error=null
    → fetch fails    → data=<unchanged>, loading=false, error=<Error>
  → refresh() called again while loading=true → no-op (FR-004)
```

---

## Concept: Unsaved-Changes Flag

**Definition**: A boolean a form or multi-step flow (currently: the Admin Story Wizard) maintains locally to say "the user has input that hasn't round-tripped to the server yet."

**Scope**: In-memory only, per mounted component instance; naturally reset to `false` on a real navigation away or a full reload (there is nothing to warn about once the page is actually gone).

### Properties

| Property | Type | Required | Value | Rationale |
|----------|------|----------|-------|-----------|
| `isDirty` | boolean | Yes | `true` from the moment a tracked field changes until the next successful save call completes | Sole input to `useUnsavedChangesWarning` (FR-010); intentionally binary, not a diff, per research.md §5 |

### State Transitions

```text
clean (isDirty=false)
  → user edits a tracked field → isDirty=true → beforeunload warning armed
    → save call (patchDraft/postMessage) succeeds → isDirty=false → warning disarmed
    → save call fails → isDirty remains true (input is still unsaved)
```

No other entities, fields, or storage are introduced by this feature.
