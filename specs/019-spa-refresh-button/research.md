# Research: In-App Screen Refresh & Reload Resilience

**Date**: 2026-08-30 | **Status**: Research Phase Complete

## 1. Root Cause: Why a Browser Reload Can Sign a User Out (FR-006/FR-007/FR-009)

**Unknown**: The spec's premise is that "using the browser's refresh button will kill the app." What in the current codebase actually causes that, so the fix targets the real defect rather than a guess?

**Decision**: `ProtectedRoute.jsx` calls `useIsAuthenticated()` and immediately renders `<Navigate to="/login" replace />` when it returns `false` — with no check of MSAL's own initialization state. `@azure/msal-react`'s `MsalProvider` must first call `PublicClientApplication.initialize()` and `handleRedirectPromise()`, which asynchronously reads the cached account from `localStorage` (`msalConfig.js` sets `cacheLocation: "localStorage"`, so the session *is* present across a reload — it just isn't loaded into memory yet on the very first render). During that window, `useIsAuthenticated()` reports `false` for a user with a perfectly valid session, and `ProtectedRoute` redirects to `/login` before MSAL finishes reading its own cache. The fix is to gate `ProtectedRoute` on `useMsal().inProgress` (MSAL's `InteractionStatus`) — render a loading state while `inProgress !== InteractionStatus.None`, and only judge `isAuthenticated` once MSAL has finished initializing.

**Rationale**: This explains the exact symptom in FR-007/FR-009/SC-004 ("never required to sign in again" / "restore the user... where it is still valid") without inventing a new persistence mechanism — the session was never actually lost, the check just ran too early.

**Alternatives considered**:
- Switching `cacheLocation` to `sessionStorage` or adding a custom persistence layer: rejected — the cache location was never the problem; the bug is a premature synchronous read of async-loading state.
- Wrapping every protected page in `MsalAuthenticationTemplate`: rejected as a larger refactor than needed; a single `inProgress` check in the one existing `ProtectedRoute` gate is the minimal fix (YAGNI).

**Validation**: A component test renders `ProtectedRoute` with a mocked `useMsal` returning `inProgress: InteractionStatus.Startup` and asserts it shows a loading state (not a redirect); a second case with `inProgress: InteractionStatus.None, isAuthenticated: true` asserts children render.

---

## 2. Root Cause: Why a Browser Reload on a Nested Route Can Show an Error Page (FR-006/SC-003)

**Unknown**: `App.jsx` uses `react-router-dom`'s `BrowserRouter`, which relies entirely on client-side JavaScript to render a route like `/admin/stories/new`. A hard reload or a direct URL open asks the *server* (Azure Static Web Apps) for that exact path first. Does the current deployment guarantee that request resolves to the SPA shell rather than a platform 404?

**Decision**: No — there is no `staticwebapp.config.json` anywhere in the repo, and `frontend-deploy.yml` deploys `src/frontend/dist` with `api_location: ""` (the linked Function App backend, per `infrastructure/terraform/main.tf`'s "Links the Function App as this Static Web App's backend" comment, is attached separately at the SWA-resource level, not via this workflow's `api_location`). Add `src/frontend/public/staticwebapp.config.json` with an explicit `navigationFallback` rewriting unmatched navigation requests to `/index.html`, excluding `/api/*` (the linked backend's route prefix) and static asset extensions. This turns an implicit, undocumented platform default into an explicit, reviewable, and testable contract — see `contracts/reload-resilience.md`.

**Rationale**: Even where Azure Static Web Apps' own default behavior might already happen to serve `index.html` for an unmatched path in some configurations, relying on an unstated platform default for a NON-NEGOTIABLE user-facing requirement (FR-006, "MUST NOT... error page") is exactly the kind of implicit behavior Principle IX's rationale warns about — deployment/platform routing behavior that automated tests running against mocks or a local dev server cannot exercise. Pinning it explicitly in-repo also makes the contract something `/speckit-analyze` and code review can actually check.

**Alternatives considered**:
- Switching from `BrowserRouter` to `HashRouter` (URLs like `/#/admin/stories/new`) so the server only ever sees `/`: rejected — a larger, visible URL-shape change with no upside once the fallback config exists, and inconsistent with the already-shipped, bookmarked/shared URLs from `002`/`003`.
- Adding a custom 404 page that client-side redirects: rejected — still shows a transient error/blank page during the redirect, which is exactly what FR-006 prohibits; a server-side rewrite is strictly better and is the platform-native mechanism for this.

**Validation**: An integration test (or a documented manual quickstart step, since this is genuinely a hosting-platform behavior — see Principle IX) confirms a direct request for a nested path returns the app shell, not a 404, against a deployed or SWA-emulated environment (`swa-cli` / Azure Static Web Apps CLI emulator, if available, is the closest automatable approximation; the definitive check remains the quickstart's manual verification against the real deployment).

---

## 3. Reusing vs. Reinventing the Refresh Pattern (FR-001/FR-002/FR-004)

**Unknown**: `MainMenu.jsx` already has a working `refetch`-driven "Refresh"/"Try again" button (from `useCapabilities`); `AdminAccountsPage.jsx` has its own local `refresh` callback with no visible button, no in-flight guard beyond a `loading` boolean, and no error handling; `AdminStoryWizardPage.jsx` has none. Should each screen keep inventing its own version, or is there a shared abstraction worth extracting?

**Decision**: Extract a small `useRefreshable(fetchFn)` hook — wraps an async function, exposes `{ data, loading, error, refresh }`, and internally no-ops a `refresh()` call while one is already in flight (satisfying FR-004 uniformly instead of per-screen). Pair it with a `RefreshButton` component (`.btn.btn-secondary`, `disabled` + relabeled while `loading`) so every screen renders the control identically. `MainMenu`, `AdminAccountsPage`, and `AdminStoryWizardPage` are migrated onto it.

**Rationale**: Three screens already show three slightly different hand-rolled versions of the same idea (one has a button, one doesn't; none but `MainMenu` handle a failed fetch without risking the top-level `ErrorBoundary`). Centralizing keeps FR-004/FR-005's guarantees true by construction for every current and future screen, rather than as a convention someone has to remember to repeat (directly serves Principle I's "every... edge case MUST have a corresponding automated test" — one hook's tests cover the guarantee everywhere it's used).

**Alternatives considered**:
- A data-fetching library (e.g., TanStack Query): rejected — pulls in a new dependency and a caching model this feature doesn't need (Principle IV); the app has three simple screens, not a cache-invalidation problem.
- Leaving each screen's refresh logic as-is and only adding a visible button: rejected — would still leave `AdminAccountsPage`'s and `AdminStoryWizardPage`'s uncaught-exception-on-failed-refresh gap open, failing FR-005.

**Validation**: `useRefreshable.test.jsx` asserts a second `refresh()` call while one is pending is a no-op (FR-004) and that a rejected fetch sets `error` without throwing (FR-005); each migrated screen's existing/extended test confirms the button is present and functional (FR-001/FR-002).

---

## 4. Surfacing "Session Expired" Distinctly from a Normal Login Screen (FR-008)

**Unknown**: `useCapabilities.js` already redirects to Microsoft's login on a 401 (`instance.loginRedirect(loginRequest)`), and `ProtectedRoute` redirects an unauthenticated user to `/login`. FR-008 requires this be accompanied by "a clear explanation," not a bare login screen indistinguishable from a first-time sign-in.

**Decision**: `LoginScreen.jsx` already has exactly this mechanism, just not yet used for this case — a local `MESSAGES` map (`cancelled`/`failed`) driving a `status`/`message` pair rendered as inline copy. Add a third key, `sessionExpired: "Your session ended — please sign in again."`, and carry the reason via React Router navigation state (`navigate("/login", { state: { reason: "session-expired" } })` / `<Navigate to="/login" state={{ reason: "session-expired" }} replace />`) rather than a query param, so `LoginScreen` reads `useLocation().state?.reason` on mount and seeds its existing `status`/`message` state from it — the exact same rendering path its own `handleSignIn` failure cases already use.

**Rationale**: Reuses both the existing redirect-to-`/login` mechanism and `LoginScreen`'s already-built status-message pattern rather than inventing a second, parallel way to say the same kind of thing (Principle IV). Router state is also a more natural fit than a query param here since `ProtectedRoute` already renders `<Navigate>` (a React Router element) rather than performing a raw redirect.

**Alternatives considered**:
- A global toast/notification system: rejected — no such system exists yet, and building one is out of scope for a single message (YAGNI).
- Silently redirecting with no explanation (today's behavior): rejected outright — this is exactly what FR-008 prohibits.

**Validation**: A `LoginScreen` test asserts the explanatory line renders when `location.state.reason === "session-expired"` and is absent otherwise; an integration test drives the expired-session path and asserts the navigation carries that state.

---

## 5. Unsaved-Input Warning Mechanism (FR-010, User Story 3)

**Unknown**: No form or wizard in the codebase currently warns before a reload/close discards input. What's the minimal, standard mechanism, and where does "dirty" state come from?

**Decision**: A small `useUnsavedChangesWarning(isDirty)` hook that attaches/detaches the standard `window.addEventListener("beforeunload", ...)` handler (calling `event.preventDefault()` / setting `event.returnValue`, the browser-standard pattern that triggers the native "leave site?" confirmation) whenever `isDirty` is `true`. `AdminStoryWizardPage` is the concrete current consumer: it passes `isDirty` as true whenever a step's local form fields differ from the last successfully-saved `draft`/`story` state.

**Rationale**: This is the browser-native mechanism for exactly this warning (no custom modal can intercept a native browser reload/close — only `beforeunload` can), and it is intentionally a *browser*-presented prompt, not an in-app one, consistent with the spec's Assumptions ("standard browser behavior for unsaved changes"). Scoping "dirty" to the wizard's own local edit state (not full byte-for-byte diffing against the server) keeps the check cheap and matches the spec's Acceptance Scenario framing ("has unsaved input" is a simple boolean, not a deep-diff requirement).

**Alternatives considered**:
- A custom in-app "are you sure?" dialog: rejected — cannot intercept the browser's own native reload/close action; only `beforeunload` can produce a prompt at that exact moment.
- Marking every keystroke dirty forever (never clearing the flag): rejected — would show the warning even immediately after a successful save, which is not "unsaved" input; the flag must clear on each successful `patchDraft`/`postMessage` round trip.

**Validation**: `useUnsavedChangesWarning.test.jsx` asserts the `beforeunload` listener is attached only while `isDirty` is `true` and removed once it flips back to `false`; a wizard integration test dirties a step's field and asserts the hook's `isDirty` output reflects it, then asserts it clears after a successful save.

---

## 6. Confirming No Backend Change Is Needed (FR-011)

**Unknown**: FR-011 requires a refreshed screen to reflect the user's *current* permissions, not permissions captured when the screen first loaded. Does this require a backend change?

**Decision**: No. `GET /api/auth/me` (consumed by `useCapabilities`) already computes `hasPlayer`/`hasAdministrator` fresh from the account-provisioning data store on every call — there is no server-side caching of a prior result. As long as the frontend's refresh action genuinely re-invokes this endpoint (rather than reusing a client-cached value), FR-011 is satisfied by the existing backend as-is.

**Rationale**: Avoids inventing backend work Principle IV would flag as premature; the only frontend obligation is to ensure `useRefreshable`-driven refreshes call the real endpoint each time, which they do by construction (no client-side response caching is introduced anywhere in this design).

**Alternatives considered**: None — this is a confirmation, not a design choice with real alternatives.

**Validation**: Existing `useCapabilities` and `/api/auth/me` tests already cover this; this feature adds no new assertion here beyond confirming `useRefreshable`'s migration of `MainMenu` still calls `refetch`/`getMe` on each activation.

---

## 7. Design Sign-Off Update (2026-08-30): Ghost Button + Icon, Mounted in the Persistent Nav

**Update**: After this plan's first pass proposed a `.btn.btn-secondary`, no-icon, per-screen-heading placement (§3 above still records that reasoning trail), the requesting product owner directly updated the hi-fi prototypes with the actual agreed design: a `.btn.btn-ghost` button combining a Lucide `refresh-cw` icon with a "Refresh" text label, mounted in the persistent top nav bar on `specs/designs/02-story-select.html`, `04-admin-wizard.html`, `05-admin-users.html`, and in the compact title bar on `03-play.html`. `specs/designs/README.md` now documents this under a "## Refresh" section: "Same treatment everywhere; it re-fetches the current view and never navigates."

**Decision**: Adopt this design as-is rather than the earlier proposal. The icon is inlined as a hand-copied SVG (the exact `<path>` data already authored in the mockups) rather than adding the `lucide-react` npm package — one icon does not justify a new dependency (Principle IV/YAGNI), and the mockup's raw-SVG approach is trivially portable into a React component as static JSX markup.

**Important correction — the mockup's `onclick="location.reload()"` is a static-prototype placeholder only.** The real implementation MUST call the screen's `useRefreshable`-driven re-fetch, never `window.location.reload()` — a real full-page reload would contradict FR-002/FR-003 (must not navigate away, sign the user out, or reset wizard step) and would also make FR-004's overlapping-refresh guard meaningless. `contracts/refresh-control.md` states this explicitly so no one copies the mockup's `onclick` literally.

**New dependency surfaced**: The persistent nav bar / title bar shown in these updated mockups does not exist as a React component yet — it is the subject of its own, separately-spec'd feature, `022-persistent-nav-redesign-done` (currently Draft: spec.md only, no plan/tasks). That feature's FR-001–FR-012 describe the nav bar's construction, capability-based item visibility, and per-screen restyling; none of its requirements mention a refresh control, so there is no functional overlap or duplication with 019 — but there is a physical one: 019's `RefreshButton` is designed to mount inside 022's nav bar / title bar component. This plan does not resolve the sequencing question (019 depends on 022 landing first, vs. 019 ships an interim placement and relocates once 022 lands) — that decision belongs to `/speckit-tasks`, informed by whichever the user/product owner intends to schedule first.

**Rationale**: Treating the product owner's direct prototype edit as authoritative (rather than re-deriving a placement from first principles) is exactly what Principle XI's sign-off gate is for — the whole point is that implementation follows an explicit human decision, not the planning agent's own design judgment.

**Alternatives considered**: Keeping the original per-screen-heading, no-icon, `.btn.btn-secondary` proposal now that a concrete, different design has been explicitly provided — rejected; that would mean implementing against a design the product owner did not choose.

**Validation**: `RefreshButton.test.jsx` snapshot/markup-asserts the button matches the mockup's structure (icon + label, `.btn.btn-ghost`, `aria-label="Refresh"`, `title="Refresh"`); a visual/manual quickstart step (already covered by Principle IX's final acceptance task) confirms it renders identically to the prototype once mounted.
