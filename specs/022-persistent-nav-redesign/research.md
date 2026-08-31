# Phase 0 Research: Persistent Navigation & Design Refresh

## 1. Where does the nav bar mount, architecturally?

**Decision**: Add `AuthenticatedLayout.jsx`, rendered from inside `ProtectedRoute.jsx`
(wrapping `children`), rather than adding it per-page or at the `App.jsx` route-table
level.

**Rationale**: `ProtectedRoute.jsx` is already the single choke point every guarded
route passes through (`App.jsx:34-87` wraps every route but `/login` in it), and it
already resolves `useCapabilities()` for its own capability-gate check — the same data
the nav bar needs to decide which links to show. Wrapping there means no route
definition in `App.jsx` needs to change, and no individual page component needs to
remember to render the nav bar itself (which would risk a screen silently missing it,
violating FR-001/SC-002).

**Alternatives considered**:
- *Each page renders its own `<NavBar>`*: rejected — exactly the "hub-menu dead end"
  problem in miniature; a screen could omit it by mistake, and five copies of the same
  render call is unnecessary duplication for zero benefit.
- *A layout `<Route>` wrapping nested routes (`react-router` layout-route pattern)*:
  would require restructuring `App.jsx`'s flat route list into a nested one. Rejected
  for this feature — bigger diff than necessary, and `ProtectedRoute` already does the
  per-route wrapping job; nesting is YAGNI here.

## 2. How does the nav bar know which item is "current"?

**Decision**: `AuthenticatedLayout` reads `useLocation().pathname` from
`react-router-dom` and passes the current path to `NavBar`, which matches it against
each item's own route to set `aria-current="page"` and the active-item styling class,
exactly as the mockups already do with a static `aria-current="page"` attribute on the
matching `<a>` (e.g. `specs/designs/04-admin-wizard.html:24`).

**Rationale**: `useLocation` is already a dependency (`react-router-dom` is already in
use); no new state or context is needed — the URL is the single source of truth for
"where am I," matching FR-007's requirement.

**Alternatives considered**: A React Context tracking "current section" set imperatively
by each page — rejected, it duplicates information the router already has and could
drift out of sync with the actual URL.

## 3. Story-play screen: title bar vs. nav bar

**Decision**: `AuthenticatedLayout` renders `TitleBar` instead of `NavBar` when
`useLocation().pathname` matches `/game` (or, more precisely, matches whichever route
serves the active story-play surface — currently `/game`), per FR-006 and the
`03-play.html` mockup's compact header.

**Rationale**: The spec (Edge Cases, FR-006) explicitly documents this as an
intentional exception to preserve the full-height reading area, not a nav-bar gap.
Route-based switching inside one layout component keeps the "which screens get which
header" decision in one place rather than scattering `if (isPlayScreen)` checks.

**Alternatives considered**: Have `GamePage.jsx` opt out of `AuthenticatedLayout`
entirely and render its own title bar inline — rejected, it would duplicate the
brand-mark/return-to-select markup `TitleBar` already needs to own, and would make
`GamePage.jsx` responsible for a decision (which header type appears) that belongs to
the layout, not the page.

## 4. Capability-to-nav-item mapping

**Decision**: Reuse `useCapabilities()` exactly as `ProtectedRoute.jsx` already does
(`hasPlayer`, `hasAdministrator` booleans from `GET /api/auth/me`); `NavBar` derives
its two link sets and the cross-role "Player view"/"Admin" links directly from these
two booleans, with no new capability, permission, or role concept introduced.

**Rationale**: Spec Assumptions state explicitly: "Capability-based visibility of nav
items reuses the existing capability model already enforced by the app's route
protections; this feature introduces no new permission logic." `hasPlayer` and
`hasAdministrator` are exactly and only the two capabilities the spec's User Story 3
and FR-002/003/008 describe (player-only, admin-only, dual, neither).

**Alternatives considered**: A dedicated `useNavItems()` hook computing a
`{label, href, visible}[]` array — considered for testability, but rejected as an
unnecessary layer for two booleans and two short, static link lists; `NavBar` can
compute this inline and still be fully unit-testable by rendering it with different
`useCapabilities()` mock return values.

## 5. Restyle strategy for the three functional screens

**Decision**: Restyle `MainMenu.jsx`, `AdminAccountsPage.jsx`, and
`AdminStoryWizardPage.jsx` in place — same components, same data-fetching/mutation
code, only their JSX structure/classes and the (now removed) ad hoc header markup
change. `MainMenu.css` is retired in favor of `designTokens.css` classes.

**Rationale**: FR-012 requires this be "a visual and navigational change only";
FR-011 specifically calls out preserving `AdminAccountsPage`'s one-at-a-time
remove-with-confirmation flow. Editing in place (rather than rewriting each page from
scratch against the mockup) is the smallest change that satisfies both constraints,
and keeps existing tests for data behavior valid with only their rendering
assertions needing updates.

**Alternatives considered**: A full rewrite of each page component from the mockup
HTML — rejected; higher regression risk against FR-011/FR-012 for no benefit, since
the existing components' logic already works correctly.

## 6. Design-artifact discrepancy: the Refresh control claim

**Finding**: `019-spa-refresh-button`'s plan.md, research.md (§7), and tasks.md (T001,
T009–T011) all assert that the product owner directly updated
`specs/designs/02-story-select.html`, `04-admin-wizard.html`, and
`05-admin-users.html` (plus `README.md`, under a new "## Refresh" section) to add a
`.btn.btn-ghost` Refresh control with an inlined Lucide `refresh-cw` icon to the shared
nav bar — citing commit `4a43123` / merged PR #79 (`71a4ca9` on `main`).

**Verification performed**: Grepped the actual contents of `specs/designs/02-story-select.html`,
`04-admin-wizard.html`, `05-admin-users.html`, and `README.md` on this branch
(descended from `main` at `4d501e0`) for "refresh"/"Refresh"/"refresh-cw"/"reload" —
**no match in any of the three nav-bar screens or the README**. Only
`specs/designs/03-play.html`'s title bar (lines 29–32) actually contains the Refresh
button. `git show 71a4ca9` confirms the merged diff touched only
`specs/022-persistent-nav-redesign/spec.md` and `specs/004-story-creation/*` content in
its first parent, with a second commit message claiming the four-screen addition — but
the file contents as they exist on `main`/this branch do not reflect that second
commit's stated scope for `02`/`04`/`05`/`README.md`.

**Decision**: Do not silently build this feature's nav bar to match either feature's
current assumption (neither "definitely no Refresh slot" nor "definitely already
agreed to have one" is safe to assume unilaterally). Instead, treat this as a Principle
XI (UI Design Pre-Agreement) gating item for `tasks.md` — see plan.md's Constitution
Check. `NavBar`'s implementation should keep its trailing button cluster (before "Sign
out") as a plain flex row so that adding a Refresh control later, if the product owner
confirms one, is a small addition rather than a restructure.

**Rationale**: Principle XI is explicit that implementation must not proceed on the
implementing agent's own design judgment where the requesting product owner's actual,
current intent is genuinely ambiguous — and here it is ambiguous precisely because two
features' planning artifacts disagree with the actual mockup files.

## 7a. Admin "Stories" nav destination (post-clarification, 2026-08-30)

**Finding**: Both `04-admin-wizard.html` and `05-admin-users.html` point their
"Stories" nav link at the same file as "New story" (`04-admin-wizard.html`), i.e. the
mockups never actually differentiate the two destinations — there is no separate
"Stories list" mockup. This plan originally assumed (without a recorded sign-off)
that "Stories" would simply land on the existing `/admin` placeholder page unchanged.
`/speckit-analyze` flagged this as an unresolved Principle XI gap; `/speckit-clarify`
resolved it directly with the requesting user (spec.md Clarifications, 2026-08-30):
"Stories" must lead to a distinct, minimal, read-only stories-list view (FR-013,
SC-007).

**Decision**: Build the list at `/admin` (`AdminPage.jsx`) using the
already-implemented, already-authorized `GET /api/manage/stories` endpoint
(`backend/api/admin/stories.py:list_stories` → `StoryService.list_summaries()` →
`{id, name, published, createdAt}` per story). Add `storyService.js` mirroring
`accountService.js`'s existing fetch pattern; `AdminPage.jsx` fetches on mount (same
pattern as `AdminAccountsPage.jsx`'s `refresh()`) and renders each story's name and
published/draft status, or an empty-state message when the list is empty.

**Rationale**: No backend work is needed — the endpoint, its admin authorization, and
its integration test (`backend/tests/integration/test_admin_stories_endpoint.py`)
already exist and are unrelated to this feature's own scope; reusing them keeps this
addition a small, in-pattern frontend change rather than a new subsystem (Principle
IV/YAGNI). This also gives "Stories" and "New story" the visibly distinct
destinations FR-002 now explicitly requires.

**Alternatives considered**:
- *Leave "Stories" pointed at the `/admin` placeholder unchanged*: rejected by the
  requesting user during clarification — an admin clicking "Stories" expecting to see
  existing stories and finding nothing was judged confusing enough to fix now rather
  than defer.
- *Build a full story-management view (edit/publish/delete actions) at `/admin`*:
  rejected — out of scope; `005-story-publishing`/`012-story-editing-and-review` own
  those actions. This feature's list is read-only.

## 7. Testing approach

**Decision**: Component tests for `NavBar` (each capability combination → expected
link set + cross-role link + `aria-current`), `TitleBar` (renders on `/game`, not
elsewhere), and `AuthenticatedLayout` (picks `NavBar` vs `TitleBar` by route);
integration tests re-asserting `AdminAccountsPage`'s existing remove/confirm behavior
still passes with the new markup, a wizard-navigation test (start a step, click a
nav link, return, confirm saved fields persist) covering FR-005/SC-003, and an
`AdminPage` integration test covering FR-013/SC-007 (renders fetched stories'
name/status; renders an empty state with no error when the list is empty), mocking
`storyService.js`'s `listStories` the same way `AdminAccountsPage.test.jsx`-style
tests already mock `accountService.js`.

**Rationale**: Matches the existing Vitest + RTL convention
(`src/frontend/tests/{components,hooks,integration}`) already used by
`019-spa-refresh-button`'s own plan and by the current test suite.

**Alternatives considered**: Visual/screenshot regression testing against the mockup
HTML files — no such tooling exists in this repo today, and Principle IV/YAGNI
disfavors introducing one for a single feature; Principle IX's user-verified
acceptance task is the intended check for visual fidelity instead.
