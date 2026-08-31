# Quickstart: Validating Persistent Navigation & Design Refresh

## Prerequisites

- `src/frontend/` dependencies installed (`npm install` in `src/frontend/`)
- A signed-in test session with at least three accounts available (or role-switchable
  test fixtures) covering: player-only, administrator-only, and dual-capability
  (see `useCapabilities()`'s `hasPlayer`/`hasAdministrator`)
- **Before running these scenarios**: confirm the Principle XI open item in
  plan.md/Constitution Check has been resolved (Refresh-slot decision) — this affects
  what a reviewer should expect to see in the nav bar's trailing button cluster.

## Automated checks

```bash
cd src/frontend
npm test              # Vitest run — NavBar/TitleBar/AuthenticatedLayout unit tests,
                       # AdminAccountsPage/AdminStoryWizardPage integration tests
                       # re-asserting unchanged functional behavior, and new AdminPage
                       # stories-list tests (see contracts/)
```

Expected: all existing tests for `MainMenu`, `AdminAccountsPage`, `AdminStoryWizardPage`
data behavior still pass (only rendering assertions differ); new `NavBar`/`TitleBar`/
`AuthenticatedLayout` tests pass for every capability combination in
`data-model.md`'s `NavItem` derivation table; new `AdminPage` tests pass for both a
populated and an empty stories list (FR-013).

## Manual validation scenarios

Run `npm run dev` in `src/frontend/` (or use the deployed environment for Principle IX's
final acceptance) and walk through:

1. **FR-013/SC-007 — Admin "Stories" list is a distinct destination from "New story"**
   Sign in as an administrator → click "Stories" in the nav bar → confirm it shows a
   list of existing stories (name + published/draft status), not the wizard, and that
   creating a new story via "New story" is a visibly different screen. With zero
   stories in the environment, confirm an empty-state message renders instead of an
   error.

2. **US1 — Navigate away from an in-progress wizard without losing it**
   Sign in as an administrator → start "New story" → fill in step 1 → click "People" in
   the nav bar → click back into "New story" → confirm step 1's fields are still
   populated and the nav bar is identical to the one on People. (spec Acceptance
   Scenarios 1–3)

3. **US2 — One consistent look across the app**
   Visit `/login`, `/menu`, `/admin/stories/new`, `/admin/accounts` in turn as an
   account with both capabilities; confirm each matches its mockup's typography, color
   tokens, and layout (`contracts/screen-restyle.md`'s table). Confirm
   `AdminAccountsPage`'s add-account form and per-row remove/confirm dialog still work
   exactly as before.

4. **US3 — See only the destinations you're allowed to use**
   Sign in as a player-only account → confirm only "My stories"/"Badges" show, no
   admin links. Sign in as an administrator-only account → confirm "Stories"/"New
   story"/"People"/"Player view" show, no player-only "Badges" link. Sign in as a
   dual-capability account → confirm both "Player view" (from admin nav) and "Admin"
   (from player nav) are present and both navigate correctly.

5. **US4 — Always know where you are**
   Load each of `/menu`, `/admin`, `/admin/stories/new`, `/admin/accounts` in turn;
   confirm exactly one nav item carries the active/`aria-current` styling, matching
   the screen being viewed.

6. **Story-play exception (SC-006)**
   Navigate to `/game`; confirm the full nav bar is replaced by the compact title bar
   (brand mark, story title, return-to-select, pause/exit) and that no primary nav
   links appear there. Compare the story pane's usable height/scroll area against its
   pre-feature size (or against `03-play.html`'s layout proportions) and confirm the
   title bar causes no reduction — this is SC-006's explicit check, not just a visual
   pass.

7. **Edge cases**
   - An account with neither capability sees only the brand mark, sign-out, and their
     name.
   - A very long story title or user display name truncates without breaking the
     bar's layout.
   - Signing out or letting a session expire mid-navigation redirects to `/login` as
     before (unchanged by this feature).
   - The admin stories list shows an empty state, not an error, when no stories exist.

## Final acceptance (Constitution Principle IX)

Per `tasks.md`'s closing acceptance task, the requesting user/product owner — not the
implementing agent — must run scenarios 1–7 above against the real deployed
environment (or the most representative environment available) and confirm the result,
including explicit confirmation of whichever Refresh-slot outcome plan.md's
Constitution Check records for Principle XI.
