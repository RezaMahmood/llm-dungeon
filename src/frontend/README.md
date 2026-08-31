# Frontend — LLM Dungeon Adventure

ReactJS single-page application implementing sign-in (via MSAL / Microsoft
Entra ID) and the capability-based main menu (feature
`002-login-and-access-control`).

## Structure

```
src/frontend/
├── src/
│   ├── components/
│   │   ├── Login/    # LoginScreen, AccessDeniedScreen
│   │   ├── Menu/      # MainMenu, GameMenuItem, AdminMenuItem
│   │   ├── Auth/      # AuthProvider (MSAL context), ProtectedRoute
│   │   └── Common/    # ErrorBoundary
│   │   └── Admin/
│   │       ├── AccountForm.jsx, AccountList.jsx
│   │       └── StoryWizard/  # CharacterTypeList, CompletionCriteriaFields,
│   │                         # Step* (004-story-creation)
│   ├── services/      # msalConfig, authService, tokenInterceptor, accountService,
│   │                  # storyService (004-story-creation)
│   ├── hooks/         # useAuth, useCapabilities
│   ├── pages/         # AdminPage, AdminAccountsPage, AdminStoryWizardPage, GamePage
│   └── styles/        # designTokens.css (vendored from specs/designs/styles.css)
```

## Setup

```bash
npm install
cp .env.example .env   # fill in VITE_AZURE_TENANT_ID, VITE_AZURE_APP_ID, VITE_AZURE_REDIRECT_URI
```

## Running locally

```bash
npm run dev
```

Serves at http://localhost:5173.

## Running tests

```bash
npm test
```

Uses Vitest + React Testing Library; MSAL and network calls are mocked.

## Architecture

- **MSAL** (`@azure/msal-react`) handles the Entra ID sign-in flow (popup) and
  token cache/refresh.
- **AuthProvider** wraps the app in `<MsalProvider>`.
- **useAuth** exposes the signed-in user's identity (oid, email).
- **useCapabilities** calls `GET /api/auth/me` and exposes `hasPlayer` /
  `hasAdministrator`.
- **ProtectedRoute** gates routes on authentication and, optionally, a
  specific capability — server-side enforcement at the destination endpoint
  is still required (see [contracts/ui-menu-states.md](../../specs/002-login-and-access-control-done/contracts/ui-menu-states.md)).

## Story creation wizard (004-story-creation)

`/admin/stories/new` (linked from the Administration/Stories page, `/admin`)
is a four-tab guided wizard — Name & cover, World & setting, Tone & reading
level, Session length, reachable in any order — for creating a new story.

- **Save** is available from any tab at any time and is the only thing that
  writes to the database — there is no automatic/implicit save. The first
  Save creates the story record (name required, everything else optional);
  every later Save updates that same record.
- Field values across all four tabs are held in browser local storage
  (`llmdungeon.storyWizard.draft`) until a Save persists them, so switching
  tabs never loses in-progress work — a purely frontend concern; there is no
  server-side draft resource.
- Tab 01's cover image is a file selected from the administrator's device;
  it uploads to blob storage (via `POST /manage/stories/{storyId}/cover-image`)
  as part of the same Save action once the story has an id.
- Tab 02's "Suggest" action is a single, one-shot call to
  `POST /manage/stories/suggest-outline` that injects a suggested outline
  into the editable outline box — not an ongoing chat.
- **Abandon** (with confirmation) discards the local draft and deletes the
  story record if one was ever saved, then returns to `/admin`. **Finished**
  (with confirmation) leaves whatever was saved alone and also returns to
  `/admin`, which doubles as the stories list.

See [004's contracts/api.md](../../specs/004-story-creation/contracts/api.md)
for the underlying story endpoints `storyService.js` calls.

## Deployment

Deployed to the Azure Static Web App provisioned by
[007-azure-infrastructure-provisioning](../../specs/007-azure-infrastructure-provisioning/spec.md)
via the GitHub Actions workflow, on merge to `main`.

## References

- [contracts/ui-login-screen.md](../../specs/002-login-and-access-control-done/contracts/ui-login-screen.md)
- [contracts/ui-menu-states.md](../../specs/002-login-and-access-control-done/contracts/ui-menu-states.md)
