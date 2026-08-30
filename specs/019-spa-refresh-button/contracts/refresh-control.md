# Contract: In-App Refresh Control

**Feature**: In-App Screen Refresh & Reload Resilience (019-spa-refresh-button)

**Status**: Design agreed 2026-08-30 — the requesting product owner updated the hi-fi prototypes directly (`specs/designs/02-story-select.html`, `03-play.html`, `04-admin-wizard.html`, `05-admin-users.html`, `README.md`) with the control specified below. This is a UI/behavior contract (this feature has no HTTP API surface — see data-model.md).

---

## Cross-feature dependency: the persistent nav bar

The agreed mockups mount this control inside a persistent top nav bar (a compact title bar on the Play screen). **That nav bar does not exist as a React component yet** — it is the subject of a separate feature, `022-persistent-nav-redesign` (Draft: spec.md only, no plan/tasks yet as of 2026-08-30). 022's FR-001–FR-012 own building the nav bar itself, capability-based item visibility, and the per-screen restyling; none of them mention a refresh control, so there's no functional overlap with 019 — only a physical one: this feature's `RefreshButton` is designed to render as one of that nav bar's (or title bar's) children.

**`tasks.md` MUST resolve, not silently assume, one of:**
- (a) 019 is sequenced after 022 lands, and `RefreshButton` is added directly into 022's finished nav component; or
- (b) 019 ships first with an interim mount point (e.g., each page's own current placeholder header) and a follow-up task relocates it once 022's nav bar exists.

This plan does not pick between (a)/(b) — see plan.md's Constitution Check, Principle XI.

---

## `useRefreshable(fetchFn)`

**Location**: `src/frontend/src/hooks/useRefreshable.js`

**Input**: `fetchFn: () => Promise<T>` — an async function that performs the screen's data fetch (already-authenticated; token acquisition stays the caller's responsibility, matching the existing `acquireTokenSilent` pattern in each page).

**Output**: `{ data: T | null, loading: boolean, error: Error | null, refresh: () => void }` (see data-model.md's Refreshable Data State).

**Behavior contract**:
1. Calling `refresh()` while `loading` is already `true` MUST be a no-op — no second concurrent call to `fetchFn` (FR-004).
2. On success, `data` is replaced, `error` is cleared, `loading` returns to `false`.
3. On failure, `data` is left unchanged (the screen keeps showing its last good state), `error` is set to the caught `Error`, `loading` returns to `false`. The hook MUST NOT let the rejection propagate to a caller-level `ErrorBoundary` (FR-005).
4. `refresh()` is called once automatically on mount (replicating each screen's existing `useEffect(() => { refresh(); }, [refresh])` pattern) and again only when the caller explicitly invokes it.

**Critical constraint**: `refresh()` MUST re-invoke `fetchFn` in place. It MUST NOT call `window.location.reload()` or trigger any client-side navigation — see the note on the prototype's `onclick` below.

---

## `<RefreshButton onClick loading />`

**Location**: `src/frontend/src/components/Common/RefreshButton.jsx`

**Agreed markup** (mirrors `specs/designs/02-story-select.html` etc. exactly):

```jsx
<button
  className="btn btn-ghost"
  type="button"
  title="Refresh"
  aria-label="Refresh"
  disabled={loading}
  onClick={onClick}
  style={{ gap: 8, padding: "8px 12px", fontSize: 13 }}
>
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
       strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flex: "none" }}>
    <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8" />
    <path d="M21 3v5h-5" />
    <path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16" />
    <path d="M8 16H3v5" />
  </svg>
  {loading ? "Refreshing…" : "Refresh"}
</button>
```

**Behavior contract**:
1. Uses `.btn.btn-ghost` (not `.btn-secondary`/`.btn-primary`) — the design-system class already used elsewhere for a lower-emphasis nav-adjacent action (matches `MainMenu`'s existing `.btn.btn-ghost.logout-btn` "Sign out" button). No new design-system class is introduced.
2. The icon is the Lucide `refresh-cw` glyph, inlined as static SVG markup copied verbatim from the mockups — **no `lucide-react` (or any icon library) dependency is added** for a single icon (Principle IV/YAGNI). This is the product's first icon usage; if a second icon is ever needed elsewhere, that is the point to reconsider vendoring a full icon set, not before.
3. `disabled` (and relabeled "Refreshing…") while `loading` is `true`, satisfying the "indicate to the user that a refresh is happening" half of FR-004 (the hook's no-op satisfies the other half). Disabled styling comes from the shared `.btn` disabled state (Principle VIII) — no per-instance override.
4. Ships all four interaction states (hover/pressed/focus/disabled) for free via the shared `.btn`/`.btn-ghost` styling — no per-instance state styling is added.

**Note on the prototype's `onclick="location.reload()"`**: the static HTML mockups use `location.reload()` purely because they are inert prototypes with no real data-fetching to call — it is a placeholder to make the button clickable in a browser, not a behavioral requirement. The real `RefreshButton` MUST be wired to a screen's `useRefreshable`-provided `refresh`, never to a full page reload (see research.md §7 and the "Critical constraint" above).

---

## Screen-by-screen mounting (per the agreed prototypes)

| Screen | Route | Data source | Mount point (per updated mockup) | Notes |
|--------|-------|--------------|------------------------------------|-------|
| Story select / Main Menu | `/menu` (mockup: `02-story-select.html`) | `useCapabilities` (`GET /api/auth/me`) and/or story list, once that exists | Persistent nav bar, right-aligned before "Sign out" | Migrates `MainMenu`'s existing ad hoc `refetch`/error-button pattern onto `useRefreshable`/`RefreshButton`, inside 022's nav bar once it exists |
| Play surface | `/game` (mockup: `03-play.html`) | Placeholder today (008-core-gameplay builds real content) | Compact title bar, left of "Save a checkpoint" / "Pause & exit" | Deferred until 008 gives this screen real data — see plan.md Scale/Scope; mount point is now confirmed in advance |
| Admin Story Wizard | `/admin/stories/new` (mockup: `04-admin-wizard.html`) | `createDraft` | Persistent nav bar, right-aligned before "Sign out" | MUST NOT change `activeStep` (FR-003) — `useRefreshable` never touches step-selection state, only `draft`/`story` |
| Admin Accounts (People) | `/admin/accounts` (mockup: `05-admin-users.html`) | `listAccounts` | Persistent nav bar, right-aligned before "Sign out" | Currently has a `refresh()` callback with no visible button and no error handling — both gaps close here |
| Login | `/login` (mockup: `01-login.html`) | none | No control | Unchanged — no fetched data, matches spec Assumptions |

---

## Non-goals

- No client-side response caching or stale-while-revalidate behavior — every `refresh()` call re-fetches from the network (needed for FR-011's "current permissions" guarantee, see research.md §6).
- No global/app-wide refresh-all action — each screen's control refreshes only that screen's own data (FR-002's "that screen's current data"), even though it visually sits in a shared nav bar.
- No new icon library dependency — one inlined SVG, per Constraints above.
- Building the persistent nav bar itself is explicitly out of scope for 019 — that is `022-persistent-nav-redesign`'s deliverable (see Cross-feature dependency above).
