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
│   │       └── StoryWizard/  # ConversationPanel, CharacterTypeList,
│   │                         # CompletionCriteriaFields, Step* (004-story-creation)
│   ├── services/      # msalConfig, authService, tokenInterceptor, accountService,
│   │                  # storyDraftService (004-story-creation)
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

`/admin/stories/new` (linked from the Administration page) is a four-step
guided wizard — Name & cover, World & setting, Tone & reading level, Session
length, reachable in any order — for creating a new story. The World &
setting step embeds a conversational panel (plain-language idea plus
guiding questions) alongside dedicated character-type and completion-criteria
fields. The wizard has no manual "save" button: once the world prompt, at
least one character type, and at least one completion criterion exist, the
backend generates and persists the story automatically on that same write,
and the page shows the generated (unpublished) result. See
[004's contracts/api.md](../../specs/004-story-creation/contracts/api.md) for
the underlying draft/story endpoints `storyDraftService.js` calls.

## Deployment

Deployed to the Azure Static Web App provisioned by
[007-azure-infrastructure-provisioning](../../specs/007-azure-infrastructure-provisioning/spec.md)
via the GitHub Actions workflow, on merge to `main`.

## References

- [contracts/ui-login-screen.md](../../specs/002-login-and-access-control-done/contracts/ui-login-screen.md)
- [contracts/ui-menu-states.md](../../specs/002-login-and-access-control-done/contracts/ui-menu-states.md)
