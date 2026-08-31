# Contract: In-App Refresh Control

**Feature**: In-App Screen Refresh & Reload Resilience (019-spa-refresh-button)

**Status**: Design agreed 2026-08-30 — the requesting product owner updated the hi-fi prototypes directly (`specs/designs/02-story-select.html`, `03-play.html`, `04-admin-wizard.html`, `05-admin-users.html`, `README.md`) with the control specified below. This is a UI/behavior contract (this feature has no HTTP API surface — see data-model.md).

---

## Cross-feature dependency: the persistent nav bar (resolved 2026-08-31)

The agreed mockups mount this control inside a persistent top nav bar (a compact title bar on the Play screen). That nav bar was built by a separate feature, `022-persistent-nav-redesign-done`, which has since **merged to `main`** (`1b79aa8`, `5a4dce6`; PRs #103/#104): `src/frontend/src/components/Layout/NavBar.jsx` and `TitleBar.jsx` now exist, and `NavBar.jsx` reserves an explicit `data-nav-slot="trailing-actions"` `<span>` for this feature's `RefreshButton`. 022's own FR-001–FR-012 own the nav bar's structure and capability-based visibility; none of them mention a refresh control, so there is no functional overlap — only the (now-resolved) physical one.

**Newly discovered wiring gap**: `AuthenticatedLayout.jsx` renders `NavBar`/`TitleBar` as a **sibling** of the active page's content, not a parent — `{isStoryPlay ? <TitleBar/> : <NavBar/>} {children}` — so a page has no prop-based path to hand its `useRefreshable` state to the nav bar next to it. (`TitleBar.jsx` has this identical, still-unsolved gap for its own `onSaveCheckpoint`/`onPauseExit` props.)

**Resolution (decided 2026-08-31, `/speckit-analyze` remediation)**: a small `RefreshContext` — see below. Rejected alternative: lifting `NavBar` rendering into each page, which would undo 022's centralization and reintroduce per-page header duplication.

---

## `RefreshContext`

**Location**: `src/frontend/src/context/RefreshContext.jsx`

**Purpose**: Lets a page publish its `useRefreshable` state up to `NavBar`/`TitleBar`, which render as its sibling (not its parent) under `AuthenticatedLayout`.

**API**:
- `<RefreshProvider>` — wraps `AuthenticatedLayout`'s children once, near the app root, so any page underneath can publish into it and `NavBar`/`TitleBar` (also underneath the same provider) can read it.
- `usePublishRefresh({ refresh, loading })` — called by a page (e.g. `MainMenu`, `AdminAccountsPage`, `AdminStoryWizardPage`) with its `useRefreshable` output; sets the context value while mounted and clears it on unmount, so navigating away from a page removes its control from the nav bar.
- `useRefreshContext()` — called by `NavBar` (and, once the Play screen has real data, `TitleBar`); returns `{ refresh, loading } | null`. `NavBar` renders `RefreshButton` in `trailing-actions` only when this is non-null.

**Behavior contract**:
1. Exactly one page's state is published at a time — the currently-mounted page's `usePublishRefresh` call. A page that never calls it (e.g. `LoginScreen`) leaves the context `null`, so `NavBar` shows no refresh control.
2. Unmounting the publishing page (route change) clears the published value before the next page's `useEffect` runs, so the nav bar never briefly shows a stale/wrong screen's refresh control.
3. This is UI wiring state only — no data, no persistence; scoped to a single mounted tree.

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
| Story select / Main Menu | `/menu` (mockup: `02-story-select.html`) | `useCapabilities` (`GET /api/auth/me`) and/or story list, once that exists | `NavBar.jsx`'s `trailing-actions` slot, via `usePublishRefresh` | Migrates `MainMenu`'s existing ad hoc `refetch`/error-button pattern onto `useRefreshable`; publishes into `RefreshContext` rather than rendering `RefreshButton` itself |
| Play surface | `/game` (mockup: `03-play.html`) | Placeholder today (008-core-gameplay builds real content) | `TitleBar.jsx`'s `trailing-actions` slot (not wired in this feature) | Deferred until 008 gives this screen real data — see plan.md Scale/Scope; `TitleBar` will consume `RefreshContext` the same way `NavBar` does once that lands |
| Admin Story Wizard | `/admin/stories/new` (mockup: `04-admin-wizard.html`) | `createDraft` | `NavBar.jsx`'s `trailing-actions` slot, via `usePublishRefresh` | MUST NOT change `activeStep` (FR-003) — `useRefreshable` never touches step-selection state, only `draft`/`story` |
| Admin Accounts (People) | `/admin/accounts` (mockup: `05-admin-users.html`) | `listAccounts` | `NavBar.jsx`'s `trailing-actions` slot, via `usePublishRefresh` | Currently has a `refresh()` callback with no visible button and no error handling — both gaps close here |
| Login | `/login` (mockup: `01-login.html`) | none | No control | Unchanged — no fetched data, matches spec Assumptions; never calls `usePublishRefresh` |

---

## Non-goals

- No client-side response caching or stale-while-revalidate behavior — every `refresh()` call re-fetches from the network (needed for FR-011's "current permissions" guarantee, see research.md §6).
- No global/app-wide refresh-all action — each screen's control refreshes only that screen's own data (FR-002's "that screen's current data"), even though it visually sits in a shared nav bar.
- No new icon library dependency — one inlined SVG, per Constraints above.
- Building the persistent nav bar itself is explicitly out of scope for 019 — that is `022-persistent-nav-redesign-done`'s deliverable (see Cross-feature dependency above).
