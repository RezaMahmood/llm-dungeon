# Contract: Screen Restyle onto the Modernist Design System

**Feature**: Persistent Navigation & Design Refresh (022-persistent-nav-redesign)

**Status**: Agreed — `specs/designs/{01,02,04,05}.html` are the acceptance reference
per FR-010 and the constitution's Screen Contracts section. This is a UI/behavior
contract; this feature has no HTTP API surface.

## Per-screen contract

| Screen | Route | Mockup | Functional code touched? | Notes |
|---|---|---|---|---|
| Login | `/login` | `01-login.html` | No — `LoginScreen.jsx` already uses `.btn`, `.hr`, `.text-muted`, token spacing (research.md finding) | Confirm/complete alignment only; no `AuthenticatedLayout` (unauthenticated route) |
| Hub / story select | `/menu` | `02-story-select.html` | No — `MainMenu.jsx`'s existing menu-item logic (`GameMenuItem`/`AdminMenuItem`) is unchanged | Remove ad hoc `<h1>`/logout header (now in `NavBar`); retire `MainMenu.css`; body content stays what exists today (real story list is `004-story-creation-done`/future scope, not this feature's) |
| Admin wizard | `/admin/stories/new` | `04-admin-wizard.html` | No — draft fetch/save/autosave, `activeStep` state, per-step validation all unchanged (FR-005, FR-012) | Restyle step-tab row and step content per mockup; `NavBar` replaces the page's own header |
| People (accounts) | `/admin/accounts` | `05-admin-users.html` | No — `AccountForm`/`AccountList`'s data operations and one-at-a-time remove-with-confirmation unchanged (FR-011) | Restyle form/list layout per mockup; `NavBar` replaces the page's own header |
| Story play | `/game` | `03-play.html` (header only) | No — `GamePage.jsx` remains a content placeholder (008-core-gameplay scope) | Only the header changes, from nothing to `TitleBar`; body content is out of scope until 008 lands |
| Admin stories list | `/admin` | *(no dedicated mockup)* | Yes — new, read-only (FR-013) | Not one of FR-010's five named screens, but gets `NavBar` via `AuthenticatedLayout`; fetches `GET /api/manage/stories` on mount (via new `storyService.js`) and renders each story's name + published/draft status using existing token-based list/tag styling, or an empty-state message when there are no stories yet. This is the "Stories" nav destination, distinct from "New story" (FR-002) |

## Behavior contract (applies to every screen above)

1. Every color, font, spacing, radius, and shadow value comes from
   `designTokens.css`'s existing custom properties — no new hex/magic-pixel value is
   introduced anywhere in this restyle (Principle VIII).
2. No screen introduces a new component class duplicating something
   `designTokens.css` already provides (e.g., no screen-local button, input, or card
   reimplementation) — narrowly-scoped layout utilities with no visual opinion of
   their own (matching the mockups' own `.ovnum`/`.rowhov`/`.storyscroll` pattern) are
   the only permitted exception (Principle VIII).
3. No data-fetching, mutation, validation, or capability-check logic changes on any
   of the three functional screens (`MainMenu.jsx`, `AdminStoryWizardPage.jsx`,
   `AdminAccountsPage.jsx`) — every prior passing test for that logic continues to
   pass; only rendering/markup assertions in those tests are expected to change
   (FR-012).
4. `AdminAccountsPage.jsx`'s remove flow still requires per-row confirmation before
   deletion, still one account at a time, no bulk action introduced (FR-011).
5. `AdminStoryWizardPage.jsx`'s wizard progress (saved fields) survives a nav-bar
   click away and back (FR-005, SC-003).

   **Corrected during implementation (2026-08-31)**: this contract originally assumed
   the wizard already had "draft-fetch-on-mount" behavior, so FR-005 would fall out of
   leaving its logic untouched. That assumption was wrong — `AdminStoryWizardPage.jsx`
   called `createDraft` unconditionally on every mount, so navigating away and back
   started a **brand-new blank draft**, stranding work the server had already saved.
   Giving the wizard a nav bar without fixing this would have actively created the data
   loss FR-005/SC-003 forbid.

   The minimal fix: the wizard records the id of the draft it is building in
   `sessionStorage` (`llmdungeon.storyWizard.activeDraftId`) and, on mount, resumes
   that draft via the existing `getDraft` endpoint instead of creating a new one;
   the key is cleared once the draft becomes a generated story, and a missing or
   stale draft falls back to creating a fresh one. No backend change; the wizard's
   step state, validation, patch/autosave and generation logic are otherwise
   untouched, so §3 still holds. Covered by
   `tests/integration/wizard_nav_persistence.test.jsx`.

## Non-goals

- Building the real "story select" list content shown in `02-story-select.html`
  (in-progress/published story rows) — that is `004-story-creation-done`'s scope; this
  feature restyles `MainMenu.jsx`'s current hub content, it does not build a new
  player-facing list. (The admin stories list added at `/admin` per FR-013 is a
  separate, read-only, admin-only view — not the player story-select experience.)
- Adding edit, publish/unpublish, or delete actions to the admin stories list —
  read-only per FR-013; those actions are `005-story-publishing`'s/
  `012-story-editing-and-review`'s scope.
- Building the real story-play experience shown below `03-play.html`'s title bar —
  `008-core-gameplay`'s scope; this feature adds only the title bar.
