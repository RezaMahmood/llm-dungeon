# Contract: Persistent Nav Bar / Title Bar

**Feature**: Persistent Navigation & Design Refresh (022-persistent-nav-redesign)

**Status**: Agreed for the link sets and structure below (spec.md FR-001–FR-009,
`specs/designs/02-story-select.html`, `04-admin-wizard.html`, `05-admin-users.html`).
**The trailing button cluster before "Sign out" is explicitly NOT yet finalized** —
see the Open Item at the end of this contract and plan.md's Constitution Check
(Principle XI). This is a UI/behavior contract; this feature has no HTTP API surface.

---

## Cross-feature dependency: `019-spa-refresh-button`

This nav bar / title bar is the mount point `019-spa-refresh-button`'s `RefreshButton`
is designed to render inside (see that feature's `contracts/refresh-control.md`).
Building `NavBar`'s trailing button cluster as an ordinary flex row (not a hardcoded
"Sign out is the last child" assumption) keeps that future addition non-restructuring,
whichever way the Open Item below resolves.

---

## `<AuthenticatedLayout>{children}</AuthenticatedLayout>`

**Location**: `src/frontend/src/components/Layout/AuthenticatedLayout.jsx`

**Behavior contract**:
1. Renders `NavBar` for every authenticated route except the story-play route
   (currently `/game`), where it renders `TitleBar` instead (FR-001, FR-006).
2. Renders `children` below/after whichever header it chose.
3. Never renders on `/login` — this component is only ever mounted from inside
   `ProtectedRoute.jsx`, which unauthenticated users never reach (FR-009).
4. Passes no props children don't already receive today — this is a pure
   presentational wrapper, not a new data-fetching boundary.

## `<NavBar />`

**Location**: `src/frontend/src/components/Layout/NavBar.jsx`

**Markup base** (from `designTokens.css:216-227`'s existing `.nav`/`.nav-brand`
classes, and `specs/designs/04-admin-wizard.html:21-30` / `05-admin-users.html:20-29`
for the admin link set, `specs/designs/02-story-select.html:21-26` for the player set):

```jsx
<div className="nav">
  <span className="nav-brand">Lantern{/* + "Admin" sub-label when hasAdministrator, per 04/05 markup */}</span>
  {/* admin set, visible when hasAdministrator */}
  <a href="/admin" aria-current={isCurrent("/admin") || undefined}>Stories</a>
  <a href="/admin/stories/new" aria-current={isCurrent("/admin/stories/new") || undefined}>New story</a>
  <a href="/admin/accounts" aria-current={isCurrent("/admin/accounts") || undefined}>People</a>
  {/* divider + cross-role link, only when hasAdministrator && hasPlayer */}
  <span className="nav-divider" />
  <a href="/menu">Player view</a>
  {/* player set, visible when hasPlayer */}
  <a href="/menu" aria-current={isCurrent("/menu") || undefined}>My stories</a>
  <a href="#">Badges</a>
  {/* cross-role link, only when hasAdministrator && hasPlayer */}
  <a href="/admin">Admin</a>
  {/* always visible, right-aligned */}
  <a href="/login" style={{ marginLeft: "auto" }} onClick={signOut}>Sign out</a>
  <span className="tag tag-neutral">{userName}</span>
</div>
```

**Behavior contract**:
1. Item visibility follows the derivation rules in `data-model.md`'s `NavItem` table
   — driven solely by `useCapabilities()`'s `hasPlayer`/`hasAdministrator`, with no
   new capability or permission concept (FR-008, spec Assumptions).
2. Exactly one item (or none, on `/login` — unreachable here) carries
   `aria-current="page"`, matching `useLocation().pathname` (FR-007). No two items are
   ever both current at once.
3. The dual-capability cross-role links ("Player view" from the admin set, "Admin"
   from the player set) render only when both `hasPlayer` and `hasAdministrator` are
   true (spec User Story 3, Acceptance Scenario 3).
4. When neither capability is granted, only the brand mark, "Sign out," and the user's
   name render — no primary destination links (Edge Cases).
5. "Sign out" and the user-name tag are always present, right-aligned, regardless of
   capabilities (FR-004).
6. Long user display names or story titles truncate/ellipsize rather than breaking
   the bar's layout (Edge Cases) — reuse the existing `text-overflow: ellipsis`
   utility pattern already available via the design tokens; no new CSS is invented
   beyond what a narrowly-scoped utility class permits under Principle VIII.

## `<TitleBar story={...} />`

**Location**: `src/frontend/src/components/Layout/TitleBar.jsx`

**Markup base** (from `specs/designs/03-play.html:23-33`, Refresh button excluded per
the Open Item below):

```jsx
<div className="titlebar">
  <a href="/menu" className="nav-brand">Lantern</a>
  <span className="titlebar-divider" />
  <span className="titlebar-title">{storyTitle}</span>
  <button className="btn btn-secondary" type="button" onClick={onSaveCheckpoint}>Save a checkpoint</button>
  <button className="btn btn-primary" type="button" onClick={onPauseExit}>Pause &amp; exit</button>
</div>
```

**Behavior contract**:
1. Renders only on the story-play route (currently `/game`), replacing `NavBar`
   entirely — not an addition alongside it (FR-006).
2. The brand mark returns to story select (`/menu`), matching
   `specs/designs/README.md`'s documented behavior ("The `Lantern` mark at its left
   returns to story select").
3. `storyTitle` truncates/ellipsizes rather than pushing "Save a checkpoint"/"Pause &
   exit" out of view (Edge Cases).
4. Preserves the full-height story reading area below it — no change to the
   scroll-contract rules already governing `/game` (constitution's Layout and scroll
   contract section; this feature does not alter that contract, only the header above it).
5. **Out of scope for this feature**: `Save a checkpoint`/`Pause & exit`'s actual
   behavior is `GamePage.jsx`'s and `008-core-gameplay`'s concern — `TitleBar` renders
   the buttons and calls whatever handlers `GamePage.jsx` supplies (currently
   no-ops/placeholders, matching `GamePage.jsx`'s current placeholder status).

---

## Open item: the trailing button cluster (Refresh control)

**Do not implement a Refresh button as part of this feature's tasks** — 019 owns
`RefreshButton`'s component and behavior. This feature's obligation is only to leave
the trailing button cluster (before "Sign out" on `NavBar`, before "Save a checkpoint"
on `TitleBar`) as an ordinary flex row so a future `RefreshButton` insertion doesn't
require restructuring — and to route the Principle XI sign-off (plan.md Constitution
Check) that decides whether one belongs there at all before this feature's own
implementation tasks are marked complete, since the sign-off task gates this feature's
nav-bar tasks, not only 019's.

## Non-goals

- No new capability/permission model — reuses `hasPlayer`/`hasAdministrator` as-is.
- No client-side route guarding logic changes — `ProtectedRoute.jsx`'s existing
  authentication/capability checks are unchanged in substance; this feature only adds
  a rendering wrapper around what it already renders.
- No new icon library or icon usage beyond what the merged mockups already specify.
- Building `019-spa-refresh-button`'s `RefreshButton`/`useRefreshable` is explicitly
  out of scope here — see the Open Item above.
