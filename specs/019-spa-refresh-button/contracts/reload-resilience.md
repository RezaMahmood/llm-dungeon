# Contract: Browser Reload Resilience

**Feature**: In-App Screen Refresh & Reload Resilience (019-spa-refresh-button)

This is a UI/hosting behavior contract covering what MUST happen when the browser's own native reload (or a direct URL open, or back/forward navigation) hits any authenticated route. See research.md §1–§2 for the root-cause analysis behind each guarantee below.

---

## Guarantee 1 — Deep-link routes resolve to the app shell, not a platform 404 (FR-006, SC-003)

**Mechanism**: `src/frontend/staticwebapp.config.json`, deployed as part of `src/frontend/dist` (per `frontend-deploy.yml`).

**Contract**:
- A request for any path that is not a real static asset (no file extension) and not under the linked backend's `/api/*` prefix MUST be rewritten to `/index.html` (`navigationFallback.rewrite`).
- `/api/*` MUST be excluded from the fallback (`navigationFallback.exclude`), so backend calls continue to reach the linked Azure Functions app rather than being served the SPA shell.
- Real static assets (`*.js`, `*.css`, images, etc.) MUST be excluded from the fallback so a missing asset still 404s normally rather than silently serving HTML (which would otherwise surface as a confusing JS parse error, not a clean 404).

**Verification**: Automated where an Azure Static Web Apps emulator is available in CI; otherwise (or in addition) verified manually against the real deployment per quickstart.md and signed off under Principle IX's final acceptance task, since this is platform routing behavior a local dev server (Vite's own dev server has different fallback semantics) cannot fully stand in for.

---

## Guarantee 2 — A valid session is never mistaken for an expired one during page load (FR-007, FR-009, SC-004)

**Mechanism**: `ProtectedRoute.jsx`, reading `useMsal().inProgress`.

**Contract**:
- While `inProgress !== InteractionStatus.None` (MSAL is still starting up / reading its cache / processing a redirect), `ProtectedRoute` MUST render a loading state — it MUST NOT redirect to `/login`.
- Only once `inProgress === InteractionStatus.None` does `ProtectedRoute` evaluate `isAuthenticated`. If `true`, render the protected children (after the existing capability check); if `false`, redirect to `/login` with no "session expired" reason (this is a genuinely unauthenticated visitor, not an expired session).
- A session that MSAL's `localStorage` cache confirms is still valid MUST reach the originally-requested screen without a re-authentication prompt (FR-009).

**Verification**: `ProtectedRoute.test.jsx` covers both `inProgress` states combined with both `isAuthenticated` outcomes (4 cases). An integration test simulates a full reload (remounting the component tree with a pre-populated MSAL mock) and asserts no redirect occurs before initialization completes.

---

## Guarantee 3 — An actually-expired session gets a clear explanation, not a bare error (FR-008)

**Mechanism**: React Router navigation state carried on the redirect to `/login`, read by `LoginScreen` via `useLocation().state` and rendered through its existing `MESSAGES`/`status` pattern (research.md §4).

**Contract**:
- When `useCapabilities` receives a 401 after an interactive sign-in already succeeded once (its existing `REDIRECT_ATTEMPTED_KEY`-guarded path), the user MUST be routed to `/login` with `state: { reason: "session-expired" }` before any automatic re-authentication attempt, rather than being bounced straight to Microsoft's hosted sign-in with no explanation.
- `LoginScreen` MUST add a `sessionExpired` entry to its existing `MESSAGES` map ("Your session ended — please sign in again.") and render it via its existing `status`/`message` state when `location.state?.reason === "session-expired"` on mount; it MUST render exactly as it does today otherwise (a first-time, never-signed-in visitor sees the plain login screen unchanged).

**Verification**: `LoginScreen.test.jsx` (new or extended) asserts both render paths.

---

## Non-goals

- No change to `cacheLocation` or MSAL's token cache mechanism (research.md §1) — the cache was never the defect.
- No offline support or service worker — reload resilience here means "reload while online works correctly," not "the app works with no network."
- No change to `HashRouter`/`BrowserRouter` choice (research.md §2).
